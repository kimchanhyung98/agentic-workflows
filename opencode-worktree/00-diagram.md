# OpenCode Worktree 아키텍처 다이어그램

## 1. 모듈 아키텍처 및 초기화

```mermaid
flowchart TD
    START([OpenCode 플러그인 로드]) --> CTX["Plugin Context 수신<br/>directory, client"]

    subgraph INIT["초기화 단계"]
        direction TB
        CTX --> DB["SQLite 초기화<br/>initStateDb"]
        DB --> WAL["PRAGMA journal_mode=WAL<br/>PRAGMA busy_timeout=5000"]
        WAL --> SCHEMA["테이블 생성"]
        SCHEMA --> S_TBL["sessions<br/>id, branch, path, created_at"]
        SCHEMA --> P_TBL["pending_operations<br/>id=1 싱글턴, type, branch, path"]
    end

    subgraph REGISTER["핸들러 등록"]
        direction TB
        CLEANUP["프로세스 정리 핸들러<br/>SIGTERM / SIGINT / beforeExit<br/>→ WAL checkpoint + DB close"]
        T1["worktree_create<br/>격리 환경 생성 + 터미널 스폰"]
        T2["worktree_delete<br/>지연 삭제 예약"]
        EVT["이벤트 핸들러<br/>session.idle → 보류 삭제 실행"]
    end

    INIT --> REGISTER --> READY([대기: AI 도구 호출])
    style INIT fill: #1a1a2e, stroke: #16213e, color: #fff
    style REGISTER fill: #16213e, stroke: #0f3460, color: #fff
```

```mermaid
flowchart LR
    subgraph MODULES["모듈 구조"]
        direction TB
        WT["worktree.ts<br/>플러그인 진입점"]
        STATE["worktree/state.ts<br/>SQLite 상태 관리"]
        TERM["worktree/terminal.ts<br/>크로스 플랫폼 터미널"]

        subgraph PRIM["kdco-primitives 공유 라이브러리"]
            direction LR
            PID["get-project-id.ts<br/>git 루트 커밋 SHA"]
            SHELL["shell.ts<br/>bash/batch/AppleScript 이스케이프"]
            MUTEX["mutex.ts<br/>Promise 기반 뮤텍스"]
            TD["terminal-detect.ts<br/>tmux 환경 감지"]
            TOUT["with-timeout.ts<br/>타임아웃 래퍼"]
        end
    end

    WT --> STATE
    WT --> TERM
    TERM --> MUTEX
    TERM --> SHELL
    TERM --> TD
    STATE --> PID

    subgraph REUSE["다른 OCX 플러그인에서 재사용"]
        direction LR
        R1["opencode-workspace"]
        R2["opencode-background-agents"]
        R3["opencode-notify"]
    end

    PRIM -.-> REUSE
    style MODULES fill: #0f3460, stroke: #533483, color: #fff
    style PRIM fill: #264653, stroke: #2a9d8f, color: #fff
```

## 2. Worktree 생성 파이프라인

```mermaid
flowchart TD
    CALL(["worktree_create 호출"]) --> VAL

    subgraph VAL["1단계: 경계 검증"]
        direction TB
        V1["Zod branchNameSchema"]
        V1 --> V2["시작 문자 하이픈 차단<br/>옵션 인젝션 방지"]
        V2 --> V3["제어문자 · git 메타문자 차단<br/>셸 메타문자 차단"]
        V3 --> V4["경로 순회 차단<br/>.. // 절대경로"]
        V4 --> V5["255자 제한 · .lock 접미사 차단"]
    end

    VAL -->|실패| ERR(["❌ 오류 반환"])
    VAL -->|성공| GIT

    subgraph GIT["2단계: Git Worktree 생성"]
        direction TB
        EXISTS{"브랜치 존재?"}
        EXISTS -->|Yes| CHECKOUT["git worktree add<br/>worktreePath branch"]
        EXISTS -->|No| CREATE["git worktree add -b<br/>branch worktreePath base"]
    end

    GIT --> SYNC

    subgraph SYNC["3단계: 파일 동기화"]
        direction TB
        LOAD_CFG["worktree.jsonc 로드<br/>없으면 자동 생성 + Zod 검증"]
        LOAD_CFG --> PATH_CHK["isPathSafe 검증<br/>절대경로 · 상위순회 · 이탈 거부"]
        PATH_CHK --> COPY["copyFiles: .env 등<br/>독립 사본 생성"]
        COPY --> SYMLINK["symlinkDirs: node_modules 등<br/>심볼릭 링크로 디스크 절약"]
        SYMLINK --> HOOKS["postCreate 훅 실행<br/>pnpm install 등"]
    end

    SYNC --> FORK

    subgraph FORK["4단계: 세션 포크 + 컨텍스트 전파"]
        direction TB
        ROOT["parentID 체인 순회<br/>최대 10단계 → 루트 세션 ID"]
        ROOT --> FORK_API["client.session.fork"]
        FORK_API --> CP_PLAN["plan.md 복사<br/>작업 계획 유지"]
        CP_PLAN --> CP_DEL["delegations 복사<br/>위임 상태 유지"]
        CP_DEL --> ROLLBACK{"실패 시 원자적 롤백<br/>포크 세션 삭제 + 디렉토리 정리"}
    end

    FORK --> TERMINAL["5단계: 터미널 스폰<br/>openTerminal → opencode --session ID"]
    TERMINAL --> RECORD["6단계: DB 기록<br/>addSession"]
    RECORD --> DONE(["✅ 새 터미널에서 OpenCode 실행 중"])
    style VAL fill: #e76f51, stroke: #f4a261, color: #fff
    style GIT fill: #1a1a2e, stroke: #16213e, color: #fff
    style SYNC fill: #264653, stroke: #2a9d8f, color: #fff
    style FORK fill: #16213e, stroke: #0f3460, color: #fff
```

## 3. Worktree 삭제 및 지연 삭제 패턴

```mermaid
flowchart TD
    DELETE(["worktree_delete"]) --> FIND{"getSession<br/>현재 세션의 worktree 조회"}
    FIND -->|없음| NO_WT(["연결된 worktree 없음"])
    FIND -->|있음| PENDING

    subgraph DEFERRED["지연 삭제 패턴: Deferred Delete"]
        direction TB
        PENDING["setPendingDelete<br/>INSERT OR REPLACE 싱글턴<br/>기존 보류 작업은 경고 후 대체"]
        PENDING --> RESPOND(["세션 종료 시 정리됩니다 반환<br/>→ 작업 중 데이터 손실 방지"])
    end

    RESPOND -.-> IDLE

    subgraph IDLE_HANDLER["session.idle 이벤트 핸들러"]
        direction TB
        IDLE["session.idle 이벤트 감지"]
        IDLE --> CHECK{"getPendingDelete<br/>보류 삭제 존재?"}
        CHECK -->|없음| SKIP([처리 없음])
    end

    CHECK -->|있음| CLEANUP

    subgraph CLEANUP["정리 프로세스"]
        direction TB
        PRE_HOOKS["① preDelete 훅 실행<br/>docker compose down 등"]
        PRE_HOOKS --> GIT_ADD["② git add -A<br/>모든 변경사항 스테이징"]
        GIT_ADD --> GIT_COMMIT["③ git commit --allow-empty<br/>worktree session snapshot"]
        GIT_COMMIT --> REMOVE["④ git worktree remove --force"]
        REMOVE --> CLEAR["⑤ clearPendingDelete<br/>removeSession"]
    end

    CLEANUP --> DONE(["✅ 브랜치에 변경사항 보존<br/>worktree 깨끗하게 제거"])
    style DEFERRED fill: #3d348b, stroke: #7678ed, color: #fff
    style IDLE_HANDLER fill: #1a1a2e, stroke: #16213e, color: #fff
    style CLEANUP fill: #2d132c, stroke: #801336, color: #fff
```

## 4. SQLite 상태 모델 및 생명주기

```mermaid
erDiagram
    SESSIONS {
        text id PK "포크된 세션 ID"
        text branch "브랜치명"
        text path "worktree 절대 경로"
        text created_at "ISO 8601 생성 시각"
    }

    PENDING_OPERATIONS {
        integer id PK "항상 1 싱글턴 제약"
        text type "spawn 또는 delete"
        text branch "대상 브랜치"
        text path "worktree 경로"
        text session_id "세션 ID - spawn만 사용"
    }

    SESSIONS ||--o| PENDING_OPERATIONS: "삭제 예약 시 참조"
```

```mermaid
stateDiagram-v2
    [*] --> Validated: worktree_create 호출 + 브랜치 검증 통과

    state CreatePhase {
        Validated --> GitCreated: git worktree add
        GitCreated --> Synced: copyFiles + symlinkDirs + postCreate 훅
        Synced --> Forked: session.fork + plan/delegations 복사
    }

    Forked --> Active: 터미널 스폰 + DB 기록

    state ActivePhase {
        Active --> Active: 격리된 OpenCode 세션에서 독립 작업
    }

    Active --> PendingDelete: worktree_delete → setPendingDelete

    state PendingPhase {
        PendingDelete --> PendingDelete: 세션 아직 활성
    }

    PendingDelete --> Cleanup: session.idle 이벤트 발생

    state CleanupPhase {
        Cleanup --> PreHook: preDelete 훅 실행
        PreHook --> Committed: git add + commit 스냅샷
        Committed --> Removed: git worktree remove --force
        Removed --> DBCleared: clearPendingDelete + removeSession
    }

    DBCleared --> [*]: 완료
```

## 5. 크로스 플랫폼 터미널 감지

```mermaid
flowchart TD
    OPEN(["openTerminal 호출"]) --> DETECT["detectTerminalType"]
    DETECT --> P1{"tmux 내부?<br/>TMUX 환경변수"}
    P1 -->|Yes| TMUX
    P1 -->|No| P2{"WSL 환경?<br/>WSL_DISTRO_NAME 또는<br/>os.release에 microsoft"}
    P2 -->|Yes| WSL
    P2 -->|No| P3{"process.platform"}
    P3 -->|darwin| MAC_DETECT
    P3 -->|win32| WIN
    P3 -->|linux| LINUX_DETECT

    subgraph TMUX["tmux (모든 플랫폼 우선)"]
        direction TB
        T_MUTEX["Mutex.runExclusive<br/>소켓 레이스 방지"]
        T_MUTEX --> T_SPAWN["Bun.spawnSync 배열 기반<br/>셸 보간 없음"]
        T_SPAWN --> T_DELAY["150ms 안정화 대기<br/>tmux 서버 처리 시간"]
    end

    subgraph MAC_DETECT["macOS 터미널 감지 (환경변수 우선순위)"]
        direction TB
        M1["GHOSTTY_RESOURCES_DIR → Ghostty<br/>open -na, 인라인 명령"]
        M2["ITERM_SESSION_ID → iTerm2<br/>AppleScript write text, 탭 생성"]
        M3["KITTY_WINDOW_ID → Kitty<br/>@ launch --type tab 우선, 새 창 폴백"]
        M4["ALACRITTY_WINDOW_ID → Alacritty<br/>--working-directory, detached"]
        M5["__CFBundleIdentifier → Warp<br/>open -b, detached"]
        M6["TERM_PROGRAM 폴백 → Terminal.app<br/>open -a Terminal, withTempScript"]
    end

    subgraph LINUX_DETECT["Linux 터미널 감지 (6단계 폴백 체인)"]
        direction TB
        L1["① 현재 터미널 감지<br/>KITTY · WEZTERM · ALACRITTY<br/>GHOSTTY · GNOME · KONSOLE"]
        L1 --> L2["② xdg-terminal-exec<br/>XDG 표준"]
        L2 --> L3["③ x-terminal-emulator<br/>Debian/Ubuntu"]
        L3 --> L4["④ 모던 터미널<br/>kitty · alacritty · wezterm · ghostty · foot"]
        L4 --> L5["⑤ DE 터미널<br/>gnome-terminal · konsole · xfce4-terminal"]
        L5 --> L6["⑥ xterm 최후 수단"]
    end

    subgraph WSL["WSL (Linux → Windows 인터롭)"]
        direction TB
        WSL1["wt.exe 우선<br/>Windows Terminal via PATH"]
        WSL1 --> WSL2["bash 폴백<br/>현재 터미널에서 새 프로세스"]
    end

    subgraph WIN["Windows"]
        direction TB
        W1["Windows Terminal wt.exe"]
        W1 --> W2["cmd.exe 폴백"]
    end

    style TMUX fill: #2a9d8f, stroke: #264653, color: #fff
    style MAC_DETECT fill: #0f3460, stroke: #533483, color: #fff
    style LINUX_DETECT fill: #1a1a2e, stroke: #16213e, color: #fff
    style WSL fill: #3d348b, stroke: #7678ed, color: #fff
    style WIN fill: #16213e, stroke: #0f3460, color: #fff
```

## 6. 임시 스크립트 생명주기

```mermaid
flowchart TD
    SPAWN(["터미널 스폰 요청"]) --> TYPE{"터미널 유형"}
    TYPE -->|동기 터미널| SYNC
    TYPE -->|비동기 터미널| ASYNC
    TYPE -->|Windows| BATCH

    subgraph SYNC["동기: Terminal.app"]
        direction TB
        S1["withTempScript 호출"]
        S1 --> S2["스크립트 파일 생성 + chmod 755"]
        S2 --> S3["스크립트 실행<br/>프로세스 완료 대기"]
        S3 --> S4["finally: 스크립트 삭제"]
    end

    subgraph ASYNC["비동기: 대부분의 터미널"]
        direction TB
        A1["스크립트 파일 직접 생성"]
        A1 --> A2["trap 자기 삭제 트랩 삽입<br/>EXIT INT TERM 시그널"]
        A2 --> A3["detached 스폰<br/>proc.unref"]
        A3 --> A4["스크립트 자가 삭제<br/>EXIT 시그널 시"]
        A1 -.->|" ⚠️ withTempScript 사용 금지 "| NOTE["finally 블록이 detached 프로세스보다<br/>먼저 실행 → 레이스 컨디션"]
    end

    subgraph BATCH["Windows .bat"]
        direction TB
        B1["batch 스크립트 생성"]
        B1 --> B2["goto 자기 삭제 관용구 삽입<br/>batch 실행 후 파일 삭제"]
        B2 --> B3["detached 스폰"]
    end

    SYNC --> CLEAN(["✅ 정리 완료"])
    ASYNC --> CLEAN
    BATCH --> CLEAN
    ASYNC -.->|" 스폰 실패 시 "| ERR_CLEAN["orphaned 스크립트<br/>catch 블록에서 수동 삭제"]
    ERR_CLEAN --> CLEAN
    style SYNC fill: #2a9d8f, stroke: #264653, color: #fff
    style ASYNC fill: #e76f51, stroke: #f4a261, color: #fff
    style BATCH fill: #3d348b, stroke: #7678ed, color: #fff
```

## 7. 파일 동기화 전략

```mermaid
flowchart LR
    subgraph MAIN["메인 워크트리 (프로젝트 루트)"]
        ENV[".env / .env.local<br/>비밀 정보"]
        NM["node_modules/<br/>수백 MB"]
        SRC["src/<br/>소스 코드"]
        CFG[".opencode/worktree.jsonc<br/>동기화 설정"]
    end

    subgraph WT["새 워크트리"]
        ENV_COPY[".env 독립 복사본<br/>변경해도 원본 불변"]
        NM_LINK["node_modules/ → 심볼릭 링크<br/>디스크 절약, 즉시 사용"]
        SRC_GIT["src/ git checkout<br/>브랜치별 독립 코드"]
    end

    ENV -->|" copyFiles<br/>isPathSafe 검증 후 복사 "| ENV_COPY
    NM -->|" symlinkDirs<br/>isPathSafe 검증 후 링크 "| NM_LINK
    SRC -->|" git worktree add<br/>브랜치 체크아웃 "| SRC_GIT
    CFG -.->|" 로드: jsonc-parser + Zod 검증<br/>없으면 기본 템플릿 자동 생성 "| WT
    style MAIN fill: #264653, color: #fff
    style WT fill: #2a9d8f, color: #fff
```

## 8. 보안 검증 체인

```mermaid
flowchart TD
    INPUT(["사용자 입력: 브랜치명, 경로"]) --> LAYER1

    subgraph LAYER1["Layer 1: 브랜치명 검증 - Zod Schema"]
        direction TB
        Z1["빈 문자열 · 255자 초과 거부"]
        Z1 --> Z2["시작 하이픈 차단<br/>→ git 옵션 인젝션 방지"]
        Z2 --> Z3["시작/끝 슬래시 · 이중슬래시 · 이중점 차단<br/>→ 경로 순회 방지"]
        Z3 --> Z4["at-brace 구문 차단<br/>→ git reflog 구문 방지"]
        Z4 --> Z5["제어문자 차단<br/>→ 터미널 이스케이프 방지"]
        Z5 --> Z6["git 메타문자 차단<br/>→ git ref 규칙 준수"]
        Z6 --> Z7["셸 메타문자 차단<br/>→ 명령 인젝션 방지"]
        Z7 --> Z8["시작/끝 점 · .lock 접미사 차단<br/>→ git 내부 충돌 방지"]
    end

    LAYER1 --> LAYER2

    subgraph LAYER2["Layer 2: 경로 안전성 검증"]
        direction TB
        P1["절대 경로 거부<br/>path.isAbsolute"]
        P1 --> P2["이중점 포함 거부<br/>상위 디렉토리 순회"]
        P2 --> P3["기준 디렉토리 이탈 거부<br/>path.resolve + startsWith"]
    end

    LAYER2 --> LAYER3

    subgraph LAYER3["Layer 3: 실행 보안"]
        direction TB
        E1["git · tmux 명령<br/>Bun.spawn 배열 기반<br/>셸 보간 완전 차단"]
        E2["셸 문자열 이스케이프<br/>assertShellSafe: null 바이트 검증<br/>escapeBash / escapeBatch"]
        E3["사용자 훅 명령<br/>bash -c 실행<br/>설정 파일 신뢰 기반"]
    end

    LAYER3 --> SAFE(["안전한 실행"])
    style LAYER1 fill: #e76f51, stroke: #f4a261, color: #fff
    style LAYER2 fill: #e63946, stroke: #f4a261, color: #fff
    style LAYER3 fill: #264653, stroke: #2a9d8f, color: #fff
```

## 9. 프로젝트 ID 생성 및 캐싱

```mermaid
flowchart TD
    START(["getProjectId 호출"]) --> GIT_CHK{".git 존재?"}
    GIT_CHK -->|없음| HASH["SHA-256 경로 해시<br/>→ 16자 hex"]
    GIT_CHK -->|디렉토리| CACHE_CHK
    GIT_CHK -->|파일| RESOLVE["gitdir 참조 해석<br/>.git 파일 → gitdir: 경로 추출<br/>commondir → 공유 .git 디렉토리"]
    RESOLVE --> CACHE_CHK
    CACHE_CHK{".git/opencode<br/>캐시 파일"} -->|유효한 40/16자 hex| RETURN(["캐시된 ID 반환"])
    CACHE_CHK -->|없음 또는 무효| GIT_REV["git rev-list --max-parents=0 --all<br/>5초 타임아웃"]
    GIT_REV -->|성공| ROOT_SHA["루트 커밋 SHA 목록 정렬<br/>→ 첫 번째 40자 hex"]
    GIT_REV -->|실패| HASH
    GIT_REV -->|타임아웃| KILL["proc.kill 후 폴백"]
    KILL --> HASH
    ROOT_SHA --> CACHE_WRITE[".git/opencode에 캐시 저장"]
    CACHE_WRITE --> RETURN
    HASH --> RETURN
    style START fill: #3a86ff, color: #fff
    style RETURN fill: #06d6a0, color: #000
    style HASH fill: #e63946, color: #fff
```

## 10. 데이터 경로 맵

```mermaid
flowchart TD
    subgraph PROJECT["프로젝트 디렉토리"]
        direction TB
        GITDIR[".git/opencode<br/>프로젝트 ID 캐시 40자 SHA"]
        OCDIR[".opencode/worktree.jsonc<br/>동기화 설정 JSONC"]
    end

    subgraph HOME["~/.local/share/opencode/"]
        direction TB
        WT_DIR["worktree/<project-id>/<branch>/<br/>격리된 worktree 파일"]
        PLUGIN_DB["plugins/worktree/project-id.sqlite<br/>세션 + 보류 연산 상태, WAL 모드"]
        WS_DIR["workspace/project-id/session-id/plan.md<br/>작업 계획, 세션 포크 시 복사"]
        DL_DIR["delegations/project-id/session-id/<br/>위임 상태, 세션 포크 시 복사"]
    end

    subgraph TEMP["OS 임시 디렉토리"]
        direction TB
        SCRIPTS["worktree-*.sh / .bat<br/>터미널 스폰 스크립트, 자동 삭제"]
    end

    PROJECT -.->|" 프로젝트 ID로 연결 "| HOME
    HOME -.->|" 세션 포크 시 "| WS_DIR
    HOME -.->|" 세션 포크 시 "| DL_DIR
    style PROJECT fill: #264653, color: #fff
    style HOME fill: #0f3460, stroke: #533483, color: #fff
    style TEMP fill: #6b2737, stroke: #e63946, color: #fff
```

## 11. 전체 End-to-End 파이프라인

```mermaid
flowchart TD
    AI(["AI 에이전트"]) --> CREATE

    subgraph CREATE["생성 단계"]
        direction LR
        C1["Zod 브랜치<br/>검증"] --> C2["git worktree<br/>add"] --> C3["파일 동기화<br/>copy + symlink"] --> C4["세션 포크<br/>plan + delegations"]
    end

    CREATE --> SPAWN["터미널 스폰"]
    SPAWN --> DETECT

    subgraph DETECT["플랫폼 자동 감지"]
        direction LR
        D1["tmux?"] --> D2["WSL?"] --> D3["macOS 7종<br/>Linux 10종<br/>Windows 2종"]
    end

    DETECT --> WORK

    subgraph WORK["작업 단계: 격리된 환경"]
        direction LR
        W1["독립 터미널"] --> W2["포크된 OpenCode 세션<br/>plan.md 컨텍스트 유지"] --> W3["자유로운 실험<br/>메인 환경 영향 없음"]
    end

    WORK --> DELETE_CALL["worktree_delete 호출"]
    DELETE_CALL --> DEFER

    subgraph DEFER["지연 삭제"]
        direction LR
        F1["DB에 삭제 예약<br/>싱글턴 pending"] --> F2["session.idle<br/>이벤트 대기"]
    end

    DEFER --> CLEANUP

    subgraph CLEANUP["정리 단계"]
        direction LR
        CL1["preDelete<br/>훅 실행"] --> CL2["git add -A<br/>+ commit<br/>스냅샷"] --> CL3["git worktree<br/>remove --force"] --> CL4["DB 정리<br/>pending + session"]
    end

    CLEANUP --> DONE(["✅ 브랜치에 변경사항 보존<br/>worktree 깨끗하게 제거"])
    AI -.->|" 동시에 여러 worktree 가능<br/>각각 독립 터미널 + 세션 "| CREATE
    style CREATE fill: #1a1a2e, stroke: #16213e, color: #fff
    style DETECT fill: #3d348b, stroke: #7678ed, color: #fff
    style WORK fill: #0f3460, stroke: #533483, color: #fff
    style DEFER fill: #264653, stroke: #2a9d8f, color: #fff
    style CLEANUP fill: #2d132c, stroke: #801336, color: #fff
```
