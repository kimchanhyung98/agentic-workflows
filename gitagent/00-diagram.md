# GitAgent 아키텍처 다이어그램

## 1. 7-Layer 표준 디렉토리 구조

```mermaid
flowchart TD
    ROOT["Agent Repository"] --> L1
    ROOT --> L2
    ROOT --> L3
    ROOT --> L4
    ROOT --> L5
    ROOT --> L6
    ROOT --> L7

    subgraph L1["Layer 1: Identity (Required)"]
        A["agent.yaml\nManifest + Schema"]
        S["SOUL.md\nPersonality + Style"]
    end

    subgraph L2["Layer 2: Behavior & Rules"]
        R["RULES.md\nmust-always / must-never"]
        D["DUTIES.md\nSegregation of Duties"]
        AG["AGENTS.md\nFramework-agnostic fallback"]
        PR["PROMPT.md\nCustom system prompt"]
    end

    subgraph L3["Layer 3: Capabilities"]
        SK["skills/\nAgent Skills standard"]
        TL["tools/\nMCP-compatible YAML"]
        WF["workflows/\nDeterministic steps"]
        SUB["agents/\nSub-agent definitions"]
    end

    subgraph L4["Layer 4: Knowledge & Memory"]
        K["knowledge/\nindex.yaml + docs"]
        M["memory/\nmemory.yaml + layers"]
    end

    subgraph L5["Layer 5: Lifecycle & Ops"]
        H["hooks/\nhooks.yaml + scripts"]
        C["config/\ndefault.yaml + env overrides"]
        EX["examples/\ngood/bad outputs"]
    end

    subgraph L6["Layer 6: Compliance"]
        CP["compliance/\nrisk-assessment.md\nregulatory-map.yaml\nvalidation-schedule.yaml"]
    end

    subgraph L7["Layer 7: Runtime"]
        RT[".gitagent/\ndeps, cache, state.json\n(gitignored)"]
    end
```

## 2. CLI 명령 체계

```mermaid
flowchart TD
    USER["User / CI"] --> CLI["gitagent CLI\n(commander.js)"]

    subgraph COMMANDS["Commands (11)"]
        INIT["init\n--template minimal|standard|full"]
        VAL["validate\n--compliance"]
        INFO["info"]
        EXP["export\n--format <format>"]
        IMP["import\n--from <format>"]
        RUN["run\n--adapter <target>"]
        INS["install"]
        AUD["audit"]
        SKILL["skills\nsearch|install|list|info"]
        LYZR["lyzr"]
        REG["registry"]
    end

    CLI --> COMMANDS

    INIT --> REPO["Agent Repo scaffold"]
    VAL --> CHECK["Schema + Reference + SOD validation"]
    INFO --> DISPLAY["Agent summary display"]
    EXP --> ADAPT["Adapter format output"]
    IMP --> CONVERT["External → GitAgent conversion"]
    RUN --> RUNTIME["Adapter-based execution"]
    INS --> DEP["Git-based dependency install"]
    AUD --> REPORT["Compliance audit report"]
    SKILL --> SKREG["Skill registry operations"]
    LYZR --> LYZR_OP["Lyzr Studio 연동"]
    REG --> REG_OP["레지스트리 관리"]
```

## 3. validate 검증 파이프라인

```mermaid
sequenceDiagram
    participant U as User/CI
    participant V as validate
    participant Y as loader.ts
    participant A as AJV (schemas.ts)
    participant F as File System
    participant S as skill-loader.ts
    participant C as Compliance Rules

    U->>V: gitagent validate [--compliance]

    rect rgb(240, 248, 255)
        Note over V,A: Phase 1: agent.yaml 스키마 검증
        V->>Y: loadAgentManifest()
        Y-->>V: AgentManifest
        V->>A: validateSchema(manifest, 'agent-yaml')
        A-->>V: schema errors/warnings
    end

    rect rgb(245, 255, 245)
        Note over V,F: Phase 2: SOUL.md 검증
        V->>F: SOUL.md 존재 여부
        V->>F: 내용 비어있지 않은지
        V->>F: 제목만 있지 않은지
    end

    rect rgb(255, 248, 240)
        Note over V,F: Phase 3: 참조 무결성
        V->>F: skills/ 디렉토리 존재 확인
        V->>F: tools/*.yaml 파일 존재 확인
        V->>F: agents/ 디렉토리 or .md 존재 확인
    end

    rect rgb(255, 245, 245)
        Note over V,S: Phase 4: Skills 검증
        V->>S: parseSkillMd() per skill
        S-->>V: frontmatter + instructions
        V->>A: validateSchema(frontmatter, 'skill')
        Note over V: name 규칙: kebab-case, <=64자, -- 불가
        Note over V: description <=1024자
        Note over V: instructions ~5000 토큰 권장
    end

    rect rgb(248, 240, 255)
        Note over V,A: Phase 5: hooks/tools YAML 스키마
        V->>A: validateSchema(hooks, 'hooks')
        V->>F: hook script 파일 존재 확인
        V->>A: validateSchema(tool, 'tool')
    end

    opt --compliance flag
        rect rgb(255, 255, 240)
            Note over V,C: Phase 6: 컴플라이언스 검증
            V->>C: risk_tier 기반 최소 요구사항
            V->>C: FINRA 2210/3110/4511 규칙
            V->>C: Federal Reserve SR 11-7
            V->>C: SEC 17a-4, CFPB 바이어스 테스트
            V->>C: SOD role/conflict/assignment/handoff 검증
            C-->>V: compliance findings
        end
    end

    V-->>U: pass/fail + errors + warnings
```

## 4. Export 어댑터 변환 흐름

```mermaid
flowchart TD
    SRC["GitAgent Repository"] --> LOAD["Loader\nloadAgentManifest()\nloadFileIfExists()\nloadAllSkills()"]

    LOAD --> BUILD["System Prompt Builder"]

    BUILD --> |"SOUL.md\nRULES.md\nDUTIES.md\nSkills\nKnowledge\nCompliance"| ADAPTER{"Target Adapter"}

    ADAPTER --> |"system-prompt"| SP["Plain Text\n(any LLM)"]
    ADAPTER --> |"claude-code"| CC["CLAUDE.md\n+ skills metadata"]
    ADAPTER --> |"openai"| OA["Python SDK code\nAgent + tools"]
    ADAPTER --> |"crewai"| CA["YAML config\nagents + tasks"]
    ADAPTER --> |"gemini"| GM["GEMINI.md\n+ settings.json"]
    ADAPTER --> |"cursor"| CR[".cursor/rules/*.mdc"]
    ADAPTER --> |"github"| GH["Actions workflow YAML"]
    ADAPTER --> |"copilot"| CP["Copilot instructions"]
    ADAPTER --> |"opencode"| OC["OpenCode config"]
    ADAPTER --> |"lyzr"| LY["Lyzr Studio JSON"]
    ADAPTER --> |"openclaw"| OW["OpenClaw format"]
    ADAPTER --> |"nanobot"| NB["Nanobot manifest"]
    ADAPTER --> |"codex"| CX["Codex format"]

    SP --> FIDELITY["Fidelity"]
    CC --> FIDELITY
    OA --> FIDELITY
    FIDELITY --> |"Complete"| HIGH["system-prompt\nclaude-code"]
    FIDELITY --> |"Medium"| MED["openai, crewai\ngemini, cursor"]
    FIDELITY --> |"Low (lossy)"| LOW["lyzr, github\ncopilot, nanobot"]
```

## 5. Run 실행 흐름 (Claude Code 어댑터)

```mermaid
sequenceDiagram
    participant U as User
    participant R as run command
    participant G as git-cache.ts
    participant L as loader.ts
    participant S as skill-loader.ts
    participant A as adapters/system-prompt.ts
    participant C as runners/claude.ts
    participant CC as Claude Code CLI

    U->>R: gitagent run --repo <url> --adapter claude
    R->>G: resolveRepo(url, branch)
    G-->>R: agentDir

    R->>L: loadAgentManifest(agentDir)
    L-->>R: AgentManifest

    R->>C: runWithClaude(agentDir, manifest)

    rect rgb(240, 248, 255)
        Note over C: System Prompt 빌드
        C->>A: exportToSystemPrompt(agentDir)
        A->>L: loadFileIfExists(SOUL.md, RULES.md, DUTIES.md)
        A->>S: loadAllSkills(skillsDir)
        A->>L: knowledge/index.yaml → always_load docs
        A-->>C: systemPrompt (concatenated)
    end

    rect rgb(245, 255, 245)
        Note over C: CLI 인수 구성
        C->>C: --model (manifest.model.preferred)
        C->>C: --fallback-model (manifest.model.fallback[0])
        C->>C: --max-turns (manifest.runtime.max_turns)
        C->>C: --permission-mode plan (if human_in_the_loop=always)
        C->>C: --allowedTools (skills + tools/*.yaml)
        C->>C: --agents (sub-agent config from agents/)
        C->>C: --add-dir (knowledge/, skills/)
        C->>C: --settings (hooks → Claude Code hook mapping)
        C->>C: --append-system-prompt (full prompt)
    end

    rect rgb(255, 248, 240)
        Note over C,CC: 실행
        C->>CC: spawnSync(claude, args)
        CC-->>U: Interactive session
    end
```

## 6. 컴플라이언스 SOD 검증 모델

```mermaid
flowchart TD
    CFG["agent.yaml\ncompliance section"] --> RISK{"risk_tier\nlow|standard|high|critical"}
    CFG --> FW{"frameworks[]"}
    CFG --> SOD{"segregation_of_duties"}

    RISK --> |"high/critical"| HR["Required:\n- human_in_the_loop != none\n- audit_logging = true\n- validation_cadence >= quarterly\n- compliance/ directory\n- risk-assessment.md"]

    FW --> |"finra"| F1["FINRA Rules:\n- 2210: fair_balanced, no_misleading\n- 3110: supervision config\n- 4511: recordkeeping config"]
    FW --> |"federal_reserve"| F2["SR 11-7:\n- model_risk section required\n- ongoing_monitoring = true"]
    FW --> |"sec"| F3["SEC:\n- 17a-4: audit_logging\n- Reg S-P: PII handling"]
    FW --> |"cfpb"| F4["CFPB:\n- bias_testing recommended"]

    SOD --> ROLE["roles[] >= 2\nUnique IDs"]
    SOD --> CONFLICT["conflicts[][]\nReferences valid roles\nNo self-conflict"]
    SOD --> ASSIGN["assignments{}\nNo conflicting roles per agent\nAgent exists in manifest"]
    SOD --> HANDOFF["handoffs[]\nValid role references\n>= 2 distinct roles"]
    SOD --> ENFORCE["enforcement\nstrict: errors block\nadvisory: warnings only"]

    HR --> RESULT["Validation Result"]
    F1 --> RESULT
    F2 --> RESULT
    F3 --> RESULT
    F4 --> RESULT
    ROLE --> RESULT
    CONFLICT --> RESULT
    ASSIGN --> RESULT
    HANDOFF --> RESULT
    ENFORCE --> RESULT
```

## 7. Hook 라이프사이클 이벤트 맵핑

```mermaid
flowchart LR
    subgraph GITAGENT["GitAgent Hook Events"]
        E1["on_session_start"]
        E2["pre_tool_use"]
        E3["post_tool_use"]
        E4["pre_response"]
        E5["post_response"]
        E6["on_error"]
        E7["on_session_end"]
    end

    subgraph CLAUDE["Claude Code Events"]
        C1["SessionStart"]
        C2["PreToolUse"]
        C3["PostToolUse"]
        C4["UserPromptSubmit"]
        C5["Stop"]
        C6["PostToolUseFailure"]
        C7["SessionEnd"]
    end

    E1 --> C1
    E2 --> C2
    E3 --> C3
    E4 --> C4
    E5 --> C5
    E6 --> C6
    E7 --> C7

    subgraph PROTOCOL["Hook I/O Protocol (JSON)"]
        IN["stdin: event, timestamp,\ndata, session"]
        OUT["stdout: action\n(allow|block|modify),\nmodifications, audit"]
    end
```

## 8. Skill Progressive Disclosure

```mermaid
flowchart TD
    SKILL["skills/<name>/SKILL.md"] --> TIER{"Loading Tier"}

    TIER --> |"Tier 1: Metadata (~100 tokens)"| T1["loadSkillMetadata()\nname + description only\nFor listing/routing"]
    TIER --> |"Tier 2: Full (<5000 tokens)"| T2["loadSkillFull()\nfrontmatter + instructions\nFor active use"]
    TIER --> |"Tier 3: With Resources"| T3["scripts/\nreferences/\nassets/\nexamples/\nagents/"]

    subgraph DISCOVERY["Discovery Priority"]
        D1["1. <agentDir>/skills/"]
        D2["2. <agentDir>/.agents/skills/"]
        D3["3. <agentDir>/.claude/skills/"]
        D4["4. <agentDir>/.github/skills/"]
        D5["5. ~/.agents/skills/"]
    end
```

## 9. 전체 실행 라이프사이클

```mermaid
flowchart TD
    DEF["Definition Phase\nagent.yaml + SOUL.md + ..."] --> VAL["Validation Phase\ngitagent validate --compliance"]
    VAL --> |"pass"| VCS["Version Control\ngit commit + tag + branch"]
    VAL --> |"fail"| FIX["Fix errors"]
    FIX --> DEF

    VCS --> ENV["Environment Promotion\ndev → staging → main"]
    ENV --> RUN["Execution Phase\ngitagent run --adapter <target>"]

    RUN --> RESOLVE["Resolve: git clone/cache"]
    RESOLVE --> LOAD["Load: manifest + docs + skills"]
    LOAD --> ADAPT["Adapt: framework-specific setup"]
    ADAPT --> SPAWN["Spawn: target CLI/SDK"]

    SPAWN --> HOOK1["Hook: on_session_start\nLoad compliance context\nLoad MEMORY.md"]
    HOOK1 --> PROCESS["Request Processing"]

    PROCESS --> HOOK2["Hook: pre_tool_use\nAudit tool call"]
    HOOK2 --> TOOL["Tool Execution"]
    TOOL --> HOOK3["Hook: post_tool_use\nValidate output"]
    HOOK3 --> RESPONSE["Response Generation"]

    RESPONSE --> HOOK4["Hook: pre_response\nCompliance check"]
    HOOK4 --> OUTPUT["Send Response"]
    OUTPUT --> HOOK5["Hook: post_response\nAudit log"]

    OUTPUT --> |"session end"| HOOK6["Hook: on_session_end\nUpdate memory\nFinalize audit"]

    PROCESS --> |"error"| HOOK7["Hook: on_error\nEscalate to supervisor"]
    HOOK7 --> PROCESS

    HOOK6 --> AUDIT["Post-Execution\ngitagent audit\nCompliance report"]
```
