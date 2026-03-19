# 로컬 개발 자동화 에이전트 아키텍처 다이어그램

이 문서는 초안 `00-diagram.md`와 보강본 `00-diagram-claude.md`, `00-diagram-codex.md`를 종합해 정리한 최종 구조입니다.
핵심 참조축은 `Stripe Minions`의 하네스 우선 설계, `Open SWE`의 run/state/sandbox 구조, `OpenCode Worktree`의 실행 경계, `Oh My OpenAgent`의 역할
분리와 복구 체계, `Agentic Workflow`와 `Design Pattern`의 패턴 분류입니다.

핵심 원칙은 단순합니다.
**AI CLI를 역할별 런타임으로 분해하고, 그 주변에 상태, 권한, 게이트, 재시도, 승인, 발행을 구조로 강제해야 운영 가능한 개발 자동화 시스템이 됩니다.**

---

## 1. 전체 시스템 구조

이 시스템은 단일 AI가 처음부터 끝까지 직접 처리하는 구조가 아닙니다.
`입력 수집 → 실행 문맥 생성 → 컨텍스트/기획 → 승인 → 격리 실행 → 검증/복구 → 산출물 발행`의 7개 레이어를 따라, 여러 AI CLI 세션이 서로 다른 권한으로 협력합니다.

- `🧠` = LLM 판단 단계
- `🔒` = 결정론적 게이트
- `👤` = 사람 승인 또는 개입

```mermaid
flowchart TB
    subgraph L1["<b>L1: Intake</b><br/>책임: 요청 수신 · 정규화 · source 판별<br/>권한: 읽기 전용 · 저장소 쓰기 금지"]
        CH_CLI["⌨️ CLI"]
        CH_WEB["🌐 Web UI"]
        CH_BOT["💬 Slack · Discord · OpenClaw"]
        INTAKE["📥 요청 정규화<br/>이벤트 필터링 · source 인증<br/>출력: task request"]
        CH_CLI & CH_WEB & CH_BOT --> INTAKE
    end

    subgraph L2["<b>L2: Run Control</b><br/>책임: run 생성 · 상태 저장 · 큐잉 · 세션 조율<br/>권한: 상태 저장소 쓰기 · 실행 plane 직접 쓰기 금지"]
        RUN["Run Manager<br/>run_id · session_id · 상태 추적"]
        QUEUE["Queue / Pending Messages<br/>(busy 시 적재)"]
        STORE["State Store<br/>status · retries · workspace_ref"]
    end

    subgraph L3["<b>L3: Context & Planning</b><br/>책임: 탐색 · 조사 · 기획 문서 생성 · 기획 검증<br/>권한: repo 읽기 · 문서 생성 · <b>코드 변경 금지</b>"]
        DISCOVER["🔍 결정론적 탐색<br/>repo · docs · Git · 구조화 컨텍스트"]
        RESEARCH["🌐 외부 조사 (선택)<br/>라이브러리 문서 · edge cases"]
        AI_CTX["📂 AI 컨텍스트 (선택)<br/>도메인 · 모델 · API"]
        PLAN_CLI["🧠 Main AI CLI<br/>Claude Code / Codex / Gemini CLI"]
        PLAN_DOC["📋 Plan Doc<br/>범위 · 수정 계획 · 테스트 개요<br/>주의사항 · 미해결 판단"]
        PLAN_REVIEW["🔒 멀티 AI 리뷰<br/>(기획 검증)"]
    end

    subgraph L4["<b>L4: Approval & Policy</b><br/>책임: 사람 승인 · 정책 적용 · 권한 발급<br/>권한: 승인 전 write/publish 금지"]
        HUMAN["👤 Human Approval"]
        POLICY["🔒 Policy Gate<br/>권한 · 모드 · 금지 규칙"]
        TOKEN["✅ Execution Grant<br/>scope: workspace 내부만"]
    end

    subgraph L5["<b>L5: Execution Plane</b><br/>책임: 격리 workspace · 코드 수정 · 도구 실행<br/>권한: 승인된 workspace 내부만 쓰기"]
        WS["🖥️ Workspace Manager<br/>Worktree / VM / Docker"]
        EXEC_A["🧠 Executor AI CLI A"]
        EXEC_B["🧠 Executor AI CLI B"]
        SECRETS["🔐 Scoped Secrets / Env"]
    end

    subgraph L6["<b>L6: Verification & Recovery</b><br/>책임: 게이트 실행 · 병렬 리뷰 · 수정 루프 제어<br/>권한: 검증 가능 · <b>publish 금지</b>"]
        GATE_DET["🔒 Deterministic Gates<br/>format · lint · typecheck · test"]
        GATE_INT["🔒 Selective / Integration Checks"]
        REV_A["🧠 Reviewer AI CLI A"]
        REV_B["🧠 Reviewer AI CLI B"]
        REV_C["🧠 Reviewer AI CLI C"]
        JUDGE["⚖️ Judge Controller"]
        FIX["🧠 Structured Fix Loop"]
    end

    subgraph L7["<b>L7: Output & Trace</b><br/>책임: commit/PR · 실패 보고 · 추적 보존<br/>권한: <b>publish 권한은 이 레이어만 보유</b>"]
        OUT_PR["✅ Commit / PR"]
        OUT_FAIL["📋 Failure Report"]
        TRACE["🧾 Artifact Store<br/>plan · diff · gate logs · review docs"]
        NOTIFY["📢 Reply / Notification"]
    end

    INTAKE --> RUN
    RUN --> QUEUE
    RUN --> STORE
    RUN --> DISCOVER
    DISCOVER --> RESEARCH
    DISCOVER --> AI_CTX
    DISCOVER & RESEARCH & AI_CTX --> PLAN_CLI --> PLAN_DOC --> PLAN_REVIEW
    PLAN_REVIEW -->|" ❌ 부족 "| DISCOVER
    PLAN_REVIEW -->|" ✅ 충분 "| HUMAN
    HUMAN -->|" ❌ 수정 요청 "| PLAN_DOC
    HUMAN -->|" ✅ 승인 "| POLICY --> TOKEN
    TOKEN --> WS
    SECRETS --> WS
    WS --> EXEC_A & EXEC_B
    EXEC_A & EXEC_B --> GATE_DET --> GATE_INT
    GATE_DET -->|" ❌ fail "| FIX
    GATE_INT -->|" ❌ fail "| FIX
    GATE_INT -->|" ✅ pass "| REV_A & REV_B & REV_C
    REV_A & REV_B & REV_C --> JUDGE
    JUDGE -->|" ✅ pass "| OUT_PR
    JUDGE -->|" ❌ fix "| FIX -->|" retry ≤ N "| EXEC_A
    JUDGE -->|" ❌ escalate "| OUT_FAIL
    FIX -->|" ❌ 한도 초과 "| OUT_FAIL
    OUT_PR & OUT_FAIL --> TRACE
    OUT_PR & OUT_FAIL --> NOTIFY
    STORE -.-> PLAN_CLI
    STORE -.-> WS
    TRACE -.-> PLAN_REVIEW
    TRACE -.-> JUDGE
    WS -->|" ❌ provision fail "| RUN
    style L1 fill: #e3f2fd, stroke: #1565C0
    style L2 fill: #e8f5e9, stroke: #2E7D32
    style L3 fill: #fff8e1, stroke: #F9A825
    style L4 fill: #fff3e0, stroke: #E65100
    style L5 fill: #ede7f6, stroke: #4527A0
    style L6 fill: #f3e5f5, stroke: #6A1B9A
    style L7 fill: #c8e6c9, stroke: #2E7D32
```

---

## 2. 레이어별 운영 계약

아래 표가 이 아키텍처의 운영 계약입니다.
각 레이어는 무엇을 받아서 무엇을 내보내는지, 어디까지 권한을 가지는지, 실패하면 어디로 되돌아가는지가 명시되어야 합니다.

| 레이어                            | 책임                                | 주요 입력                                       | 주요 출력                                              | 허용 권한                                       | 실패 시 전이                                                         |
|--------------------------------|-----------------------------------|---------------------------------------------|----------------------------------------------------|---------------------------------------------|-----------------------------------------------------------------|
| **L1 Intake**                  | 요청 정규화, source별 필터링, 실행 진입점 통합    | CLI/Web/메신저 이벤트                             | `task request`                                     | 읽기 전용, 저장소 쓰기 금지                            | 잘못된 입력은 즉시 거부 또는 보완 요청                                          |
| **L2 Run Control**             | run 생성, 상태 저장, 큐잉, 동시 실행 조율       | `task request`, 현재 run 상태                   | `run context`, `session state`, queue item         | 상태 저장소 쓰기, 실행 plane 직접 쓰기 금지                | busy면 queue 적재, 상태 손상 시 infra recovery                          |
| **L3 Context & Planning**      | 코드/문서/Git 탐색, 계획 생성, 계획 리뷰 조립     | `run context`, repo 읽기, docs, 구조화 컨텍스트      | `context packet`, `plan doc`, `plan review pack`   | repo 읽기, 문서 생성 가능, 코드 변경 금지                 | 컨텍스트 부족 시 재탐색, 기획 리뷰 실패 시 준비 단계 반복                              |
| **L4 Approval & Policy**       | 사람 승인, 실행 모드 결정, 권한 토큰 발급         | `plan doc`, review 결과, 정책 규칙                | `execution grant`, 승인/반려 결정                        | 승인 전 publish/write 금지                       | 반려 시 L3로 회귀, 정책 위반 시 block                                      |
| **L5 Execution Plane**         | 격리 workspace 준비, AI CLI 실행, 코드 수정 | `execution grant`, `plan doc`, workspace 설정 | `diff`, `workspace logs`, intermediate patch       | 승인된 workspace 내부 쓰기만 허용                     | workspace 생성 실패 시 reprovision, CLI crash 시 runtime retry        |
| **L6 Verification & Recovery** | 결정론적 검증, 병렬 리뷰, 자동 수정 루프 제어       | `diff`, 테스트 로그, review artifacts            | `gate report`, `review docs`, pass/fix/escalate 판정 | 검증 도구 실행, review artifact 생성, publish 직접 금지 | gate fail은 self-fix, review fail은 fix loop, retry 초과 시 escalate |
| **L7 Output & Trace**          | commit/PR 생성, 실패 리포트 작성, 알림/추적 보존 | 최종 판정, gate 통과 결과, review 결과                | `commit`, `PR`, `failure report`, trace artifacts  | publish 권한은 이 레이어만 보유                       | publish 실패 시 재시도 또는 사람에게 전달                                     |

---

## 3. AI CLI 역할 분리

AI CLI는 단일 주체가 아니라 역할별 런타임입니다.
같은 종류의 CLI를 써도 세션과 권한을 분리해야 하며, `메인 오케스트레이터`, `실행자`, `리뷰어`, `판정자`가 같은 디렉토리와 같은 권한을 공유하면 구조가 무너집니다.

```mermaid
graph LR
    TASK["작업 요청"]
    MAIN["🧠 Main AI CLI<br/>Claude Code / Codex / Gemini CLI<br/>역할: 오케스트레이션 · 계획 · 상태 판단"]
    RESEARCH["🔍 Research AI CLI<br/>역할: 외부 문서 조사 · 읽기 전용"]
    EXEC["⚡ Executor AI CLI Pool<br/>역할: 코드 수정 · 테스트 · 수정 루프"]
    REVIEW["🤖 Reviewer AI CLI Pool<br/>역할: plan/diff/log 검토 · 병렬 리뷰"]
    JUDGE["⚖️ Judge Controller<br/>역할: 결과 종합 · fix/escalate 판정"]
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

| 역할                   | 권한                                     | 금지 사항                          |
|----------------------|----------------------------------------|--------------------------------|
| **Main AI CLI**      | 요청 해석, 기획 문서 작성, 워크플로우 분기 결정           | 승인 전 코드 수정, 직접 publish         |
| **Research AI CLI**  | 문서/레퍼런스 탐색, 읽기 전용 분석                   | 코드 수정, commit, PR              |
| **Executor AI CLI**  | 승인된 workspace 안에서 코드 수정, 테스트 실행        | main repo 직접 쓰기, 승인 없는 publish |
| **Reviewer AI CLI**  | plan doc, diff, gate logs 검토, 리뷰 문서 생성 | 코드 수정, commit, PR              |
| **Judge Controller** | pass/fix/escalate 판정, 재시도 카운트 관리       | 코드 직접 수정                       |

---

## 4. 시퀀스 흐름

정적 구조와 별개로, 실제 런타임에서는 아래 순서로 상호작용이 진행됩니다.
핵심은 `Main AI CLI`가 전체 흐름을 조율하되, `plan review`, `human approval`, `workspace execution`, `deterministic gate`, `publish`가
명확히 분리된다는 점입니다.

```mermaid
sequenceDiagram
    actor User as 👤 사용자
    participant Entry as L1 Intake
    participant Run as L2 Run Control
    participant Main as L3 Main AI CLI
    participant Review as Multi-AI Review
    participant Human as L4 Human Approval
    participant WS as L5 Workspace Manager
    participant Exec as L5 Executor CLI
    participant Gate as L6 Deterministic Gates
    participant Judge as L6 Judge
    participant Out as L7 Output
    User ->> Entry: 작업 요청
    Entry ->> Run: 정규화된 task request
    Run ->> Main: run context 전달

    rect rgb(255, 248, 225)
        Note over Main, Review: Context & Planning
        Main ->> Main: repo / docs / Git 탐색
        opt 외부 정보 필요
            Main ->> Main: 외부 문서 조사
        end
        Main ->> Main: plan doc 생성
        loop 기획 리뷰 통과할 때까지
            Main ->> Review: plan review 요청
            Review -->> Main: pass / feedback
        end
    end

    Main ->> Human: plan doc 승인 요청
    alt 승인 거부
        Human -->> Main: 수정 요청
        Main ->> Main: plan 수정 후 재제출
    else 승인
        Human -->> Main: execution grant
        Main ->> WS: workspace provision
        WS -->> Exec: isolated workspace 제공
    end

    rect rgb(243, 229, 245)
        Note over Exec, Judge: Execution + Verification
        loop retry <= N
            Exec ->> Exec: 코드 수정
            Exec ->> Gate: lint / typecheck / test
            Gate -->> Exec: pass / fail
            alt gate 통과
                Exec ->> Review: diff / logs review 요청
                Review -->> Judge: review docs
                Judge -->> Exec: pass / fix / escalate
            else gate 실패
                Exec ->> Exec: self-fix
            end
        end
    end

    alt publish 가능
        Exec ->> Out: final diff + gate report
        Out -->> User: Commit / PR / 완료 알림
    else 실패 에스컬레이션
        Exec ->> Out: failure report
        Out -->> User: 실패 보고 / 사람 개입 요청
    end
```

---

## 5. 컨텍스트 수집과 Plan Doc 계약

준비 단계는 `Prompt Chaining`에 가까운 결정론적 파이프라인으로 설계합니다.
핵심은 **코드 쓰기 전에 Plan Doc을 산출물로 고정**하고, plan review와 human approval을 통과해야만 write 권한이 열리도록 하는 것입니다.

```mermaid
flowchart TD
    START["run context"]
    START --> D1["요청 의도 · 범위 파악"]
    D1 --> D2["repo 탐색<br/>파일 구조 · import 관계 · 관련 docs"]
    D2 --> D3["Git 이력 확인<br/>기존 구현 패턴 · 최근 변경"]
    D3 --> D4{"외부 정보 필요?"}
    D4 -->|" 예 "| D5["외부 문서 조사<br/>라이브러리 사용법 · 함정 · edge cases"]
    D4 -->|" 아니오 "| D6
    D5 --> D6["구조화된 AI 컨텍스트 병합<br/>도메인 · 모델 · API 스펙"]
    D6 --> P1["📋 Plan Doc 생성"]
    P1 --> P2["🔒 병렬 plan review"]
    P2 --> P3{"리뷰 판정"}
    P3 -->|" ❌ 부족 "| D1
    P3 -->|" ✅ 충분 "| H{"👤 사람 승인?"}
    H -->|" ❌ 수정 요청 "| D1
    H -->|" ✅ 승인 "| OUT["execution grant 발급"]
    style START fill: #e3f2fd, stroke: #1565C0
    style D5 fill: #fff8e1, stroke: #F9A825
    style P1 fill: #e8f5e9, stroke: #2E7D32
    style P2 fill: #ede7f6, stroke: #4527A0
    style H fill: #fff3e0, stroke: #E65100
    style OUT fill: #c8e6c9, stroke: #2E7D32
```

### Plan Doc 필수 필드

| 필드                    | 목적                          |
|-----------------------|-----------------------------|
| **컨텍스트 요약**           | 어떤 코드, 문서, 이력을 근거로 판단했는지 기록 |
| **변경 목표**             | 무엇을 왜 바꾸는지 고정               |
| **수정 파일 후보**          | 실행 범위를 제한하고 리뷰 근거 제공        |
| **테스트 시나리오**          | 실행 단계의 gate 기준 제공           |
| **주의사항 / edge cases** | 외부 조사와 도메인 지식의 반영 여부를 추적    |
| **미해결 판단**            | 사람이 결정해야 할 항목 분리            |

### Plan Doc 소비자

```mermaid
graph TB
    subgraph Sources["입력 소스"]
        S1["🔍 결정론적 탐색"]
        S2["🌐 추가 조사"]
        S3["📂 AI 컨텍스트"]
    end

    subgraph PlanDoc["📋 Plan Doc"]
        D["6개 필수 필드"]
    end

    subgraph Consumers["소비자"]
        C1["🔒 멀티 AI 리뷰 (기획 검증)"]
        C2["👤 Human Approval"]
        C3["🧠 Executor AI CLI"]
        C4["🔒 멀티 AI 리뷰 (코드 검증)"]
    end

    S1 & S2 & S3 --> PlanDoc
    PlanDoc --> C1 -->|" 통과 "| C2 -->|" 승인 "| C3
    PlanDoc -.->|" 기획 대조 기준 "| C4
    style Sources fill: #fff8e1, stroke: #F9A825
    style PlanDoc fill: #e8f5e9, stroke: #2E7D32
    style Consumers fill: #e3f2fd, stroke: #1565C0
```

---

## 6. 실행 워크스페이스 · 권한 모델 · 실행 모드

실행 plane의 핵심 원칙은 `workspace boundary = permission boundary`입니다.
초안의 `로컬 / VM / Docker` 선택은 단순한 환경 옵션이 아니라, **실행 권한과 실패 영향 범위를 결정하는 아키텍처 요소**로 취급해야 합니다.

```mermaid
flowchart TD
    GRANT["execution grant"] --> MODE{"실행 경계 선택"}
    MODE -->|" local-safe "| WT["🌿 Git Worktree Mode<br/>브랜치 검증 · 파일 동기화 · 세션 포크"]
    MODE -->|" isolated "| BOX["🐳 VM / Docker Sandbox Mode<br/>repo clone · env 주입 · 네트워크 정책"]
    WT --> EXEC["Executor AI CLI"]
    BOX --> EXEC
    REPO["원본 repo"] -.-> WT
    SECRET["Scoped secrets"] --> BOX
    POLICY["network / prod access policy"] --> BOX
    EXEC --> DIFF["diff / patch / logs"]
    style WT fill: #ede7f6, stroke: #4527A0
    style BOX fill: #fff8e1, stroke: #F9A825
    style EXEC fill: #e3f2fd, stroke: #1565C0
    style DIFF fill: #c8e6c9, stroke: #2E7D32
```

### 실행 경계별 권한 매트릭스

| 경계                       | 읽기                      | 쓰기                       | 네트워크              | 비밀정보           | Git publish |
|--------------------------|-------------------------|--------------------------|-------------------|----------------|-------------|
| **Prepare / Plan**       | repo, docs, Git history | plan doc만                | 외부 문서 조회 가능       | 원칙적으로 불필요      | 금지          |
| **Review**               | plan doc, diff, logs    | review doc만              | 모델 API 호출 수준      | 불필요            | 금지          |
| **Local Worktree**       | worktree 내부 전체          | worktree 내부만             | 프로젝트 정책에 따름       | 최소 범위 env만     | 금지          |
| **Isolated VM / Docker** | sandbox 내부 repo         | sandbox 내부만              | 차단 또는 allowlist   | scoped secret만 | 금지          |
| **Output**               | final diff, gate report | commit metadata, PR body | Git hosting 접근 허용 | publish 최소 토큰  | 허용          |

### 권한 모델의 핵심 규칙

1. **승인 전 write 금지**: plan 단계 AI CLI는 코드 수정 권한이 없습니다.
2. **workspace 밖 쓰기 금지**: executor는 main repo가 아니라 worktree 또는 sandbox 안에서만 수정합니다.
3. **publish 권한 분리**: commit / PR 생성은 output layer만 수행합니다.
4. **secret scope 축소**: execution에 꼭 필요한 환경변수만 주입합니다.
5. **네트워크 정책 외부화**: executor 프롬프트가 아니라 infra 정책으로 제어합니다.

### 실행 모드 선택

실행 모드는 단순 UX 옵션이 아니라, 승인 경로와 권한 범위를 바꾸는 정책 스위치입니다.
기본값은 `human-reviewed`이고, `--auto`는 격리 조건이 충분할 때만 열리는 고위험 모드로 취급합니다.

```mermaid
flowchart LR
    REQ["작업 요청"] --> MODE{"실행 모드"}
    MODE -->|" human-reviewed "| HR["사람 승인 필수"]
    MODE -->|" --auto "| AUTO["사람 승인 생략 가능<br/>정책 조건 충족 시만"]
    HR --> ENV1{"실행 경계"}
    AUTO --> ENV2{"실행 경계"}
    ENV1 -->|" local worktree "| W1["🌿 Git Worktree<br/>브랜치 격리 + 세션 분리"]
    ENV1 -->|" isolated vm/docker "| W2["🐳 VM / Docker<br/>격리 + 제한된 secret"]
    ENV2 -->|" isolated vm/docker "| A1["One-Shot에 가까운 실행<br/>격리 + 정책 허용 필수"]
    ENV2 -->|" local "| A2["⚠️ 비권장<br/>격리 없는 auto 실행"]
    style HR fill: #e8f5e9, stroke: #2E7D32
    style AUTO fill: #fff3e0, stroke: #E65100
    style A1 fill: #c8e6c9, stroke: #2E7D32
    style A2 fill: #ffcdd2, stroke: #C62828
```

### 운영 관점의 모드 비교

| 모드                 | 승인     | 권장 경계                        | 적합한 상황           | 비고                     |
|--------------------|--------|------------------------------|------------------|------------------------|
| **human-reviewed** | 필수     | local worktree / VM / Docker | 기본 개발 자동화, 팀 환경  | 현재 아키텍처의 기본값           |
| **--auto**         | 조건부 생략 | VM / Docker 우선               | 반복적이고 범위가 명확한 작업 | policy gate에서 별도 허용 필요 |
| **local + auto**   | 생략     | 로컬                           | 특별한 경우 외 비권장     | 격리 부재로 권한 경계가 약함       |

---

## 7. 검증 · 리뷰 · 자동 수정 파이프라인

검증 plane은 `Stripe Minions`의 결정론적 게이트와 `Evaluator-Optimizer` 패턴을 조합한 구조입니다.
핵심은 **빠른 내부 루프**와 **비싼 외부 루프**를 분리하는 것입니다.

```mermaid
flowchart TB
    START["Executor AI CLI 결과<br/>diff + logs"]

    subgraph Inner["내부 루프: 결정론적 Gate"]
        G1["format / lint"]
        G2["typecheck"]
        G3["unit / local test"]
    end

    subgraph Outer["외부 루프: 심화 검증"]
        G4["selective / integration check"]
        RV["🤖 병렬 reviewer AI CLI"]
        JD{"⚖️ Judge 판정"}
        FIX["🧠 구조화된 피드백 기반 수정"]
        COUNT{"retry <= N?"}
    end

    START --> G1 --> G2 --> G3
    G1 -->|" ❌ fail "| FIX
    G2 -->|" ❌ fail "| FIX
    G3 -->|" ❌ fail "| FIX
    G3 -->|" ✅ pass "| G4
    G4 -->|" ❌ fail "| FIX
    G4 -->|" ✅ pass "| RV --> JD
    JD -->|" ✅ pass "| DONE["✅ publish 후보"]
    JD -->|" ❌ fix "| FIX
    JD -->|" ❌ escalate "| FAIL["📋 failure report"]
    FIX --> COUNT
    COUNT -->|" yes "| START
    COUNT -->|" no "| FAIL
    style Inner fill: #e3f2fd, stroke: #1565C0
    style Outer fill: #ede7f6, stroke: #4527A0
    style DONE fill: #c8e6c9, stroke: #2E7D32
    style FAIL fill: #ffcdd2, stroke: #C62828
```

### Reviewer AI CLI의 분업 예시

| 리뷰어            | 입력               | 주 임무                   |
|----------------|------------------|------------------------|
| **Reviewer A** | plan doc + diff  | 계획 대비 요구사항 충족 여부       |
| **Reviewer B** | diff + gate logs | 경계 조건, 사이드 이펙트, 회귀 위험  |
| **Reviewer C** | diff + 테스트 개요    | 테스트 누락, 구현 정합성, 버그 가능성 |

### 재시도 규칙

| 실패 유형                               | 처리 방식                          | 카운트 방식                     |
|-------------------------------------|--------------------------------|----------------------------|
| **lint / type / local test 실패**     | executor가 즉시 수정 후 재실행          | 내부 루프, 별도 카운트 또는 낮은 비용 카운트 |
| **integration / selective test 실패** | self-fix 루프 진입                 | 외부 retry 카운트               |
| **AI review 실패**                    | structured feedback 기반 수정      | 외부 retry 카운트               |
| **reviewer 간 불일치**                  | judge가 escalate 또는 보수적 fail 선택 | retry 미소비 또는 1회 소모         |
| **retry 한도 초과**                     | failure report 작성 후 사람에게 전달    | 종료                         |

---

## 8. 멀티 AI 리뷰 모듈

`plan review`와 `code review`는 서로 다른 시스템이 아니라, 같은 review harness를 다른 입력으로 재사용하는 구조입니다.
이 모듈은 병렬 리뷰어, 결과 집계기, 판정 규칙으로 구성되며 준비 단계와 실행 단계 모두에서 호출됩니다.

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1["artifact<br/>plan doc 또는 diff"]
        I2["criteria<br/>요구사항 · 테스트 개요 · gate logs"]
    end

    subgraph Reviewers["병렬 reviewer AI CLI"]
        R1["Reviewer A<br/>요구사항 대조"]
        R2["Reviewer B<br/>엣지케이스 / 회귀"]
        R3["Reviewer C<br/>구현 정합성 / 버그"]
    end

    subgraph Aggregation["집계 및 판정"]
        AGG["⚖️ Judge / Aggregator"]
        DEC{"판정"}
    end

    subgraph Output["출력"]
        O1["✅ pass"]
        O2["❌ fix feedback"]
        O3["❌ escalate"]
    end

    I1 & I2 --> R1 & R2 & R3
    R1 & R2 & R3 --> AGG --> DEC
    DEC --> O1
    DEC --> O2
    DEC --> O3
    style Input fill: #fff8e1, stroke: #F9A825
    style Reviewers fill: #ede7f6, stroke: #4527A0
    style Aggregation fill: #fff3e0, stroke: #E65100
    style Output fill: #c8e6c9, stroke: #2E7D32
```

### 단계별 재사용 방식

| 호출 위치          | 입력 artifact        | 판정 기준                  | 실패 시                 |
|----------------|--------------------|------------------------|----------------------|
| **Prepare 단계** | `plan doc`         | 범위 적절성, 실행 가능성, 누락 여부  | 기획 단계 재진입            |
| **Execute 단계** | `diff + gate logs` | 요구사항 충족, 회귀 위험, 테스트 누락 | fix loop 또는 escalate |

---

## 9. 상태 전이 · 오류 처리 · 실패 전이

운영 가능한 시스템은 상태 전이를 명시해야 합니다.
아래 상태도는 `요청 수신`에서 `PR 발행` 또는 `실패 보고`까지의 핵심 경로와, 각 실패가 어디로 되돌아가는지를 보여줍니다.

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Queued: 기존 run busy
    Received --> Preparing: 즉시 처리 가능
    Queued --> Preparing: dequeue
    Preparing --> PlanReviewed: plan doc + AI review 완료
    PlanReviewed --> AwaitingApproval
    AwaitingApproval --> Preparing: 사람 반려 / plan 수정 요청
    AwaitingApproval --> Provisioning: 승인
    Provisioning --> Executing: workspace 준비 성공
    Provisioning --> ProvisionRetry: 일시적 infra 실패
    ProvisionRetry --> Provisioning
    ProvisionRetry --> Escalated: 재시도 초과
    Executing --> DeterministicChecks
    DeterministicChecks --> Executing: gate fail -> self-fix
    DeterministicChecks --> AIReview: gate pass
    AIReview --> Executing: 수정 필요
    AIReview --> ReadyToPublish: 통과
    AIReview --> Escalated: 위험 높음 / 불일치 / retry 초과
    ReadyToPublish --> Publishing
    Publishing --> Published: commit / PR 성공
    Publishing --> Escalated: publish 실패
    Escalated --> [*]
    Published --> [*]
```

### 오류 분류와 처리 정책

| 오류 클래스                        | 예시                               | 감지 레이어               | 기본 처리                        | 최종 전이                     |
|-------------------------------|----------------------------------|----------------------|------------------------------|---------------------------|
| **입력 오류**                     | source 포맷 불일치, 필수 정보 누락          | Intake               | 즉시 reject 또는 보완 요청           | 종료 또는 Received 재진입        |
| **상태 충돌**                     | 기존 run busy, 중복 요청               | Run Control          | queue 적재 또는 interrupt 정책 적용  | Queued                    |
| **컨텍스트 부족**                   | 관련 파일 식별 실패, 문서 부족               | Context & Planning   | 재탐색, 추가 조사                   | Preparing                 |
| **기획 리뷰 실패**                  | 기획 논리 부족, 누락, 실행 불가              | Context & Planning   | 피드백 반영 후 재작성                 | Preparing                 |
| **승인 실패**                     | 범위 과다, plan 부실                   | Approval             | plan 수정 후 재제출                | Preparing                 |
| **정책 위반**                     | 승인 없는 publish, forbidden path 수정 | Policy Gate          | 즉시 block                     | Escalated                 |
| **workspace provisioning 실패** | worktree 생성 실패, sandbox boot 실패  | Execution Plane      | 제한된 infra retry              | Provisioning 또는 Escalated |
| **CLI runtime 오류**            | 프로세스 crash, JSON 파싱 실패           | Execution / Recovery | same-run retry, 필요 시 CLI 재시작 | Executing 또는 Escalated    |
| **결정론적 gate 실패**              | lint/test/typecheck 실패           | Verification         | self-fix loop                | Executing                 |
| **리뷰 실패**                     | 요구사항 누락, 회귀 위험                   | Verification         | structured fix loop          | Executing 또는 Escalated    |
| **fatal auth / secret 오류**    | publish token 없음, secret 주입 실패   | Output / Execution   | 재시도 최소화, 사람 전달               | Escalated                 |

---

## 10. 핵심 산출물 데이터 흐름

이 시스템은 코드만 만드는 것이 아니라, 단계별 산출물을 생산하고 다음 레이어가 그 산출물을 입력으로 소비하는 구조입니다.
그래서 `입력/출력`이 불분명하면 아키텍처가 아니라 프롬프트 모음이 됩니다.

```mermaid
graph LR
    A1["Task Request"]
    A2["Run Context<br/>source · repo · session"]
    A3["Context Packet<br/>관련 파일 · docs · Git 이력"]
    A4["Plan Doc<br/>범위 · 수정 계획 · 테스트 개요"]
    A5["Approval Decision<br/>approve / reject / restrict"]
    A6["Workspace Handle<br/>worktree path / sandbox id"]
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

### 산출물별 소비자

| 산출물                  | 다음 소비자                       | 용도                  |
|----------------------|------------------------------|---------------------|
| **Context Packet**   | Main AI CLI                  | 계획 생성의 근거           |
| **Plan Doc**         | 사람, reviewer AI, executor AI | 승인 기준이자 구현 계약       |
| **Workspace Handle** | executor AI                  | 수정 가능한 경계 지정        |
| **Gate Report**      | judge, reviewer AI           | 코드 품질의 결정론적 근거      |
| **Review Pack**      | judge, output layer          | publish 가능 여부 최종 판단 |
| **Failure Report**   | 사람                           | 재시도 대신 수동 개입 판단     |

---

## 11. 참조 시스템 비교

여기서부터는 본문 아키텍처의 설계 근거를 비교 관점에서 정리합니다.
핵심 본문은 1-10절이고, 아래 내용은 외부 시스템과의 차이를 통해 왜 이런 구조를 선택했는지 설명하는 보조 섹션입니다.

### 안전성 모델 비교

이 최종 구조는 `격리 기반`, `등급 기반`, `샌드박스 기반`, `리뷰 기반` 모델의 중간지점에 위치합니다.
기본값은 `리뷰 = 권한`이지만, 실행 모드와 실행 경계에 따라 `격리 = 권한` 방향으로 이동할 수 있게 설계합니다.

```mermaid
graph TB
    subgraph M["Stripe Minions<br/><b>격리 = 권한</b>"]
        direction TB
        M1["Devbox VM · 인터넷 차단<br/>프로덕션 접근 불가"]
        M2["One-Shot 자율 실행"]
    end

    subgraph C["Coinbase Cloudbot<br/><b>등급 = 권한</b>"]
        direction TB
        C1["Repository Sensitivity Matrix"]
        C2["위험도별 자율/감독 결정"]
    end

    subgraph S["Open SWE<br/><b>샌드박스 = 권한</b>"]
        direction TB
        S1["Sandbox backend + thread state"]
        S2["thread 기반 자율 실행"]
    end

    subgraph L["로컬 개발 자동화<br/><b>리뷰 = 권한</b>"]
        direction TB
        L1["Plan Doc → 멀티 AI 리뷰 → 사람 승인"]
        L2["Policy Gate → Execution Grant → 선택적 격리"]
    end

    style M fill: #fff8e1, stroke: #F9A825
    style C fill: #e0f2f1, stroke: #00695C
    style S fill: #fce4ec, stroke: #C62828
    style L fill: #e3f2fd, stroke: #1565C0
```

### 피드백 루프 비교

```mermaid
graph TB
    subgraph Minions_FB["Stripe Minions: 비용 기반 3-Tier"]
        direction LR
        MT1["Tier 1: Local Lint"]
        MT2["Tier 2: CI Selective Tests"]
        MT3["Tier 3: Self-Fix"]
        MT1 --> MT2 --> MT3
    end

    subgraph OMO_FB["Oh My OpenAgent: 다층 회복"]
        direction LR
        OT1["Hook 방어"]
        OT2["모델 폴백"]
        OT3["연속 실행 / 백오프"]
        OT4["Circuit Breaker"]
        OT1 --> OT2 --> OT3 --> OT4
    end

    subgraph Local_FB["최종 로컬 구조: 결정론적 → 멀티 리뷰"]
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

### 참조 시스템 매핑

현재 아키텍처는 단일 원본을 베낀 것이 아니라, 각 시스템에서 유효했던 구조 요소를 선택적으로 결합한 것입니다.
아래 표는 어떤 요소를 어디서 가져왔는지, 그리고 현재 구조에서 무엇으로 치환했는지를 보여줍니다.

```mermaid
graph LR
    M["Stripe Minions"] --> A["Gate + Feedback"]
    O["Open SWE"] --> B["Run State + Queue + Publish Layer"]
    W["OpenCode Worktree"] --> C["Workspace Boundary"]
    H["Oh My OpenAgent"] --> D["Role Split + Recovery"]
    E["Effective Agents"] --> E2["Pattern Skeleton"]
    G["Design Pattern"] --> F["HITL + Review-Critique + Policy"]
    A & B & C & D & E2 & F --> CUR["현재 로컬 개발 자동화 아키텍처"]
    style CUR fill: #c8e6c9, stroke: #2E7D32
```

| 참조 시스템                                  | 가져온 핵심 요소                                                  | 현재 문서에서의 대응                                                         |
|-----------------------------------------|------------------------------------------------------------|---------------------------------------------------------------------|
| **Stripe Minions**                      | 결정론적 gate, feedback loop, harness 우선                       | `검증 · 리뷰 · 자동 수정 파이프라인`, `설계 원칙`                                    |
| **Open SWE**                            | run context, queue/state, sandbox 재사용, publish layer 분리    | `전체 시스템 구조`, `레이어별 운영 계약`                                           |
| **OpenCode Worktree**                   | worktree 기반 실행 경계, 세션 분리, 브랜치 격리                           | `실행 워크스페이스 · 권한 모델 · 실행 모드`                                         |
| **Oh My OpenAgent**                     | 역할 분리, 폴백/재시도, 복구 컨트롤러                                     | `AI CLI 역할 분리`, `참조 시스템 비교`, `상태 전이 · 오류 처리 · 실패 전이`                |
| **Agentic Workflow / Effective Agents** | prompt chaining, orchestrator-workers, evaluator-optimizer | `컨텍스트 수집과 Plan Doc 계약`, `적용 패턴 매핑`                                  |
| **Design Pattern**                      | human-in-the-loop, review-critique, custom logic           | `실행 워크스페이스 · 권한 모델 · 실행 모드`, `멀티 AI 리뷰 모듈`, `상태 전이 · 오류 처리 · 실패 전이` |

### Stripe Minions 계층 대응

| 구분         | Stripe Minions    | 최종 로컬 구조                 | 핵심 차이                             |
|------------|-------------------|--------------------------|-----------------------------------|
| 레이어 수      | 6계층               | 7계층                      | Run Control · Approval/Policy를 분리 |
| 안전성        | VM 격리 중심          | 리뷰 + Policy Gate 중심      | 격리 우선 vs 리뷰 우선                    |
| 에이전트 코어    | 단일 Goose 기반       | 역할 분리된 AI CLI 세션         | 단일 코어 vs 다역할                      |
| 컨텍스트       | Toolshed MCP 큐레이션 | repo/docs/Git + 구조화 컨텍스트 | 큐레이션 vs 탐색 조합                     |
| 코드 검증      | 단일 Review         | 멀티 AI 리뷰 + Judge         | 단일 검토 vs 교차 검증                    |
| 피드백 루프     | 3-Tier 비용 계층      | Gate → Review → Fix      | 비용 계층 vs 운영 계약                    |
| publish 권한 | agent core와 가까움   | L7 Output에만 존재           | 분산 vs 분리                          |
| 상태 관리      | one-shot 성향       | run 상태/큐/세션 명시           | 암묵적 vs 명시적                        |

---

## 12. 적용 패턴 매핑

이 아키텍처는 하나의 패턴으로 설명되지 않습니다.
레이어별로 서로 다른 패턴을 조합해야 전체 시스템이 안정적으로 동작합니다.

```mermaid
graph TB
    subgraph Layers["아키텍처 레이어"]
        L1["Context & Planning"]
        L2["AI CLI 역할 분리"]
        L3["Approval Gate"]
        L4["Execution + Fix Loop"]
        L5["Reviewer Pool"]
        L6["State / Queue / Policy"]
    end

    subgraph Patterns["적용 패턴"]
        P1["Prompt Chaining"]
        P2["Orchestrator-Workers"]
        P3["Human-in-the-Loop"]
        P4["Evaluator-Optimizer<br/>+ Iterative Refinement"]
        P5["Parallelization<br/>+ Review-Critique"]
        P6["Custom Logic / Policy Gate"]
    end

    P1 --> L1
    P2 --> L2
    P3 --> L3
    P4 --> L4
    P5 --> L5
    P6 --> L6
    style Layers fill: #e3f2fd, stroke: #1565C0
    style Patterns fill: #e8f5e9, stroke: #2E7D32
```

### 레이어별 패턴 해석

| 레이어                        | 주요 패턴                                      | 이유                                |
|----------------------------|--------------------------------------------|-----------------------------------|
| **Context & Planning**     | Prompt Chaining                            | 순차 탐색과 중간 검증이 중요                  |
| **AI CLI 역할 분리**           | Orchestrator-Workers                       | 메인 CLI가 실행/리뷰 CLI를 동적으로 조율        |
| **Approval Gate**          | Human-in-the-Loop                          | 권한 부여가 사람 승인과 결합됨                 |
| **Execution + Fix Loop**   | Evaluator-Optimizer / Iterative Refinement | 생성-검증-수정 반복                       |
| **Reviewer Pool**          | Parallelization / Review-Critique          | 독립 관점 리뷰를 병렬 수행                   |
| **State / Queue / Policy** | Custom Logic                               | 상태 전이, 큐, 권한, 금지 규칙은 코드 기반 제어가 필요 |

---

## 13. 설계 원칙

이 문서에서 제안하는 최종 구조를 한 줄로 줄이면, `AI CLI를 엔진으로 쓰고 하네스를 시스템으로 설계한다`입니다.
초안의 문제의식은 유지하되, 최종본에서는 실제 운영 구조로 바꾸기 위해 원칙을 아래처럼 고정합니다.

```mermaid
graph LR
    P1["🔧 AI CLI를 엔진으로 사용<br/>Claude Code · Codex · Gemini CLI"]
    P2["🏗️ 하네스 우선<br/>상태 · 권한 · 게이트 · 추적을 구조화"]
    P3["📋 계획이 먼저<br/>Plan Doc 없이는 write 금지"]
    P4["🔐 실행 경계 = 권한 경계<br/>worktree / sandbox 기반 격리"]
    P5["⚡ 검증은 결정론적으로<br/>lint · typecheck · test는 구조로 강제"]
    P6["🤖 리뷰는 병렬로<br/>단일 AI 판단에 의존하지 않음"]
    P7["🚫 재시도는 제한적으로<br/>못 고치면 실패를 드러내고 사람에게 올림"]
    P8["🧾 모든 단계는 artifact를 남김<br/>plan · diff · logs · review docs"]
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
