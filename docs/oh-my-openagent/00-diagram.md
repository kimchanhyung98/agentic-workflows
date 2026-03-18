# OMO 실행 파이프라인 다이어그램

## 1. 전체 플러그인 초기화 흐름

```mermaid
flowchart TD
    START([OpenCode CLI 시작]) --> INIT[OhMyOpenCodePlugin 초기화]
    INIT --> CONFIG[initConfigContext<br/>+ loadPluginConfig]
    CONFIG --> MERGE["3단계 설정 병합<br/>Project - User - Defaults"]
    MERGE --> MANAGERS[매니저 생성]
    MANAGERS --> MGR_TMUX[TmuxSessionManager]
    MANAGERS --> MGR_BG["BackgroundManager<br/>동시성: 5/모델"]
    MANAGERS --> MGR_SKILL[SkillMcpManager]
    MANAGERS --> MGR_CFG[ConfigHandler]
    MANAGERS --> TOOLS["도구 등록 (26개)"]
    TOOLS --> HOOKS["훅 생성 (46개)"]
    HOOKS --> H_CORE["코어 훅 (37개)<br/>Session + ToolGuard + Transform"]
    HOOKS --> H_CONT["연속 훅 (7개)<br/>Boulder + Atlas + Ralph"]
    HOOKS --> H_SKILL["스킬 훅 (2개)"]
    H_CORE & H_CONT & H_SKILL --> PLUGIN[플러그인 인터페이스 반환]
    PLUGIN --> READY([대기: 사용자 입력])
```

## 2. 메시지 처리 파이프라인 (chat.message → API 호출 → 응답)

```mermaid
flowchart TD
    USER([사용자 메시지 입력]) --> CM[chat.message 핸들러]

    subgraph PHASE1["1단계: 사전 개입 (chat.message)"]
        CM --> SET_AGENT[세션 에이전트 설정]
        SET_AGENT --> VARIANT[First-Message Variant Gate]
        VARIANT --> FALLBACK_CHK{모델 폴백<br/>보류 중?}
        FALLBACK_CHK -->|Yes| APPLY_FB[폴백 모델 적용]
        FALLBACK_CHK -->|No| SET_MODEL[세션 모델 설정]
        APPLY_FB --> SET_MODEL
        SET_MODEL --> STOP_GUARD[stopContinuationGuard]
        STOP_GUARD --> BG_NOTIFY[backgroundNotificationHook<br/>완료된 백그라운드 태스크 알림]
        BG_NOTIFY --> KEYWORD["keyword-detector<br/>ultrawork/search/analyze 감지"]
        KEYWORD --> START_WORK[start-work 훅]
        START_WORK --> ATLAS_PRE["Atlas 훅<br/>세션 유형, 실패 횟수, 에이전트 매칭"]
    end

    subgraph PHASE2["2단계: 메시지 전처리 (messages.transform)"]
        ATLAS_PRE --> CTX_INJ[contextInjectorMessagesTransform<br/>AGENTS.md / README.md 주입]
        CTX_INJ --> THINK_VAL[thinkingBlockValidator<br/>사고 블록 구조 검증]
    end

    subgraph PHASE3["3단계: API 호출"]
        THINK_VAL --> SYS_TRANSFORM[system.transform<br/>시스템 프롬프트 변환]
        SYS_TRANSFORM --> PARAMS["chat.params<br/>헤더, 파라미터 설정"]
        PARAMS --> API_CALL["LLM API 호출<br/>모델별 프로바이더"]
    end

    API_CALL --> RESPONSE{응답 유형}
    RESPONSE -->|텍스트| DISPLAY([사용자에게 표시])
    RESPONSE -->|도구 호출| TOOL_EXEC[도구 실행 파이프라인]
    RESPONSE -->|에러| ERROR_HANDLE[에러 처리 흐름]
    style PHASE1 fill: #1a1a2e, stroke: #16213e, color: #fff
    style PHASE2 fill: #16213e, stroke: #0f3460, color: #fff
    style PHASE3 fill: #0f3460, stroke: #533483, color: #fff
```

## 3. 도구 실행 파이프라인 (Before → Execute → After)

```mermaid
flowchart TD
    TOOL_CALL([도구 호출 요청]) --> BEFORE

    subgraph BEFORE["tool.execute.before (10개 훅)"]
        direction TB
        B1[writeExistingFileGuard<br/>Read 선행 확인] --> B2[claudeCodeHooks<br/>settings.json 호환]
        B2 --> B3[commentChecker<br/>AI 코멘트 차단]
        B3 --> B4[directoryAgentsInjector<br/>AGENTS.md 자동 주입]
        B4 --> B5[directoryReadmeInjector<br/>README.md 자동 주입]
        B5 --> B6[rulesInjector<br/>조건부 규칙 주입]
        B6 --> B7[tasksTodowriteDisabler<br/>태스크 시스템 활성 시 TodoWrite 차단]
        B7 --> B8[sisyphusJuniorNotepad<br/>서브에이전트 노트패드 주입]
        B8 --> B9[atlasHook<br/>Boulder 상태 관리]
        B9 --> B10{task 도구?}
        B10 -->|Yes| DELEGATE[서브에이전트 위임 처리]
        B10 -->|No| EXECUTE
    end

    subgraph EXEC["도구 실행"]
        EXECUTE["파일: Read/Write/Edit/Bash<br/>정밀: LSP 6종, AST-grep<br/>터미널: Tmux interactive_bash<br/>위임: Task/call_omo_agent"]
    end

    DELEGATE --> EXECUTE

    subgraph AFTER["tool.execute.after (8개 훅)"]
        direction TB
        A1[toolOutputTruncator<br/>출력 크기 제한] --> A2[commentChecker<br/>사후 검증]
        A2 --> A3[emptyTaskResponseDetector<br/>빈 응답 감지]
        A3 --> A4[editErrorRecovery<br/>편집 실패 재시도]
        A4 --> A5[delegateTaskRetry<br/>위임 실패 재시도]
        A5 --> A6[hashlineReadEnhancer<br/>Read 출력 라인 해시 추가]
        A6 --> A7[jsonErrorRecovery<br/>JSON 파싱 에러 복구]
        A7 --> A8[atlasHook<br/>Boulder 상태 업데이트]
    end

    EXEC --> AFTER
    AFTER --> RESULT(["결과 반환 → LLM 다음 단계"])
    style BEFORE fill: #2d132c, stroke: #801336, color: #fff
    style EXEC fill: #801336, stroke: #c72c41, color: #fff
    style AFTER fill: #c72c41, stroke: #ee4540, color: #fff
```

## 4. 에이전트 오케스트레이션 & 위임 체계

```mermaid
flowchart TD
    SISYPHUS["🪨 Sisyphus<br/>메인 오케스트레이터<br/>claude-opus-4-6 max"]
    SISYPHUS -->|심층 코딩 위임| HEPHAESTUS["🔨 Hephaestus<br/>자율 딥 워커<br/>gpt-5.3-codex medium"]
    SISYPHUS -->|전략 기획 위임| PROMETHEUS["🔥 Prometheus<br/>전략 기획자<br/>claude-opus-4-6 max"]
    SISYPHUS -->|사전 컨설팅| METIS["🧠 Metis<br/>Pre-Planning 컨설턴트<br/>claude-opus-4-6 max, temp 0.3"]
    SISYPHUS -->|플랜 검토| MOMUS["🎭 Momus<br/>플랜 리뷰어<br/>gpt-5.4 xhigh"]
    SISYPHUS -->|읽기 전용 자문| ORACLE["🔮 Oracle<br/>읽기 전용 컨설턴트<br/>gpt-5.4 high"]
    SISYPHUS -->|코드 탐색| EXPLORE["🔍 Explore<br/>코드베이스 검색<br/>grok-code-fast-1"]
    SISYPHUS -->|외부 문서 검색| LIBRARIAN["📚 Librarian<br/>외부 문서/코드 검색<br/>gemini-3-flash"]
    SISYPHUS -->|" 이미지/PDF 분석 "| LOOKER["👁️ Multimodal-Looker<br/>시각 자료 분석<br/>gpt-5.3-codex medium"]
    SISYPHUS -->|카테고리 실행| SJ["⚡ Sisyphus-Junior<br/>카테고리 실행자<br/>claude-sonnet-4-6"]
    ATLAS["🗺️ Atlas<br/>Todo 오케스트레이터<br/>claude-sonnet-4-6"]
    ATLAS -.->|Boulder 강제 실행| SISYPHUS

    subgraph TOOL_RESTRICT["도구 제한"]
        ORACLE_R["Oracle: write, edit,<br/>task, call_omo_agent 금지"]
        LIBRARIAN_R["Librarian: write, edit,<br/>task, call_omo_agent 금지"]
        EXPLORE_R["Explore: write, edit,<br/>task, call_omo_agent 금지"]
        LOOKER_R["Looker: read 외 전부 금지"]
        MOMUS_R["Momus: write, edit, task 금지"]
    end

    style SISYPHUS fill: #ff6b35, stroke: #ff9f1c, color: #fff
    style ATLAS fill: #2ec4b6, stroke: #cbf3f0, color: #000
    style HEPHAESTUS fill: #3a86ff, stroke: #8338ec, color: #fff
    style PROMETHEUS fill: #ff006e, stroke: #fb5607, color: #fff
```

## 5. 모델 폴백 체인

```mermaid
flowchart LR
    subgraph SISYPHUS_FB["Sisyphus 폴백"]
        S1[claude-opus-4-6 max] -->|실패| S2[kimi-k2.5]
        S2 -->|실패| S3[gpt-5.4]
        S3 -->|실패| S4[glm-5]
    end

    subgraph HEPH_FB["Hephaestus 폴백"]
        H1[gpt-5.3-codex medium] -->|실패| H2[gpt-5.4 medium]
    end

    subgraph ORACLE_FB["Oracle 폴백"]
        O1[gpt-5.4 high] -->|실패| O2[gemini-3.1-pro]
        O2 -->|실패| O3[claude-opus-4-6]
    end

    subgraph EXPLORE_FB["Explore 폴백"]
        E1[grok-code-fast-1] -->|실패| E2[minimax-m2.5]
        E2 -->|실패| E3[claude-haiku-4-5]
        E3 -->|실패| E4[gpt-5-nano]
    end

    ERR([API 에러 발생]) --> CLASSIFY{에러 분류}
    CLASSIFY -->|재시도 가능| RETRY[같은 모델 재시도]
    CLASSIFY -->|폴백 필요| CHAIN[폴백 체인 진행]
    CLASSIFY -->|치명적| FAIL([실패 보고])
    RETRY -->|재실패| CHAIN
    CHAIN --> NEXT[다음 폴백 모델 적용]
    style ERR fill: #e63946, color: #fff
    style FAIL fill: #e63946, color: #fff
```

## 6. Boulder 연속 실행 메커니즘 (todo-continuation-enforcer)

```mermaid
stateDiagram-v2
    [*] --> Idle: 세션 대기
    Idle --> TodoCheck: session.idle 이벤트
    TodoCheck --> Idle: 미완료 TODO 없음
    TodoCheck --> Countdown: 미완료 TODO 존재
    Countdown --> Recovery: 2초 카운트다운 완료
    Countdown --> Idle: 사용자 취소
    Recovery --> Prompting: 연속 프롬프트 주입
    Prompting --> Working: LLM 작업 재개
    Working --> TodoCheck: 작업 완료 후 idle
    Working --> StagnationCheck: 진전 없음 감지
    StagnationCheck --> Backoff: 정체 확인
    Backoff --> Wait30s: 실패 1회 30초
    Backoff --> Wait60s: 실패 2회 60초
    Backoff --> Wait120s: 실패 3회 120초
    Backoff --> Wait240s: 실패 4회 240초
    Backoff --> Wait300s: 실패 5회 이상 5분 일시정지
    Wait30s --> Recovery
    Wait60s --> Recovery
    Wait120s --> Recovery
    Wait240s --> Recovery
    Wait300s --> Recovery
    Working --> AbortCheck: 중단 조건 감지
    AbortCheck --> [*]: 사용자 취소 또는 에이전트 에러
```

## 7. Atlas 마스터 오케스트레이터 의사결정 게이트

```mermaid
flowchart TD
    EVENT([session.idle 이벤트]) --> G1{세션 유형<br/>판별}
    G1 -->|primary| G2{중단 조건<br/>확인}
    G1 -->|subagent| SKIP([Atlas 스킵])
    G2 -->|중단 필요| ABORT([세션 중단])
    G2 -->|계속| G3{실패 횟수<br/>확인}
    G3 -->|임계값 초과| COOLDOWN[쿨다운 대기]
    G3 -->|허용 범위| G4{백그라운드<br/>태스크 확인}
    G4 -->|완료 대기 중| WAIT([태스크 완료 대기])
    G4 -->|없음/완료| G5{에이전트<br/>매칭}
    G5 -->|매칭 성공| G6{플랜 완료도<br/>확인}
    G5 -->|매칭 실패| FALLBACK[기본 행동]
    G6 -->|미완료| BOULDER[Boulder 연속 실행]
    G6 -->|완료| G7{쿨다운<br/>확인}
    G7 -->|쿨다운 중| WAIT_CD[쿨다운 대기]
    G7 -->|가능| COMPLETE([작업 완료 처리])
    COOLDOWN --> G4
    style EVENT fill: #264653, color: #fff
    style BOULDER fill: #e76f51, color: #fff
    style ABORT fill: #e63946, color: #fff
    style COMPLETE fill: #2a9d8f, color: #fff
```

## 8. 백그라운드 태스크 병렬 실행

```mermaid
flowchart TD
    TASK_CALL["task() 도구 호출"] --> LAUNCH_INPUT["LaunchInput 구성<br/>description, prompt,<br/>category?, subagent_type?"]
    LAUNCH_INPUT --> SPAWN_CHK{스폰 예산<br/>확인}
    SPAWN_CHK -->|초과| REJECT([스폰 거부])
    SPAWN_CHK -->|허용| DEPTH_CHK{중첩 깊이<br/>확인}
    DEPTH_CHK -->|초과| REJECT
    DEPTH_CHK -->|허용| CONCUR_CHK{"동시성 한도<br/>확인 - 5/모델"}
    CONCUR_CHK -->|초과| QUEUE[대기열]
    CONCUR_CHK -->|허용| SPAWN[서브에이전트 스폰]
    QUEUE --> SPAWN
    SPAWN --> BG_SESSION["격리된 백그라운드 세션"]
    BG_SESSION --> EXEC_LOOP["독립 실행<br/>(자체 컨텍스트)"]
    EXEC_LOOP --> CIRCUIT{서킷 브레이커<br/>반복 도구 사용 감지}
    CIRCUIT -->|정상| EXEC_LOOP
    CIRCUIT -->|이상| FORCE_STOP[강제 중단]
    EXEC_LOOP -->|완료| RESULT["결과 반환"]
    EXEC_LOOP -->|실패| FB_CHK{폴백 가능?}
    FB_CHK -->|Yes| FB_RETRY[폴백 모델로 재시도]
    FB_CHK -->|No| FAIL_RESULT[실패 결과 반환]
    FB_RETRY --> EXEC_LOOP
    RESULT --> NOTIFY["backgroundNotificationHook<br/>메인 세션에 알림"]
    FAIL_RESULT --> NOTIFY
    FORCE_STOP --> NOTIFY
    NOTIFY --> PERSIST["background tasks json<br/>이력 저장"]
    NOTIFY --> WAKEUP["메인 세션 chat.message<br/>응답 사이클에 결과 주입"]
    WAKEUP --> RESUME["Sisyphus 컨텍스트 업데이트<br/>후속 작업 재개"]
    style SPAWN fill: #3a86ff, color: #fff
    style BG_SESSION fill: #8338ec, color: #fff
    style NOTIFY fill: #ff006e, color: #fff
    style WAKEUP fill: #06d6a0, color: #000
```

## 9. Ralph Loop (자기 참조 개발 루프)

```mermaid
flowchart TD
    START(["/ralph-loop 또는 /ulw-loop"]) --> INIT["상태 초기화<br/>.sisyphus/ralph-loop.local.md"]
    INIT --> ITER["반복 N 시작<br/>(max: 100)"]
    ITER --> PROMPT["연속 프롬프트 빌드<br/>continuation prompt builder"]
    PROMPT --> LLM["LLM 실행"]
    LLM --> OUTPUT["응답 분석"]
    OUTPUT --> DONE_CHK{"promise DONE 태그<br/>감지?"}
    DONE_CHK -->|Yes| COMPLETE([루프 완료])
    DONE_CHK -->|No| COUNT_CHK{"반복 횟수<br/>100 미만?"}
    COUNT_CHK -->|Yes| ITER
    COUNT_CHK -->|No| TIMEOUT([최대 반복 초과])
    ITER -.->|" /stop-continuation<br/>또는 cancelLoop "| CANCEL([사용자 중단])
    LLM -.->|MessageAbortedError| CANCEL
    style START fill: #06d6a0, color: #000
    style COMPLETE fill: #06d6a0, color: #000
    style TIMEOUT fill: #ef476f, color: #fff
    style CANCEL fill: #e63946, color: #fff
```

## 10. 전체 End-to-End 파이프라인 요약

```mermaid
flowchart TD
    USER(["사용자 입력"]) --> HOOKS_PRE

    subgraph HOOKS_PRE["Tier 1-3: 사전 처리"]
        direction LR
        CM["chat.message<br/>10단계 처리"] --> MT["messages.transform<br/>컨텍스트 주입 + 검증"] --> ST["system.transform<br/>시스템 프롬프트"]
    end

    HOOKS_PRE --> API["☁️ LLM API 호출"]
    API --> RESP{응답 유형}
    RESP -->|텍스트| OUT(["사용자 출력"])
    RESP -->|도구 호출| TOOL_PIPE

    subgraph TOOL_PIPE["Tier 2: 도구 실행"]
        direction LR
        TB["before 훅<br/>가드 + 주입"] --> TE["도구 실행"] --> TA["after 훅<br/>복구 + 검증"]
    end

    TOOL_PIPE --> API
    RESP -->|에러| ERR_PIPE

    subgraph ERR_PIPE["에러 복구"]
        direction LR
        CLASSIFY["에러 분류"] --> FB["모델 폴백<br/>/ 런타임 폴백"]
        FB --> RETRY_API["재시도"]
    end

    ERR_PIPE --> API
    API --> IDLE(["세션 대기"])
    IDLE --> CONT_PIPE

    subgraph CONT_PIPE["Tier 4: 연속 실행"]
        direction LR
        ATLAS_D["Atlas 의사결정<br/>7단계 게이트"] --> BOULDER_D["Boulder<br/>지수 백오프"] --> RALPH_D["Ralph Loop<br/>자기 참조"]
    end

    CONT_PIPE -->|TODO 남음| API
    CONT_PIPE -->|완료| DONE(["작업 완료"])
    USER -.->|" /stop-continuation "| STOP_INT(["사용자 인터럽트"])
    STOP_INT -.-> DONE
    style USER fill: #264653, color: #fff
    style STOP_INT fill: #e63946, color: #fff
    style API fill: #2a9d8f, color: #fff
    style OUT fill: #264653, color: #fff
    style DONE fill: #06d6a0, color: #000
    style HOOKS_PRE fill: #1a1a2e, stroke: #16213e, color: #fff
    style TOOL_PIPE fill: #2d132c, stroke: #801336, color: #fff
    style ERR_PIPE fill: #6b2737, stroke: #e63946, color: #fff
    style CONT_PIPE fill: #3d348b, stroke: #7678ed, color: #fff
```
