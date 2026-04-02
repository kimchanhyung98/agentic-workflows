# OpenSpace 아키텍처 다이어그램

## 1. 전체 시스템 계층 구조

```mermaid
flowchart TD
    subgraph Host["Host Agent Layer"]
        A1["Claude Code / Codex / OpenClaw / nanobot / Cursor"]
    end

    subgraph MCP["OpenSpace MCP Server Layer"]
        B1["openspace-mcp (FastMCP)<br/>stdio / SSE transport"]
        B2["host_skills<br/>delegate-task / skill-discovery"]
        B3["_MCPSafeStdout<br/>stdout 보호 메커니즘"]
    end

    subgraph Orchestrator["OpenSpace Orchestrator (tool_layer.py)"]
        C0["OpenSpace + OpenSpaceConfig"]
        C1["Phase 1: Skill-Guided Execution"]
        C2["Phase 2: Tool-Fallback Execution"]
        C3["Post-Execution Pipeline"]
    end

    subgraph Agent["GroundingAgent Runtime"]
        D1["GroundingAgent<br/>반복 루프 (max_iterations)"]
        D2["LLMClient (litellm 래퍼)<br/>Rate Limit + 재시도 로직"]
        D3["GroundingClient<br/>Provider Registry + Tool Cache"]
        D4["RecordingManager<br/>conversations.jsonl / traj.jsonl"]
    end

    subgraph Backends["Backend Providers"]
        E1["ShellProvider<br/>Local/Server 이중 모드<br/>bash/python 실행"]
        E2["GUIProvider<br/>Anthropic Computer Use<br/>PyAutoGUI 자동화"]
        E3["MCPProvider<br/>다중 MCP 서버 관리<br/>stdio/HTTP/WS/Sandbox"]
        E4["WebProvider<br/>Deep Research (OpenRouter)<br/>Perplexity sonar"]
        E5["SystemProvider<br/>메타 도구 (도구 목록 등)"]
    end

    subgraph Skill["Skill Engine"]
        F1["SkillRegistry<br/>발견 / 선택 / 주입"]
        F2["SkillRanker<br/>BM25 + embedding 하이브리드"]
        F3["ExecutionAnalyzer<br/>사후 실행 분석"]
        F4["SkillEvolver<br/>FIX / DERIVED / CAPTURED"]
        F5["SkillStore<br/>SQLite WAL + Version DAG"]
    end

    subgraph Quality["Quality Tracking"]
        G1["ToolQualityManager<br/>성공률 / 지연시간 추적"]
        G2["QualityStore<br/>도구 품질 DB"]
        G3["SearchCoordinator<br/>BM25 + embedding + LLM + 품질"]
    end

    subgraph Cloud["Cloud Skill Community (선택)"]
        H1["OpenSpaceClient<br/>upload / download / search"]
        H2["SkillSearchEngine<br/>BM25 + vector 하이브리드"]
        H3["open-space.cloud API"]
    end

    subgraph Frontend["Dashboard (선택)"]
        I1["React 18 + Vite 6 + Tailwind"]
        I2["스킬 계보 그래프 / Diff 뷰어"]
        I3["워크플로우 타임라인"]
    end

    A1 -->|MCP 프로토콜| B1
    A1 -->|host_skills 등록| B2
    B1 --> C0
    C0 --> C1
    C1 -->|실패 시| C2
    C1 & C2 --> C3
    C1 & C2 --> D1
    D1 --> D2
    D1 --> D3
    D1 --> D4
    D3 --> E1
    D3 --> E2
    D3 --> E3
    D3 --> E4
    D3 --> E5
    C0 --> F1
    F1 --> F2
    C3 --> F3
    F3 --> F4
    F4 --> F5
    D3 --> G1
    G1 --> G2
    D3 --> G3
    G1 -->|품질 점수| G3
    G1 -->|문제 도구| F4
    F5 --> H1
    H1 --> H2
    H2 --> H3
    F5 --> I2
    D4 --> I3
```

## 2. 2단계 실행 파이프라인

```mermaid
sequenceDiagram
    participant U as User / Host Agent
    participant O as OpenSpace (tool_layer)
    participant R as SkillRegistry
    participant A as GroundingAgent
    participant T as Tools (Backend)
    participant AN as Analyzer
    participant EV as Evolver
    participant DB as SkillStore
    U ->> O: execute(task, workspace)

    rect rgb(230, 245, 255)
        Note over O, A: Phase 1: Skill-Guided Execution
        O ->> R: select_skills_with_llm(task)
        R ->> R: 품질 필터링 → BM25+embedding 사전필터 → LLM plan-then-select
        R -->> O: 선택된 스킬 + 컨텍스트
        O ->> A: set_skill_context() + process()

        loop max_iterations
            A ->> A: 스킬 컨텍스트 (1회차만) + 메시지 캡핑
            A ->> T: tool 호출 (shell/gui/mcp/web)
            T -->> A: 결과 (30,000자 캡핑)
            A ->> A: <COMPLETE> 확인 / 가이던스 주입
        end

        alt 성공
            A -->> O: 결과 반환
        else 실패
            O ->> O: 워크스페이스 정리 (실패 아티팩트 삭제)
        end
    end

    rect rgb(255, 245, 230)
        Note over O, A: Phase 2: Tool-Fallback (Phase 1 실패 시)
        O ->> A: clear_skill_context() + process()
        loop max_iterations (풀 예산)
            A ->> T: tool 호출 (스킬 없이)
            T -->> A: 결과
        end
        A -->> O: 결과 반환
    end

    rect rgb(245, 255, 230)
        Note over O, EV: Post-Execution Pipeline
        O ->> AN: analyze_execution(recording)
        AN ->> AN: 대화로그 포맷팅 (우선순위 절삭)
        AN ->> AN: LLM 에이전트 분석 (최대 5반복)
        AN -->> DB: record_analysis() (카운터 원자적 업데이트)
        AN -->> EV: evolution_suggestions

        alt 진화 제안 존재
            EV ->> EV: _run_evolution_loop (최대 5반복, 도구 사용)
            EV ->> EV: apply-retry 사이클 (최대 3회)
            EV ->> DB: evolve_skill() (이전 비활성화 + 새 버전)
            EV ->> R: update_skill() (즉시 사용 가능)
        end
    end

    O -->> U: 최종 결과 + evolved_skills 정보
```

## 3. 3중 진화 트리거 시스템

```mermaid
flowchart LR
    subgraph Trigger1["Trigger 1: Post-Execution Analysis"]
        A1["작업 실행 완료"] --> A2["ExecutionAnalyzer"]
        A2 --> A3["LLM 에이전트 분석<br/>(대화로그 + traj.jsonl)"]
        A3 --> A4["EvolutionSuggestion 생성"]
    end

    subgraph Trigger2["Trigger 2: Tool Degradation"]
        B1["도구 성공률 하락"] --> B2["ToolQualityManager"]
        B2 --> B3["find_skills_by_tool()"]
        B3 --> B4["LLM 확인<br/>'이 스킬이 수정 필요한가?'"]
    end

    subgraph Trigger3["Trigger 3: Metric Monitor"]
        C1["주기적 스킬 건강 검사"] --> C2["_diagnose_skill_health()"]
        C2 --> C3{"진단 결과"}
        C3 -->|" fallback_rate > 0.4 "| C4["FIX 후보"]
        C3 -->|" applied + completion < 0.35 "| C5["FIX 후보"]
        C3 -->|" effective_rate < 0.55 "| C6["DERIVED 후보"]
        C4 & C5 & C6 --> C7["LLM 확인"]
    end

    A4 & B4 & C7 --> D["SkillEvolver"]
    D --> E{"진화 모드"}
    E -->|기존 스킬 수정| F["FIX<br/>in-place 업데이트<br/>새 skill_id, 같은 경로"]
    E -->|파생 스킬 생성| G["DERIVED<br/>새 디렉토리<br/>부모 is_active 유지"]
    E -->|새 패턴 포착| H["CAPTURED<br/>완전히 새로운 스킬<br/>부모 없음"]
    F & G & H --> I["에이전트 루프 (최대 5반복)"]
    I --> J["apply-retry (최대 3회)"]
    J --> K["validate_skill_dir()"]
    K --> L["SkillStore.evolve_skill()"]
    L --> M["SkillRegistry 즉시 업데이트"]

    subgraph Safety["안전장치"]
        S1["Semaphore (max_concurrent=3)"]
        S2["<EVOLUTION_FAILED> 자기 거부"]
        S3["min_selections (5) 데이터 부족 보호"]
        S4["addressed_degradations 반복 방지"]
        S5["모호한 LLM 응답 → 기본 스킵"]
    end
```

## 4. Provider-Session-Connector 아키텍처

```mermaid
flowchart TD
    subgraph Core["코어 추상 계층"]
        P["Provider (ABC)"]
        S["BaseSession (ABC)"]
        C["BaseConnector (ABC)"]
        CM["BaseConnectionManager (ABC)"]
    end

    subgraph Shell["Shell Backend"]
        SP["ShellProvider"]
        SS["ShellSession"]
        SC1["LocalShellConnector<br/>(subprocess 직접)"]
        SC2["ShellConnector<br/>(HTTP API)"]
        ST["도구: shell_agent, read_file,<br/>write_file, list_dir, run_shell"]
    end

    subgraph GUI["GUI Backend"]
        GP["GUIProvider"]
        GS["GUISession"]
        GC1["LocalGUIConnector<br/>(PyAutoGUI 직접)"]
        GC2["GUIConnector<br/>(HTTP API)"]
        GA["AnthropicGUIClient<br/>claude-sonnet-4-5<br/>computer-use-2025-01-24"]
    end

    subgraph MCP_B["MCP Backend"]
        MP["MCPProvider"]
        MS["MCPSession"]
        MC1["StdioConnector"]
        MC2["HttpConnector<br/>StreamableHTTP → SSE → JSON-RPC"]
        MC3["WebSocketConnector"]
        MC4["SandboxConnector<br/>(E2B + supergateway)"]
        MT["도구 캐시 2계층<br/>원본 + 정제(Claude 호환)"]
    end

    subgraph Web["Web Backend"]
        WP["WebProvider"]
        WS["WebSession"]
        WC["WebConnector (OpenRouter)"]
        WT["도구: deep_research_agent"]
    end

    P --> SP & GP & MP & WP
    SP --> SS --> SC1 & SC2
    GP --> GS --> GC1 & GC2
    GC1 & GC2 --> GA
    MP --> MS --> MC1 & MC2 & MC3 & MC4
    WP --> WS --> WC
    SS --> ST
    WS --> WT
    MS --> MT
    C --> SC1 & SC2 & GC1 & GC2 & MC1 & MC2 & MC3 & MC4 & WC
```

## 5. 하이브리드 도구/스킬 검색 파이프라인

```mermaid
flowchart TD
    Q["작업 쿼리"] --> SC["SearchCoordinator"]

    subgraph ToolSearch["도구 검색"]
        TS1["전체 Provider에서 도구 수집"]
        TS2["ToolRanker<br/>TF-IDF + 임베딩 하이브리드"]
        TS3{"도구 50개 초과?"}
        TS4["LLM 필터링<br/>(백엔드/서버 수준 선별)"]
        TS5["품질 점수 반영<br/>score × penalty"]
    end

    subgraph SkillSearch["스킬 검색"]
        SS1["품질 필터링<br/>selections≥2 & completions=0 → 제거<br/>applied≥2 & fallbacks>50% → 제거"]
        SS2{"스킬 10개 초과?"}
        SS3["BM25 + embedding 사전필터<br/>상위 max(15, max_skills×5)"]
        SS4["LLM plan-then-select<br/>카탈로그 + 품질 통계 제공"]
        SS5["최종 선택 (최대 max_skills)"]
    end

    SC --> TS1
    TS1 --> TS2
    TS2 --> TS3
    TS3 -->|Yes| TS4
    TS3 -->|No| TS5
    TS4 --> TS5
    SC --> SS1
    SS1 --> SS2
    SS2 -->|Yes| SS3
    SS2 -->|No| SS4
    SS3 --> SS4
    SS4 --> SS5
```

## 6. GDPVal 벤치마크 평가 흐름

```mermaid
flowchart TD
    subgraph Setup["벤치마크 준비"]
        S1["tasks_50.json<br/>44 직업군 × 9 산업<br/>결정론적 50 서브셋"]
        S2["참조 파일 프리페치<br/>(ref_cache/)"]
        S3["TokenTracker 설치<br/>(litellm CustomLogger)"]
    end

    subgraph Phase1["Phase 1: Cold Start"]
        P1A["스킬 DB 초기화"]
        P1B["50개 태스크 순차 실행"]
        P1C["태스크별: 토큰 추적 → 실행 → 평가"]
        P1D["스킬 누적/진화"]
        P1E["스킬 스냅샷 + DB 백업"]
    end

    subgraph Phase2["Phase 2: Warm Rerun"]
        P2A["Phase 1 전체 스킬 라이브러리 로드"]
        P2B["동일 50개 태스크 재실행"]
        P2C["동일 평가 파이프라인"]
    end

    subgraph Eval["평가 지표"]
        E1["Quality (0~1)<br/>LLMEvaluator (GPT-4o)<br/>태스크당 평균 48.8개 루브릭"]
        E2["Income<br/>0.6 Payment Cliff<br/>score < 0.6 → 수입 없음"]
        E3["Token Efficiency<br/>6차원 분석<br/>(전체/에이전트 × prompt/completion/total)"]
        E4["Value Capture<br/>Income / Task Value × 100"]
    end

    subgraph Compare["비교 분석"]
        C1["comparison.jsonl<br/>태스크별 Phase 1 vs Phase 2"]
        C2["summary.json<br/>토큰 절감, 비용 절감, 품질 비교"]
        C3["리더보드 비교<br/>ClawWork 7개 에이전트 대비"]
    end

    S1 --> S2 --> S3
    S3 --> P1A --> P1B --> P1C --> P1D --> P1E
    P1E --> P2A --> P2B --> P2C
    P1C & P2C --> E1 & E2 & E3 & E4
    E1 & E2 & E3 & E4 --> C1 --> C2 --> C3
```

## 7. 스킬 데이터 모델 및 리니지 DAG

```mermaid
flowchart TD
    subgraph SkillRecord["SkillRecord"]
        SR["skill_id: string<br/>name: string<br/>description: string<br/>path: string (SKILL.md)<br/>is_active: bool<br/>category: TOOL_GUIDE | WORKFLOW | REFERENCE<br/>visibility: PRIVATE | PUBLIC"]
        SM["total_selections: int<br/>total_applied: int<br/>total_completions: int<br/>total_fallbacks: int"]
    end

    subgraph Lineage["SkillLineage (Version DAG)"]
        L1["IMPORTED / CAPTURED<br/>→ 루트 노드 (generation=0)<br/>→ parent_skill_ids = []"]
        L2["FIXED<br/>→ 부모 1개 (동일 스킬)<br/>→ 같은 name/path, 새 skill_id<br/>→ 이전 is_active=False"]
        L3["DERIVED<br/>→ 부모 1+개<br/>→ 새 name/디렉토리<br/>→ 부모 is_active 유지"]
    end

    subgraph IDScheme["Skill ID 체계"]
        ID1["{name}__imp_{uuid8}<br/>(초기 임포트)"]
        ID2["{name}__v{gen}_{uuid8}<br/>(진화된 스킬)"]
    end

    subgraph Storage["영속화"]
        DB1["SQLite WAL (.openspace/openspace.db)"]
        DB2["skill_records 테이블"]
        DB3["skill_lineage_parents (다대다)"]
        DB4["execution_analyses"]
        DB5["skill_judgments"]
        DB6[".skill_id 사이드카 파일"]
    end

    SR --> L1 & L2 & L3
    L1 --> ID1
    L2 & L3 --> ID2
    SR --> DB2
    L1 & L2 & L3 --> DB3
    DB2 & DB3 & DB4 & DB5 --> DB1
    ID1 & ID2 --> DB6
```

## 8. 보안 계층 구조

```mermaid
flowchart TD
    subgraph Layer1["Layer 1: 명령어 검사"]
        A1["SecurityPolicyManager"]
        A2["shlex.split() 토큰화"]
        A3["OS별 차단 목록<br/>common + linux/darwin/windows"]
        A4["대화형 CLI 프롬프트<br/>(MCP에서는 기본 거부)"]
    end

    subgraph Layer2["Layer 2: 도구 스키마 검증"]
        B1["ToolSchema<br/>jsonschema.validate"]
        B2["파라미터 유효성 검사"]
    end

    subgraph Layer3["Layer 3: 샌드박스 격리"]
        C1["E2BSandbox<br/>(선택적, 기본 비활성)"]
        C2["SandboxConnector<br/>(supergateway → SSE)"]
    end

    subgraph Layer4["Layer 4: 스킬 안전성"]
        D1["check_skill_safety()"]
        D2["차단: ClawdAuthenticatorTool"]
        D3["경고: malware, phish, keylogger<br/>api_key, token, password<br/>wallet, seed_phrase"]
    end

    subgraph Layer5["Layer 5: 클라우드 보안"]
        E1["zip 경로 순회 공격 방지<br/>is_relative_to() 검증"]
        E2["API 키 마스킹 (8자만 표시)"]
    end

    Layer1 --> Layer2 --> Layer3
    Layer4 -.->|스킬 등록 시| Layer1
    Layer5 -.->|클라우드 다운로드 시| Layer4
```
