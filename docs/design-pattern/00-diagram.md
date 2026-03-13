# Design Pattern Diagram

Google Cloud 기반 에이전틱 AI 디자인 패턴 12가지를 분류와 오케스트레이션 방식에 따라 종합한 다이어그램입니다.

---

## 전체 패턴 분류

12가지 패턴은 **단일 에이전트**, **멀티 에이전트(순차)**, **멀티 에이전트(동적 오케스트레이션)**, **반복 워크플로우**, **특수 요구사항** 5개 카테고리로 분류됩니다. 오케스트레이션 방식은 코드
기반, AI 기반, 하이브리드로 나뉩니다.

```mermaid
graph TB
    subgraph Single["단일 에이전트"]
        S1["01. Single Agent<br/>모델 + 도구 + 시스템 프롬프트"]
    end

    subgraph Sequential["멀티 에이전트 · 순차"]
        M1["02. Sequential<br/>선형 파이프라인"]
        M2["03. Parallel<br/>동시 독립 처리"]
        M3["04. Loop<br/>종료 조건까지 반복"]
        M4["05. Review & Critique<br/>생성자 + 비평자"]
        M5["06. Iterative Refinement<br/>주기적 결과 개선"]
    end

    subgraph Dynamic["멀티 에이전트 · 동적 오케스트레이션"]
        D1["07. Coordinator<br/>AI 기반 동적 라우팅"]
        D2["08. Hierarchical<br/>다단계 계층 위임"]
        D3["09. Swarm<br/>전체 에이전트 간 협업"]
    end

    subgraph Iterative["반복 워크플로우"]
        I1["10. ReAct<br/>Think → Act → Observe"]
    end

    subgraph Special["특수 요구사항"]
        SP1["11. Human-in-the-Loop<br/>체크포인트 기반 승인"]
        SP2["12. Custom Logic<br/>코드 기반 조건 분기"]
    end

    S1 -.->|"확장"| M1
    M1 --> M2 & M3
    M3 --> M4 & M5
    M5 -.->|"동적 전환"| D1
    D1 --> D2 --> D3
    I1 -.->|"결합 가능"| D1
    SP1 -.->|"삽입 가능"| M1 & D1
    SP2 -.->|"조합"| M1 & M2 & M3

    style Single fill: #e3f2fd, stroke: #1565C0
    style Sequential fill: #e8f5e9, stroke: #2E7D32
    style Dynamic fill: #fff3e0, stroke: #E65100
    style Iterative fill: #f3e5f5, stroke: #6A1B9A
    style Special fill: #fce4ec, stroke: #C62828
```

## 복잡도·비용·오케스트레이션 비교

패턴 선택 시 복잡도, 비용, 오케스트레이션 방식을 종합적으로 고려해야 합니다.

```mermaid
quadrantChart
    title 복잡도 vs 비용
    x-axis "낮은 비용" --> "높은 비용"
    y-axis "낮은 복잡도" --> "높은 복잡도"
    quadrant-1 "고복잡·고비용"
    quadrant-2 "고복잡·저비용"
    quadrant-3 "저복잡·저비용"
    quadrant-4 "저복잡·고비용"
    Sequential: [0.15, 0.15]
    Parallel: [0.30, 0.20]
    Loop: [0.25, 0.30]
    "Single Agent": [0.35, 0.40]
    "Review-Critique": [0.40, 0.45]
    "Iterative Refine": [0.45, 0.50]
    Coordinator: [0.55, 0.65]
    ReAct: [0.60, 0.70]
    "Human-in-Loop": [0.50, 0.55]
    "Custom Logic": [0.55, 0.50]
    Hierarchical: [0.75, 0.80]
    Swarm: [0.90, 0.95]
```
