# Agentic Workflow Diagram

에이전틱 워크플로우의 개념, 에이전트 구성 요소, 핵심 패턴, 구현 패턴을 종합한 다이어그램입니다.

---

## 전체 구조

에이전틱 워크플로우는 **개념 → 구성 요소 → 핵심 패턴 → 구현 패턴**의 계층 구조로 이루어져 있습니다. 에이전트는 Brain, Planning, Memory, Tools, Action 5개 모듈로 구성되며,
Andrew Ng의 4가지 핵심 패턴(Reflection, Tool Use, Planning, Multi-Agent)을 기반으로 5가지 구현 패턴(Prompt Chaining, Routing,
Parallelization, Orchestrator-Workers, Evaluator-Optimizer)으로 실체화됩니다.

```mermaid
graph TB
    subgraph Foundation["개념 기반"]
        CONCEPT["Agentic AI<br/>자율적 목표 설정 · 환경 상호작용 · 자기 주도 의사결정"]
    end

    subgraph Components["에이전트 구성 요소"]
        BRAIN["🧠 Brain<br/>Foundation Model"]
        PLAN["📋 Planning<br/>작업 분해 · CoT · 재계획"]
        MEM["💾 Memory<br/>단기: 세션 컨텍스트<br/>장기: 벡터 DB · 경험"]
        TOOL["🔧 Tools<br/>검색 · 코드 실행 · API · 파일"]
        ACT["⚡ Action<br/>도구 호출 · 응답 생성 · 상태 변경"]
    end

    subgraph CorePatterns["핵심 패턴 (Andrew Ng)"]
        P1["🔄 Reflection<br/>자기 검토 · 자기 수정"]
        P2["🛠️ Tool Use<br/>외부 도구 활용"]
        P3["📝 Planning<br/>CoT · ToT · ReAct"]
        P4["👥 Multi-Agent<br/>계층형 · P2P · 파이프라인"]
    end

    subgraph ImplPatterns["구현 패턴"]
        I1["Prompt Chaining<br/>순차 호출 + 게이트 검증"]
        I2["Routing<br/>입력 분류 → 전문 핸들러"]
        I3["Parallelization<br/>섹셔닝 · 보팅"]
        I4["Orchestrator-Workers<br/>동적 작업 분배"]
        I5["Evaluator-Optimizer<br/>생성 → 평가 → 피드백 루프"]
    end

    CONCEPT --> BRAIN
    CONCEPT --> PLAN
    CONCEPT --> MEM
    CONCEPT --> TOOL
    CONCEPT --> ACT
    BRAIN --> P1 & P2 & P3 & P4
    P1 --> I5
    P2 --> I1 & I2
    P3 --> I4
    P4 --> I3 & I4
    style Foundation fill: #e8f4f8, stroke: #2196F3
    style Components fill: #fff3e0, stroke: #FF9800
    style CorePatterns fill: #e8f5e9, stroke: #4CAF50
    style ImplPatterns fill: #fce4ec, stroke: #E91E63
```

## 구현 패턴 선택 흐름

작업 특성에 따라 적합한 구현 패턴을 선택하는 의사결정 흐름입니다.

```mermaid
flowchart TD
    START(["작업 분석"]) --> Q1{"고정된 순서로<br/>분해 가능?"}
    Q1 -->|Yes| I1["Prompt Chaining"]
    Q1 -->|No| Q2{"입력 유형별<br/>다른 처리?"}
    Q2 -->|Yes| I2["Routing"]
    Q2 -->|No| Q3{"독립적 하위<br/>작업 존재?"}
    Q3 -->|Yes| I3["Parallelization"]
    Q3 -->|No| Q4{"동적이고<br/>예측 불가?"}
    Q4 -->|Yes| I4["Orchestrator-Workers"]
    Q4 -->|No| I5["Evaluator-Optimizer"]
    style START fill: #fff, stroke: #333
    style I1 fill: #e3f2fd, stroke: #1565C0
    style I2 fill: #e8f5e9, stroke: #2E7D32
    style I3 fill: #fff8e1, stroke: #F9A825
    style I4 fill: #fce4ec, stroke: #C62828
    style I5 fill: #f3e5f5, stroke: #6A1B9A
```
