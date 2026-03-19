# Coinbase Cloudbot: 설계 및 워크플로우 분석

## 1. 개요

공개 자료를 종합하면, Cloudbot은 Coinbase 내부의 Slack 중심 코딩/백그라운드 에이전트를 가리키는 이름으로 보인다.
다만 Coinbase 공식 블로그는 `Cloudbot`라는 이름과 내부 모드 구성을 직접 설명하지 않고, 대신 이 에이전트를 가능하게 하는 기반 인프라와 운영 원칙을 공개한다.

인터뷰와 공개 발언 기준으로는 버그 리포트, 피드백, 티켓 문맥에서 PR 작성과 문제 분석까지 이어지는 자동화 흐름이 핵심 사용 사례로 보인다.

### 공식적으로 확인된 기반 인프라

| 항목         | 공개 내용                                                                                         | 근거                                                    |
|------------|-----------------------------------------------------------------------------------------------|-------------------------------------------------------|
| 개발자용 AI 도구 | Cursor, Copilot, Claude Code 등을 전사적으로 도입                                                      | Tools for Developer Productivity, 2025-08-06          |
| 내부 MCP 통합  | GitHub, Linear 중심의 MCP 통합                                                                     | Tools for Developer Productivity, 2025-08-06          |
| 모델 인프라     | OpenAI-compatible router, 일일 1,500명+ 사용                                                       | Tools for Developer Productivity, 2025-08-06          |
| 접근 제어      | repository sensitivity matrix로 민감 리포지토리 접근 제어                                                 | Tools for Developer Productivity, 2025-08-06          |
| 에이전트 운영 원칙 | code-first, observability-first, tracing, evaluation harness, auditability, human-in-the-loop | Building enterprise AI agents at Coinbase, 2025-12-22 |

즉, `Cloudbot`의 존재와 방향성은 공개적으로 뒷받침되지만, 세부 워크플로우와 내부 명칭은 공식 문서보다 공개 발언과 2차 정리에 더 많이 의존한다.

---

## 2. 자체 구축 배경

다른 회사들이 오픈소스 에이전트를 포크하거나 기존 프레임워크 위에 구성한 것과 달리, Coinbase는 Cloudbot을 처음부터 직접 만든 사례로 반복 언급된다.

| 회사           | 에이전트         | 아키텍처 방식                           |
|--------------|--------------|-----------------------------------|
| Stripe       | Minions      | Goose 포크 (Fork)                   |
| Ramp         | Inspect      | OpenCode 기반 구성 (Compose)          |
| **Coinbase** | **Cloudbot** | **완전 자체 구축 (Build from Scratch)** |

### 자체 구축을 선택한 이유

Coinbase는 암호화폐 금융 플랫폼으로서 일반 기업과 다른 수준의 보안·컴플라이언스 요건을 갖는다.

- **보안 요건**: 결제·자산 관련 코드에 대한 엄격한 접근 제어
- **컴플라이언스**: 금융 규제 준수를 위한 감사 추적(Audit Trail) 필요
- **데이터 격리**: 외부 클라우드 에이전트에 내부 코드베이스 노출 불가

> "우리는 다른 보안 요건이 있어서 외부 에이전트로는 시작할 수 없었다." — Chintan Turakhia

Coinbase 공식 블로그에서도 **repository sensitivity matrix**를 운영하여 민감 리포지토리에 대한 에이전트 접근을 제어한다고 밝혔다.

---

## 3. 핵심 설계 결정

### 3.1 멀티 모델 지원

Cloudbot은 특정 LLM에 종속되지 않고, 작업 유형과 상황에 따라 **여러 모델을 선택적으로 활용**한다.
Claude, Gemini 등 다양한 모델을 목적에 맞게 조합한다.

참고: Coinbase 공식 블로그에서는 **OpenAI-compatible router**를 운영하며 1,500명 이상의 엔지니어가 매일 사용한다고 밝혔다.

### 3.2 Linear-first 컨텍스트

Linear 티켓은 Cloudbot 관련 공개 발언에서 가장 자주 등장하는 컨텍스트 허브다.
다만 공식 문서가 직접 확인하는 범위는 GitHub/Linear MCP 통합까지이며, "모든 컨텍스트의 단일 진실 공급원"이라는 표현은 공식 문서에 없다.

```text
Slack 버그 리포트 → Linear Agent로 티켓 자동 생성
→ Cloudbot이 티켓 컨텍스트 기반으로 실행
→ MCPs(DataDog, Sentry, Amplitude 등)로 추가 정보 수집
```

> "내가 깨달은 것은, 컨텍스트가 가장 중요한 것이다. 그래서 우리가 모든 컨텍스트를 수집하는 곳이 Linear이고, 그 Linear 컨텍스트로 에이전트를 트리거하면, 에이전트는 모든 MCP — DataDog,
> Sentry, Amplitude — 로 들어간다." — Chintan Turakhia

참고: Coinbase 공식 블로그에서는 GitHub/Linear MCP 통합을 확인했으나, "Linear가 단일 진실 공급원"이라는 표현은 공식 문서에서 직접 확인되지 않았다.

### 3.3 In-house Sandbox

Coinbase는 에이전트를 자사 인프라에 호스팅하고, 접근 제어와 감사 가능성을 갖춘 방식으로 운영한다고 밝혔다.
Cloudbot 전용 샌드박스의 내부 구현 상세는 공개되지 않았지만, "사내 호스팅 + 강한 통제"라는 방향은 공식 문서와 일치한다.

| 공식적으로 확인된 요소 | 내용                                            |
|--------------|-----------------------------------------------|
| 자사 인프라 호스팅   | agent는 Coinbase 인프라 안에서 운영되어야 함               |
| 접근 제어        | repository sensitivity matrix로 민감 코드 접근 제한    |
| 추적/평가        | tracing, evaluation harness, curated datasets |
| 감사/승인        | immutable record, human-in-the-loop           |

공식 블로그에서 에이전트를 **코드-우선, 관측 가능, 평가 가능, 감사 가능**하게 구축한다고 밝혔다.

### 3.4 MCPs + Custom Skills

에이전트는 MCP 서버와 Custom Skills를 통해 내부 시스템과 통합된다.

| 도구            | 역할                 |
|---------------|--------------------|
| Datadog MCP   | 성능 메트릭, 알림 조회      |
| Sentry MCP    | 에러 트래킹, 스택 트레이스 분석 |
| Amplitude MCP | 사용자 행동 데이터 분석      |
| GitHub MCP    | 코드 탐색, PR 생성       |
| Custom Skills | 내부 시스템 특화 기능       |

참고: 공식 블로그에서는 GitHub/Linear 중심의 MCP 통합을 확인했으나, DataDog/Sentry/Amplitude의 구체적 MCP 연동은 공개 발언과 2차 정리에 의존한다.

---

## 4. 공개 자료에 반복 등장하는 3가지 상호작용 패턴

아래 세 패턴은 공개 발언과 외부 정리에 반복 등장하지만, Coinbase 공식 문서가 제품 명세처럼 직접 공개한 내부 명칭은 아니다.

### 4.1 PR 생성 패턴

가장 자주 언급되는 흐름은 이슈나 티켓 문맥에서 Pull Request까지 이어지는 자동화다.

**워크플로우**:

1. Slack 스레드 또는 피드백 워크플로우에서 에이전트를 호출
2. GitHub/Linear 중심의 문맥을 로드
3. 필요 시 모니터링/제품 데이터 등 추가 정보를 수집
4. 사내 환경에서 구현 또는 수정안을 생성
5. GitHub에 PR 또는 Draft PR을 생성

### 4.2 계획 작성 패턴

코드를 작성하지 않고, **구현 계획만 수립**하여 Linear에 기록한다.

**워크플로우**:

1. Slack 또는 티켓 문맥에서 에이전트를 호출
2. 티켓 분석 및 구현 방향 검토
3. 상세 구현 계획 작성
4. 작업 항목이나 스레드에 계획 기록, 인간 검토 대기

### 4.3 설명/분석 패턴

코드 변경 없이, **시스템 상태나 에러를 분석하고 설명**한다.

**워크플로우**:

1. Slack 또는 운영 이슈 문맥에서 에이전트를 호출
2. 로그, 메트릭, 사용자 이벤트 등 관련 데이터 수집 가능
3. 에러 로그와 운영 신호를 종합 분석
4. 근본 원인 파악 및 설명 제공

---

## 5. 검증 및 승인 파이프라인

Coinbase 공식 블로그에서 직접 확인되는 검증 요소는 아래와 같다.

- 모든 도구 호출, 검색, 결정, 출력이 **추적(traced)**됨
- 결정론적 데이터 단계와 LLM 단계를 분리하고, LLM 단계는 **evaluation harness**와 큐레이션된 데이터셋으로 관리
- **human-in-the-loop**를 의도적인 시스템 구성 요소로 둠
- 각 실행마다 입력, 사용 데이터, 판단 과정, 승인 주체를 남기는 **immutable record**를 생성

LangChain 블로그 비교표에서는 Cloudbot의 검증 방식이 **"Agent Councils + Auto-merge"**로 기재되어 있다.
다만 Coinbase 공식 문서는 Agent Council의 구조와 자동 머지 조건을 공개하지 않았다.

아래 도식은 외부 출처 기반 추정이다:

```text
PR 생성 → Agent Council (복수 에이전트 리뷰) → 변경 위험도 평가
├── 낮음 (텍스트, 설정 등) → 자동 머지 (Auto-merge)
├── 중간 → 인간 리뷰 요청
└── 높음 (결제, 보안) → 엄격한 인간 리뷰 + 컴플라이언스 검토
```

즉, 공식적으로 확인된 것은 `추적`, `평가`, `감사`, `인간 승인`이고, `Agent Council + Auto-merge`는 그 위에 얹힌 외부 추정 레이어다.

---

## 6. AI 도입 전략

### 6.1 Cursor 전사 도입

- 2025년 2월까지 **모든 Coinbase 엔지니어가 Cursor 사용**
- DevX 팀이 GitHub, Linear MCP 서버를 자체 개발하여 Cursor와 통합
- "Cursor Wins" Slack 채널에서 성공 사례 공유 → 조직 내 바이럴 확산
- 엔지니어 리더가 직접 핸즈온 시연하여 도입 드라이브

### 6.2 PR 스프린트 (PR Sprint)

팀 내 AI 도입 문화를 만들기 위해 "PR 스프린트" 이벤트를 도입했다.

- 15~30분 내에 대량의 버그를 수정하는 경쟁 방식
- **100명의 엔지니어가 15분 만에 약 70개 PR 생성** (출처에 따라 70~75로 표기)
- 하룻밤에 200개 이상의 버그를 발견하고 처리
- 엔지니어들의 자발적 참여와 팀 내 바이럴 효과

### 6.3 자동화 우선순위

Coinbase는 수동적이고, 시간 소모적이며, 의사결정이 많은 작업을 우선 자동화했다:

1. **Summarize and triage**: 요약 및 분류
2. **Collect and compare**: 수집 및 비교
3. **Draft with references for a human to approve**: 참조 기반 초안 작성, 인간 승인

---

## 7. 성과

| 지표             | Before | After         |
|----------------|--------|---------------|
| PR 리뷰 시간       | ~150시간 | ~15시간         |
| 피드백 → 기능 배포    | 수 주    | 수 분           |
| AI 에이전트 PR 비율  | —      | 전체 머지 PR의 ~5% |
| 엔지니어 AI 플랫폼 사용 | —      | 1,500명+ 매일 사용 |

---

## 8. 3사 내부 코딩 에이전트 비교

Coinbase(Cloudbot), Stripe(Minions), Ramp(Inspect)는 독립적으로 구축했으나 유사한 패턴에 수렴했다.

| 항목      | Coinbase Cloudbot           | Stripe Minions                | Ramp Inspect                   |
|---------|-----------------------------|-------------------------------|--------------------------------|
| 아키텍처 방식 | 완전 자체 구축                    | Goose 포크                      | OpenCode 기반 구성                 |
| 실행 환경   | In-house Sandbox            | AWS EC2 devboxes (pre-warmed) | Modal containers (pre-warmed)  |
| 도구      | MCPs + Custom Skills        | ~500개, 에이전트별 큐레이션             | OpenCode 내장                    |
| 오케스트레이션 | PR/계획/설명 패턴                 | Blueprints (결정론적 + 에이전틱)      | —                              |
| 검증      | Agent Councils + Auto-merge | —                             | Visual DOM verification        |
| 호출 방식   | Slack-native                | Slack + embedded buttons      | Slack + web + Chrome extension |

### 공통 설계 패턴

1. **격리된 실행 환경**: 클라우드 샌드박스에서 전체 권한 부여, 프로덕션은 차단
2. **큐레이션된 도구셋**: 축적이 아닌 선별된 도구 유지
3. **Slack-first 호출**: 기존 워크플로우에서 마찰 없이 에이전트 호출
4. **풍부한 시작 컨텍스트**: Linear, Slack, GitHub에서 사전 정보 수집
5. **서브에이전트 오케스트레이션**: 복잡한 작업을 전문화된 하위 에이전트에 분배

---

## 9. 설계 인사이트

### Coinbase 특유의 차별점

| 요소    | 접근 방식                                       |
|-------|---------------------------------------------|
| 아키텍처  | 완전 자체 구축 (보안·컴플라이언스 우선)                     |
| 컨텍스트  | Linear 중심 수집                                |
| 검증    | Agent Council + 위험도별 자동/수동 머지               |
| 채택    | PR 스프린트, Slack 채널 기반 자발적 확산                 |
| 운영 원칙 | Observability-first (tracing, eval harness) |

### code-first graph 패턴

Coinbase 공식 블로그에서 code-first graph 패턴 채택을 언급했다:

- "데이터" 노드(unit-tested)와 "LLM" 노드(evaluated)의 분리
- Observability, evaluation, human-in-the-loop 제어를 first-class 관심사로 부착
- 향후 LangGraph를 tracing, evaluation, logging에 활용할 계획

단, Cloudbot 자체가 LangGraph 위에 구축되었는지는 공개되지 않았다.

---

## 참고 자료

- [Coinbase: Building Enterprise AI Agents at Coinbase](https://www.coinbase.com/blog/building-enterprise-AI-agents-at-Coinbase)
- [Coinbase: Tools for Developer Productivity at Coinbase](https://www.coinbase.com/blog/Tools-for-Developer-Productivity-at-Coinbase)
- [How I AI: Coinbase Podcast (Chintan Turakhia)](https://www.youtube.com/watch?v=tidINuXB7PA)
- [Lenny's Newsletter: How Coinbase Scaled AI to 1,000+ Engineers](https://www.lennysnewsletter.com/p/how-coinbase-scaled-ai-to-1000-engineers)
- [LangChain: Open SWE — Open-Source Framework for Internal Coding Agents](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/)
- [Ry Walker Research: Coinbase Cloudbot](https://rywalker.com/research/coinbase-claudebot)
