# Coinbase Cloudbot: 워크플로우 분석

## 1. 개요

Coinbase의 Cloudbot은 **완전 자체 구축(Built from Scratch)** 방식의 내부 AI 코딩 에이전트다.
Coinbase 엔지니어링 시니어 디렉터 Chintan Turakhia 주도로 개발되었으며, 1,000명 이상의 엔지니어가 일상적인 개발 워크플로우에서 활용한다.

> "버그 리포트에서 PR까지" — Cloudbot은 이 전 과정을 자동화한다.

---

## 2. 자체 구축 배경

다른 회사들이 오픈소스 에이전트를 포크하거나 기존 프레임워크 위에 구성한 것과 달리, Coinbase는 처음부터 Cloudbot을 직접 만들었다.

| 회사 | 에이전트 | 아키텍처 방식 |
|---|---|---|
| Stripe | Minions | Goose 포크 (Fork) |
| Ramp | Inspect | OpenCode 기반 구성 (Compose) |
| **Coinbase** | **Cloudbot** | **완전 자체 구축 (Build from Scratch)** |

### 자체 구축을 선택한 이유

Coinbase는 암호화폐 금융 플랫폼으로서 일반 기업과 다른 수준의 보안·컴플라이언스 요건을 갖는다.

- **보안 요건**: 결제·자산 관련 코드에 대한 엄격한 접근 제어
- **컴플라이언스**: 금융 규제 준수를 위한 감사 추적(Audit Trail) 필요
- **데이터 격리**: 외부 클라우드 에이전트에 내부 코드베이스 노출 불가

> "우리는 다른 보안 요건이 있어서 외부 에이전트로는 시작할 수 없었다." — Chintan Turakhia

---

## 3. 핵심 설계 결정

### 3.1 멀티 모델 지원

Cloudbot은 특정 LLM에 종속되지 않고, 작업 유형과 상황에 따라 **여러 모델을 선택적으로 활용**한다.
Claude, Gemini 등 다양한 모델을 목적에 맞게 조합한다.

### 3.2 Linear-first 컨텍스트

모든 작업의 맥락은 **Linear 티켓 하나로 통일**된다. 이는 컨텍스트 분산 문제를 해소하고, 에이전트가 시작 전부터 충분한 정보를 갖추도록 한다.

```text
Slack 버그 리포트 → Linear Agent로 티켓 자동 생성
→ Cloudbot이 티켓 컨텍스트 기반으로 실행
→ MCPs(DataDog, Sentry, Amplitude 등)로 추가 정보 수집
```

### 3.3 In-house Sandbox

완전 격리된 자체 개발 샌드박스에서 코드를 실행한다. 프로덕션 환경 접근은 차단되며, 금융 컴플라이언스 경계 역할을 수행한다.

| 구성 요소 | 역할 |
|---|---|
| 격리 실행 환경 | 코드 실행 시 외부 및 프로덕션 접근 차단 |
| 컴플라이언스 경계 | 금융 규제 요건을 충족하는 보안 샌드박스 |
| 완전 권한 부여 | 샌드박스 내부에서는 에이전트에 전체 권한 제공 |

### 3.4 MCPs + Custom Skills

에이전트는 MCP(Model Context Protocol) 서버와 자체 구현한 Custom Skills를 통해 내부 시스템과 통합된다.

| 도구 | 역할 |
|---|---|
| DataDog MCP | 성능 메트릭, 알림 조회 |
| Sentry MCP | 에러 트래킹, 스택 트레이스 분석 |
| Amplitude MCP | 사용자 행동 데이터 분석 |
| GitHub MCP | 코드 탐색, PR 생성 |
| Custom Skills | 내부 시스템 특화 기능 |

---

## 4. 3가지 운영 모드

Cloudbot은 세 가지 모드로 동작하며, 각각 다른 목적에 맞게 설계되었다.

### 4.1 Create PR 모드

가장 핵심적인 모드로, Linear 티켓에서 Pull Request까지 자율 생성한다.

**워크플로우**:

1. Slack에서 `cloudbot create pr [티켓 ID]` 호출
2. Linear 티켓 컨텍스트 로드
3. MCPs를 통해 관련 정보 수집 (DataDog, Sentry 등)
4. In-house Sandbox에서 코드 구현
5. GitHub에 PR 생성
6. Slack에 **Cursor 딥링크 + QR코드** 회신

> QR코드는 모바일 앱의 원클릭 테스트를 위해 제공된다. 엔지니어가 스캔하면 해당 브랜치의 빌드로 즉시 이동한다.

### 4.2 Plan 모드

코드를 작성하지 않고, **구현 계획만 수립**하여 Linear에 기록한다. 인간이 검토 후 실행 여부를 결정한다.

**워크플로우**:

1. Slack에서 `cloudbot plan [티켓 ID]` 호출
2. 티켓 분석 및 구현 방향 검토
3. 상세 구현 계획 작성
4. Linear 티켓에 계획 기록
5. 엔지니어에게 검토 요청

> Cursor의 Plan 모드와 유사하다. 위험도가 높거나 복잡한 작업에서 활용한다.

### 4.3 Explain 모드

코드 변경 없이, **시스템 상태나 에러를 분석하고 설명**한다.

**워크플로우**:

1. Slack에서 `cloudbot explain [이슈 설명]` 호출
2. DataDog, Sentry, Amplitude 등에서 관련 데이터 수집
3. 에러 로그, 메트릭, 사용자 이벤트 종합 분석
4. 근본 원인 파악 및 설명 제공

**활용 예시**:

```text
cloudbot explain why is Chintan's app not working right now?
→ DataDog 메트릭 + Sentry 에러 + Amplitude 이벤트 종합 분석
→ 근본 원인 및 영향 범위 설명
```

---

## 5. 개발자 경험과 도입 전략

### 5.1 Slack 네이티브 설계

Coinbase는 Slack을 핵심 도입 레버로 활용했다. "Slack에 무언가를 쓰는 비용은 제로이지만, Slack 질문에 답하는 비용은 막대하다."는 인식 하에, AI로 이 비용을 흡수하는 설계를 채택했다.

- **Cloudbot Playground 채널**: 전사 엔지니어가 자유롭게 실험하는 전용 채널
- **마찰 최소화**: 새로운 도구 학습 없이 기존 Slack 워크플로우에 통합

### 5.2 PR 스프린트 (PR Sprint)

팀 내 AI 도입 문화를 만들기 위해 "PR 스프린트" 이벤트를 도입했다.

- 15~30분 내에 대량의 버그를 수정하는 경쟁 방식
- 하룻밤에 200개 이상의 버그를 발견하고 처리
- 엔지니어들의 자발적 참여와 팀 내 바이럴 효과

### 5.3 성과 및 목표

| 지표 | 현재 | 목표 |
|---|---|---|
| PR 사이클 | ~150시간 | 5분 이하 |
| 하룻밤 버그 처리 | 200+ | — |
| 도입 대상 | 1,000+ 엔지니어 | 전사 확대 |

---

## 6. 설계 인사이트

### 핵심 원칙: "컨텍스트가 가장 중요하다"

> "내가 깨달은 것은, 컨텍스트가 가장 중요한 것이다. 그래서 우리가 모든 컨텍스트를 수집하는 곳이 Linear이고, 그 Linear 컨텍스트로 에이전트를 트리거하면, 에이전트는 모든 MCP — DataDog, Sentry, Amplitude — 로 들어간다." — Chintan Turakhia

### 3가지 공통 설계 패턴

Stripe, Ramp, Coinbase 세 회사의 내부 코딩 에이전트는 독립적으로 구축되었음에도 다음 세 가지에 수렴했다:

| 패턴 | 설명 |
|---|---|
| **격리된 샌드박스** | 에이전트가 실수해도 프로덕션에 영향 없는 완전 격리 환경 |
| **Slack-first 진입점** | 기존 협업 도구에서 마찰 없이 에이전트 호출 |
| **풍부한 시작 컨텍스트** | 에이전트 실행 전 Linear/Slack/GitHub에서 최대한 컨텍스트 사전 수집 |

### Coinbase 특유의 차별점

| 요소 | Cloudbot의 접근 |
|---|---|
| 아키텍처 | 완전 자체 구축 (보안·컴플라이언스 우선) |
| 컨텍스트 | Linear 단일 소스 집중 |
| 검증 | Agent Council 기반 코드 리뷰 + 위험도별 자동/수동 머지 |
| 채택 | PR 스프린트, Cloudbot Playground 채널로 자발적 확산 |

---

## 참고 자료

- [Coinbase: Building Enterprise AI Agents at Coinbase](https://www.coinbase.com/blog/building-enterprise-AI-agents-at-Coinbase)
- [How I AI: Coinbase Podcast (Chintan Turakhia, Sr. Director of Engineering)](https://www.youtube.com/watch?v=tidINuXB7PA)
- [LangChain: Open SWE — Open-Source Framework for Internal Coding Agents](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/)
- [Enough About Harnesses, Your Org Needs Its Own Coding Agent (@kishan_dahya)](https://x.com/kishan_dahya/status/2028971339974099317)
