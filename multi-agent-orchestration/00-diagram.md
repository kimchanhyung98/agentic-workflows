# 다중 에이전트 오케스트레이션 다이어그램

---

## 1. 5-Mode 실행 의사결정

입력된 작업의 위험도와 명시적 지정에 따라 실행 모드를 결정합니다.

```mermaid
flowchart LR
    START(["작업 입력"]) --> EXPLICIT{"명시적 모드\n지정?"}
    EXPLICIT -->|Yes| USE["지정된 모드 사용"]
    EXPLICIT -->|No| RISK{"위험도 평가"}

    RISK -->|낮음| SOLO["solo\n단독 실행"]
    RISK -->|읽기 전용| QUICK["quick\n빠른 분석"]
    RISK -->|중간| PRECISE["precise\n순차 검증"]
    RISK -->|보안 키워드| CROSS["cross\n병렬 교차"]
    RISK -->|프로덕션 키워드| CRITICAL["critical\n순차 체인"]

    USE --> EXEC(["모드 실행"])
    SOLO --> EXEC
    QUICK --> EXEC
    PRECISE --> EXEC
    CROSS --> EXEC
    CRITICAL --> EXEC

    style SOLO fill:#f3e5f5,stroke:#6A1B9A
    style QUICK fill:#f3e5f5,stroke:#6A1B9A
    style PRECISE fill:#f3e5f5,stroke:#6A1B9A
    style CROSS fill:#f3e5f5,stroke:#6A1B9A
    style CRITICAL fill:#f3e5f5,stroke:#6A1B9A
```

---

## 2. Cross Mode -- 병렬 실행 흐름

두 에이전트가 독립적으로 병렬 분석하고, Judge가 결과를 종합 판정합니다.

```mermaid
graph TB
    PROMPT["프롬프트"]

    subgraph parallel["병렬 실행"]
        direction LR
        AGENT_A["Agent A\n(Protocol: speed)"]
        AGENT_B["Agent B\n(Protocol: precision)"]
    end

    PROMPT --> AGENT_A
    PROMPT --> AGENT_B
    AGENT_A --> COLLECT["결과 수집 + 결정론적 정렬"]
    AGENT_B --> COLLECT
    COLLECT --> DEDUP["Finding 중복 제거\n(category + location)"]
    DEDUP --> JUDGE{"Judge Rules\n5단계 판정"}
    JUDGE -->|PASS| PASS_RESULT["PASS"]
    JUDGE -->|FAIL| FAIL_RESULT["FAIL + 피드백"]

    style JUDGE fill:#e8f5e9,stroke:#2E7D32
    style PASS_RESULT fill:#69db7c,color:#fff
    style FAIL_RESULT fill:#ff6b6b,color:#fff
    style AGENT_A fill:#fff3e0,stroke:#FF9800
    style AGENT_B fill:#fff3e0,stroke:#FF9800
```

---

## 3. Critical Mode -- 순차 체인 흐름

각 단계의 결과가 다음 단계의 입력에 누적되는 순차 실행입니다. 가장 높은 신뢰도를 제공합니다.

```mermaid
graph TB
    PROMPT["프롬프트"]
    PROMPT --> STEP1["Step 1: Agent A\n(Protocol: speed)"]
    STEP1 -->|result_A| STEP2["Step 2: Agent B\n(prompt + result_A)\n(Protocol: precision)"]
    STEP2 -->|result_B| STEP3["Step 3: Primary\n(prompt + result_A + result_B)\n(Protocol: plan_conformance)"]
    STEP3 --> JUDGE{"Judge Rules\n5단계 판정"}
    JUDGE -->|PASS| DONE["PASS"]
    JUDGE -->|FAIL| FALLBACK["FAIL → 강등/재시도"]

    style JUDGE fill:#e8f5e9,stroke:#2E7D32
    style STEP1 fill:#fff3e0,stroke:#FF9800
    style STEP2 fill:#fff3e0,stroke:#FF9800
    style STEP3 fill:#fff3e0,stroke:#FF9800
    style DONE fill:#69db7c,color:#fff
    style FALLBACK fill:#ff6b6b,color:#fff
```

---

## 4. 자동 승격/강등 상태

Policy 기반으로 승격(escalation)하고, 에이전트 실패 시 강등(de-escalation)합니다.

```mermaid
stateDiagram-v2
    [*] --> solo: 기본 모드

    solo --> cross: 보안 관련 키워드 감지
    solo --> critical: 프로덕션 관련 키워드 감지
    cross --> critical: 추가 위험 요소 감지

    state "Fallback Chain (강등)" as fallback {
        critical --> cross: Agent 실패
        cross --> precise: 병렬 Agent 실패
        precise --> solo: 보조 Agent 실패
    }

    solo --> [*]: 작업 완료

    note right of solo
        저위험 키워드 감지 시
        상위 모드에서 자동 강등
    end note
```

---

## 참고 자료

- [개념 개요](/multi-agent-orchestration/01-overview.md) -- 5가지 실행 모드 상세
- [Judge Rules](/multi-agent-orchestration/02-judge-rules.md) -- 결정론적 판정 로직
- [Provider Routing](/multi-agent-orchestration/03-provider-routing.md) -- Fallback 체인, Timeout Budget
