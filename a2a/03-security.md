# A2A 보안 분석

> A2A 프로토콜 v1.0의 보안 위협 모델, 인증/인가 메커니즘, 엔터프라이즈 보안 권장사항을 정리한 문서입니다.

---

## 1. 위협 모델

A2A 프로토콜의 보안 위협은 LLM 기반 에이전트 간 통신의 고유한 특성에서 비롯됩니다. 기존 API 보안과 달리, **모든 클라이언트가 고도로 자동화된 행위자**라는 점이 핵심 차이입니다.

### 1.1 핵심 위협 벡터

| 위협                 | 설명                    | 심각도      |
|--------------------|-----------------------|----------|
| **프롬프트 인젝션**       | 악의적 입력으로 에이전트 행동 조작   | Critical |
| **Agent Card 스푸핑** | 위조된 Agent Card로 신뢰 탈취 | High     |
| **무단 리소스 사용**      | LLM 컴퓨팅 리소스 무단 소비     | High     |
| **데이터 유출**         | 에이전트 간 전송 데이터 탈취      | High     |
| **결과 조작**          | 중간자 공격으로 Task 결과 변조   | High     |
| **스트림 탈취**         | SSE 세션 가로채기           | Medium   |
| **직렬화 공격**         | JSON-RPC 페이로드 조작      | Medium   |

### 1.2 공격 표면

```text
┌─────────────────────────────────────────────────────┐
│                     공격 표면                         │
├──────────────┬──────────────────────────────────────┤
│ Discovery    │ Agent Card 위조, DNS 하이재킹          │
│ Transport    │ TLS 다운그레이드, MITM, SSE 탈취       │
│ Authentication│ 토큰 탈취, OAuth 플로우 조작           │
│ Message      │ 프롬프트 인젝션, 페이로드 조작          │
│ Executor     │ 비즈니스 로직 우회, 권한 상승           │
│ Artifact     │ 결과 변조, 데이터 유출                 │
└──────────────┴──────────────────────────────────────┘
```

---

## 2. Agent Card 보안

### 2.1 Agent Card 서명

v1.0에서 JSON Canonicalization(RFC 8785) + JWS(RFC 7515) 기반 서명을 표준으로 지원합니다. 정규화된 JSON에 서명하여 일관된 검증이 가능합니다.

```json
{
  "signatures": [{
    "protected": "eyJhbGciOiJFUzI1NiIs...",
    "signature": "QFdkNLNszlGj3z3u0YQGt_T9..."
  }]
}
```

### 2.2 Agent Card 인터페이스

v1.0에서 Agent Card는 단일 `url` 필드 대신 `supportedInterfaces[]` 배열로 여러 전송 프로토콜(HTTP, gRPC 등)을 선언할 수 있습니다.

```json
{
  "supportedInterfaces": [
    { "type": "http", "url": "https://agent.example.com/a2a" },
    { "type": "grpc", "url": "grpc://agent.example.com:443" }
  ]
}
```

### 2.3 위험 요소

- **중앙 레지스트리 부재**: 누구나 Agent Card를 게시할 수 있어 스푸핑 비용이 낮음
- **서명 미강제**: 클라이언트가 서명 검증을 건너뛸 수 있음
- **발급자 신원 미검증**: Card 자체만으로는 에이전트의 정당성을 보장하지 않음

### 2.4 권장사항

- Agent Card 서명을 **필수**로 적용
- 발급자 신원 검증 프로세스 구축
- 신뢰할 수 있는 에이전트 레지스트리 운영
- Card 갱신 주기와 만료 정책 설정
- 민감한 스킬 정보는 `extendedAgentCard` (인증 후 조회)에만 노출

---

## 3. 인증/인가 메커니즘

### 3.1 지원 인증 스키마

| 스키마             | 용도           | 강도    |
|-----------------|--------------|-------|
| `oauth2`        | 에이전트 간 위임 인증 | 높음    |
| `openIdConnect` | ID 기반 인증     | 높음    |
| `mutualTls`     | 상호 인증서 검증    | 매우 높음 |
| `http` (Bearer) | 토큰 기반 접근     | 중간    |
| `apiKey`        | 단순 키 기반 접근   | 낮음    |

### 3.2 OAuth 2.0 보안 고려사항

v1.0에서 보안 강화를 위해 **Implicit Grant**와 **Resource Owner Password Credentials** 플로우가 **제거**되었습니다. 대신 Device Code 플로우(RFC 8628)와 PKCE(Proof Key for Code Exchange) 지원이 추가되었습니다.

| 항목         | 위험                   | 완화 방안                          |
|------------|----------------------|--------------------------------|
| 토큰 수명      | 장기 유효 토큰 유출 시 지속적 위험 | 단기 수명 토큰 (15-30분)              |
| 스코프 범위     | 과도한 권한 부여            | 스킬별 세분화된 스코프                   |
| 동의 메커니즘    | 프로토콜 수준 사용자 승인 미흡    | 명시적 승인 플로우 구축                   |
| 토큰 저장      | 에이전트 메모리 내 토큰 노출     | 보안 토큰 저장소 사용                    |
| 인가 코드 가로채기 | 코드 탈취 후 토큰 교환       | PKCE 필수 적용                      |
| 입력 제한 디바이스 | 브라우저 없는 환경의 인증 어려움   | Device Code 플로우(RFC 8628) 활용    |

### 3.3 In-Task Authentication

Task 실행 중 추가 인증이 필요한 시나리오:

```text
Client → Agent: message/send (작업 요청)
Agent → Client: TaskStatus { state: "TASK_STATE_AUTH_REQUIRED", message: "OAuth token needed" }
Client: Out-of-band 인증 수행
Client → Agent: message/send (인증 정보 포함)
Agent → Client: TaskStatus { state: "TASK_STATE_WORKING" } → { state: "TASK_STATE_COMPLETED" }
```

> v1.0에서 TaskStatus의 state 값은 `TASK_STATE_` 접두사를 사용하는 표준화된 enum으로 변경되었습니다 (예: `TASK_STATE_AUTH_REQUIRED`, `TASK_STATE_WORKING`, `TASK_STATE_COMPLETED`).

---

## 4. 전송 보안

### 4.1 TLS 요구사항

- **최소**: TLS 1.2 (TLS 1.3 권장)
- gRPC: HTTP/2 + TLS 필수
- Webhook 엔드포인트: HTTPS 필수
- 인증서 고정(Certificate Pinning) 권장

### 4.2 스트리밍 보안

| 위협        | 설명                 | 완화                      |
|-----------|--------------------|-------------------------|
| SSE 탈취    | 세션 토큰으로 타 스트림 도청   | 세션별 고유 토큰, 클라이언트 IP 바인딩 |
| 연결 유지 공격  | 장시간 SSE 연결로 리소스 고갈 | 연결 타임아웃, 하트비트 검증        |
| 재연결 재생 공격 | 끊긴 SSE를 재생 토큰으로 탈취 | 일회성 재연결 토큰              |

### 4.3 직렬화 보안

JSON-RPC 2.0 사용에 따른 보안 고려사항:

- **페이로드 크기 제한**: DoS 방지를 위한 최대 크기 설정
- **중첩 깊이 제한**: 깊은 JSON 구조로 인한 파싱 비용 방지
- **유니코드 정규화**: 정규화 공격 방지
- **입력 새니타이제이션**: 모든 Part 콘텐츠 검증

### 4.4 표준화된 에러 처리

v1.0에서 `google.rpc.Status`를 채택하여 에러 응답 형식이 표준화되었습니다. 이를 통해 에이전트 간 일관된 에러 전파와 디버깅이 가능합니다.

```json
{
  "code": 7,
  "message": "PERMISSION_DENIED: insufficient scope for skill 'currency-exchange'",
  "details": []
}
```

---

## 5. 멀티테넌시 지원

v1.0에서 모든 요청에 `tenant` 필드가 포함되어 멀티테넌시를 네이티브로 지원합니다. 이를 통해 단일 에이전트 인스턴스가 여러 테넌트의 요청을 안전하게 처리할 수 있습니다.

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "tenant": "org-acme-corp",
    "message": { ... }
  }
}
```

### 5.1 멀티테넌시 보안 고려사항

| 위협             | 설명                      | 완화 방안                    |
|----------------|-------------------------|--------------------------|
| 테넌트 간 데이터 누출   | 잘못된 격리로 타 테넌트 데이터 접근    | 요청/응답 파이프라인에서 테넌트 격리 강제  |
| 테넌트 사칭         | `tenant` 필드 위조로 타 테넌트 행세 | 인증 토큰과 테넌트 ID 매핑 검증      |
| 리소스 경합         | 특정 테넌트의 과도한 리소스 사용      | 테넌트별 레이트 제한 및 쿼터 설정      |

---

## 6. 데이터 보호

### 6.1 데이터 최소 제공 원칙

에이전트 간 통신 시 필요 최소한의 데이터만 전송합니다.

```text
✅ 작업 수행에 필요한 최소 정보
✅ 스킬별 필요 데이터 범위 정의
❌ 전체 사용자 프로필 전달
❌ 불필요한 컨텍스트 공유
```

### 6.2 민감 데이터 처리

- 결제 정보, 개인 식별 정보(PII)는 전용 보안 채널 사용
- Artifact에 민감 데이터 포함 시 암호화 또는 참조 URL 사용
- 메타데이터에 민감 정보 포함 금지
- Task/Message/Artifact 보존 기간 정책 수립

### 6.3 감사 추적

```json
{
  "auditLog": {
    "taskId": "task-001",
    "contextId": "session-001",
    "clientAgent": "purchasing-concierge",
    "remoteAgent": "currency-exchange",
    "operation": "message/send",
    "timestamp": "2025-07-15T10:30:00Z",
    "status": "completed",
    "dataClassification": "internal"
  }
}
```

---

## 7. 프롬프트 인젝션 방어

A2A 환경에서 프롬프트 인젝션은 특히 위험합니다. 하나의 에이전트가 다른 에이전트에게 악의적 지시를 포함한 메시지를 전달할 수 있기 때문입니다.

### 7.1 방어 전략

| 계층        | 방어 방법                        |
|-----------|------------------------------|
| **입력 검증** | Message/Part 콘텐츠 구조 검증 및 필터링 |
| **샌드박싱**  | 에이전트 실행 환경 격리                |
| **출력 검증** | Artifact 산출물의 무결성/적합성 검증     |
| **권한 분리** | 에이전트별 최소 권한 원칙 적용            |
| **모니터링**  | 비정상 요청 패턴 탐지 및 차단            |

### 7.2 Confused Deputy 문제

LLM 기반 에이전트는 "혼동 대리인(Confused Deputy)" 공격에 취약합니다. 에이전트가 자신의 권한을 이용해 공격자의 요청을 수행할 수 있습니다.

**완화 방안**: 능력 기반 접근 제어(Capability-Based Access Control) 도입. 리소스 자체가 접근 제어를 판단하도록 설계합니다.

---

## 8. 엔터프라이즈 보안 체크리스트

### 8.1 배포 전 점검

- [ ] 모든 Agent Card에 JWS(RFC 7515) 디지털 서명 적용
- [ ] OAuth 2.0 (PKCE 필수) 또는 mTLS 인증 구성
- [ ] Implicit/Password OAuth 플로우 비활성화 확인
- [ ] TLS 1.3 전송 암호화 확인
- [ ] API 게이트웨이를 통한 중앙 집중식 트래픽 관리
- [ ] 에이전트별 및 테넌트별 레이트 제한 설정
- [ ] 페이로드 크기 및 중첩 깊이 제한
- [ ] Webhook 엔드포인트 HTTPS 및 검증 토큰 설정
- [ ] 멀티테넌시 격리 정책 검증

### 8.2 운영 점검

- [ ] Task/Message/Artifact 감사 로그 수집
- [ ] 비정상 트래픽 패턴 모니터링 및 알림
- [ ] 토큰 만료/갱신 정책 운영
- [ ] 정기적 보안 감사 및 모의 침투 테스트
- [ ] 에이전트 카드 갱신 주기 관리
- [ ] 인시던트 대응 절차 수립

### 8.3 개발 점검

- [ ] 프롬프트 인젝션 방어 메커니즘 구현
- [ ] 입력/출력 새니타이제이션 적용
- [ ] 에이전트 실행 환경 격리 (샌드박싱)
- [ ] 세분화된 스코프 기반 권한 설계
- [ ] SDK 보안 업데이트 적용 절차
- [ ] MCP 공격 표면과 함께 통합 검토

---

## 9. A2A + MCP 보안 통합

A2A와 MCP를 함께 사용하는 아키텍처에서의 보안 경계:

```text
┌──────────────────────────────────────────┐
│              신뢰 경계 1                   │
│  Client Agent ←── A2A ──→ Remote Agent   │
│   (인증/인가)        (Agent Card 검증)     │
├──────────────────────────────────────────┤
│              신뢰 경계 2                   │
│  Remote Agent ←── MCP ──→ Tool/Data      │
│   (권한 범위)        (도구 접근 제어)       │
└──────────────────────────────────────────┘
```

- A2A 계층: 에이전트 간 신뢰 확립, 작업 위임 권한 검증
- MCP 계층: 도구/데이터 접근 제어, 실행 환경 격리
- 두 계층의 보안 정책이 **일관성**을 유지해야 함

---

## 참고 자료

- [A Security Engineer's Guide to the A2A Protocol (Semgrep)](https://semgrep.dev/blog/2025/a-security-engineers-guide-to-the-a2a-protocol/)
- [A2A Protocol Specification - Security](https://a2a-protocol.org/latest/specification/)
- [API Teams Guide to A2A (Zuplo)](https://zuplo.com/learning-center/agent-to-agent-a2a-protocol-guide)
