# 게이트 기반 워크플로우 개요

게이트 기반 N-Phase 워크플로우 파이프라인의 핵심 설계 원칙과 구조입니다.

---

## 1. 7-Phase 구조

워크플로우는 canonical phase order를 따릅니다.

- 정방향 phase order는 `plan → review → approve → impl → verify → test → done`입니다.
- 역행은 replan으로만 가능합니다.
- Policy에 의해 phase가 skip될 수 있습니다.
- Skip된 phase는 downstream precondition을 보장하도록 equivalent gate satisfaction을 남깁니다.

### Phase-Gate 매핑

| Phase | Gate | 역할 | 협업 패턴 |
|-------|------|------|----------|
| plan | G1 | 요구사항 분석, 기술 설계, 작업 분해 | 에이전트 팀 (spec-kit 루틴) |
| review | G2 | 교차 검증 (설계/보안/품질 관점) | 서브에이전트 |
| approve | G3 | 범위와 계획 승인 | HIL 조건부 |
| impl | G4 | 작업 목록 기반 구현 실행 | 서브에이전트 |
| verify | G5 | 범위 검증 + 명세 준수 확인 | 서브에이전트 |
| test | G6 | 회귀 테스트 + 수락 테스트 실행 | 에이전트 팀 (QA) |
| done | -- | 최종 확인 + 산출물 생성 | HIL 조건부 |

### Plan Phase -- Spec-Kit 루틴

plan phase는 에이전트 팀을 활용하여 기획서를 구조화합니다.
에이전트들이 서로 다른 관점에서 spec을 검토하고 반박합니다.

| 산출물 | 역할 |
|--------|------|
| constitution | 프로젝트 불변 규칙 |
| spec | 요구사항 명세 |
| plan | 기술 설계 + 작업 분해 |
| tasks | 구현 작업 목록 |
| test criteria | 수락 기준 |

### Test Phase -- QA 에이전트 팀

test phase는 에이전트 팀을 활용하여 엣지/코너 케이스를 탐색합니다.

- happy path 검증 에이전트와 적극적 파괴 시도 에이전트를 병렬로 운영합니다.
- 경쟁 가설 구조로, 한쪽이 "통과"를 주장하면 다른 쪽이 깨뜨리려 시도합니다.
- 단일 에이전트의 확증 편향을 방지하여 테스트 커버리지를 높입니다.

---

## 2. Agent Card

Agent Card는 Phase별 런타임 계약입니다.
Phase가 무엇을 입력으로 받고, 무엇을 출력하며, 어떤 조건에서 통과/실패하는지를 정의합니다.

### 핵심 계약 요소

| 요소 | 역할 |
|------|------|
| `input.required_artifacts` | Phase 실행에 필수인 입력 산출물 |
| `input.required_state` | 선행 Gate 통과 전제조건 |
| `output.structured_result` | Gate 평가에 사용할 구조화된 결과 스키마 |
| `gate.pass_conditions` | Gate 통과 조건 목록 (모두 AND) |
| `gate.on_pass` / `gate.on_fail` | Gate 결과에 따른 라우팅 |
| `retry.max` | Phase별 최대 재시도 횟수 |
| `hil` | Human-in-the-Loop 필수 여부 |

### JSON 계약 예시

```json
{
  "phase": "review",
  "input": {
    "required_artifacts": ["spec", "plan", "tasks"],
    "required_state": { "G1": "passed" }
  },
  "output": {
    "structured_result": {
      "findings": "array",
      "severity_counts": "object",
      "recommendation": "string"
    }
  },
  "gate": {
    "pass_conditions": [
      "findings.critical_count == 0",
      "findings.high_count <= threshold"
    ],
    "on_pass": { "next": "approve" },
    "on_fail": {
      "critical_found": { "action": "replan", "target": "plan" },
      "default": { "action": "retry" }
    }
  },
  "retry": { "max": 2 },
  "hil": false
}
```

---

## 3. Result Envelope

모든 Phase 실행 결과는 Result Envelope 형식으로 반환됩니다.

### status 정의

| status | 의미 | 후속 처리 |
|--------|------|----------|
| `completed` | Worker가 정상 완료 반환 | Gate 평가 (pass_conditions 확인) |
| `escaped` | Worker가 정상 완료 불가 보고 | escape 메타데이터 기록 후 자동 규칙 엔진으로 판정 |
| `failed` | Worker 실행 자체 실패 | 즉시 Gate FAIL 처리 |

### escape severity

| severity | 의미 |
|----------|------|
| `advisory` | 참고 수준, 진행에 영향 없음 |
| `degraded` | 품질 저하이나 기능적 진행 가능 |
| `warning` | 명세 이탈 등 주의 필요 |
| `critical` | 복구 불가, 즉각 조치 필요 |

---

## 4. 상태 외부화

모든 워크플로우 상태는 파일 시스템에 JSON으로 외부화합니다.
LLM 컨텍스트 윈도우에 의존하지 않으며, 세션 간 상태를 유지합니다.

### 상태 디렉토리 구조

```
.workflow/
├── state.json          # 워크플로우 전체 상태
├── artifacts/          # Phase별 산출물
│   ├── plan/
│   ├── review/
│   └── ...
└── history/            # 실행 이력
```

### state.json 핵심 필드

```json
{
  "workflowId": "uuid",
  "changeClass": "standard",
  "currentPhase": "impl",
  "totalExecutions": 12,
  "replanCount": 1,
  "phases": {
    "plan": { "status": "completed", "retries": 0 },
    "review": { "status": "completed", "retries": 1 },
    "approve": { "status": "completed", "retries": 0 },
    "impl": { "status": "in_progress", "retries": 0 }
  },
  "gates": {
    "G1": "passed",
    "G2": "passed",
    "G3": "passed"
  }
}
```

---

## 5. 실행 카운터

무한 루프를 방지하기 위한 안전장치입니다.
워크플로우 전체에 걸친 총 실행 횟수 상한(MAX=30)을 적용합니다.

### Budget 계층

| Budget 유형 | 범위 | 소진 시 동작 |
|-------------|------|-------------|
| 실행 카운터 (`totalExecutions`) | 워크플로우 전체 (MAX=30) | RuntimeError로 워크플로우 중단 |
| Retry budget (`retry.max`) | Phase별 | Phase abort |
| Replan budget (`maxReplans`) | 워크플로우 전체 | escalate_user |

세 가지 Budget이 계층적으로 동작합니다.
Phase별 retry budget이 먼저 소진되면 해당 Phase가 abort됩니다.
Replan budget이 소진되면 사용자에게 위임됩니다.
총 실행 횟수가 30에 도달하면 워크플로우 전체가 중단됩니다.

---

## 참고 자료

- [검토-비평 패턴](/design-pattern/05-review-critique.md) — 생성기 + 비평가의 검증 루프
- [인간 참여형 패턴](/design-pattern/11-human-in-the-loop.md) — 워크플로에 인간 개입 체크포인트 통합
