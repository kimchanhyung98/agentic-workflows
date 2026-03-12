# Effective Agents Diagram

Anthropic의 Building Effective Agents 프레임워크에 기반한 6가지 패턴을 종합한 다이어그램입니다.

---

## 전체 구조

Anthropic 프레임워크는 패턴을 **Workflows**(1~5번, 사전 정의된 코드 경로)와 **Agents**(6번, LLM의 동적 의사결정)로 구분합니다. 단순한 Prompt Chaining에서 완전 자율
에이전트까지, 복잡도와 자율성이 점진적으로 증가하는 스펙트럼을 이룹니다.

```mermaid
graph LR
    subgraph Workflows["Workflows (사전 정의 경로)"]
        direction TB
        W1["01. Prompt Chaining<br/>순차 분해 + 게이트 검증"]
        W2["02. Routing<br/>입력 분류 → 전문 핸들러"]
        W3["03. Parallelization<br/>섹셔닝 · 보팅"]
        W4["04. Orchestrator-Workers<br/>동적 작업 위임 + 결과 종합"]
        W5["05. Evaluator-Optimizer<br/>생성 → 평가 → 피드백 루프"]
    end

    subgraph Agents["Agents (동적 의사결정)"]
        W6["06. Autonomous Agent<br/>ReAct: Reason → Act → Observe"]
    end

    W1 -->|"분기 필요"| W2
    W2 -->|"병렬 처리"| W3
    W3 -->|"동적 조율"| W4
    W4 -->|"품질 반복"| W5
    W5 -->|"완전 자율"| W6

    style Workflows fill: #e8f5e9, stroke: #2E7D32
    style Agents fill: #fff3e0, stroke: #E65100
```

## 패턴 선택 흐름

작업의 예측 가능성, 독립성, 품질 기준 유무에 따라 적합한 패턴을 선택합니다.

```mermaid
flowchart TD
    START(["작업 특성 분석"]) --> Q1{"단순하고<br/>순차적인가?"}
    Q1 -->|"Yes"| P1["Prompt Chaining"]
    Q1 -->|"No"| Q2{"입력 유형에 따라<br/>다른 처리?"}
    Q2 -->|"Yes"| P2["Routing"]
    Q2 -->|"No"| Q3{"독립적 하위 작업<br/>병렬 처리 가능?"}
    Q3 -->|"Yes"| P3["Parallelization"]
    Q3 -->|"No"| Q4{"작업 흐름이<br/>예측 불가?"}
    Q4 -->|"Yes - 구조적"| P4["Orchestrator-Workers"]
    Q4 -->|"No"| Q5{"명확한 품질<br/>기준 존재?"}
    Q5 -->|"Yes"| P5["Evaluator-Optimizer"]
    Q5 -->|"No"| Q6{"개방형 목표<br/>자율 판단 필요?"}
    Q6 -->|"Yes"| P6["Autonomous Agent"]
    Q4 -->|"Yes - 개방형"| P6

    style START fill: #fff, stroke: #333
    style P1 fill: #e3f2fd, stroke: #1565C0
    style P2 fill: #e8f5e9, stroke: #2E7D32
    style P3 fill: #fff8e1, stroke: #F9A825
    style P4 fill: #fce4ec, stroke: #C62828
    style P5 fill: #f3e5f5, stroke: #6A1B9A
    style P6 fill: #fff3e0, stroke: #E65100
```

## 패턴별 핵심 메커니즘

각 패턴의 내부 동작 원리를 요약한 다이어그램입니다.

```mermaid
graph TB
    subgraph PC["Prompt Chaining"]
        pc1["Step 1"] -->|"output"| pc_gate{"Gate"} -->|"pass"| pc2["Step 2"] -->|"output"| pc3["Step 3"]
    end

    subgraph RT["Routing"]
        rt_in["Input"] --> rt_cls["Classifier"] --> rt_a["Handler A"] & rt_b["Handler B"] & rt_c["Handler C"]
    end

    subgraph PL["Parallelization"]
        pl_in["Task"] --> pl_a["Agent A"] & pl_b["Agent B"] & pl_c["Agent C"]
        pl_a & pl_b & pl_c --> pl_agg["Aggregator"]
    end

    subgraph OW["Orchestrator-Workers"]
        ow_orc["Orchestrator"] -->|"위임"| ow_w1["Worker 1"] & ow_w2["Worker 2"]
        ow_w1 & ow_w2 -->|"결과"| ow_orc
    end

    subgraph EO["Evaluator-Optimizer"]
        eo_gen["Generator"] --> eo_out["Output"] --> eo_eval["Evaluator"]
        eo_eval -->|"❌ 피드백"| eo_gen
        eo_eval -->|"✅ 통과"| eo_final["Final"]
    end

    subgraph AA["Autonomous Agent"]
        aa_reason["Reason"] --> aa_act["Act"] --> aa_obs["Observe"]
        aa_obs --> aa_reason
    end

    style PC fill: #e3f2fd, stroke: #1565C0
    style RT fill: #e8f5e9, stroke: #2E7D32
    style PL fill: #fff8e1, stroke: #F9A825
    style OW fill: #fce4ec, stroke: #C62828
    style EO fill: #f3e5f5, stroke: #6A1B9A
    style AA fill: #fff3e0, stroke: #E65100
```
