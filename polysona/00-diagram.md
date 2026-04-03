# Polysona 아키텍처 다이어그램

## 1. 전체 계층 구조

```mermaid
flowchart TD
    subgraph Host["CLI Host Layer"]
        H1["Codex<br/>AGENTS.md + agents/openai.yaml"]
        H2["Claude Code<br/>.claude-plugin + hooks"]
    end

    subgraph Skills["Skill Layer (skills/*/SKILL.md)"]
        S1["interview / introduce / trend"]
        S2["content / qa / publish / status / export"]
    end

    subgraph Agents["Agent Layer (agents/*.md)"]
        A1["profiler"]
        A2["trendsetter"]
        A3["content-writer"]
        A4["virtual-follower<br/>(context: fork)"]
        A5["admin"]
    end

    subgraph Data["Data Layer (Markdown/PLOON)"]
        D1["personas/{id}/persona.md"]
        D2["personas/{id}/nuance.md"]
        D3["personas/{id}/accounts.md"]
        D4["content/trends, drafts, qa, published"]
        D5["personas/_active.md"]
    end

    subgraph Dashboard["Dashboard Layer"]
        DB1["Hono API<br/>server/routes/api.ts"]
        DB2["React + Vite UI<br/>client/src/pages/*"]
        DB3["PLOON Parser<br/>server/lib/ploon.ts"]
    end

    H1 --> Skills
    H2 --> Skills
    Skills --> Agents
    Agents --> Data
    Data --> DB3
    DB3 --> DB1
    DB1 --> DB2
```

## 2. SETUP → LOOP 파이프라인

```mermaid
flowchart TD
    START["사용자 세션 시작"]

    subgraph SETUP["SETUP (1회 또는 주기적 갱신)"]
        I["① profiler / interview<br/>10-framework 심리 추출"]
        I --> PD["persona.md<br/>core/decide/energy/blind/interview-log"]
        I --> ND["nuance.md<br/>voice/platform/phrasing"]
        I --> AD["accounts.md<br/>rolemodel/virtual"]
    end

    subgraph LOOP["LOOP (콘텐츠 사이클마다 반복)"]
        T["② trendsetter / trend<br/>실시간 스캔 + 페르소나 필터링"]
        T --> TF["content/trends/*.md<br/>5개 순위 토픽"]
        TF --> C["③ content-writer / content<br/>persona + nuance + accounts + trend 결합"]
        C --> DF["content/drafts/*.md<br/>플랫폼별 3개 초안"]
        DF --> Q["④ virtual-follower / qa<br/>(context: fork 격리)<br/>5 팔로워 × 5 차원 + 롤모델 GAP"]
        Q --> QF["content/qa/*.md<br/>TOP 5 추천"]
        QF --> SEL["사용자 최종 선택"]
        SEL --> A["⑤ admin / publish<br/>게시 + 성과 추적 메타데이터"]
        A --> PF["content/published/*.md"]
    end

    START --> SETUP
    SETUP --> LOOP
    PF --> FB["피드백 루프<br/>실제 성과 → nuance.md 업데이트"]
    FB -.-> ND
    FB -.-> LOOP
```

## 3. 10-Framework → 데이터 목적지 매핑

```mermaid
flowchart LR
    subgraph WD["서양 심층 (6개)"]
        F1["McAdams Life Story"]
        F2["Laddering + MI + ACT"]
        F3["Clean Language"]
        F4["Johari Window"]
        F5["IFS"]
        F6["Repertory Grid"]
    end

    subgraph WS["서양 보완 (2개)"]
        F7["Object Relations"]
        F8["Projective Technique"]
    end

    subgraph EA["동양 (2개)"]
        F9["Zen Koan"]
        F10["五倫+陰陽"]
    end

    F1 --> CORE["persona.md core"]
    F2 --> DEC["persona.md decide"]
    F3 --> VOICE["nuance.md voice"]
    F4 --> BLIND["persona.md blind"]
    F5 --> BLIND
    F6 --> DEC
    F7 --> CORE
    F8 --> BLIND
    F9 --> CORE
    F10 --> CORE
```

## 4. 5 에고 레이어 & GAP 모델

```mermaid
flowchart TD
    L1["Layer 1: others-see-me<br/>타인의 시선 (Johari, 五倫)<br/>→ persona.md blind"]
    GAP1{"GAP?"}
    L2["Layer 2: want-to-be-seen<br/>보여지고 싶은 모습 (Goffman)<br/>→ nuance.md voice"]
    GAP2{"GAP?"}
    L3["Layer 3: conscious-ideal<br/>의식적 이상 (직접 입력)<br/>→ accounts.md ideal"]
    GAP3{"GAP?"}
    L4["Layer 4: rolemodel<br/>벤치마크 인물 (구체적 표준)<br/>→ accounts.md rolemodel"]
    GAP4{"GAP?"}
    L5["Layer 5: unconscious-self<br/>무의식적 자아 (McAdams/IFS/Koan)<br/>→ persona.md core"]

    L1 --- GAP1
    GAP1 --- L2
    L2 --- GAP2
    GAP2 --- L3
    L3 --- GAP3
    GAP3 --- L4
    L4 --- GAP4
    GAP4 --- L5
```

## 5. Write-then-Read 검증 & context:fork 격리

```mermaid
sequenceDiagram
    participant User
    participant Skill as SKILL.md
    participant Agent as agents/*.md
    participant FS as content/* or personas/*

    User->>Skill: /trend, /content, /qa, /publish
    Skill->>Skill: !` bash 프리로드<br/>personas/_active.md → 컨텍스트 주입

    alt QA 스킬 (context: fork)
        Skill->>Agent: 격리된 컨텍스트에서 실행
        Note right of Agent: 생성 편향 차단
    else 기타 스킬
        Skill->>Agent: 공유 컨텍스트에서 실행
    end

    Agent->>FS: Write 결과 파일 저장
    Agent->>FS: Read 저장 파일 재검증
    alt 저장 성공
        Agent-->>User: 결과 + confirmed saved path
    else 저장 실패
        Agent-->>User: 실패 보고 (성공 주장 금지)
    end
```

## 6. Codex/Claude 이중 하네스

```mermaid
flowchart LR
    subgraph Codex["Codex Harness"]
        C1["AGENTS.md<br/>시스템 철학 + 금지 규칙"]
        C2["agents/openai.yaml<br/>에이전트→스킬 바인딩"]
        C3[".agents/skills/<br/>(sync 미러링 결과)"]
        C4["scripts/sync-codex-skills.mjs"]
        C4 --> C3
    end

    subgraph Claude["Claude Code Harness"]
        L0[".claude-plugin/plugin.json<br/>8 skills + 5 agents 등록"]
        L1[".claude-plugin/marketplace.json"]
        L2["hooks/hooks.json"]
        L3["SessionStart<br/>활성 페르소나 프리로드"]
        L4["PreToolUse<br/>PLOON 덮어쓰기 방어"]
        L5["PostToolUse<br/>AI 슬롭 패턴 탐지"]
        L2 --> L3
        L2 --> L4
        L2 --> L5
    end
```

## 7. Export 이식성 흐름

```mermaid
flowchart TD
    P["personas/{active}/<br/>persona.md + nuance.md + accounts.md"]
    EX["/export 스킬 실행"]
    P --> EX

    EX --> CL["CLAUDE.generated.md<br/>Work philosophy + Decision priorities<br/>+ Tone rules + Anti-patterns"]
    EX --> AG["AGENTS.generated.md<br/>에이전트 정의 + 역할 분할<br/>+ 호출 방법"]

    CL --> ENV1["Claude Code 워크스페이스"]
    AG --> ENV2["Codex / OpenCode 워크스페이스"]
```

## 8. 대시보드 데이터 플로우

```mermaid
flowchart TD
    FILES["personas/* + content/*<br/>(PLOON Markdown)"]
    PLOON["parsePloon()<br/>섹션 → 테이블/entries/key-val"]
    FILES --> PLOON

    PLOON --> API["Hono API (/api/*)"]
    API --> P1["/api/personas<br/>/api/personas/:id"]
    API --> P2["/api/personas/:id/interview-log"]
    API --> P3["/api/personas/:id/qa-simulation<br/>20 archetypes × 5 dimensions<br/>(DJB2 결정론적 점수)"]
    API --> P4["/api/content/drafts<br/>/api/content/published"]
    API --> P5["/api/agents/status<br/>/api/status"]

    subgraph Pages["React Pages"]
        U1["PersonaDetail<br/>SelfLayerDiagram + GapAnalysis<br/>+ VoiceMixBar + FrameworkCoverage<br/>+ InterviewTimeline + PloonViewer"]
        U2["ContentPipeline<br/>ContentQualityMeter"]
        U3["VirtualFollower<br/>VirtualFollowerGrid"]
        U4["AgentMonitor<br/>AgentStatusCard"]
    end

    P1 --> U1
    P2 --> U1
    P3 --> U3
    P4 --> U2
    P5 --> U4
```
