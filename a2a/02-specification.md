# A2A 프로토콜 스펙 상세

> A2A 프로토콜 v1.0 기준, 핵심 스키마와 타입 정의를 정리한 문서입니다.
> 정규 규범 소스는 `spec/a2a.proto` (Protocol Buffers)이며, JSON 표현은 생성 산출물입니다.

---

## 1. 프로토콜 개요

| 항목      | 내용                                                        |
|---------|-----------------------------------------------------------|
| 이름      | Agent2Agent (A2A) Protocol                                |
| 현재 버전   | v1.0 (안정 릴리스, 프로덕션 준비 완료)                                 |
| 상태      | Stable                                                    |
| 관리 주체   | Linux Foundation (TSC: AWS, Cisco, Google, IBM Research, Microsoft, Salesforce, SAP, ServiceNow) |
| 전송 프로토콜 | JSON-RPC 2.0, gRPC, HTTP+JSON                             |
| 기반      | HTTP/2 + TLS                                              |

### 버전 이력

| 버전     | 주요 변경사항                                                                            |
|--------|------------------------------------------------------------------------------------|
| v0.2.x | 초기 스펙, JSON-RPC 기반, 기본 Task/Message/Artifact 모델                                    |
| v0.3.0 | gRPC 1급 지원, Agent Card 서명, auth-required/rejected 상태 추가, Extensions 메커니즘, 멀티 전송 협상 |
| v1.0   | 프로덕션 안정 릴리스, 멀티 테넌시, Part 재설계(멤버 기반 판별), SCREAMING_SNAKE_CASE 열거형, google.rpc.Status 에러, 최신 OAuth 플로우, supportedInterfaces 도입, 커서 기반 페이지네이션 |

---

## 2. Agent Card 스키마

Agent Card는 에이전트의 공개 메타데이터 문서로, `/.well-known/agent-card.json` 경로에 게시됩니다.

### 2.1 전체 구조

```json
{
  "id": "string (required)",
  "name": "string (required)",
  "description": "string (optional)",
  "version": "string (required)",
  "provider": {
    "id": "string",
    "name": "string",
    "logoUrl": "string"
  },
  "serviceEndpoint": "string (required, URI)",
  "capabilities": {
    "streaming": "boolean (default: false)",
    "pushNotifications": "boolean (default: false)",
    "extendedAgentCard": "boolean (default: false)"
  },
  "supportedInterfaces": [
    {
      "url": "string (URI)",
      "protocolBinding": "string (e.g. 'json-rpc', 'grpc', 'http')",
      "protocolVersion": "string (e.g. '1.0')"
    }
  ],
  "skills": [ "AgentSkill[]" ],
  "defaultInputModes": [ "string[]" ],
  "defaultOutputModes": [ "string[]" ],
  "securitySchemes": { "[schemeName]": "SecurityScheme" },
  "security": [ { "[schemeName]": ["scope1"] } ],
  "extensions": [ "AgentExtension[]" ],
  "signatures": [ "AgentCardSignature[]" ]
}
```

v0.3 대비 주요 변경사항:

- `protocolVersion` (최상위 필드) 제거 → `supportedInterfaces[].protocolVersion`으로 이동
- `interfaces[]` → `supportedInterfaces[]`로 변경, 각 항목에 `url`, `protocolBinding`, `protocolVersion` 포함
- `capabilities.extendedAgentCard` 필드 추가 (기존 `supportsAuthenticatedExtendedCard` 대체)

### 2.2 AgentSkill

```json
{
  "id": "string (required)",
  "name": "string (required)",
  "description": "string (optional)",
  "inputDescription": "string (optional)",
  "outputDescription": "string (optional)",
  "inputSchema": "JSON Schema (optional)",
  "outputSchema": "JSON Schema (optional)",
  "tags": ["string"],
  "examples": ["string"]
}
```

### 2.3 SupportedInterface

```json
{
  "url": "string (URI, required)",
  "protocolBinding": "string (e.g. 'json-rpc', 'grpc', 'http')",
  "protocolVersion": "string (e.g. '1.0')"
}
```

### 2.4 AgentExtension

```json
{
  "uri": "string (required, 고유 확장 식별자)",
  "description": "string (optional)",
  "required": "boolean (default: false)",
  "params": "object (optional)"
}
```

### 2.5 AgentCardSignature

RFC 7515(JWS) 기반의 Agent Card 무결성 검증 메커니즘입니다.

```json
{
  "protected": "string (Base64url 인코딩된 JWS 보호 헤더)",
  "signature": "string (계산된 서명값)",
  "header": "object (optional, 미보호 헤더)"
}
```

- 복수 서명 지원 (`signatures` 배열)
- 선택 사항이며 **강제하지는 않음**
- JSON 표준 정렬 규칙(정규화)에 따라 서명 계산

### 2.6 Agent Card 예시

```json
{
  "id": "currency-exchange-agent",
  "name": "Currency Exchange Agent",
  "description": "Provides real-time currency exchange rates",
  "version": "1.0.0",
  "serviceEndpoint": "https://api.example.com/a2a/v1",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "extendedAgentCard": false
  },
  "supportedInterfaces": [
    { "url": "https://api.example.com/a2a/v1", "protocolBinding": "json-rpc", "protocolVersion": "1.0" },
    { "url": "https://api.example.com/a2a/grpc", "protocolBinding": "grpc", "protocolVersion": "1.0" }
  ],
  "skills": [
    {
      "id": "get_exchange_rate",
      "name": "Get Currency Exchange Rate",
      "description": "Retrieves exchange rate between two currencies",
      "tags": ["Finance", "Currency"],
      "examples": ["What is the USD to EUR exchange rate?"]
    }
  ],
  "defaultInputModes": ["text", "text/plain"],
  "defaultOutputModes": ["text", "text/plain"],
  "securitySchemes": {
    "oauth2": {
      "type": "oauth2",
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.example.com/token",
          "scopes": { "agent:read": "Read access" }
        }
      }
    }
  },
  "security": [{ "oauth2": ["agent:read"] }]
}
```

---

## 3. JSON-RPC 메서드

### 3.1 메서드 목록

| 메서드                                  | 설명                         | 필수                                |
|--------------------------------------|----------------------------|-----------------------------------|
| `SendMessage`                        | 메시지 송신, Task 또는 Message 반환 | Yes                               |
| `SendStreamingMessage`               | SSE 기반 스트리밍 메시지 송신         | No (streaming capability)         |
| `GetTask`                            | 특정 Task 상태/결과 조회           | Yes                               |
| `ListTasks`                          | Task 목록 조회                 | No                                |
| `CancelTask`                         | Task 취소 요청                 | No                                |
| `SubscribeToTask`                    | Task 업데이트 스트리밍 구독          | No                                |
| `CreateTaskPushNotificationConfig`   | 웹훅 설정 생성                   | No (push capability)              |
| `GetTaskPushNotificationConfig`      | 웹훅 설정 조회                   | No                                |
| `ListTaskPushNotificationConfigs`    | 웹훅 설정 목록 조회                | No                                |
| `DeleteTaskPushNotificationConfig`   | 웹훅 설정 삭제                   | No                                |
| `GetExtendedAgentCard`               | 인증된 Agent Card 조회          | No (extendedAgentCard capability) |

### 3.2 SendMessage

동기 메시지 송신. 짧거나 즉시 완료 가능한 작업에 적합합니다.

**요청 (SendMessageRequest)**:

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [{ "text": "USD to EUR exchange rate?", "mediaType": "text/plain" }],
      "messageId": "msg-uuid-001",
      "contextId": "session-uuid-001"
    },
    "configuration": {
      "acceptedOutputModes": ["text", "text/plain"],
      "historyLength": 10,
      "returnImmediately": false
    },
    "tenant": "tenant-001",
    "metadata": {}
  }
}
```

**응답**: `Task` 또는 `Message` 객체를 반환합니다.

### 3.3 SendStreamingMessage

SSE 기반 스트리밍 호출. 장기 실행 또는 진행 가시성이 중요한 시나리오에 적합합니다.

**요청**: `SendMessage`와 동일한 파라미터

**응답**: SSE 이벤트 스트림으로 `StreamResponse` 객체를 순차 전송

### 3.4 GetTask

```json
{
  "jsonrpc": "2.0",
  "id": "req-002",
  "method": "GetTask",
  "params": {
    "id": "task-uuid-001",
    "historyLength": 5,
    "tenant": "tenant-001"
  }
}
```

### 3.5 ListTasks

```json
{
  "jsonrpc": "2.0",
  "id": "req-003",
  "method": "ListTasks",
  "params": {
    "contextId": "session-uuid-001",
    "status": "TASK_STATE_WORKING",
    "maxResults": 20,
    "cursor": "next-cursor-token",
    "tenant": "tenant-001"
  }
}
```

v1.0에서 새로 추가된 메서드이며, 페이지 기반 페이지네이션 대신 커서 기반 페이지네이션(`cursor`)을 사용합니다.

### 3.6 CancelTask

```json
{
  "jsonrpc": "2.0",
  "id": "req-004",
  "method": "CancelTask",
  "params": {
    "id": "task-uuid-001",
    "tenant": "tenant-001"
  }
}
```

### 3.7 SendMessageConfiguration

```json
{
  "acceptedOutputModes": ["text", "application/json"],
  "taskPushNotificationConfig": {
    "url": "https://client.example.com/webhook",
    "headers": { "Authorization": "Bearer ..." }
  },
  "historyLength": 10,
  "returnImmediately": false
}
```

- `historyLength`: unset(전체), 0(없음), >0(최대 N개)
- `returnImmediately`: `true`면 Task 생성 직후 즉시 반환 (비동기 패턴)
- 모든 요청 메시지에 `tenant` 필드를 포함하여 멀티 테넌시를 네이티브로 지원합니다.

---

## 4. Task 상태 모델

### 4.1 TaskState 열거형

v1.0에서 모든 열거형 값은 SCREAMING_SNAKE_CASE로 변경되었습니다.

| 상태                            | 코드 | 설명       | 유형  |
|-------------------------------|----|----------|-----|
| `TASK_STATE_UNSPECIFIED`      | 0  | 미지정      | -   |
| `TASK_STATE_SUBMITTED`        | 1  | 제출됨      | 초기  |
| `TASK_STATE_WORKING`          | 2  | 진행 중     | 활성  |
| `TASK_STATE_COMPLETED`        | 3  | 완료       | 터미널 |
| `TASK_STATE_FAILED`           | 4  | 실패       | 터미널 |
| `TASK_STATE_CANCELED`         | 5  | 취소됨      | 터미널 |
| `TASK_STATE_INPUT_REQUIRED`   | 6  | 추가 입력 필요 | 중단  |
| `TASK_STATE_AUTH_REQUIRED`    | 7  | 인증 필요    | 중단  |
| `TASK_STATE_REJECTED`         | 8  | 거부됨      | 터미널 |

역할(Role) 열거형도 동일하게 변경: `user` → `ROLE_USER`, `agent` → `ROLE_AGENT`

### 4.2 상태 전이 다이어그램

```text
[생성] → TASK_STATE_SUBMITTED → TASK_STATE_WORKING
                                 ├→ TASK_STATE_COMPLETED (터미널)
                                 ├→ TASK_STATE_FAILED (터미널)
                                 ├→ TASK_STATE_CANCELED (터미널)
                                 ├→ TASK_STATE_REJECTED (터미널)
                                 ├→ TASK_STATE_INPUT_REQUIRED (중단) → TASK_STATE_WORKING (입력 제공 후 재개)
                                 │                                   → TASK_STATE_CANCELED
                                 └→ TASK_STATE_AUTH_REQUIRED (중단) → TASK_STATE_WORKING (인증 후 재개)
                                                                    → TASK_STATE_CANCELED
```

- **터미널 상태**: 스트리밍 종료를 트리거하며, 이후 상태 변경 불가
- **중단 상태**: 클라이언트 개입이 필요하며, `SendMessage`로 재개 가능

### 4.3 TaskStatus 객체

```json
{
  "state": "TASK_STATE_WORKING",
  "message": "Processing exchange rate lookup...",
  "timestamp": "2025-07-15T10:30:00Z"
}
```

### 4.4 Task 객체

```json
{
  "id": "task-uuid-001",
  "contextId": "session-uuid-001",
  "status": { "state": "TASK_STATE_COMPLETED", "timestamp": "..." },
  "createdAt": "2025-07-15T10:29:55Z",
  "lastModified": "2025-07-15T10:30:05Z",
  "messages": [ "Message[]" ],
  "artifacts": [ "Artifact[]" ],
  "metadata": {}
}
```

v1.0에서 `createdAt`, `lastModified` 타임스탬프 필드가 추가되었습니다.

---

## 5. 메시지 타입 정의

### 5.1 Message

```json
{
  "id": "string (optional, server-generated)",
  "role": "ROLE_USER | ROLE_AGENT",
  "parts": [ "Part[] (required, 최소 1개)" ],
  "taskId": "string (optional)",
  "contextId": "string (optional)",
  "referenceTaskIds": ["string (optional)"],
  "messageId": "string (required for requests)",
  "createdAt": "RFC3339 timestamp (optional)"
}
```

### 5.2 Part (멤버 기반 판별)

Part는 Message와 Artifact를 구성하는 최소 콘텐츠 단위입니다.

v1.0에서는 `kind` 필드가 제거되고, 멤버 기반 판별(member-based discrimination)로 전환되었습니다. 어떤 필드가 존재하느냐에 따라 Part 유형이 결정됩니다.

```json
// 텍스트 Part (text 필드 존재)
{ "text": "Hello, what is the exchange rate?", "mediaType": "text/plain" }

// 파일 Part - URL 참조 (url 필드 존재)
{
  "url": "https://storage.example.com/report.pdf",
  "mediaType": "application/pdf",
  "filename": "report.pdf"
}

// 파일 Part - 인라인 바이너리 (bytes 필드 존재)
{
  "bytes": "base64-encoded-content",
  "mediaType": "image/png",
  "filename": "chart.png"
}

// 구조화 데이터 Part (data 필드 존재)
{
  "data": { "rate": 0.92, "from": "USD", "to": "EUR" },
  "mediaType": "application/json"
}
```

v0.3 대비 주요 변경사항:

- `TextPart`, `FilePart`, `DataPart` 구분 제거 → 통합 Part 타입
- `kind` 필드 제거 → 멤버 존재 여부로 유형 판별 (`text`, `url`, `bytes`, `data`)
- `file.uri` → `url` (최상위), `file.bytes` → `bytes` (최상위), `file.name` → `filename`

### 5.3 Artifact

Task 수행 결과로 생성되는 산출물입니다.

```json
{
  "id": "artifact-001",
  "name": "Exchange Rate Result",
  "description": "USD to EUR exchange rate",
  "mimeType": "application/json",
  "parts": [
    { "data": { "rate": 0.92 }, "mediaType": "application/json" }
  ],
  "createdAt": "2025-07-15T10:30:05Z",
  "metadata": {}
}
```

---

## 6. 스트리밍 이벤트

### 6.1 StreamResponse (래퍼)

스트리밍 응답은 멤버 이름 판별(member name discrimination)을 사용합니다. v1.0에서는 `kind` 필드 대신 어떤 멤버가 존재하는지로 이벤트 유형을 판별합니다.

```json
// Task 전체 상태 (task 멤버 존재)
{ "task": { "id": "...", "status": {...}, "artifacts": [...] } }

// 메시지 (message 멤버 존재)
{ "message": { "role": "ROLE_AGENT", "parts": [...] } }

// 상태 업데이트 이벤트 (taskStatusUpdate 멤버 존재)
{ "taskStatusUpdate": { "taskId": "...", "status": {...} } }

// Artifact 업데이트 이벤트 (taskArtifactUpdate 멤버 존재)
{ "taskArtifactUpdate": { "taskId": "...", "artifact": {...}, "timestamp": "..." } }
```

v0.3에서는 `{"kind": "taskStatusUpdate", ...}` 형태였으나, v1.0에서는 `{"taskStatusUpdate": {...}}` 형태로 변경되었습니다.

### 6.2 스트리밍 동작 규칙

- **Message 전용 응답**: 정확히 1개만 전송 후 스트림 즉시 종료
- **Task 라이프사이클**: Task 응답 후 0개 이상의 이벤트, 터미널 상태에서 종료
- **순서 보장**: 모든 이벤트는 생성 순서 유지 필수
- **다중 구독**: 동일 Task에 여러 클라이언트 동시 구독 가능

---

## 7. 인증/보안 스키마

### 7.1 SecurityScheme 타입

| 타입              | 설명                        |
|-----------------|---------------------------|
| `apiKey`        | API 키 기반 인증 (헤더 또는 쿼리)    |
| `http`          | HTTP 인증 (Basic, Bearer 등) |
| `oauth2`        | OAuth 2.0 플로우             |
| `openIdConnect` | OpenID Connect            |
| `mutualTls`     | 상호 TLS 인증                 |

### 7.2 OAuth2SecurityScheme 예시

v1.0에서 Implicit, Password 플로우가 제거되고, Device Code 플로우(RFC 8628)가 추가되었습니다. Authorization Code 플로우에는 PKCE 지원(`pkceRequired`)이 추가되었습니다.

```json
{
  "type": "oauth2",
  "flows": {
    "authorizationCode": {
      "authorizationUrl": "https://auth.example.com/authorize",
      "tokenUrl": "https://auth.example.com/token",
      "pkceRequired": true,
      "scopes": {
        "agent:read": "Read agent data",
        "agent:execute": "Execute agent tasks"
      }
    },
    "clientCredentials": {
      "tokenUrl": "https://auth.example.com/token",
      "scopes": { "agent:execute": "Execute agent tasks" }
    },
    "deviceCode": {
      "deviceAuthorizationUrl": "https://auth.example.com/device",
      "tokenUrl": "https://auth.example.com/token",
      "scopes": { "agent:execute": "Execute agent tasks" }
    }
  }
}
```

### 7.3 APIKeySecurityScheme 예시

```json
{
  "type": "apiKey",
  "name": "X-API-Key",
  "in": "header"
}
```

### 7.4 In-Task Authentication

Task 실행 중 추가 인증이 필요한 경우의 흐름:

1. Agent가 `TASK_STATE_AUTH_REQUIRED` 상태로 전환
2. `TaskStatus.message`에 인증 정보(PushNotificationAuthenticationInfo) 포함
3. 클라이언트가 Out-of-band로 인증 수행
4. `SendMessage`로 인증 정보와 함께 재전송
5. Task가 `TASK_STATE_WORKING` 상태로 복귀

---

## 8. 에러 처리

v1.0에서는 `google.rpc.Status`와 `ErrorInfo`를 채택하여 에러 처리가 표준화되었습니다.

### 8.1 A2A 에러 코드

| 에러                                    | 설명                   |
|---------------------------------------|----------------------|
| `TaskNotFoundError`                   | Task ID 미존재 또는 접근 불가 |
| `TaskNotCancelableError`              | 이미 완료/실패/취소된 Task    |
| `PushNotificationNotSupportedError`   | 웹훅 미지원               |
| `UnsupportedOperationError`           | 미지원 작업               |
| `ContentTypeNotSupportedError`        | 미지원 미디어 타입           |
| `InvalidAgentResponseError`           | 스펙 위반 응답             |
| `ExtendedAgentCardNotConfiguredError` | 인증 Card 미설정          |
| `ExtensionSupportRequiredError`       | 필수 Extension 미지원     |
| `VersionNotSupportedError`            | 프로토콜 버전 미지원          |

### 8.2 프로토콜별 에러 매핑

| A2A 에러                  | JSON-RPC 코드 | HTTP 상태 | gRPC 상태             |
|-------------------------|-------------|---------|---------------------|
| TaskNotFound            | -32001      | 404     | NOT_FOUND           |
| TaskNotCancelable       | -32002      | 409     | FAILED_PRECONDITION |
| UnsupportedOperation    | -32003      | 501     | UNIMPLEMENTED       |
| ContentTypeNotSupported | -32004      | 415     | INVALID_ARGUMENT    |
| InvalidAgentResponse    | -32005      | 502     | INTERNAL            |
| VersionNotSupported     | -32006      | 406     | UNIMPLEMENTED       |

### 8.3 에러 응답 구조

v1.0에서는 `google.rpc.Status` 형식을 따르며, `details` 배열에 `ErrorInfo`를 포함합니다.

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "error": {
    "code": 404,
    "message": "Task not found",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "TASK_NOT_FOUND",
        "domain": "a2a-protocol.org"
      }
    ]
  }
}
```

---

## 9. gRPC 지원

### 9.1 요구사항

- `spec/a2a.proto` (Protocol Buffers v3) 정규 정의 준수
- `A2AService` gRPC 서비스 구현
- `json_name` 어노테이션으로 HTTP/JSON 변환 호환성 보장
- TLS 암호화 필수 (gRPC over HTTP/2 with TLS)
- gRPC 상태 코드를 A2A 에러 코드로 매핑

### 9.2 전송 선택

Agent Card의 `supportedInterfaces`에서 정적으로 선언하며, 동적 협상은 정의하지 않습니다.

```json
{
  "serviceEndpoint": "https://api.example.com/a2a/v1",
  "supportedInterfaces": [
    { "url": "https://api.example.com/a2a/v1", "protocolBinding": "json-rpc", "protocolVersion": "1.0" },
    { "url": "https://api.example.com/a2a/grpc", "protocolBinding": "grpc", "protocolVersion": "1.0" }
  ]
}
```

클라이언트 선택 규칙:

1. Agent Card 파싱 → `supportedInterfaces`에서 지원 전송 목록 추출
2. `serviceEndpoint` 우선 사용
3. 미지원 시 `supportedInterfaces`에서 대체 선택

### 9.3 버전 협상

`A2A-Version` HTTP 헤더로 프로토콜 버전을 전달합니다.

---

## 10. SDK 지원 현황

| 언어                    | 패키지                            | 상태          |
|-----------------------|--------------------------------|-------------|
| Python                | `a2a-sdk`                      | 공식, PyPI 배포 |
| JavaScript/TypeScript | `@anthropic-ai/a2a`            | 공식          |
| Go                    | `github.com/a2aproject/a2a-go` | 공식          |
| Java                  | -                              | 공식          |
| .NET                  | -                              | 공식          |

---

## 참고 자료

- [A2A Protocol Specification (latest)](https://a2a-protocol.org/latest/specification/)
- [A2A Protocol Specification (v1.0)](https://a2a-protocol.org/v1.0/specification/)
- [A2A Protocol Definitions](https://a2a-protocol.org/latest/definitions/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [A2A Python SDK Reference](https://a2a-protocol.org/latest/sdk/python/api/)
