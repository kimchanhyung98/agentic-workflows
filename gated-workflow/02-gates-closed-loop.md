# Gate 평가와 Closed-Loop 의사결정

Gate 평가 절차, Retry Budget, on_fail 라우팅, Closed-Loop 의사결정 원칙, 에러 분류 체계입니다.

---

## 1. Gate 평가 절차

Gate는 Phase 실행 결과를 구조화된 규칙으로 평가하는 관문입니다.

### 불변식

- Agent Card에 정의된 `pass_conditions`를 순서대로 평가합니다. **모든 조건이 통과해야** Gate PASS입니다.
- `structured_result_shape` 검증이 실패하면 `pass_conditions`를 평가하지 않고 즉시 Gate FAIL입니다.
- Agent Card가 존재하지 않으면 `shape_only_fallback` 모드로 동작합니다. 구조 검증만 수행하고 도메인 조건은 건너뜁니다.

### 평가 순서

1. Agent Card 로드
2. `structured_result_shape` 검증 (무효 시 즉시 FAIL)
3. `pass_conditions` 순회 (하나라도 실패 시 FAIL)
4. 모든 조건 통과 시 Gate PASS

---

## 2. Retry Budget

각 Phase는 Agent Card에서 최대 재시도 횟수를 정의합니다.
Gate FAIL 시 retries 카운터가 증가하며, 한도를 초과하면 Phase가 abort됩니다.

### Retry 증가 규칙

- Gate FAIL 발생 시 해당 Phase의 retries를 1 증가시킵니다.
- `retries >= retry.max`이면 Phase를 abort합니다.
- abort 시 on_fail 라우팅에 따라 replan 또는 escalate_user로 분기합니다.

### Retry vs Replan

| 구분 | Retry | Replan |
|------|-------|--------|
| 범위 | 같은 Phase에서 재시도 | 이전 Phase로 되돌림 |
| 카운터 | Phase별 `retries` 증가 | 워크플로우 전체 `replanCount` 증가 |
| 상태 변화 | failed → in_progress | 대상 Phase 이후 모두 pending 리셋 |
| 트리거 | Gate FAIL (default 분기) | on_fail의 특정 분기 (critical_found 등) |

### Budget 소진 시 동작

| Budget | 소진 시 |
|--------|---------|
| Phase retry budget | Phase abort → on_fail 라우팅 |
| 워크플로우 replan budget | escalate_user |
| 총 실행 카운터 (MAX=30) | RuntimeError → 워크플로우 중단 |

---

## 3. on_fail 라우팅

Gate FAIL 시 Agent Card의 `on_fail` 섹션에 따라 분기합니다.

### 라우팅 우선순위

1. `failure_context.has_critical == true`이고 `on_fail.critical_found` 존재하면 해당 분기로 이동합니다.
2. 도메인 특화 분기(`high_only`, `scope_violation` 등)가 존재하면 해당 분기를 적용합니다.
3. `on_fail.default`가 존재하면 기본 분기를 적용합니다.
4. 어떤 분기도 매칭되지 않으면 같은 Phase에서 retry합니다(retry budget 확인).

### severity별 기본 라우팅

| severity | 라우팅 |
|----------|--------|
| critical | replan (plan phase로 되돌림) |
| high | prompt_user (사용자 판단 요청) |
| medium | retry (같은 Phase 재시도) |
| low | retry (같은 Phase 재시도) |

---

## 4. Closed-Loop 의사결정

Result Envelope의 status가 `escaped`일 때 자동 규칙 엔진이 다음 행동을 판정합니다.

### 규칙 원칙

- severity와 reason의 조합으로 `continue`, `replan`, `abort`, `escalate_user` 중 하나를 결정합니다.
- replan 결정 시 replan budget을 확인하며, 소진되면 `escalate_user`로 전환합니다.

### 의사결정 규칙 매트릭스

| severity | reason | 결정 | 근거 |
|----------|--------|------|------|
| advisory | (무관) | continue | 참고 사항, 진행에 영향 없음 |
| degraded | quality | continue | 품질 저하이나 기능적 진행 가능 |
| warning | spec_divergence | replan | 명세와의 이탈, 재계획 필요 |
| warning | scope_violation | replan | 허용 범위 초과, 범위 재정의 필요 |
| critical | spec_divergence | replan | 심각한 명세 이탈, 즉시 재계획 |
| critical | constraint_violation | abort | 복구 불가능한 제약 위반 |
| critical | budget_exceeded | abort | 리소스 한도 초과, 진행 불가 |
| (모든) | (규칙 미매칭) | escalate_user | 자동 판정 불가, 사람 판단 필요 |
| (모든) | (replan budget 소진) | escalate_user | 재계획 한도 초과, 사람 개입 필요 |

---

## 5. 에러 분류 체계

Phase 실행 중 발생하는 에러를 7개 유형으로 분류하고, 유형에 맞는 복구 전략을 적용합니다.

### 3계층 독립 동작

| 계층 | 처리 주체 | 대상 | 입력 |
|------|----------|------|------|
| 에러 분류 | 에러 분류 엔진 | Phase 실행 중 예외 | 에러 메시지 문자열 |
| Gate 평가 | Gate 엔진 | Phase 정상 완료 후 | Result Envelope (status=completed) |
| Closed-Loop | 의사결정 규칙 엔진 | Worker escape 후 | escape 메타데이터 (severity, reason) |

### 에러 유형 7종

| 유형 | 설명 | 복구 전략 |
|------|------|----------|
| `tool_error` | 도구 호출 실패 | 재시도 후 fallback 도구 사용 |
| `timeout` | 실행 시간 초과 | 타임아웃 증가 후 재시도 |
| `parse_error` | 출력 파싱 실패 | 프롬프트 조정 후 재시도 |
| `validation_error` | 입력/출력 검증 실패 | 입력 정제 후 재시도 |
| `resource_error` | 리소스 부족 | 리소스 확보 후 재시도 또는 abort |
| `logic_error` | 비즈니스 로직 위반 | replan으로 설계 수정 |
| `unknown_error` | 분류 불가 | escalate_user |

### 처리 순서

1. Phase 실행 중 예외 발생 시 에러 분류 엔진이 유형을 판정합니다.
2. 유형별 복구 전략(retry/fallback/abort)을 적용합니다.
3. Phase 정상 완료 시 Result Envelope의 status를 확인합니다.
4. status=completed이면 Gate 평가를 진행합니다.
5. status=escaped이면 Closed-Loop 의사결정을 적용합니다.
6. status=failed이면 즉시 Gate FAIL로 처리합니다.

---

## 장단점

| 구분 | 내용 |
|------|------|
| 장점 | Phase 간 품질을 Gate로 강제하여 결함 전파를 차단합니다 |
| 장점 | severity * reason 매트릭스로 자동 복구 판정이 가능합니다 |
| 장점 | Retry/Replan/실행 카운터의 3계층 Budget으로 무한 루프를 방지합니다 |
| 장점 | 에러 유형별 복구 전략으로 장애 복원력을 높입니다 |
| 단점 | Gate 조건 설계가 부정확하면 불필요한 반복이 발생합니다 |
| 단점 | Phase 수 증가에 따라 파이프라인 지연 시간이 늘어납니다 |
| 단점 | Agent Card 유지보수 비용이 Phase 수에 비례하여 증가합니다 |

---

## 참고 자료

- [검토-비평 패턴](/design-pattern/05-review-critique.md) — 생성기 + 비평가의 검증 루프
- [루프 패턴](/design-pattern/04-loop.md) — 종료 조건까지 반복 실행
