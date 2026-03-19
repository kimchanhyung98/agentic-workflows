# 로컬 개발 자동화 에이전트 아키텍처 Diagram

Stripe Minions의 하네스 중심 설계, Open SWE의 상태/샌드박스 관리, OpenCode Worktree의 격리 실행,
Oh My OpenAgent의 위임·폴백 체계, Agentic Workflow / Design Pattern 문서의 패턴 분류를 바탕으로 재구성한 아키텍처입니다.

핵심은 특정 모델 하나를 고도화하는 것이 아니라, **AI CLI를 역할별 컴포넌트로 배치하고 그 주변에 권한, 게이트, 상태, 재시도, 에스컬레이션을 구조로 강제하는 것**입니다.

> Minions: "Not exotic — just great engineering"
> 로컬 에이전트: 에이전트를 만드는 것이 아니라, **에이전트가 동작하는 환경을 설계**한다.

---

## 전체 아키텍처

7개 레이어를 따라, 여러 AI CLI 세션이 서로 다른 권한으로 협력합니다.
`입력 수집 → 실행 문맥 생성 → 컨텍스트/기획 → 승인 → 격리 실행 → 검증/복구 → 산출물 발행`

- 🧠 = LLM 단계 (창의적 판단)
- 🔒 = Gate 단계 (결정론적 검증 — 우회 불가)
- 👤 = Human 단계 (사람의 판단)
- ❌ → = 실패 경로 (재시도 또는 에스컬레이션)

```mermaid
flowchart TB
    subgraph L1["<b>L1: Intake</b><br/>책임: 요청 수신 · 정규화 · 소스 인증<br/>권한: 읽기 전용 · 저장소 쓰기 금지"]
        CH_CLI["⌨️ CLI"]
        CH_WEB["🌐 Web UI"]
        CH_BOT["💬 Slack · Discord<br/>(OpenClaw)"]
        INTAKE["📥 요청 정규화<br/>이벤트 필터링 · source 판별<br/>출력: task request"]
        CH_CLI & CH_WEB & CH_BOT --> INTAKE
    end

    subgraph L2["<b>L2: Run Control</b><br/>책임: run 생성 · 상태 저장 · 큐잉 · 동시 실행 조율<br/>권한: 상태 저장소 쓰기 · 실행 plane 직접 쓰기 금지"]
        RUN["Run Manager<br/>run_id · session_id · 상태 추적"]
        QUEUE["Queue / Pending Messages<br/>(busy 시 적재)"]
        STORE["State Store<br/>status · retries · workspace_ref"]
    end

    subgraph L3["<b>L3: Context & Planning</b><br/>책임: 탐색 · 기획 문서 생성 · 기획 검증<br/>권한: repo 읽기 · 문서 생성 · <b>코드 변경 금지</b>"]
        DISCOVER["🔍 결정론적 탐색<br/>Augment Context MCP<br/>(시맨틱 검색 · 관계 · Git)"]
        RESEARCH["🌐 추가 조사 (선택)<br/>웹 검색 · 엣지케이스 · 주의사항"]
        AI_CTX["📂 AI 컨텍스트 (선택)<br/>도메인 · 데이터 모델 · API"]
        PLAN_CLI["🧠 Main AI CLI<br/>Claude Code / Codex / Gemini CLI<br/>기획 문서 작성"]
        PLAN_DOC["📋 Plan Doc<br/>기획안 · 작업 계획 · 테스트 개요<br/>주의사항 · 애매한 판단"]
        PLAN_REVIEW["🔒 멀티 AI 리뷰<br/>(기획 검증)"]
    end

    subgraph L4["<b>L4: Approval & Policy</b><br/>책임: 사람 승인 · 정책 적용 · 권한 토큰 발급<br/>권한: 승인 전 write/publish 금지"]
        HUMAN["👤 Human Approval<br/>방향 · 범위 · 테스트 확인<br/>애매한 판단 결정"]
        POLICY["🔒 Policy Gate<br/>권한 · 모드 · 금지 규칙"]
        TOKEN["✅ Execution Grant<br/>write 권한 부여<br/>scope: workspace 내부만"]
    end

    subgraph L5["<b>L5: Execution Plane</b><br/>책임: 격리 workspace · 코드 수정<br/>권한: 승인된 workspace 내부 쓰기만 · main repo 직접 쓰기 금지"]
        WS["🖥️ Workspace Manager<br/>Worktree / VM / Docker"]
        EXEC_A["🧠 Executor AI CLI A<br/>(코드 수정 · 테스트)"]
        EXEC_B["🧠 Executor AI CLI B<br/>(병렬 가능)"]
        SECRETS["🔐 Scoped Secrets / Env<br/>최소 범위만 주입"]
    end

    subgraph L6["<b>L6: Verification & Recovery</b><br/>책임: 결정론적 검증 · 병렬 리뷰 · 자동 수정 제어<br/>권한: 검증 실행 · review 생성 · <b>publish 직접 금지</b>"]
        GATE_DET["🔒 Deterministic Gates<br/>format · lint · typecheck · test"]
        GATE_INT["🔒 Integration Checks<br/>(선별적 · 선택적)"]
        REV_A["🧠 Reviewer AI CLI A<br/>기획 대조 · 요구사항"]
        REV_B["🧠 Reviewer AI CLI B<br/>경계 조건 · 사이드 이펙트"]
        REV_C["🧠 Reviewer AI CLI C<br/>테스트 누락 · 버그"]
        JUDGE["🧠 Judge Controller<br/>종합 판정 · 재시도 관리"]
        FIX["🧠 자동 수정<br/>구조화된 피드백 기반"]
    end

    subgraph L7["<b>L7: Output & Trace</b><br/>책임: commit/PR · 실패 리포트 · 추적 보존<br/>권한: <b>publish 권한은 이 레이어만 보유</b>"]
        OUT_PR["✅ Commit / PR"]
        OUT_FAIL["📋 Failure Report"]
        TRACE["🧾 Artifact Store<br/>plan · diff · gate logs · review docs"]
        NOTIFY["📢 알림<br/>(CLI 출력 / Web / 메신저)"]
    end

%% L1 → L2
    INTAKE --> RUN
    RUN --> QUEUE
    RUN --> STORE
%% L2 → L3
    RUN --> DISCOVER
    DISCOVER -->|" AI 판단 "| RESEARCH
    DISCOVER -->|" 존재 시 "| AI_CTX
    DISCOVER & RESEARCH & AI_CTX --> PLAN_CLI --> PLAN_DOC --> PLAN_REVIEW
%% L3 실패 전이
    PLAN_REVIEW -->|" ❌ 부족 "| DISCOVER
%% L3 → L4
    PLAN_REVIEW -->|" ✅ 충분 "| HUMAN
    HUMAN -->|" ❌ 수정 요청 "| PLAN_DOC
    HUMAN -->|" ✅ 승인 "| POLICY --> TOKEN
%% L4 → L5
    TOKEN --> WS
    SECRETS --> WS
    WS --> EXEC_A & EXEC_B
%% L5 → L6
    EXEC_A & EXEC_B --> GATE_DET --> GATE_INT
    GATE_DET -->|" ❌ fail "| FIX
    GATE_INT -->|" ❌ fail "| FIX
    GATE_INT -->|" ✅ pass "| REV_A & REV_B & REV_C
    REV_A & REV_B & REV_C --> JUDGE
%% L6 분기
    JUDGE -->|" ✅ pass "| OUT_PR
    JUDGE -->|" ❌ fix "| FIX -->|" retry ≤ N "| EXEC_A
    JUDGE -->|" ❌ escalate "| OUT_FAIL
    FIX -->|" ❌ 한도 초과 "| OUT_FAIL
%% L7 산출물
    OUT_PR & OUT_FAIL --> TRACE
    OUT_PR & OUT_FAIL --> NOTIFY
%% 상태 참조 (점선)
    STORE -.-> PLAN_CLI
    STORE -.-> WS
    TRACE -.-> PLAN_REVIEW
    TRACE -.-> JUDGE
%% Workspace provisioning 실패
    WS -->|" ❌ provision fail "| RUN
%% 실패 리포트 → 사람
    OUT_FAIL -->|" 👤 사람 판단 "| PLAN_DOC
    style L1 fill: #e3f2fd, stroke: #1565C0
    style L2 fill: #e8f5e9, stroke: #2E7D32
    style L3 fill: #fff8e1, stroke: #F9A825
    style L4 fill: #fff3e0, stroke: #E65100
    style L5 fill: #ede7f6, stroke: #4527A0
    style L6 fill: #f3e5f5, stroke: #6A1B9A
    style L7 fill: #c8e6c9, stroke: #2E7D32
```

---

## 레이어별 책임 · 입력 · 출력 · 권한 · 실패 전이

| 레이어                            | 책임                               | 주요 입력                                  | 주요 출력                                | 허용 권한                              | 실패 시 전이                                                     | 참조 시스템                                                          |
|--------------------------------|----------------------------------|----------------------------------------|--------------------------------------|------------------------------------|-------------------------------------------------------------|-----------------------------------------------------------------|
| **L1 Intake**                  | 요청 정규화 · source 인증               | CLI/Web/메신저 이벤트                        | task request                         | 읽기 전용                              | 잘못된 입력 → 즉시 거부                                              | Open SWE (webhook 서명), Minions (4 Entry)                        |
| **L2 Run Control**             | run 생성 · 상태 · 큐잉 · 동시 실행 조율      | task request · 현재 상태                   | run context · session state          | 상태 저장소 쓰기                          | busy → queue 적재, 상태 손상 → infra recovery                     | Open SWE (Thread 상태 축적), OMO (Atlas 7-gate)                     |
| **L3 Context & Planning**      | 탐색 · 기획 생성 · 기획 검증               | run context · repo · docs              | context packet · plan doc            | repo 읽기 · 문서 생성 · **코드 변경 금지**     | 컨텍스트 부족 → 재탐색, 리뷰 실패 → 기획 반복                                | Minions (Context Hydration), LangChain (Progressive Disclosure) |
| **L4 Approval & Policy**       | 사람 승인 · 정책 적용 · 권한 토큰 발급         | plan doc · review 결과 · 정책              | execution grant · 승인/반려              | 승인 전 write 금지                      | 반려 → L3 회귀, 정책 위반 → block                                   | Cloudbot (Agent Council), design-pattern (Human-in-the-Loop)    |
| **L5 Execution Plane**         | 격리 workspace · AI CLI 실행 · 코드 수정 | execution grant · plan doc · workspace | diff · workspace logs                | workspace 내부만 쓰기                   | provision 실패 → reprovision, CLI crash → retry               | Minions (Devbox), OpenCode (Worktree 격리)                        |
| **L6 Verification & Recovery** | 결정론적 검증 · 병렬 리뷰 · 자동 수정 루프       | diff · test logs · review artifacts    | gate report · review docs · 판정       | 검증 실행 · review 생성 · **publish 금지** | gate fail → self-fix, review fail → fix loop, 초과 → escalate | Minions (3-Tier), OMO (모델 폴백 + Circuit Breaker)                 |
| **L7 Output & Trace**          | commit/PR · 실패 리포트 · 추적 보존       | 최종 판정 · gate 결과                        | commit · PR · failure report · trace | **publish 권한은 이 레이어만**             | publish 실패 → 재시도/사람 전달                                      | Open SWE (commit_and_open_pr), Minions (PR 템플릿)                 |

---

## AI CLI 역할 분리

AI CLI는 단일 주체가 아니라 **역할별 런타임**입니다.
같은 CLI를 써도 세션과 권한을 분리해야 하며, 오케스트레이터 · 실행자 · 리뷰어가 같은 권한을 공유하면 구조가 무너집니다.
OMO의 9 에이전트 + 역할별 도구 제한, Open SWE의 Thread 기반 세션 격리를 참조합니다.

```mermaid
graph LR
    TASK["작업 요청"]
    MAIN["🧠 Main AI CLI<br/>Claude Code / Codex / Gemini CLI<br/>역할: 오케스트레이션 · 계획 · 상태 판단"]
    RESEARCH["🔍 Research AI CLI<br/>역할: 외부 문서 조사<br/>권한: <b>읽기 전용</b>"]
    EXEC["⚡ Executor AI CLI Pool<br/>역할: 코드 수정 · 테스트 · 수정 루프<br/>권한: <b>workspace 내부만</b>"]
    REVIEW["🤖 Reviewer AI CLI Pool<br/>역할: plan/diff/log 검토 · 병렬 리뷰<br/>권한: <b>읽기 + review 문서 생성</b>"]
    JUDGE["⚖️ Judge Controller<br/>역할: 결과 종합 · fix/escalate 판정<br/>권한: <b>판정만 · 코드 수정 금지</b>"]
    STATE["🧾 Run State / Artifact Store"]
    TASK --> MAIN
    MAIN --> RESEARCH
    MAIN --> EXEC
    MAIN --> REVIEW
    RESEARCH --> MAIN
    EXEC --> STATE
    REVIEW --> STATE
    STATE --> JUDGE
    JUDGE -->|" fix "| EXEC
    JUDGE -->|" pass / escalate "| MAIN
    style MAIN fill: #e3f2fd, stroke: #1565C0
    style RESEARCH fill: #fff8e1, stroke: #F9A825
    style EXEC fill: #ede7f6, stroke: #4527A0
    style REVIEW fill: #f3e5f5, stroke: #6A1B9A
    style JUDGE fill: #fff3e0, stroke: #E65100
```

### 역할별 권한 계약

| 역할                   | 권한                                       | 금지 사항                          |
|----------------------|------------------------------------------|--------------------------------|
| **Main AI CLI**      | 요청 해석, 기획 문서 작성, 워크플로우 분기 결정             | 승인 전 코드 수정, 직접 publish         |
| **Research AI CLI**  | 문서/레퍼런스 탐색, 읽기 전용 분석                     | 코드 수정, commit, PR              |
| **Executor AI CLI**  | 승인된 workspace 안에서 코드 수정, 테스트 실행          | main repo 직접 쓰기, 승인 없는 publish |
| **Reviewer AI CLI**  | plan doc · diff · gate logs 검토, 리뷰 문서 생성 | 코드 수정, commit, PR              |
| **Judge Controller** | pass/fix/escalate 판정, 재시도 카운트 관리         | 코드 직접 수정                       |

---

## 시퀀스 흐름

액터 간 시간 순서의 상호작용입니다.
7개 레이어를 통과하는 전체 실행 흐름을 보여줍니다.

```mermaid
sequenceDiagram
    actor User as 👤 사용자
    participant Entry as L1: Intake
    participant Run as L2: Run Control
    participant Main as L3: Main AI CLI
    participant MCP as Augment Context MCP
    participant MAR as 멀티 AI 리뷰
    participant Human as L4: 👤 Approval
    participant WS as L5: Workspace
    participant Exec as L5: Executor CLI
    participant Gate as L6: Gate
    participant Judge as L6: Judge
    participant Git as L7: Output
    User ->> Entry: 작업 요청
    Entry ->> Run: task request (정규화)
    Run ->> Run: run_id · session_id 생성
    alt 기존 run busy
        Run ->> Run: queue 적재 → dequeue 대기
    end

    rect rgb(255, 248, 225)
        Note over Main, MAR: L3: Context & Planning
        Run ->> Main: run context
        Main ->> MCP: 프로젝트 탐색
        MCP -->> Main: 시맨틱 검색 결과
        opt AI 판단: 추가 조사 필요
            Main ->> Main: 웹 검색 · 엣지케이스
        end
        Main ->> Main: 📋 Plan Doc 작성
        loop 멀티 AI 리뷰 통과할 때까지
            Main ->> MAR: 기획 검증 요청
            MAR -->> Main: 통과 / 피드백
        end
    end

    rect rgb(255, 243, 224)
        Note over Human: L4: Approval & Policy
        Main ->> Human: Plan Doc 공유
        alt 수정 요청
            Human -->> Main: 피드백 → L3 복귀
        else 승인
            Human -->> Main: Execution Grant 발급
        end
    end

    rect rgb(237, 231, 246)
        Note over WS, Judge: L5 + L6: Execution & Verification
        Main ->> WS: workspace 준비 (worktree/VM/Docker)
        WS -->> Exec: 격리 환경 + scoped secrets

        loop 자동 수정 (max N회)
            Exec ->> Exec: ✏️ 코드 작성 (Plan Doc 기준)
            loop 내부 루프: Gate 통과까지
                Exec ->> Gate: format · lint · typecheck · test
                Gate -->> Exec: 통과 / 오류 목록
            end
            Exec ->> MAR: 코드 검증 (diff + Plan Doc)
            MAR -->> Judge: review docs
            Judge ->> Judge: 종합 판정
            alt fix
                Judge -->> Exec: 구조화된 피드백
            end
        end
    end

    rect rgb(200, 230, 201)
        Note over Git: L7: Output & Trace
        alt pass
            Judge ->> Git: Commit / PR 생성
            Git -->> User: 완료 알림
        else escalate
            Judge ->> Git: 📋 실패 리포트
            Git -->> User: 실패 알림
        end
    end
```

---

## 상태 전이와 실패 전이

`요청 수신`에서 `PR 발행` 또는 `실패 보고`까지의 핵심 경로와, 각 실패가 어디로 되돌아가는지를 보여줍니다.

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Queued: 기존 run busy
    Received --> Preparing: 즉시 처리 가능
    Queued --> Preparing: dequeue
    Preparing --> PlanReviewed: plan doc + AI 리뷰 완료
    PlanReviewed --> AwaitingApproval
    AwaitingApproval --> Preparing: 사람 반려 / 수정 요청
    AwaitingApproval --> Provisioning: 승인 (Execution Grant)
    Provisioning --> Executing: workspace 준비 성공
    Provisioning --> ProvisionRetry: 일시적 infra 실패
    ProvisionRetry --> Provisioning
    ProvisionRetry --> Escalated: 재시도 초과
    Executing --> DeterministicChecks
    DeterministicChecks --> Executing: gate fail → self-fix
    DeterministicChecks --> AIReview: gate pass
    AIReview --> Executing: fix 필요
    AIReview --> ReadyToPublish: 통과
    AIReview --> Escalated: retry 초과 / 위험
    ReadyToPublish --> Publishing
    Publishing --> Published: commit / PR 성공
    Publishing --> Escalated: publish 실패
    Escalated --> [*]
    Published --> [*]
```

---

## 오류 분류와 처리 정책

| 오류 클래스             | 예시                              | 감지 레이어          | 기본 처리                       | 최종 전이                    |
|--------------------|---------------------------------|-----------------|-----------------------------|--------------------------|
| **입력 오류**          | source 포맷 불일치, 필수 정보 누락         | L1 Intake       | 즉시 reject 또는 보완 요청          | 종료 또는 Received           |
| **상태 충돌**          | 기존 run busy, 중복 요청              | L2 Run Control  | queue 적재 또는 interrupt       | Queued                   |
| **컨텍스트 부족**        | 관련 파일 식별 실패, 문서 부족              | L3 Context      | 재탐색, 추가 조사                  | Preparing                |
| **기획 리뷰 실패**       | 기획 논리 부족, 완성도 미달                | L3 멀티 AI 리뷰     | 피드백 반영 후 재작성                | Preparing                |
| **승인 실패**          | 범위 과다, plan 부실                  | L4 Approval     | plan 수정 후 재제출               | Preparing                |
| **정책 위반**          | 승인 없는 publish, 금지 경로 수정         | L4 Policy Gate  | 즉시 block                    | Escalated                |
| **workspace 실패**   | worktree 생성 실패, sandbox boot 실패 | L5 Execution    | infra retry                 | Provisioning / Escalated |
| **CLI runtime 오류** | 프로세스 crash, JSON 파싱 실패          | L5/L6           | same-run retry, CLI 재시작     | Executing / Escalated    |
| **Gate 실패**        | lint/test/typecheck 실패          | L6 Verification | self-fix loop (내부 루프)       | Executing                |
| **리뷰 실패**          | 요구사항 누락, 회귀 위험                  | L6 Verification | structured fix loop (외부 루프) | Executing / Escalated    |

---

## 검증 · 리뷰 · 자동 수정 파이프라인 (L6)

핵심은 **빠른 내부 루프**(결정론적 Gate)와 **비싼 외부 루프**(멀티 AI 리뷰)를 분리하는 것입니다.
Minions의 3-Tier(Local Lint → CI → Self-Fix)와 OMO의 다층 회복을 조합합니다.

```mermaid
flowchart TB
    START["Executor AI CLI 결과<br/>diff + logs"]

    subgraph Inner["내부 루프: 결정론적 Gate (빠름 · 저비용)"]
        G1["format / lint"]
        G2["typecheck"]
        G3["unit / local test"]
    end

    subgraph Outer["외부 루프: 심화 검증 (느림 · 고비용)"]
        G4["selective / integration check"]
        RV["🤖 병렬 Reviewer AI CLI<br/>A: 기획 대조 · 요구사항<br/>B: 경계 조건 · 사이드 이펙트<br/>C: 테스트 누락 · 버그"]
        JD{"⚖️ Judge 판정"}
        FIX["🧠 구조화된 피드백 기반 수정"]
        COUNT{"retry ≤ N?"}
    end

    START --> G1 --> G2 --> G3
    G1 -->|" ❌ fail "| FIX
    G2 -->|" ❌ fail "| FIX
    G3 -->|" ❌ fail "| FIX
    G3 -->|" ✅ pass "| G4
    G4 -->|" ❌ fail "| FIX
    G4 -->|" ✅ pass "| RV --> JD
    JD -->|" ✅ pass "| DONE["✅ publish 후보 → L7"]
    JD -->|" ❌ fix "| FIX
    JD -->|" ❌ escalate "| FAIL["📋 failure report → L7"]
    FIX --> COUNT
    COUNT -->|" yes "| START
    COUNT -->|" no "| FAIL
    style Inner fill: #e3f2fd, stroke: #1565C0
    style Outer fill: #ede7f6, stroke: #4527A0
    style DONE fill: #c8e6c9, stroke: #2E7D32
    style FAIL fill: #ffcdd2, stroke: #C62828
```

### 재시도 규칙

| 실패 유형                       | 처리 방식                       | 카운트                   |
|-----------------------------|-----------------------------|-----------------------|
| lint / type / local test 실패 | executor 즉시 수정 후 재실행        | 내부 루프 (별도 카운트 또는 저비용) |
| integration / selective 실패  | self-fix 루프 진입              | 외부 retry 카운트          |
| AI review 실패                | structured feedback 기반 수정   | 외부 retry 카운트          |
| reviewer 간 불일치              | judge가 escalate 또는 보수적 fail | retry 미소비 또는 1회 소모    |
| retry 한도 초과                 | failure report 작성 → 사람 전달   | 종료                    |

---

## 멀티 AI 리뷰 모듈 (공유 컴포넌트)

L3(기획 검증)과 L6(코드 검증)에서 **동일 모듈을 재사용**합니다.
Minions(단일 AI Review)와 달리 복수 모델의 교차 검증으로 사각지대를 보완합니다.

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1["산출물<br/>(plan doc / diff)"]
        I2["기준 문서<br/>(plan doc / 테스트 개요)"]
    end

    subgraph Parallel["병렬 리뷰 (동시 실행)"]
        direction TB
        R1["🧠 Reviewer A<br/>기획 대조 · 논리 검증"]
        R2["🧠 Reviewer B<br/>품질 · 엣지케이스"]
        R3["🧠 Reviewer C<br/>정합성 · 버그 탐지"]
    end

    subgraph Judgment["종합 판정"]
        AGG["⚖️ Judge Controller<br/>리뷰 종합 · 결정론적 판정"]
    end

    subgraph Output_R["출력"]
        PASS["✅ pass"]
        FIX_FB["❌ fix (구조화된 피드백)"]
        ESC["❌ escalate (위험 높음)"]
    end

    I1 & I2 --> R1 & R2 & R3
    R1 & R2 & R3 --> AGG
    AGG --> PASS & FIX_FB & ESC
    style Input fill: #fff8e1, stroke: #F9A825
    style Parallel fill: #ede7f6, stroke: #4527A0
    style Judgment fill: #fff3e0, stroke: #E65100
```

---

## 실행 경계와 권한 모델

workspace 유형이 **실행 권한과 실패 영향 범위**를 결정합니다.
`workspace boundary = permission boundary` 원칙입니다.

```mermaid
flowchart TD
    GRANT["✅ Execution Grant"] --> MODE{"실행 경계 선택"}
    MODE -->|" local-safe "| WT["🌿 Git Worktree<br/>브랜치 격리 · 파일 동기화 · 세션 포크"]
    MODE -->|" isolated "| BOX["🐳 VM / Docker Sandbox<br/>repo clone · env 주입 · 네트워크 정책"]
    WT --> EXEC["Executor AI CLI"]
    BOX --> EXEC
    style WT fill: #ede7f6, stroke: #4527A0
    style BOX fill: #fff8e1, stroke: #F9A825
    style EXEC fill: #e3f2fd, stroke: #1565C0
```

### 실행 경계별 권한 매트릭스

| 경계                    | 읽기                        | 쓰기               | 네트워크            | 비밀정보          | Git publish |
|-----------------------|---------------------------|------------------|-----------------|---------------|-------------|
| **L3 Prepare / Plan** | repo · docs · Git history | plan doc만        | 외부 문서 조회 가능     | 불필요           | 금지          |
| **L6 Review**         | plan doc · diff · logs    | review doc만      | 모델 API 호출 수준    | 불필요           | 금지          |
| **L5 Local Worktree** | worktree 내부 전체            | worktree 내부만     | 프로젝트 정책에 따름     | 최소 env        | 금지          |
| **L5 VM / Docker**    | sandbox 내부 repo           | sandbox 내부만      | 차단 또는 allowlist | scoped secret | 금지          |
| **L7 Output**         | final diff · gate report  | commit · PR body | Git hosting 접근  | publish 최소 토큰 | **허용**      |

---

## Plan Doc 구조

Plan Doc은 시스템의 핵심 산출물이자 계층 간 계약(contract)입니다.

```mermaid
graph TB
    subgraph Sources["입력 소스"]
        S1["🔍 Augment Context MCP"]
        S2["🌐 추가 조사"]
        S3["📂 AI 컨텍스트"]
    end

    subgraph PlanDoc["📋 Plan Doc (6개 필수 필드)"]
        direction TB
        D1["① 컨텍스트 요약 — 판단 근거"]
        D2["② 변경 목표 — 무엇을 왜 바꾸는지"]
        D3["③ 수정 파일 후보 — 실행 범위 제한"]
        D4["④ 테스트 시나리오 — gate 기준"]
        D5["⑤ 주의사항 / edge cases — 조사 반영"]
        D6["⑥ 미해결 판단 — 사람 결정 필요"]
    end

    subgraph Consumers["소비자"]
        C1["🔒 멀티 AI 리뷰 (기획 검증)"]
        C2["👤 Human Approval"]
        C3["🧠 Executor AI CLI (구현 기준)"]
        C4["🔒 멀티 AI 리뷰 (코드 검증 — 기획 대조)"]
    end

    S1 & S2 & S3 --> PlanDoc
    PlanDoc --> C1 -->|" 통과 "| C2 -->|" 승인 "| C3
    PlanDoc -.->|" 기획 대조 "| C4
    style Sources fill: #fff8e1, stroke: #F9A825
    style PlanDoc fill: #e8f5e9, stroke: #2E7D32
    style Consumers fill: #e3f2fd, stroke: #1565C0
```

---

## 핵심 산출물 데이터 흐름

단계별 산출물을 생산하고 다음 레이어가 소비하는 구조입니다.

```mermaid
graph LR
    A1["Task Request"]
    A2["Run Context<br/>source · repo · session"]
    A3["Context Packet<br/>관련 파일 · docs · Git"]
    A4["Plan Doc<br/>범위 · 수정 계획 · 테스트"]
    A5["Execution Grant<br/>approve · scope"]
    A6["Workspace Handle<br/>worktree / sandbox id"]
    A7["Patch / Diff"]
    A8["Gate Report<br/>lint · test · typecheck"]
    A9["Review Pack<br/>review docs · judge result"]
    A10["Commit / PR"]
    A11["Failure Report"]
    A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7 --> A8 --> A9
    A9 -->|" pass "| A10
    A9 -->|" escalate "| A11
    style A4 fill: #e8f5e9, stroke: #2E7D32
    style A6 fill: #ede7f6, stroke: #4527A0
    style A8 fill: #fff8e1, stroke: #F9A825
    style A9 fill: #fff3e0, stroke: #E65100
    style A10 fill: #c8e6c9, stroke: #2E7D32
    style A11 fill: #ffcdd2, stroke: #C62828
```

---

## 안전성 모델 비교

```mermaid
graph TB
    subgraph M["Stripe Minions<br/><b>격리 = 권한</b>"]
        direction TB
        M1["Devbox VM · 인터넷 차단<br/>프로덕션 불가 · 10초 스핀업"]
        M2["One-Shot 자율 실행"]
    end

    subgraph C["Coinbase Cloudbot<br/><b>등급 = 권한</b>"]
        direction TB
        C1["Repository Sensitivity Matrix<br/>Agent Council + Risk-based Merge"]
        C2["위험도별 자율/감독 결정"]
    end

    subgraph S["Open SWE<br/><b>샌드박스 = 권한</b>"]
        direction TB
        S1["5종 백엔드 · SSRF 차단<br/>토큰 암호화 · Prompt Injection 방어"]
        S2["Thread 기반 자율 실행"]
    end

    subgraph L["로컬 에이전트<br/><b>리뷰 = 권한</b>"]
        direction TB
        L1["Plan Doc → 멀티 AI 리뷰 → 사람 승인<br/>Policy Gate → Execution Grant<br/>선택적 worktree/VM 격리"]
        L2["사전 검토 + 다중 Gate"]
    end

    style M fill: #fff8e1, stroke: #F9A825
    style C fill: #e0f2f1, stroke: #00695C
    style S fill: #fce4ec, stroke: #C62828
    style L fill: #e3f2fd, stroke: #1565C0
```

---

## 피드백 루프 비교

```mermaid
graph TB
    subgraph Minions_FB["Minions: 비용 기반 3-Tier"]
        direction LR
        MT1["Tier 1: Local Lint<br/>< 5초"]
        MT2["Tier 2: CI Selective<br/>100만+ 중 선별"]
        MT3["Tier 3: Self-Fix<br/>max 2회"]
        MT1 --> MT2 --> MT3
    end

    subgraph OMO_FB["OMO: 다층 회복 4-Tier"]
        direction LR
        OT1["Tier 1: Hook 방어<br/>Before/After 46개"]
        OT2["Tier 2: 모델 폴백<br/>3-4개 체인"]
        OT3["Tier 3: Boulder<br/>지수 백오프"]
        OT4["Tier 4: Circuit Breaker<br/>무한 루프 강제 정지"]
        OT1 --> OT2 --> OT3 --> OT4
    end

    subgraph Local_FB["로컬 에이전트: 결정론적 → LLM 2-Tier"]
        direction LR
        LT1["내부: Gate<br/>format · lint · type · test"]
        LT2["외부: 멀티 AI 리뷰<br/>교차 검증 + Judge 판정"]
        LT3["자동 수정<br/>max N회 → escalate"]
        LT1 --> LT2 --> LT3
    end

    style Minions_FB fill: #fff8e1, stroke: #F9A825
    style OMO_FB fill: #fce4ec, stroke: #C62828
    style Local_FB fill: #e3f2fd, stroke: #1565C0
```

---

## Stripe Minions 계층 대응

| 구분         | Stripe Minions                  | 로컬 에이전트                               | 핵심 차이                        |
|------------|---------------------------------|---------------------------------------|------------------------------|
| 레이어 수      | 6계층                             | 7계층                                   | Run Control · Policy Gate 분리 |
| 안전성        | VM 격리 (격리 = 권한)                 | 리뷰 + Policy Gate (리뷰 = 권한)            | 격리 vs 검토                     |
| 에이전트 코어    | Goose Fork (커스텀 단일)             | AI CLI 역할 분리 (Main/Exec/Review/Judge) | 단일 vs 다역할                    |
| 컨텍스트       | Toolshed MCP (400+ → 15개)       | Augment Context MCP (시맨틱)             | 큐레이션 vs 시맨틱 검색               |
| 코드 검증      | Review (단일 AI)                  | 멀티 AI 리뷰 (병렬 교차 검증)                   | 단일 vs 교차                     |
| 피드백 루프     | 3-Tier (Lint → CI → Self-Fix 2) | 2-Tier (Gate → Review+Fix N)          | 비용 계층 vs Gate 순서             |
| publish 권한 | Agent Core가 직접                  | L7 Output만 보유                         | 분산 vs 분리                     |
| 상태 관리      | 없음 (One-Shot)                   | Run Control (큐 · 상태 · 세션)             | 없음 vs 명시                     |

---

## 적용 패턴 매핑

```mermaid
graph TB
    subgraph Layers["아키텍처 레이어"]
        LA["L3: Context & Planning"]
        LB["AI CLI 역할 분리"]
        LC["L4: Approval Gate"]
        LD["L5+L6: Execution + Fix Loop"]
        LE["L6: Reviewer Pool"]
        LF["L2: State / Queue / Policy"]
    end

    subgraph Patterns["적용 패턴"]
        P1["Prompt Chaining<br/><i>Anthropic</i>"]
        P2["Orchestrator-Workers<br/><i>Anthropic</i>"]
        P3["Human-in-the-Loop<br/><i>Google Cloud</i>"]
        P4["Evaluator-Optimizer<br/>+ Iterative Refinement<br/><i>Anthropic + Google Cloud</i>"]
        P5["Parallelization + Review-Critique<br/><i>Anthropic + Google Cloud</i>"]
        P6["Custom Logic<br/><i>Google Cloud</i>"]
    end

    P1 --> LA
    P2 --> LB
    P3 --> LC
    P4 --> LD
    P5 --> LE
    P6 --> LF
    style Layers fill: #e3f2fd, stroke: #1565C0
    style Patterns fill: #e8f5e9, stroke: #2E7D32
```

---

## 에이전트 시스템 포지셔닝

```mermaid
quadrantChart
    title "자율성 vs 복잡도"
    x-axis "낮은 복잡도" --> "높은 복잡도"
    y-axis "낮은 자율성" --> "높은 자율성"
    quadrant-1 "고자율 · 고복잡"
    quadrant-2 "고자율 · 저복잡"
    quadrant-3 "저자율 · 저복잡"
    quadrant-4 "저자율 · 고복잡"
    "Auto Improve Loop": [0.25, 0.80]
    "Open SWE": [0.55, 0.75]
    "Stripe Minions": [0.85, 0.90]
    "Coinbase Cloudbot": [0.70, 0.70]
    "로컬 에이전트": [0.55, 0.50]
    "로컬 에이전트 (--auto)": [0.60, 0.75]
    "Deep Analysis": [0.40, 0.30]
    "Oh My OpenAgent": [0.75, 0.65]
```

---

## 설계 원칙

```mermaid
graph LR
    P1["🔧 AI CLI를 엔진으로<br/>Claude Code · Codex · Gemini CLI<br/>역할별 세션 분리"]
    P2["🏗️ 하네스 우선<br/>상태 · 권한 · 게이트 · 추적을<br/>구조화"]
    P3["📋 계획이 먼저<br/>Plan Doc 없이는<br/>write 금지"]
    P4["🔐 실행 경계 = 권한 경계<br/>worktree / sandbox 기반<br/>격리"]
    P5["⚡ 검증은 결정론적으로<br/>lint · typecheck · test는<br/>구조로 강제"]
    P6["🤖 리뷰는 병렬로<br/>단일 AI 판단에<br/>의존하지 않음"]
    P7["🚫 재시도는 제한적으로<br/>못 고치면 실패를 드러내고<br/>사람에게 올림"]
    P8["🧾 모든 단계는 artifact를<br/>plan · diff · logs ·<br/>review docs"]
    P1 --- P2 --- P3 --- P4
    P5 --- P6 --- P7 --- P8
    style P1 fill: #e3f2fd, stroke: #1565C0
    style P2 fill: #e8f5e9, stroke: #2E7D32
    style P3 fill: #fff8e1, stroke: #F9A825
    style P4 fill: #fff3e0, stroke: #E65100
    style P5 fill: #e0f2f1, stroke: #00695C
    style P6 fill: #ede7f6, stroke: #4527A0
    style P7 fill: #f3e5f5, stroke: #6A1B9A
    style P8 fill: #c8e6c9, stroke: #2E7D32
```
