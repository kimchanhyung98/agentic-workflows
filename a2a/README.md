# A2A 분석

Google의 Agent2Agent(A2A) 프로토콜 문서를 기준으로, 에이전트 간 상호운용(interop) 구조와 실행 패턴을 정리한 문서입니다.

A2A는 **Agent Card 기반 발견(discovery)**, **Task 중심 상호작용**, **동기/스트리밍/비동기 완료 패턴**을 표준화해 서로 다른 에이전트 시스템 간 협업을 목표로 합니다.
v1.0 정식 릴리즈이며, Linux Foundation에서 관리하고, 150개 이상의 조직이 참여하고 있습니다. TSC에는 AWS, Cisco, Google, IBM, Microsoft, Salesforce, SAP, ServiceNow가 포함됩니다.

---

## 문서 구성

| 문서                                     | 내용                                                                                 |
|----------------------------------------|------------------------------------------------------------------------------------|
| [아키텍처 다이어그램](/a2a/00-diagram.md)       | Agent Card 발견, 메시지 흐름, Task lifecycle, 비동기 패턴, 멀티 에이전트 위임, 전송 선택, In-Task 인증 |
| [설계 및 실행 플로우 분석](/a2a/01-analysis.md)  | 핵심 개념, 프로토콜 계층, 핵심 오퍼레이션, 비동기 패턴, 보안 고려사항, MCP 비교, 버전별 변경사항                       |
| [프로토콜 스펙 상세](/a2a/02-specification.md) | Agent Card 스키마, JSON-RPC 메서드, Task 상태 모델, 타입 정의, 인증 스키마, 에러 코드, gRPC 지원            |
| [보안 분석](/a2a/03-security.md)           | 위협 모델, Agent Card 보안, 인증/인가, 전송 보안, 프롬프트 인젝션 방어, 엔터프라이즈 체크리스트                      |
| [구현 가이드](/a2a/04-implementation.md)    | Google Cloud Agent Engine 배포, Codelab 예제, 서버/클라이언트 구현 패턴, 엔터프라이즈 배포                |

---

## 아키텍처 개요

```text
Client Agent
  └─ Agent Card 조회 (/.well-known/agent-card.json)
       └─ 원격 Agent의 skills / capabilities / auth / supportedInterfaces 확인
            ↓
A2A 호출 (JSON-RPC / gRPC / HTTP+JSON)
  ├─ SendMessage (동기)
  ├─ SendStreamingMessage (SSE 스트리밍)
  └─ GetTask / ListTasks / CancelTask / SubscribeToTask
            ↓
Remote Agent
  ├─ Task 생성/업데이트
  ├─ Message(Part: 멤버 기반 판별) 처리
  ├─ Artifact 산출물 생성
  └─ 상태 전이(WORKING → INPUT_REQUIRED/AUTH_REQUIRED/COMPLETED/FAILED/CANCELED/REJECTED)
            ↓
결과 전달
  ├─ 동기 응답(SendMessage)
  ├─ SSE 스트리밍(SendStreamingMessage)
  └─ Push Notification(웹훅) 기반 비동기 완료
```

### 핵심 설계 포인트

- **발견 가능성(Discoverability)**: Agent Card를 통해 호출 전 기능/제약/인증을 파악합니다.
- **Task 중심 상호작용**: 단발 요청이 아니라 상태를 가진 작업 단위로 협업합니다.
- **멀티모달 메시지 모델**: Message는 멤버 기반 판별(text, url, data 등)로 구성된 Part들로 이루어집니다.
- **비동기 우선 설계**: 긴 작업은 streaming(SSE)과 push notification으로 분리 처리합니다.
- **멀티 전송 지원**: JSON-RPC, gRPC, HTTP+JSON을 `supportedInterfaces`로 동등하게 지원합니다.
- **보안 내장 설계**: OAuth2(PKCE, Device Code), mTLS, API Key, OpenID Connect + Agent Card 서명(JWS + RFC 8785).
- **멀티테넌시**: `tenant` 필드로 단일 엔드포인트에서 다중 에이전트를 격리 운영할 수 있습니다.
- **상호보완적 표준 전략**: A2A(Agent 간 협업)와 MCP(도구/컨텍스트 연결)를 함께 사용할 수 있습니다.

---

## 참고 자료

### 공식 문서

- [A2A Protocol 공식 사이트](https://a2a-protocol.org/latest/)
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [What's New in v1.0](https://a2a-protocol.org/latest/whats-new-v1/)
- [Announcing Version 1.0](https://a2a-protocol.org/latest/announcing-1.0/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [A2A Samples Repository](https://github.com/a2aproject/a2a-samples)

### Google Cloud

- [Google Cloud Agent Engine A2A 개발 가이드](https://docs.cloud.google.com/agent-builder/agent-engine/develop/a2a?hl=ko)
- [A2A 구매 컨시어지 Codelab](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge?hl=ko#0)
- [A2A 프로토콜 업그레이드 블로그](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)
- [A2A 발표 블로그](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)

### 분석/가이드

- [IBM - What Is Agent2Agent Protocol?](https://www.ibm.com/think/topics/agent2agent-protocol)
- [Semgrep - A Security Engineer's Guide to the A2A Protocol](https://semgrep.dev/blog/2025/a-security-engineers-guide-to-the-a2a-protocol/)
- [Zuplo - A2A Protocol Guide for API Teams](https://zuplo.com/learning-center/agent-to-agent-a2a-protocol-guide)
- [Linux Foundation - A2A Protocol Project Launch](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
