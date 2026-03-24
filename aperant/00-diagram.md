# Aperant 아키텍처 다이어그램

## 1. 전체 계층 구조

```mermaid
flowchart TD
    subgraph UI["Renderer (React 19 + Zustand)"]
        UI1["Task Board / Review / Terminal / Settings"]
        UI2["Zustand Stores"]
    end

    subgraph IPC["Main Process / IPC"]
        IPC1["ipc-handlers/*<br/>task, github, gitlab, linear, mcp, memory ..."]
        IPC2["taskStateManager<br/>XState task machine"]
        IPC3["agent-events-handlers<br/>worker 이벤트 → status/plan sync"]
    end

    subgraph Runtime["Task Runtime"]
        RT1["AgentManager"]
        RT2["AgentProcessManager"]
        RT3["WorkerBridge / worker_threads"]
        RT4["AgentEvents<br/>structured phase parser"]
    end

    subgraph Orch["오케스트레이션"]
        OR1["SpecOrchestrator<br/>complexity-first spec pipeline"]
        OR2["BuildOrchestrator<br/>planning → coding → qa_review → qa_fixing"]
        OR3["QALoop<br/>qa_reviewer ↔ qa_fixer"]
        OR4["Spec Agentic Mode<br/>SpawnSubagent 기반"]
    end

    subgraph Provider["모델 / 인증"]
        PV1["Provider Registry<br/>11 providers"]
        PV2["Auth Resolver<br/>priority queue + legacy profile fallback"]
        PV3["Phase Config<br/>phase별 모델·thinking"]
    end

    subgraph Tools["도구 / 보안"]
        TL1["ToolRegistry<br/>9 builtin tools + MCP merge"]
        TL2["Tool.define hooks<br/>write-path containment"]
        TL3["bashSecurityHook<br/>denylist + per-command validators"]
    end

    subgraph Repo["Git 작업공간"]
        RP1["main project"]
        RP2[".auto-claude/specs/{specId}"]
        RP3[".auto-claude/worktrees/tasks/{specId}"]
        RP4["merge / discard / cleanup handlers"]
    end

    subgraph Feature["부가 러너"]
        F1["AgentQueueManager<br/>roadmap / ideation queue"]
    end

    UI1 --> IPC1
    UI2 -.-> UI1
    IPC1 --> IPC2
    IPC1 --> IPC3
    IPC1 --> RT1
    IPC3 --> IPC2
    RT1 --> RT2
    RT2 --> RT3
    RT2 --> RT4
    RT3 --> OR1
    RT3 --> OR2
    RT3 --> OR3
    RT3 -.-> OR4
    RT3 --> TL1
    TL1 --> TL2
    TL1 --> TL3
    RT1 --> PV1
    PV1 --> PV2
    PV1 --> PV3
    PV3 --> RT3
    RT1 --> RP2
    RT1 --> RP3
    RP3 --> RP4
    F1 -.-> RT2
```

## 2. TASK_START 실행 흐름

```mermaid
sequenceDiagram
    participant UI as Renderer
    participant IPC as task/execution-handlers.ts
    participant State as taskStateManager
    participant AM as AgentManager
    participant Auth as Auth Resolver
    participant WT as createOrGetWorktree
    participant PM as AgentProcessManager
    participant WB as WorkerBridge
    participant Worker as worker.ts

    UI->>IPC: IPC_CHANNELS.TASK_START(taskId)
    IPC->>IPC: task/project 조회 + git/auth 검증
    IPC->>IPC: implementation_plan.json subtasks 유효성 확인
    IPC->>State: PLANNING_STARTED / PLAN_APPROVED / USER_RESUMED
    IPC->>IPC: fileWatcher.watch(main spec 또는 worktree spec)

    alt spec.md 없음
        IPC->>AM: startSpecCreation(...)
        AM->>Auth: resolveAuth(...)
        Auth-->>AM: provider + model + credentials
        AM->>PM: spawnWorkerProcess(spec_orchestrator)
    else spec.md 있음
        IPC->>AM: startTaskExecution(...)
        AM->>Auth: resolveAuth(...)
        Auth-->>AM: provider + model + credentials
        AM->>WT: createOrGetWorktree(projectPath, specId, baseBranch)
        WT-->>AM: worktreePath / branch / copied spec dir
        AM->>PM: spawnWorkerProcess(build_orchestrator)
    end

    PM->>WB: bridge.spawn(executorConfig)
    WB->>Worker: worker.ts
    Worker-->>PM: task-event / execution-progress / result / exit
    PM-->>IPC: emitter 이벤트 전달
    IPC-->>UI: TASK_LOG / TASK_PROGRESS / TASK_STATUS_CHANGE
```

## 3. 오케스트레이션 파이프라인

### 3.1 스펙 생성 (SpecOrchestrator)

```mermaid
flowchart TD
    A["complexity_assessment"] --> B{"complexity"}

    B -->|simple| S1["quick_spec"]
    S1 --> S2["validation"]

    B -->|standard| T1["discovery"]
    T1 --> T2["requirements"]
    T2 --> T3["spec_writing"]
    T3 --> T4["planning"]
    T4 --> T5["validation"]

    B -->|complex| C1["discovery"]
    C1 --> C2["requirements"]
    C2 --> C3["research"]
    C3 --> C4["context"]
    C4 --> C5["spec_writing"]
    C5 --> C6["self_critique"]
    C6 --> C7["planning"]
    C7 --> C8["validation"]
```

### 3.2 빌드 실행 (BuildOrchestrator + QALoop)

```mermaid
flowchart TD
    A["planning<br/>implementation_plan.json 생성/정규화"] --> B["coding<br/>subtask 순차/병렬 실행"]
    B --> C["qa_review<br/>구현 검증"]
    C --> D{"QA 통과?"}
    D -->|아니오| E["qa_fixing<br/>이슈 수정"]
    E --> C
    D -->|예| F["human_review 대기"]
    F --> G{"승인?"}
    G -->|예| H["done 또는 merge 단계"]
    G -->|아니오| I["QA_FIX_REQUEST.md 작성"]
    I --> J["startQAProcess()"]
    J --> C
```

## 4. auto-swap (rate limit/auth failure) 복원 흐름

```mermaid
flowchart TD
    A["Worker 실행 중 오류 발생"] --> B{"에러 분류"}
    B -->|429 rate limit| C["sdk-rate-limit 이벤트 emit"]
    B -->|401 auth failure| D["auth-failure 이벤트 emit"]
    B -->|기타| Z["실패 이벤트 전파"]
    C --> E["auto-swap-restart-task emit"]
    D --> E
    E --> F["AgentManager.restartTask(taskId, newProfileId)"]
    F --> G{"swapCount < 2?"}
    G -->|아니오| Z
    G -->|예| H["현재 프로세스 kill"]
    H --> I["generation 증가<br/>stale exit 방지"]
    I --> J["stuck subtask reset"]
    J --> K["startSpecCreation / startTaskExecution 재호출"]
    K --> L["새 provider/account로 Worker 재실행"]
```

## 5. worktree 생명주기

```mermaid
stateDiagram-v2
    [*] --> CheckExisting: startTaskExecution
    CheckExisting --> Reuse: git에 등록된 worktree 존재
    CheckExisting --> CleanupStale: 디렉토리만 남은 stale 상태
    CleanupStale --> Create: stale 제거 후 재생성
    CheckExisting --> Create: worktree 없음

    Reuse --> Active
    Create --> Active: git worktree add -b auto-claude/{specId}
    Active --> Review: QA 통과 → human_review
    Review --> Rejected: TASK_REVIEW rejected
    Rejected --> Active: QA_FIX_REQUEST + QA 재실행
    Review --> Merge: TASK_WORKTREE_MERGE
    Merge --> Cleanup: full merge + cleanupWorktree
    Merge --> Retained: stage-only merge / keepWorktree
    Retained --> Cleanup: discard 또는 forceCleanup
    Cleanup --> [*]
```

## 6. 리뷰/QA 분기

```mermaid
flowchart TD
    A["TASK_REVIEW(taskId, approved?)"] --> B{"approved?"}

    B -->|Yes| C["qa_report.md 기록 + MARK_DONE"]

    B -->|No & worktree 있음| D["main 작업공간 reset / checkout / clean"]
    D --> E["worktree spec dir에 QA_FIX_REQUEST.md 저장"]
    E --> F["startQAProcess(worktreePath)"]
    F --> G["USER_RESUMED 상태 전이"]

    B -->|No & worktree 없음| H["main spec dir에 QA_FIX_REQUEST.md 저장"]
    H --> I["startQAProcess(projectPath)"]
    I --> G
```

## 7. AI 세션 내부 실행 흐름

```mermaid
flowchart TD
    A["runContinuableSession()<br/>runAgentSession() 감싸기"] --> B["streamText() 호출<br/>— Vercel AI SDK v6"]
    B --> C{"응답 수신"}
    C -->|tool_call| D["ToolRegistry + MCP 도구 조회"]
    D --> E{"쓰기 도구?"}
    E -->|예| F["allowedWritePaths 검사"]
    E -->|아니오| G{"bash 도구?"}
    F --> G
    G -->|예| H["bashSecurityHook<br/>denylist + validator"]
    H -->|deny| I["거부 응답 반환"]
    H -->|allow| J["도구 실행"]
    G -->|아니오| J
    J --> K["결과를 대화에 추가"]
    K --> B
    C -->|text / reasoning / tool-result| L["stream-event 전파"]
    L --> M{"maxSteps / stopWhen 도달?"}
    M -->|아니오| B
    M -->|예| N["세션 종료"]
    C -->|401 / 429| O["onAuthRefresh / onAccountSwitch"]
    O -->|성공| B
    O -->|실패| P["에러 반환"]
    C -->|context 85%+| Q["경고, 90% 이상이면 continuation 또는 abort"]
```

## 8. Semantic Merge 파이프라인

```mermaid
flowchart TD
    A["merge 요청<br/>TASK_WORKTREE_MERGE"] --> B["file-evolution.ts<br/>baseline + task 버전 로드"]
    B --> C["semantic-analyzer.ts<br/>변경 의도 분류 (35+ 타입)"]
    C --> D["conflict-detector.ts<br/>겹치는 변경 영역 식별"]
    D --> E{"충돌 존재?"}
    E -->|없음| F["auto-merger.ts<br/>deterministic 전략 적용"]
    E -->|있음| G{"충돌 심각도"}
    G -->|LOW/MEDIUM| F
    G -->|HIGH/CRITICAL| H["merge_resolver agent<br/>AI 충돌 해결"]
    H --> I{"해결 성공?"}
    I -->|예| J["병합 결과 적용"]
    I -->|아니오| K["HUMAN_REQUIRED<br/>사람 확인 필요"]
    F --> J
    J --> L["merge report 생성<br/>auto/AI/review 통계"]
```

## 9. Provider 인증 해석 흐름

```mermaid
flowchart TD
    A["Auth Resolver"] --> B["providerAccounts + globalPriorityOrder 로드"]
    B --> C["우선순위 큐 정렬"]
    C --> D{"계정 순회"}
    D --> E["provider/model 매핑 해석"]
    E --> F["토큰 유효성 확인"]
    F -->|유효| G["사용량 / rate limit 확인"]
    G -->|사용 가능| H["해당 account 사용"]
    G -->|제한 초과| D
    F -->|만료| I["토큰 갱신 시도"]
    I -->|성공| G
    I -->|실패| D
    D -->|모두 실패| J["레거시 Claude profile fallback"]
```
