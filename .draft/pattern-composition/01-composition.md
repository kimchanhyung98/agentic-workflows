# 패턴 조합 사례

개별 패턴을 결합하여 더 큰 시스템을 구성한 3가지 사례입니다.
각 사례는 단일 프로덕션 시스템에서 일반화한 것이며, base 패턴은 이 레포의 [설계 패턴](/design-pattern/README.md) 문서를 참조합니다.

---

## 사례 1: 게이트 워크플로우

4가지 base 패턴을 결합하여 Phase 간 Gate가 있는 워크플로우를 구성합니다.

### 구성 패턴과 역할

| base 패턴 | 역할 |
|-----------|------|
| [순차 패턴](/design-pattern/02-sequential.md) | Phase를 고정 순서로 연결 (plan → review → approve → impl → verify → test → done) |
| [검토-비평 패턴](/design-pattern/05-review-critique.md) | 각 Phase 결과를 Gate가 평가하여 통과/실패 판정 |
| [인간 참여형 패턴](/design-pattern/11-human-in-the-loop.md) | 승인(approve) Phase에서 사람의 최종 판단을 요구 |
| [반복 개선 패턴](/design-pattern/06-iterative-refinement.md) | Gate 실패 시 같은 Phase를 재시도하거나 이전 Phase로 되돌림 |

### 개별 패턴만으로 부족한 것

- **순차 패턴**은 실패 시 재시도를 정의하지 않습니다. Phase가 실패하면 파이프라인이 멈춥니다.
- **검토-비평 패턴**은 생성-비평 사이클을 설명하지만, 비평 실패 시 "어디로 돌아갈지"를 정의하지 않습니다.
- **인간 참여형 패턴**은 체크포인트와 에스컬레이션을 다루지만, 이 레포의 base 문서는 자동 판정과 인간 판정의 구체적 전환 규칙(severity 임계값, 변경 등급별 정책)까지는 명시하지 않습니다.

### 조합으로 필요해진 것

1. **Agent Card** — Phase별 입출력 계약, Gate 통과 조건, 재시도 예산을 JSON으로 정의 ([상세](/pattern-composition/02-contracts.md))
2. **Result Envelope** — Worker가 정상 완료/이탈/실패 중 어느 상태인지 표준 스키마로 전달
3. **State Schema** — Gate 결과와 Phase 재시도 횟수를 외부화하여 세션 재개와 Provider 교체를 지원
4. **Closed-Loop 판정** — severity와 reason 조합으로 continue/replan/abort/escalate를 자동 결정
5. **전역 실행 제한** — 전체 Phase 실행 횟수 상한으로 무한 루프 방지

이 중 1, 2, 3은 base 패턴 문서에 정의되지 않은 계약입니다.

---

## 사례 2: 분석 파이프라인

3가지 base 패턴을 결합하여 코드 분석 파이프라인을 구성합니다.

### 구성 패턴과 역할

| base 패턴 | 역할 |
|-----------|------|
| [순차 패턴](/design-pattern/02-sequential.md) | 4개 Layer를 고정 순서로 실행 (Input → Bundle → Analyze → Output) |
| [병렬 패턴](/design-pattern/03-parallel.md) | Analyze Layer에서 다중 Writer를 병렬 실행 |
| [계층적 분해 패턴](/design-pattern/08-hierarchical.md) | 전체 분석을 파일별 → 단위별 → 교차검증으로 단계 분해 |

### 개별 패턴만으로 부족한 것

- **순차 패턴**은 중간 단계 실패 시 처음부터 재실행해야 합니다. 대규모 분석에서는 비용이 급증합니다.
- **병렬 패턴**은 병렬 결과를 병합하는 방법을 정의하지 않습니다. 두 Writer가 모순되는 결과를 내면 어떻게 합니까?
- **계층적 분해 패턴**은 분해 구조를 설명하지만, 하위 단계 결과를 상위로 합성하는 규칙을 정의하지 않습니다.

### 조합으로 필요해진 것

1. **관찰/판단 분리** — Layer 2(사실 수집)와 Layer 3(평가)를 구조적으로 격리하여 확증 편향 방지
2. **Writer/Judge 패턴** — 다중 Writer 결과를 Judge가 claim 단위로 병합. Judge는 새로운 claim을 생성하지 못하고, 기존 claim만 선별/병합
3. **점진적 재개** — 해시 기반 변경 감지로 마지막 완료 Stage부터 재개. 전체 재실행 방지
4. **State Schema** — 분석 진행 상태를 파일로 외부화하여 세션 재개와 동시성 제어

---

## 사례 3: 멀티에이전트 Judge

3가지 base 패턴을 결합하여 다중 에이전트 판정 시스템을 구성합니다.

### 구성 패턴과 역할

| base 패턴 | 역할 |
|-----------|------|
| [병렬 패턴](/design-pattern/03-parallel.md) | cross 모드에서 2개 에이전트를 병렬로 독립 실행 |
| [코디네이터 패턴](/design-pattern/07-coordinator.md) | 오케스트레이터가 위험도에 따라 5가지 모드 중 하나를 동적 선택 |
| [맞춤 로직 패턴](/design-pattern/12-custom-logic.md) | 결정론적 Judge Rules로 에이전트 결과를 PASS/FAIL 판정 |

### 개별 패턴만으로 부족한 것

- **병렬 패턴**은 독립 실행을 다루지만, 결과가 모순될 때의 판정 규칙을 정의하지 않습니다.
- **코디네이터 패턴**은 동적 라우팅을 설명하지만, 라우팅된 모드가 실패했을 때의 강등/승격 경로를 정의하지 않습니다.
- **맞춤 로직 패턴**은 코드 기반 분기를 허용하지만, 어떤 규칙 순서가 결정론적인지 제시하지 않습니다.

### 조합으로 필요해진 것

1. **5단계 결정론적 Judge** — 순서가 있는 규칙 체인 (CRITICAL→FAIL, MAJOR≥2→FAIL, 불일치→FAIL, 비대칭 신뢰, 합의→PASS)
2. **에스컬레이션 체인** — 고급 모드 실패 시 중간 단계로 강등 (critical → cross → precise → solo)
3. **자동 승격/강등** — 프롬프트의 위험 키워드로 모드를 자동 조정
4. **Timeout Budget 상속** — 순차 체인에서 누적 경과 시간을 추적하여 후속 단계 timeout 조정

---

## 조합 패턴 비교

| 속성 | 게이트 워크플로우 | 분석 파이프라인 | 멀티에이전트 Judge |
|------|-----------------|---------------|------------------|
| base 패턴 수 | 4 | 3 | 3 |
| 추가 계약 수 | 3 (Agent Card, Envelope, State) | 2 (Writer/Judge, State) | 2 (Judge Rules, Escalation) |
| 발견된 실패 유형 | 10 | 8 | 9 |
| 핵심 추가 요소 | Closed-Loop 자동 판정 | 관찰/판단 분리 | 결정론적 Judge |

---

## 참고 자료

- [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md) — base 패턴 정의
- [조합 계약 상세](/pattern-composition/02-contracts.md) — Agent Card, Result Envelope, State Schema
- [실패 분류](/pattern-composition/03-failure-taxonomy.md) — 조합에서 발생한 실패 유형
