# A2A 아키텍처 다이어그램

## 1. Discovery와 Agent Card

```mermaid
sequenceDiagram
    participant C as Client Agent
    participant D as /.well-known/agent-card.json
    participant R as Remote Agent

    C->>D: Agent Card 조회 (GET)
    D-->>C: id, name, skills, capabilities, securitySchemes, supportedInterfaces
    C->>C: 지원 기능/인증 방식/전송 프로토콜 확인
    opt Agent Card 서명 검증
        C->>C: JWS(RFC 7515) + JSON Canonicalization(RFC 8785) 서명 검증
    end
    C->>R: JSON-RPC 또는 gRPC 요청 준비
    R-->>C: A2A 호출 가능
```

## 2. SendMessage vs SendStreamingMessage

```mermaid
flowchart LR
    C["Client Agent"] --> CH{"호출 방식 선택"}
    CH -->|"SendMessage"| SM["단일 응답(JSON-RPC)"]
    CH -->|"SendStreamingMessage"| SS["스트리밍 응답(SSE 이벤트)"]

    SM --> R1["Task 상태/결과를 한 번에 수신"]
    SS --> R2["Task 진행 이벤트를 순차 수신"]

    R1 --> OUT["작업 완료 또는 후속 조회"]
    R2 --> OUT
```

## 3. Task Lifecycle

```mermaid
stateDiagram-v2
    [*] --> SUBMITTED
    SUBMITTED --> WORKING
    WORKING --> INPUT_REQUIRED: 추가 입력 필요
    WORKING --> AUTH_REQUIRED: 인증 필요
    INPUT_REQUIRED --> WORKING: 입력 제공 후 재개
    AUTH_REQUIRED --> WORKING: 인증 후 재개
    WORKING --> COMPLETED
    WORKING --> FAILED
    WORKING --> CANCELED
    WORKING --> REJECTED: 거부
    INPUT_REQUIRED --> CANCELED
    AUTH_REQUIRED --> CANCELED
```

## 4. Streaming(SSE) + Push Notification 비동기 패턴

```mermaid
sequenceDiagram
    participant C as Client Agent
    participant R as Remote Agent
    participant W as Client Webhook

    C->>R: SendStreamingMessage
    R-->>C: SSE: TASK_STATE_WORKING
    R-->>C: SSE: progress + artifact update

    opt 연결 종료 또는 장기 실행
        C->>R: CreateTaskPushNotificationConfig
        R-->>W: TASK_STATE_COMPLETED/FAILED 이벤트 푸시
        W-->>C: 내부 시스템 업데이트
    end
```

## 5. A2A + MCP 조합

```mermaid
flowchart TD
    User["User/System"] --> CA["Client Agent (A2A client)"]
    CA --> RA["Remote Agent (A2A server)"]
    RA --> MCP["MCP Server(s)"]
    MCP --> Tools["Enterprise Tools / Data / APIs"]

    CA -. Agent Card 기반 발견 .-> RA
    RA -. Tool/Context access .-> MCP

    Note1["A2A: Agent 간 작업 위임/협업"]:::note
    Note2["MCP: 도구/데이터 표준 연결"]:::note
    CA --> Note1
    MCP --> Note2

    classDef note fill:#f7f7f7,stroke:#999,color:#333;
```

## 6. 멀티 에이전트 위임 패턴 (Codelab 예제)

```mermaid
sequenceDiagram
    participant U as User
    participant PC as Purchasing Concierge<br/>(ADK, Agent Engine)
    participant BA as Burger Agent<br/>(CrewAI, Cloud Run)
    participant PA as Pizza Agent<br/>(LangGraph, Cloud Run)

    PC->>BA: Agent Card 조회
    BA-->>PC: skills: [create_burger_order]
    PC->>PA: Agent Card 조회
    PA-->>PC: skills: [create_pizza_order]

    U->>PC: "버거 2개, 피자 1개 주문"
    PC->>PC: 요청 분석 → 에이전트 선택
    PC->>BA: SendMessage (버거 주문)
    BA-->>PC: TASK_STATE_COMPLETED + Artifact
    PC->>PA: SendMessage (피자 주문)
    PA-->>PC: TASK_STATE_COMPLETED + Artifact
    PC-->>U: 주문 결과 통합 응답
```

## 7. 전송 프로토콜 선택

```mermaid
flowchart LR
    C["Client Agent"] --> AC["Agent Card 조회"]
    AC --> IF{"supportedInterfaces 확인"}
    IF -->|"json-rpc"| JR["JSON-RPC 2.0<br/>(HTTP/1.1+)"]
    IF -->|"grpc"| GR["gRPC<br/>(HTTP/2 + TLS)"]
    IF -->|"http"| HT["HTTP+JSON<br/>(REST-like)"]
    JR --> REQ["A2A 요청"]
    GR --> REQ
    HT --> REQ
```

## 8. In-Task Authentication

```mermaid
sequenceDiagram
    participant C as Client Agent
    participant R as Remote Agent
    participant Auth as Auth Provider

    C->>R: SendMessage (작업 요청)
    R->>R: 추가 인증 필요 판단
    R-->>C: TaskStatus: TASK_STATE_AUTH_REQUIRED<br/>+ 인증 정보 안내
    C->>Auth: Out-of-band 인증
    Auth-->>C: 자격증명 발급
    C->>R: SendMessage (인증 정보 포함)
    R-->>C: TaskStatus: TASK_STATE_WORKING → TASK_STATE_COMPLETED
```

