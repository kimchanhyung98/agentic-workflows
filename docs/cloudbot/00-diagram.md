# Cloudbot 아키텍처 다이어그램

## 1. 전체 시스템 아키텍처

Cloudbot은 Slack → Linear → In-house Sandbox → MCPs → PR 의 흐름으로 동작합니다.

```mermaid
graph TB
    subgraph L1["진입점 (Entry Points)"]
        SL["💬 Slack\nCloudbot Playground"]
        LI["📋 Linear\n티켓 생성"]
    end

    subgraph L2["컨텍스트 (Context Layer)"]
        LA["Linear Agent\n티켓 파싱 · 분류"]
        MC["MCPs + Custom Skills\nDataDog · Sentry · Amplitude"]
    end

    subgraph L3["실행 환경 (Sandbox)"]
        SB["In-house Sandbox\n완전 격리 · 보안 컴플라이언스"]
    end

    subgraph L4["에이전트 코어 (Agent Core)"]
        MM["멀티 모델 LLM\n모델 비종속 · 상황별 선택"]
        SK["Custom Skills\n내부 도구 통합"]
    end

    subgraph L5["운영 모드 (3 Modes)"]
        M1["🔨 Create PR\nLinear → 코드 → PR"]
        M2["📝 Plan\n계획 작성 → Linear 기록"]
        M3["🔍 Explain\nDataDog/Sentry 분석"]
    end

    subgraph L6["출력 (Output)"]
        PR["✅ Pull Request\nCursor 딥링크 + QR코드"]
        PL["📋 Linear Plan\n인간 검토 대기"]
        EX["📊 디버그 분석\n원인 파악 결과"]
    end

    SL --> LI
    LI --> LA
    LA --> MC
    MC --> SB
    SB --> MM
    MM --> SK
    SK --> M1
    SK --> M2
    SK --> M3
    M1 --> PR
    M2 --> PL
    M3 --> EX

    style L1 fill:#e3f2fd,stroke:#1565C0
    style L2 fill:#e8f5e9,stroke:#2E7D32
    style L3 fill:#fff8e1,stroke:#F9A825
    style L4 fill:#f3e5f5,stroke:#6A1B9A
    style L5 fill:#fce4ec,stroke:#C62828
    style L6 fill:#c8e6c9,stroke:#2E7D32
```

## 2. 3가지 운영 모드

```mermaid
flowchart TD
    INPUT([Slack 요청]) --> LINEAR[Linear 티켓 확인]
    LINEAR --> MODE{운영 모드 선택}

    MODE -->|"cloudbot create pr"| CPR
    MODE -->|"cloudbot plan"| PLAN
    MODE -->|"cloudbot explain"| EXP

    subgraph CPR["🔨 Create PR 모드"]
        CPR1[티켓 컨텍스트 로드] --> CPR2[코드 분석]
        CPR2 --> CPR3[구현 실행]
        CPR3 --> CPR4[PR 생성]
        CPR4 --> CPR5["Cursor 딥링크\n+ QR코드 회신"]
    end

    subgraph PLAN["📝 Plan 모드"]
        PLAN1[티켓 분석] --> PLAN2[구현 계획 수립]
        PLAN2 --> PLAN3[Linear에 계획 기록]
        PLAN3 --> PLAN4[인간 검토 대기]
    end

    subgraph EXP["🔍 Explain 모드"]
        EXP1[DataDog/Sentry 조회] --> EXP2[에러 분석]
        EXP2 --> EXP3[근본 원인 파악]
        EXP3 --> EXP4[디버그 결과 회신]
    end
```

## 3. 컨텍스트 파이프라인 (Linear-first)

Cloudbot의 모든 컨텍스트는 Linear를 단일 진실 공급원(Single Source of Truth)으로 삼습니다.

```mermaid
flowchart LR
    subgraph INPUT["입력 소스"]
        SL["Slack 스레드\n(버그 리포트, 회의록)"]
        GH["GitHub\n(코드, PR, 이슈)"]
    end

    subgraph LINEAR_LAYER["Linear (중심 컨텍스트)"]
        TRIAGE["Linear Agent\n자동 분류 · 티켓 생성"]
        TICKET["티켓\n(제목, 설명, 우선순위)"]
    end

    subgraph MCP_LAYER["MCPs + Custom Skills"]
        DD["DataDog\n성능 메트릭"]
        ST["Sentry\n에러 트래킹"]
        AMP["Amplitude\n사용자 이벤트"]
        GIT["GitHub MCP\n코드 탐색"]
    end

    SL --> TRIAGE
    GH --> TRIAGE
    TRIAGE --> TICKET
    TICKET --> DD
    TICKET --> ST
    TICKET --> AMP
    TICKET --> GIT
    DD & ST & AMP & GIT --> AGENT["Cloudbot\n에이전트 실행"]
```

## 4. 검증 및 병합 파이프라인

```mermaid
flowchart TD
    PR_GEN([PR 생성]) --> COUNCIL

    subgraph COUNCIL["Agent Council (검토)"]
        A1["에이전트 리뷰어 1"]
        A2["에이전트 리뷰어 2"]
        A3["에이전트 리뷰어 N"]
    end

    COUNCIL --> RISK{변경 위험도 평가}

    RISK -->|"낮음\n(텍스트, 설정 등)"| AUTO["🟢 자동 머지\n(Auto-merge)"]
    RISK -->|"중간"| HUMAN_REVIEW["👤 인간 리뷰 요청"]
    RISK -->|"높음\n(결제, 보안 관련)"| STRICT["🔴 엄격한 인간 리뷰\n(컴플라이언스 검토)"]

    AUTO --> MERGED([머지 완료])
    HUMAN_REVIEW --> APPROVED{승인?}
    STRICT --> APPROVED
    APPROVED -->|Yes| MERGED
    APPROVED -->|No| FEEDBACK[피드백 → Cloudbot 재시도]
    FEEDBACK --> PR_GEN
```

## 5. Slack 네이티브 워크플로우

```mermaid
sequenceDiagram
    participant E as 엔지니어
    participant S as Slack
    participant L as Linear
    participant C as Cloudbot
    participant G as GitHub

    E->>S: 버그 리포트 / 회의록 공유
    S->>L: Linear Agent: 티켓 자동 생성
    L-->>E: 👀 티켓 생성 알림
    E->>S: "cloudbot create pr [티켓 ID]"
    S->>C: 요청 전달
    C->>L: 티켓 컨텍스트 로드
    C->>C: MCPs 통해 추가 컨텍스트 수집
    C->>C: In-house Sandbox에서 코드 구현
    C->>G: PR 생성
    C->>S: Cursor 딥링크 + QR코드 회신
    E->>E: QR코드로 모바일 앱 즉시 테스트
```
