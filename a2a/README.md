# A2A 분석

Google의 Agent2Agent(A2A) 프로토콜 문서를 기준으로, 에이전트 간 상호운용(interop) 구조와 실행 패턴을 정리한 문서입니다.

A2A는 **Agent Card 기반 발견(discovery)**, **Task 중심 상호작용**, **동기/스트리밍/비동기 완료 패턴**을 표준화해 서로 다른 에이전트 시스템 간 협업을 목표로 합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/a2a/00-diagram.md) | Agent Card 발견, sendMessage/sendStreamingMessage, Task lifecycle, SSE/Push 비동기 흐름, A2A+MCP 조합 |
| [설계 및 실행 플로우 분석](/a2a/01-analysis.md) | 핵심 개념, 프로토콜 계층, 핵심 오퍼레이션, 엔터프라이즈/보안 고려사항, MCP 비교, 체크리스트/트레이드오프 |

---

## 아키텍처 개요

```text
Client Agent
  └─ Agent Card 조회(Discovery)
       └─ 원격 Agent의 capabilities / auth / endpoint 확인
            ↓
A2A JSON-RPC 호출 (sendMessage / sendStreamingMessage / getTask / ...)
            ↓
Remote Agent
  ├─ Task 생성/업데이트
  ├─ Message(Part들) 처리
  ├─ Artifact 산출물 생성
  └─ 상태 전이(working → input-required / completed / failed / canceled)
            ↓
결과 전달
  ├─ 동기 응답(sendMessage)
  ├─ SSE 스트리밍(sendStreamingMessage)
  └─ Push Notification(웹훅) 기반 비동기 완료
```

### 핵심 설계 포인트

- **발견 가능성(Discoverability)**: Agent Card를 통해 호출 전 기능/제약/인증을 파악합니다.
- **Task 중심 상호작용**: 단발 요청이 아니라 상태를 가진 작업 단위로 협업합니다.
- **멀티모달 메시지 모델**: Message는 여러 Part(예: text, file 등)로 구성됩니다.
- **비동기 우선 설계**: 긴 작업은 streaming(SSE)과 push notification으로 분리 처리합니다.
- **상호보완적 표준 전략**: A2A(Agent 간 협업)와 MCP(도구/컨텍스트 연결)를 함께 사용할 수 있습니다.

---

## 참고 자료

- [A2A README](https://raw.githubusercontent.com/a2aproject/A2A/main/README.md)
- [A2A Specification](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- [What is A2A](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/what-is-a2a.md)
- [Key Concepts](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/key-concepts.md)
- [A2A and MCP](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/a2a-and-mcp.md)
- [Agent Discovery](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/agent-discovery.md)
- [Streaming and Async](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/streaming-and-async.md)
- [Enterprise Ready](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/enterprise-ready.md)
- [Life of a Task](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/life-of-a-task.md)
- [Google Cloud Agent Engine A2A 개발 가이드](https://docs.cloud.google.com/agent-builder/agent-engine/develop/a2a?hl=ko)
- [A2A 구매 컨시어지 Codelab](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge?hl=ko#0)
