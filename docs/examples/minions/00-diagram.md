# Stripe Minions Diagram

Stripe의 프로덕션 AI 코딩 에이전트 시스템 Minions의 6계층 아키텍처와 실행 파이프라인을 종합한 다이어그램입니다.

---

## 6계층 아키텍처

Minions는 **Entry Points → Context Hydration → Devbox → Agent Core → Feedback Loop → Output(PR)** 6개 계층으로 구성됩니다. Stripe의
기존 개발 인프라(CI/CD, 린터, MCP)를 최대한 재활용하며, 에이전트가 아닌 하네스(harness) 설계에 투자하는 것이 핵심 철학입니다.

```mermaid
graph TB
    subgraph L1["Layer 1: Entry Points"]
        EP1["💬 Slack<br/>@minion"]
        EP2["⌨️ CLI"]
        EP3["🌐 Web UI"]
        EP4["🔄 CI Auto-Ticket"]
    end

    subgraph L2["Layer 2: Context Hydration (MCP)"]
        LR["Link Resolver<br/>URL → 컨텍스트"]
        PS["Prompt Scanner<br/>패턴 감지"]
        CB["Context Builder<br/>컨텍스트 조합"]
        TS["Toolshed MCP<br/>400+ → 15개 큐레이션"]
    end

    subgraph L3["Layer 3: Devbox"]
        DB["격리된 VM<br/>코드 · 서비스 사전 로드<br/>인터넷 차단 · Prod 접근 불가<br/>10초 스핀업"]
    end

    subgraph L4["Layer 4: Agent Core (Goose Fork)"]
        THINK["🧠 Think<br/>(LLM)"]
        WRITE["✏️ Write Code<br/>(LLM)"]
        LINT["🔍 Linter<br/>(Gate)"]
        GIT["📦 Git Commit<br/>(Gate)"]
        TEST["🧪 Tests<br/>(Gate)"]
        REVIEW["📋 Review<br/>(LLM)"]
    end

    subgraph L5["Layer 5: Feedback Loop (3-Tier)"]
        T1["Tier 1: Local Lint<br/>< 5초"]
        T2["Tier 2: CI Selective Tests<br/>100만+ 중 선별"]
        T3["Tier 3: Agent Self-Fix<br/>최대 2회"]
    end

    subgraph L6["Layer 6: Output"]
        PR["✅ Pull Request<br/>CI 통과 · 린터 클린<br/>PR 템플릿 작성 완료"]
    end

    EP1 & EP2 & EP3 & EP4 --> LR
    LR --> PS --> CB
    CB --> TS
    TS --> DB
    DB --> THINK --> WRITE --> LINT --> GIT --> TEST --> REVIEW
    REVIEW --> T1 --> T2
    T2 -->|" 실패 "| T3 -->|" 재시도 "| THINK
    T2 -->|" 통과 "| PR
    style L1 fill: #e3f2fd, stroke: #1565C0
    style L2 fill: #e8f5e9, stroke: #2E7D32
    style L3 fill: #fff8e1, stroke: #F9A825
    style L4 fill: #f3e5f5, stroke: #6A1B9A
    style L5 fill: #fce4ec, stroke: #C62828
    style L6 fill: #c8e6c9, stroke: #2E7D32
```

## 3대 설계 원칙

Minions의 핵심 설계 철학인 3가지 원칙을 요약합니다. 에이전트 자체보다 에이전트를 둘러싼 **하네스**(harness) — CI/CD, 린터, MCP, 격리 환경 — 에 투자하는 것이 성공의 열쇠입니다.

```mermaid
graph LR
    P1["🔧 CI/CD & Dev Tooling 마스터<br/>기존 인프라를 에이전트의 가드레일로 활용"]
    P2["🔌 MCP 학습<br/>400+ 도구를 15개로 큐레이션<br/>컨텍스트 하이드레이션 자동화"]
    P3["🏗️ 시스템 설계 투자<br/>에이전트가 아닌 하네스에 투자<br/>격리 · 안전 · 피드백 루프"]
    P1 --- P2 --- P3
    style P1 fill: #e3f2fd, stroke: #1565C0
    style P2 fill: #e8f5e9, stroke: #2E7D32
    style P3 fill: #fff3e0, stroke: #E65100
```
