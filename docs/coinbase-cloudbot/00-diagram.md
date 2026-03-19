# Cloudbot 아키텍처 다이어그램

> 아래 다이어그램은 공개 인터뷰, LangChain 블로그 비교표, 2차 분석 자료를 종합하여 재구성한 것이다.
> Coinbase 공식 문서에서 Cloudbot 내부 아키텍처를 직접 공개한 사례는 확인되지 않았다.
> 공식 블로그로 직접 확인된 기반과, Cloudbot 관련 공개 발언에서 재구성한 흐름을 구분해 읽는 것이 안전하다.

## 1. 공개 자료 기준 전체 그림

```mermaid
graph TB
    subgraph L1["공식적으로 확인된 기반"]
        MCP["GitHub / Linear MCP"]
        ROUTER["OpenAI-compatible router<br/>일일 1,500명+ 사용"]
        SAFE["Repository sensitivity matrix<br/>Tracing · Eval · Auditability"]
    end

    subgraph L2["Cloudbot 관련 재구성"]
        SL["💬 Slack / 피드백 스레드"]
        AG["🤖 Slack-native background agent<br/>(Cloudbot로 알려짐)"]
        EXT["🔌 추가 도구 연동?<br/>Datadog · Sentry · Amplitude"]
        OUT["🧾 PR 작성 · 계획 메모 · 이슈 설명"]
    end

    SL --> AG
    MCP --> AG
    ROUTER --> AG
    SAFE --> AG
    AG --> EXT
    AG --> OUT
    EXT --> OUT
    style L1 fill: #e3f2fd, stroke: #1565C0
    style L2 fill: #fce4ec, stroke: #C62828
```

## 2. 공개 자료에 반복 등장하는 상호작용 패턴

> `Create PR / Plan / Explain`이라는 명칭과 분류는 공개 발언과 2차 정리를 바탕으로 재구성한 것이다.
> Coinbase 공식 문서에서 내부 명령어 또는 제품 명세 형태로 공개한 것은 아니다.

```mermaid
flowchart TD
    INPUT(["Slack 또는 피드백 트리거"]) --> LINEAR["GitHub / Linear 컨텍스트 확인"]
    LINEAR --> MODE{"재구성된 패턴"}
    MODE -->|" PR 작성 "| CPR
    MODE -->|" 계획 작성 "| PLAN
    MODE -->|" 이슈 설명 "| EXP

    subgraph CPR["🔨 PR 작성 패턴"]
        CPR1["이슈 / 티켓 문맥 로드"] --> CPR2["추가 정보 수집 가능"]
        CPR2 --> CPR3["사내 환경에서 구현"]
        CPR3 --> CPR4["PR 또는 Draft PR 생성"]
    end

    subgraph PLAN["📝 계획 작성 패턴"]
        PLAN1["티켓 분석"] --> PLAN2["구현 계획 수립"]
        PLAN2 --> PLAN3["작업 항목 또는 스레드에 기록"]
    end

    subgraph EXP["🔍 이슈 설명 패턴"]
        EXP1["로그 / 메트릭 / 문맥 조회 가능"] --> EXP2["에러 분석"]
        EXP2 --> EXP3["근본 원인 파악 · 결과 회신"]
    end
```

## 3. 컨텍스트 파이프라인

공개 발언 기준으로는 Linear가 중요한 컨텍스트 허브로 반복 등장한다.
공식 문서로 직접 확인되는 것은 GitHub/Linear MCP 통합이며, 추가 도구 연동은 공개 발언과 2차 정리에 더 의존한다.

```mermaid
flowchart LR
    subgraph INPUT["입력 소스"]
        SL["Slack 스레드"]
        GH["GitHub"]
        LI["Linear"]
    end

    subgraph LINEAR_LAYER["공식적으로 확인된 컨텍스트 기반"]
        MCP["GitHub / Linear MCP"]
        TICKET["이슈 / 티켓 문맥"]
    end

    subgraph MCP_LAYER["추가 도구 연동 (재구성)"]
        DD["Datadog?"]
        ST["Sentry?"]
        AMP["Amplitude?"]
    end

    SL --> MCP
    GH --> MCP
    LI --> MCP
    MCP --> TICKET
    TICKET --> DD
    TICKET --> ST
    TICKET --> AMP
    MCP --> AGENT["Cloudbot 실행"]
    DD & ST & AMP --> AGENT
```

## 4. 검증 및 병합 파이프라인

> 공식 블로그로 직접 확인되는 것은 tracing, evaluation harness, human-in-the-loop, immutable record다.
> `Agent Councils + Auto-merge`는 LangChain 비교표와 외부 정리에서 반복되지만, 내부 동작 상세는 공개되지 않았다.

```mermaid
flowchart TD
    PR_GEN(["PR 생성"]) --> OFFICIAL["Tracing · Artifacts · Eval Harness<br/>(공식)"]
    OFFICIAL --> HUMAN["Human review / approval owner<br/>(공식)"]
    OFFICIAL --> COUNCIL["Agent Council + risk-based merge?<br/>(2차 정리)"]
    COUNCIL --> HUMAN
    HUMAN --> MERGED(["머지 / 후속 조치"])
```

## 5. 3사 내부 코딩 에이전트 비교

```mermaid
graph LR
    subgraph CB["Coinbase Cloudbot"]
        CB1["자체 구축"]
        CB2["In-house Sandbox"]
        CB3["MCPs + Skills"]
        CB4["Agent Councils"]
    end

    subgraph SM["Stripe Minions"]
        SM1["Goose 포크"]
        SM2["AWS EC2 devboxes"]
        SM3["~500 도구"]
        SM4["Blueprints"]
    end

    subgraph RI["Ramp Inspect"]
        RI1["OpenCode 기반"]
        RI2["Modal containers"]
        RI3["OpenCode 내장"]
        RI4["Visual DOM 검증"]
    end

    COMMON["공통 패턴:<br/>격리 샌드박스<br/>Slack-first<br/>풍부한 컨텍스트<br/>서브에이전트"]
    CB --- COMMON
    SM --- COMMON
    RI --- COMMON
```
