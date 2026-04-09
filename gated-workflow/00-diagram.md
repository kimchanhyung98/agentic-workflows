# 게이트 기반 워크플로우 다이어그램

게이트 기반 워크플로우의 구조와 흐름을 시각화한 다이어그램입니다.

---

## 1. Phase 파이프라인 (Gate 포함)

7개 Phase가 정방향으로 진행되며, 각 Phase 사이에 Gate가 존재합니다.
Gate FAIL 시 on_fail 라우팅에 따라 retry 또는 replan으로 분기합니다.

```mermaid
flowchart TD
    PLAN["Phase 1: plan"] --> G1{"Gate G1"}
    G1 -->|PASS| REVIEW["Phase 2: review"]
    G1 -->|FAIL| PLAN
    REVIEW --> G2{"Gate G2"}
    G2 -->|PASS| APPROVE["Phase 3: approve"]
    G2 -->|"FAIL: CRITICAL"| PLAN
    APPROVE --> G3{"Gate G3"}
    G3 -->|PASS| IMPL["Phase 4: impl"]
    G3 -->|FAIL| PLAN
    IMPL --> G4{"Gate G4"}
    G4 -->|PASS| VERIFY["Phase 5: verify"]
    G4 -->|FAIL| IMPL
    VERIFY --> G5{"Gate G5"}
    G5 -->|PASS| TEST["Phase 6: test"]
    G5 -->|FAIL| IMPL
    TEST --> G6{"Gate G6"}
    G6 -->|PASS| DONE["Phase 7: done"]
    G6 -->|FAIL| IMPL

    style PLAN fill:#fce4ec,stroke:#E91E63
    style REVIEW fill:#fce4ec,stroke:#E91E63
    style APPROVE fill:#fce4ec,stroke:#E91E63
    style IMPL fill:#fce4ec,stroke:#E91E63
    style VERIFY fill:#fce4ec,stroke:#E91E63
    style TEST fill:#fce4ec,stroke:#E91E63
    style DONE fill:#fce4ec,stroke:#E91E63
    style G1 fill:#e8f4f8,stroke:#2196F3
    style G2 fill:#e8f4f8,stroke:#2196F3
    style G3 fill:#e8f4f8,stroke:#2196F3
    style G4 fill:#e8f4f8,stroke:#2196F3
    style G5 fill:#e8f4f8,stroke:#2196F3
    style G6 fill:#e8f4f8,stroke:#2196F3
```

**범례**:
- 분홍색: Phase (실행 단계)
- 파란색: Gate (통과 조건 평가)

---

## 2. Phase 상태 머신

하나의 Phase가 거치는 상태 전이입니다.

```mermaid
stateDiagram-v2
    [*] --> pending: 워크플로우 초기화

    pending --> in_progress: Phase 시작

    in_progress --> completed: Gate PASS
    in_progress --> escaped: Worker가 escape 반환
    in_progress --> failed: Gate FAIL

    escaped --> deciding: severity * reason 규칙 평가

    deciding --> in_progress: continue (같은 Phase 재시도)
    deciding --> pending: replan (대상 Phase로 리셋)
    deciding --> aborted: abort (제약 위반)
    deciding --> escalated: escalate_user (규칙 미매칭)

    failed --> in_progress: retry (budget 내)
    failed --> aborted: retry budget 소진
    failed --> pending: on_fail replan

    completed --> [*]: 다음 Phase로 진행
    aborted --> [*]: 워크플로우 중단
    escalated --> [*]: 사용자 판단 대기
```

### 상태 정의

| 상태 | 설명 | 전이 조건 |
|------|------|----------|
| `pending` | 실행 대기 | 초기화 또는 replan 리셋 |
| `in_progress` | 실행 중 | Phase 시작 |
| `completed` | 정상 완료 | Gate PASS |
| `escaped` | Worker가 완료 불가 보고 | Result Envelope status=escaped |
| `failed` | Gate 실패 | Gate FAIL |
| `deciding` | 자동 규칙 평가 중 | escape 후 severity*reason 매칭 |
| `aborted` | 워크플로우 중단 | 제약 위반 또는 retry budget 소진 |
| `escalated` | 사람에게 위임 | 규칙 미매칭 또는 replan budget 소진 |

---

## 3. Closed-Loop 의사결정 트리

Result Envelope 수신 후 자동 판정 규칙을 적용하는 흐름입니다.

```mermaid
flowchart LR
    ENVELOPE["Result Envelope 수신"] --> STATUS{"status 확인"}

    STATUS -->|completed| COMPLETED["Gate 평가 진행"]
    STATUS -->|escaped| ESCAPED["escape 메타데이터 추출"]
    STATUS -->|failed| FAILED["즉시 Gate FAIL"]

    ESCAPED --> JUDGE{"severity * reason 평가"}

    JUDGE -->|"advisory 또는 degraded+quality"| CONTINUE["continue"]
    JUDGE -->|"spec_divergence 또는 scope 이탈"| REPLAN["replan"]
    JUDGE -->|"constraint_violation"| ABORT["abort"]
    JUDGE -->|"규칙 미매칭 또는 budget 소진"| ESCALATE["escalate_user"]

    style STATUS fill:#fff8e1,stroke:#F9A825
    style JUDGE fill:#fff8e1,stroke:#F9A825
    style CONTINUE fill:#e8f4f8,stroke:#2196F3
    style REPLAN fill:#fff8e1,stroke:#F9A825
    style ABORT fill:#fce4ec,stroke:#E91E63
    style ESCALATE fill:#fce4ec,stroke:#E91E63
```

---

## 4. Gate 평가 흐름

Agent Card를 기반으로 Gate 통과 여부를 판정하는 절차입니다.

```mermaid
flowchart TD
    LOAD["1. Agent Card 로드"] --> EXISTS{"Agent Card 존재?"}

    EXISTS -->|예| SHAPE["2. structured_result_shape 검증"]
    EXISTS -->|아니오| FALLBACK["shape_only_fallback"]
    FALLBACK --> VALID

    SHAPE --> VALID{"shape 유효?"}

    VALID -->|유효| CONDITIONS["3. pass_conditions 순회"]
    VALID -->|무효| FAIL["Gate FAIL"]

    CONDITIONS --> ALL_PASS{"모든 조건 통과?"}

    ALL_PASS -->|모두 통과| PASS["Gate PASS"]
    ALL_PASS -->|하나라도 실패| FAIL

    style LOAD fill:#fce4ec,stroke:#E91E63
    style SHAPE fill:#fce4ec,stroke:#E91E63
    style CONDITIONS fill:#fce4ec,stroke:#E91E63
    style EXISTS fill:#fff8e1,stroke:#F9A825
    style VALID fill:#fff8e1,stroke:#F9A825
    style ALL_PASS fill:#fff8e1,stroke:#F9A825
    style PASS fill:#e8f4f8,stroke:#2196F3
    style FAIL fill:#fce4ec,stroke:#E91E63
    style FALLBACK fill:#e8f4f8,stroke:#2196F3
```

---

## 참고 자료

- [검토-비평 패턴](/design-pattern/05-review-critique.md) — 생성기 + 비평가의 검증 루프
- [루프 패턴](/design-pattern/04-loop.md) — 종료 조건까지 반복 실행
