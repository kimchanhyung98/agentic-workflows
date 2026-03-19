# Open SWE 아키텍처 다이어그램

## 1. 프로젝트 구조

```mermaid
flowchart LR
    subgraph External["외부 트리거"]
        Slack["Slack<br/>(앱 멘션)"]
        Linear["Linear<br/>(코멘트)"]
        GitHub["GitHub<br/>(Issue/PR 코멘트)"]
    end

    subgraph Ingress["Ingress 계층"]
        WebApp["agent/webapp.py<br/>서명 검증, 페이로드 파싱<br/>thread ID/컨텍스트 결정"]
    end

    subgraph Coordination["Thread 조율 계층"]
        Client["LangGraph SDK/Client<br/>runs.create, store.put_item"]
        Threads["LangGraph Threads/Runs"]
        Store["LangGraph Store<br/>pending_messages"]
        Platform["LangGraph Runtime<br/>server.py:get_agent 호출"]
    end

    subgraph Runtime["Agent Runtime 계층"]
        Server["agent/server.py<br/>sandbox·인증·프롬프트 준비<br/>create_deep_agent 조립"]
        Prompt["agent/prompt.py"]
        MW["agent/middleware/*<br/>큐 주입, 오류 처리<br/>빈 응답 방지, PR 안전망"]
        Tools["agent/tools/*<br/>PR 생성, 댓글, HTTP"]
    end

    subgraph Infra["인프라 계층"]
        SandboxUtils["agent/utils/sandbox*<br/>sandbox 상태, 경로 해석"]
        Auth["agent/utils/auth.py + encryption.py<br/>토큰 해석, Fernet 암호화"]
        Utils["agent/utils/*<br/>GitHub, Slack, Linear API"]
        SB["agent/integrations/*<br/>LangSmith, Daytona<br/>Modal, Runloop, Local"]
    end

    subgraph Systems["외부 시스템"]
        Repo["GitHub 저장소"]
        GHAPI["GitHub API"]
        SLAPI["Slack API"]
        LNAPI["Linear API"]
        LS["LangSmith"]
    end

    Slack --> WebApp
    Linear --> WebApp
    GitHub --> WebApp

    WebApp --> Client
    Client --> Threads
    Client --> Store
    Threads --> Platform

    Platform --> Server
    Server --> Prompt
    Server --> MW
    Server --> Tools
    Server --> SandboxUtils
    Server --> Auth

    SandboxUtils --> SB
    SB --> LS
    Tools --> Utils
    Utils --> GHAPI
    Utils --> SLAPI
    Utils --> LNAPI
    Tools --> Repo
```

## 2. 전체 실행 흐름

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Source as Slack/Linear/GitHub
    participant WebApp as webapp.py
    participant SDK as LangGraph SDK
    participant Platform as LangGraph Runtime
    participant Server as server.py
    participant Tools as 도구/외부 API
    participant Sandbox as 샌드박스
    participant Agent as Deep Agent
    participant GH as GitHub
    participant Reply as 원본 채널

    User->>Source: @openswe 요청
    Source->>WebApp: webhook 전달
    WebApp->>WebApp: 서명 검증 + source별 컨텍스트 정리
    WebApp->>WebApp: thread ID 결정 + 입력 구성

    alt Slack 요청
        WebApp->>SDK: runs.create (interrupt 전략)
    else Linear/GitHub + idle
        WebApp->>SDK: runs.create
    else Linear/GitHub + busy
        WebApp->>SDK: store.put_item() 큐잉
    end

    SDK->>Platform: thread/run 스케줄링
    Platform->>Server: get_agent(config) 호출
    Server->>Server: resolve_github_token()
    Server->>Sandbox: sandbox 연결/생성 + repo clone/pull
    Server->>Server: construct_system_prompt()
    Server->>Server: create_deep_agent(<br/>model, prompt, tools,<br/>backend, middleware)
    Server-->>Platform: 에이전트 반환

    loop ReAct 루프 (max 1,000회)
        Note over Agent: check_message_queue<br/>(큐 메시지 주입)
        Agent->>Agent: 상황 분석 + 도구 선택
        Agent->>Tools: 도구 호출
        Tools->>Sandbox: 파일 탐색/수정/셸 실행
        Sandbox-->>Tools: 결과
        Tools-->>Agent: 도구 결과
        Note over Tools: ToolErrorMiddleware<br/>(예외 → ToolMessage)
        Note over Agent: ensure_no_empty_msg<br/>(빈 응답 방지)
    end

    alt 코드 변경 있음
        Agent->>Tools: commit_and_open_pr()
        Tools->>Sandbox: git add → commit → push
        Tools->>GH: Draft PR 생성
        Agent->>Reply: 결과 회신
    else 답변만 필요
        Agent->>Reply: 요약/답변 회신
    end

    Note over Platform: open_pr_if_needed<br/>(안전망: 미생성 시 자동 PR)
```

## 3. 데이터 흐름 및 상태 변화

```mermaid
flowchart TD
    Payload["Webhook payload"] --> Normalize["source별 정규화<br/>(서명 검증, 필터링)"]
    Normalize --> ThreadId["Deterministic thread ID 생성"]
    Normalize --> PromptInput["프롬프트/입력 콘텐츠 구성"]

    ThreadId --> Configurable["LangGraph configurable<br/>(source, repo, issue/pr/slack context)"]
    ThreadId --> ThreadMeta["Thread metadata<br/>(sandbox_id, repo_dir,<br/>github_token_encrypted, repo)"]
    ThreadId --> Queue["LangGraph Store queue<br/>(namespace: ('queue', thread_id),<br/>key: pending_messages)"]

    Configurable --> Server["server.py: get_agent()"]
    ThreadMeta --> Server
    Queue --> MW["check_message_queue<br/>(조회 후 삭제 → 다음 모델 호출 전 주입)"]

    Server --> Auth["GitHub token 해석/저장"]
    Server --> SB["sandbox 연결/생성"]
    SB --> RepoFS["sandbox 내부 작업 디렉토리"]

    PromptInput --> AgentRun["Deep Agent 실행"]
    MW --> AgentRun
    RepoFS --> AgentRun

    AgentRun --> GitChanges["git add → commit → push"]
    GitChanges --> Branch["Git branch<br/>open-swe/{thread_id}"]
    Branch --> PR["Draft Pull Request"]
    AgentRun --> ChannelReply["Slack/Linear/GitHub 회신"]

    Auth --> ThreadMeta
    SB --> ThreadMeta
    PR --> ChannelReply
```

## 4. 트리거별 처리 분기

### 4.1 Slack 멘션 처리

```mermaid
flowchart TD
    A["POST /webhooks/slack"] --> B["서명 검증"]
    B --> C{"url_verification?"}
    C -->|예| RET["challenge 반환"]
    C -->|아니오| D{"app_mention 이벤트?"}
    D -->|아니오| D2{"메시지에 봇 태그 포함?"}
    D2 -->|아니오| IGN["무시"]
    D2 -->|예| E
    D -->|예| E{"봇 메시지?"}
    E -->|예| IGN
    E -->|아니오| F["이모지 리액션 (👀)"]

    F --> G["저장소 결정<br/>① repo:owner/name<br/>② GitHub URL 패턴<br/>③ 기존 메타데이터<br/>④ 환경변수 기본값"]
    G --> H{"조직 허용목록 확인"}
    H -->|거부| IGN
    H -->|허용| I["thread ID 생성<br/>MD5(channel:thread_ts)"]

    I --> J["스레드 메시지 조회"]
    J --> K["관련 컨텍스트 선택<br/>(last_mention/full_thread)"]
    K --> L["runs.create<br/>(source: slack,<br/>multitask_strategy=interrupt)"]
    L --> M["Slack trace URL 회신"]
```

### 4.2 Linear 코멘트 처리

```mermaid
flowchart TD
    A["POST /webhooks/linear"] --> B["서명 검증"]
    B --> C{"Comment create?"}
    C -->|아니오| IGN["무시"]
    C -->|예| D{"봇 코멘트?"}
    D -->|예| IGN
    D -->|아니오| E{"@openswe 포함?"}
    E -->|아니오| IGN
    E -->|예| F["이슈 상세 조회 (GraphQL)"]

    F --> G["LINEAR_TEAM_TO_REPO<br/>저장소 매핑"]
    G --> H{"조직 허용목록 확인"}
    H -->|거부| IGN
    H -->|허용| I["thread ID 생성<br/>SHA256(linear-issue:id)"]

    I --> J["사용자 이메일 추출<br/>(코멘트 작성자 우선)"]
    J --> K["이미지 URL 추출<br/>(설명 + 최근 코멘트)"]
    K --> L["프롬프트 구성"]

    L --> M{"thread busy?"}
    M -->|예| N["queue_message_for_thread()"]
    M -->|아니오| O["runs.create<br/>(source: linear)"]
    O --> P["Linear trace URL 코멘트"]
```

### 4.3 GitHub 이벤트 처리

```mermaid
flowchart TD
    A["POST /webhooks/github"] --> B["서명 검증<br/>(HMAC-SHA256)"]
    B --> C{"이벤트 유형?"}
    C -->|"지원 외"| IGN["무시"]
    C -->|"issues"| ISS["Issue 처리"]
    C -->|"issue_comment"| CMT{"PR의 코멘트?"}
    C -->|"pull_request_review<br/>pull_request_review_comment"| PR["PR 코멘트 처리"]

    CMT -->|"아니오"| ISS
    CMT -->|"예"| PR

    subgraph IssueFlow["GitHub Issue 흐름"]
        ISS --> ISS_TAG{"@open-swe 태그?"}
        ISS_TAG -->|아니오| IGN2["무시"]
        ISS_TAG -->|예| ISS_ID["thread ID 생성<br/>SHA256(github-issue:id)"]
        ISS_ID --> ISS_EXIST{"기존 thread?"}
        ISS_EXIST -->|아니오| ISS_FULL["전체 이슈 컨텍스트 프롬프트"]
        ISS_EXIST -->|예| ISS_FOLLOW["후속/업데이트 프롬프트"]
        ISS_FULL --> ISS_RUN["runs.create 또는<br/>queue_message_for_thread()"]
        ISS_FOLLOW --> ISS_RUN
    end

    subgraph PRFlow["GitHub PR 코멘트 흐름"]
        PR --> PR_CTX["PR 컨텍스트 추출"]
        PR_CTX --> PR_BRANCH["브랜치명에서 thread ID 추출<br/>open-swe/{uuid}"]
        PR_BRANCH --> PR_FOUND{"thread ID 존재?"}
        PR_FOUND -->|아니오| IGN3["무시"]
        PR_FOUND -->|예| PR_TOKEN["GitHub 토큰 해석"]
        PR_TOKEN --> PR_REACT["이모지 리액션 (👀)"]
        PR_REACT --> PR_CMT["마지막 @open-swe 이후<br/>코멘트 3종 소스 병합"]
        PR_CMT --> PR_RUN["runs.create 또는<br/>queue_message_for_thread()"]
    end
```

## 5. 샌드박스 생명주기

```mermaid
stateDiagram-v2
    [*] --> CheckCache: get_agent() 호출

    CheckCache --> CachedHit: 메모리 캐시 존재
    CheckCache --> CheckMetadata: 캐시 없음

    CheckMetadata --> WaitCreation: sandbox_id == "__creating__"
    CheckMetadata --> CreateNew: sandbox_id 없음
    CheckMetadata --> Reconnect: sandbox_id 존재

    WaitCreation --> Active: 폴링 대기 (최대 180초)

    CreateNew --> Creating: create_sandbox()
    Creating --> Cloning: 저장소 클론
    Cloning --> Active: 클론 완료

    Reconnect --> Active: 기존 sandbox 재연결
    Reconnect --> CreateNew: 연결 실패

    CachedHit --> Active: pull latest
    CachedHit --> Recreate: SandboxClientError

    Recreate --> Creating: _recreate_sandbox()

    Active --> Active: 도구 실행 (execute, write)
    Active --> Cached: 에이전트 종료 → 메모리 캐싱
    Cached --> Active: 동일 thread 재실행

    Active --> Failed: 연결 실패
    Failed --> Recreate
```

## 6. 미들웨어 파이프라인

```mermaid
flowchart TB
    subgraph BeforeModel["@before_model"]
        BM["check_message_queue_before_model"]
        BM_DESC["Store에서 pending_messages 조회<br/>→ 삭제 → human 메시지로 주입"]
    end

    subgraph ModelCall["LLM 호출"]
        LLM["기본 LLM<br/>(Claude Opus 4.6)"]
    end

    subgraph ToolExec["AgentMiddleware"]
        TE["ToolErrorMiddleware"]
        TE_DESC["도구 예외를 JSON ToolMessage로 변환<br/>→ 에이전트 크래시 방지"]
    end

    subgraph AfterModel["@after_model"]
        AM["ensure_no_empty_msg"]
        AM_DESC["도구 호출 없는 텍스트 응답 감지<br/>→ commit_and_open_pr 호출 여부 확인<br/>→ 아니면 no_op 주입하여 루프 유지"]
    end

    subgraph AfterAgent["@after_agent"]
        AA["open_pr_if_needed"]
        AA_DESC["commit_and_open_pr 결과 없고<br/>변경사항 있으면 자동 커밋/푸시/PR"]
    end

    BM --> LLM
    LLM --> TE
    TE --> AM
    AM -->|"루프 계속"| BM
    AM -->|"종료"| AA
```

## 7. 인증 데이터 흐름

```mermaid
flowchart TD
    START["resolve_github_token(config, thread_id)"]
    START --> META{"thread metadata에<br/>github_token_encrypted 존재?"}

    META -->|예| DECRYPT["decrypt_token()<br/>(Fernet 복호화)"]
    DECRYPT --> DONE["GitHub 토큰 반환"]

    META -->|아니오| SRC{"트리거 소스?"}

    SRC -->|Linear| EMAIL_L["코멘트 작성자 이메일"]
    SRC -->|Slack| EMAIL_S["Slack 프로필 이메일"]
    SRC -->|GitHub| GH_CHECK{"bot_token_only_mode?"}

    EMAIL_L --> LS["LangSmith 사용자 ID 조회"]
    EMAIL_S --> LS

    LS --> OAUTH["GitHub OAuth 토큰 획득"]
    OAUTH --> ENC["encrypt_token()"]

    GH_CHECK -->|예| APP["GitHub App 설치 토큰<br/>(JWT → Installation Token)"]
    GH_CHECK -->|아니오| MAP["GITHUB_USER_EMAIL_MAP<br/>(로그인 → 이메일 매핑)"]
    MAP --> LS

    APP --> ENC
    ENC --> PERSIST["persist_encrypted_github_token()<br/>(thread metadata 저장)"]
    PERSIST --> DONE

    OAUTH -->|실패| FAIL["leave_failure_comment()<br/>(Slack/Linear/GitHub)"]
```

## 8. 계층 구조 요약

| 계층 | 역할 | 핵심 컴포넌트 |
|------|------|--------------|
| **Ingress** | 외부 webhook 수신, 서명 검증, 페이로드 파싱, thread 라우팅 | `webapp.py` |
| **Thread 조율** | 작업 상태 지속, 큐 메시지 관리, 메타데이터 보존 | LangGraph Thread, Store |
| **Agent Runtime** | sandbox·인증·프롬프트 준비, Deep Agent 조립 | `server.py`, `prompt.py`, `middleware/` |
| **Tool/Integration** | LLM이 호출하는 도구, 외부 API 연결, sandbox 상태/백엔드 연동 | `tools/`, `utils/`, `integrations/` |
| **External Systems** | GitHub API, Slack API, Linear API, LangSmith, sandbox provider | 외부 서비스 |

**의존 방향:**
- `webapp.py` → LangGraph SDK / utils (직접 `server.py` 호출 안함)
- LangGraph Runtime → `server.py:get_agent`
- `server.py` → prompt / middleware / tools / sandbox/auth utils
- tools / middleware → utils → 외부 API
- sandbox utils → integrations → sandbox provider
