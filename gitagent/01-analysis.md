# GitAgent 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `open-gitagent/gitagent`
- 버전: v0.1.7 (spec v0.1.0)
- 성격: git-native 에이전트 표준 + CLI 구현체
- 핵심 목표: **에이전트 정체성/규칙/도구를 코드 리포지토리처럼 선언, 버전관리, 이식**

GitAgent는 런타임 프레임워크 자체를 통일하려는 접근이 아니라, **에이전트 정의 레이어를 표준화**해 Claude Code/OpenAI/CrewAI 등으로의 이동 비용을 줄이는 방향을 취합니다. "하나의 정의, 다수의 런타임" 전략입니다.

---

## 2. 핵심 설계 원칙

### 2.1 Git-native 표준화

`agent.yaml` + `SOUL.md`를 최소 단위로 두고, 나머지 구조를 선택적으로 확장합니다.

- 장점: 최소 진입장벽(2개 파일) + 점진적 확장
- 효과: 버전 히스토리, 브랜치 기반 실험, PR 리뷰, 롤백을 에이전트 운영에 직접 적용
- 패턴: 13가지 아키텍처 패턴이 git-native 설계에서 자연스럽게 파생됨

### 2.2 Framework-agnostic + Adapter

동일 원본 정의를 여러 포맷으로 변환하는 `export/import` 구조를 채택합니다.

- 설계 의도: 실행 엔진(lock-in)보다 정의 자산의 재사용성 극대화
- 결과: 조직별 도구 스택이 달라도 동일 에이전트 자산 공유 가능
- 각 어댑터는 손실(lossy) 정보를 명시적으로 문서화

### 2.3 Compliance-first 확장

`agent.yaml`에 `compliance`와 `segregation_of_duties`를 1급 필드로 포함합니다.

- 일반 AI 에이전트 도구가 후순위로 다루는 규제/감사 요구를 사전 구조화
- FINRA, Federal Reserve, SEC, CFPB, EU AI Act, UK FCA 등 금융/규제 프레임워크 지원
- 모델 리스크 관리(SR 11-7), 데이터 거버넌스, 벤더 관리까지 포괄

### 2.4 Progressive Disclosure

스킬 로딩을 3단계로 나누어 컨텍스트 효율을 극대화합니다.

- Tier 1: 메타데이터만 (~100 토큰) — 라우팅/리스팅용
- Tier 2: 전체 지침 (<5000 토큰) — 활성 사용
- Tier 3: 리소스 포함 — 스크립트, 참조문서, 에셋

---

## 3. 7-Layer 파일 모델

### Layer 1: Identity (Required)

| 파일 | 역할 | 비고 |
|---|---|---|
| `agent.yaml` | Machine-readable manifest | JSON Schema로 엄격 검증, 유일한 강제 스키마 |
| `SOUL.md` | 에이전트 정체성, 성격, 커뮤니케이션 스타일 | Human-readable, 비어있으면 검증 실패 |

`agent.yaml`은 스펙에서 유일하게 스키마 검증이 강제되는 파일입니다. 핵심 필드:

```yaml
# Required
name: kebab-case-name       # ^[a-z][a-z0-9-]*$
version: "1.0.0"            # semantic version
description: "..."

# Recommended
spec_version: "0.1.0"

# Optional
model:
  preferred: claude-opus-4-6
  fallback: [claude-sonnet-4-5-20250929]
  constraints: { temperature, max_tokens, top_p, ... }
extends: parent-agent-url   # 단일 상속
dependencies: [...]          # 합성(composition)
skills: [skill-name, ...]
tools: [tool-name, ...]
agents: { sub-agent: { description, delegation } }
delegation: { mode: auto|explicit|router }
runtime: { max_turns, temperature, timeout }
a2a: { url, capabilities, authentication }
compliance: { ... }          # 가장 복잡한 섹션
```

### Layer 2: Behavior & Rules

| 파일 | 역할 |
|---|---|
| `RULES.md` | 강제 제약 (must-always, must-never, safety boundaries) |
| `DUTIES.md` | 역할 분리 및 권한 경계 (segregation of duties 정책) |
| `AGENTS.md` | 프레임워크 비종속 보조 지침 (Cursor/Copilot 등 폴백용) |
| `PROMPT.md` | 커스텀 시스템 프롬프트 (선택적) |

### Layer 3: Capabilities

| 디렉토리 | 역할 | 표준 |
|---|---|---|
| `skills/` | 재사용 가능 모듈 | Agent Skills open standard (agentskills.io) |
| `tools/` | MCP 호환 도구 정의 | YAML 스키마, implementation type |
| `workflows/` | 결정론적 다단계 절차 | depends_on, 조건 실행, 데이터 흐름 |
| `agents/` | 서브에이전트 정의 | 계층적 에이전트 시스템 |

### Layer 4: Knowledge & Memory

| 디렉토리 | 역할 | 구조 |
|---|---|---|
| `knowledge/` | 참조 문서 | index.yaml으로 priority/always_load 관리 |
| `memory/` | 세션 간 지속 상태 | memory.yaml + MEMORY.md + daily-log/ + context.md |

### Layer 5: Lifecycle & Ops

| 디렉토리 | 역할 |
|---|---|
| `hooks/` | 이벤트 핸들러 (JSON over stdin/stdout 프로토콜) |
| `config/` | 환경별 오버라이드 (default.yaml, production.yaml) |
| `examples/` | 교정 인터랙션 (good-outputs.md, bad-outputs.md) |

### Layer 6: Compliance

| 파일 | 역할 |
|---|---|
| `compliance/risk-assessment.md` | 리스크 평가 문서 |
| `compliance/regulatory-map.yaml` | 규제 매핑 |
| `compliance/validation-schedule.yaml` | 검증 스케줄 |

### Layer 7: Runtime

`.gitagent/` 디렉토리 — gitignored, deps, cache, state.json 등 런타임 상태 보관

---

## 4. CLI 소스 코드 구조

### 4.1 진입점 (`src/index.ts`)

Commander.js 기반으로 11개 커맨드를 등록합니다:

```text
init, validate, info, export, import,
install, audit, skills, run, lyzr, registry
```

### 4.2 유틸리티 (`src/utils/`)

| 파일 | 역할 |
|---|---|
| `loader.ts` | `loadAgentManifest()`, `loadFileIfExists()` — 핵심 로딩, TypeScript 인터페이스 정의 |
| `skill-loader.ts` | `parseSkillMd()`, `loadAllSkills()`, `loadSkillMetadata()` — Agent Skills 표준 파싱 |
| `schemas.ts` | JSON Schema 로딩, AJV 검증 |
| `git-cache.ts` | `resolveRepo()` — git clone, 캐시(~/.cache/gitagent/), 브랜치/태그 지원 |
| `skill-discovery.ts` | skillsmp 마켓플레이스 API 연동 |
| `auth-provision.ts` | .env 기반 API 키 관리 |
| `format.ts` | 터미널 출력 포맷팅(chalk) |

### 4.3 `AgentManifest` 인터페이스 (`loader.ts`)

```typescript
interface AgentManifest {
  name: string;
  version: string;
  description: string;
  model?: { preferred?, fallback?[], constraints? };
  extends?: string;
  dependencies?: Array<{ name, source, version?, mount?, vendor_management? }>;
  skills?: string[];
  tools?: string[];
  agents?: Record<string, { description?, delegation? }>;
  delegation?: { mode?, router? };
  runtime?: { max_turns?, temperature?, timeout? };
  a2a?: { url?, capabilities?[], authentication?, protocols?[] };
  compliance?: ComplianceConfig;
  tags?: string[];
  metadata?: Record<string, unknown>;
}
```

`ComplianceConfig`은 supervision, recordkeeping, model_risk, data_governance, communications, vendor_management, segregation_of_duties 7개 하위 섹션으로 구성됩니다.

---

## 5. 실행 플로우 (CLI 관점)

### 5.1 `init` — 스캐폴딩

`src/commands/init.ts`에서 `minimal/standard/full` 템플릿을 생성합니다.

| 템플릿 | 생성 파일 | 대상 |
|---|---|---|
| minimal | agent.yaml, SOUL.md | 개인 실험, 프로토타입 |
| standard | + RULES.md, AGENTS.md, skills/, knowledge/, memory/ | 일반 개발팀 |
| full | + DUTIES.md, compliance/, hooks/, config/, workflows/ | 규제 환경, 엔터프라이즈 |

템플릿이 곧 조직 성숙도 선택지 역할을 합니다.

### 5.2 `validate` — 정적 품질 게이트

`src/commands/validate.ts`는 6단계 다층 검증을 수행합니다:

1. **agent.yaml 스키마 검증**: AJV로 JSON Schema 대조
2. **SOUL.md 검증**: 파일 존재, 비어있지 않음, 제목만 있지 않음
3. **참조 무결성**: manifest가 참조한 skills/tools/agents가 파일 시스템에 존재
4. **Skills 검증**: SKILL.md frontmatter 파싱, Agent Skills 명명 규칙, 토큰 크기 권고
5. **hooks/tools YAML 스키마**: hooks.yaml, tools/*.yaml 각각 검증, script 파일 존재 확인
6. **컴플라이언스 검증** (`--compliance`): risk tier 요구사항, 프레임워크별 규칙, SOD 충돌 탐지

SOD 검증이 특히 정교합니다:

- 최소 2개 역할 정의 필수
- 충돌 쌍이 유효한 role ID 참조
- 에이전트별 역할 할당에서 충돌 역할 동시 보유 탐지
- 핸드오프에 최소 2개 distinct 역할 필요
- strict 모드에서는 충돌 시 에러, advisory 모드에서는 경고

CI에서 `gitagent validate --compliance`를 강제하면 "실행 전에 깨지는 구성"을 대부분 사전에 차단할 수 있습니다.

### 5.3 `export` — 포맷 변환

`src/commands/export.ts` + `src/adapters/`에서 13개 포맷으로 변환합니다.

**공통 빌드 과정** (system-prompt adapter 기준):

```
1. loadAgentManifest() → manifest
2. loadFileIfExists(SOUL.md) → identity
3. loadFileIfExists(RULES.md) → constraints
4. loadFileIfExists(DUTIES.md) → duty policy
5. loadAllSkills(skillsDir) → full instructions + allowed tools
6. knowledge/index.yaml → always_load documents 내용 포함
7. compliance → constraint bullet points 변환
8. memory/MEMORY.md → 현재 상태 요약 포함
→ 전체 연결(concatenate) → system prompt 문자열
```

**Claude Code 어댑터** (`claude-code.ts`)의 차이점:

- Skills를 메타데이터만 포함 (progressive disclosure — 전체 지침은 파일 참조로 안내)
- Compliance를 structured markdown 섹션으로 변환
- knowledge의 always_load 문서를 `## Reference:` 섹션으로 삽입
- Model 선호를 HTML 코멘트로 포함

**Shared compliance builder** (`shared.ts`):

- human_in_the_loop, escalation_triggers, FINRA 2210, PII handling → bullet point 변환
- SOD의 assignments, conflicts, handoffs, isolation → structured constraint 텍스트
- 여러 markdown 기반 어댑터에서 재사용

### 5.4 `run` — 실행 환경 연결

`src/commands/run.ts`는 레포 해석 → 매니페스트 로딩 → 어댑터 선택 → 실행의 흐름을 거칩니다.

**Claude Code runner** (`src/runners/claude.ts`)의 상세 흐름:

1. `exportToSystemPrompt(agentDir)` → system prompt 빌드
2. CLI 인수 구성:
   - `--model`: manifest.model.preferred
   - `--fallback-model`: manifest.model.fallback[0]
   - `--max-turns`: manifest.runtime.max_turns
   - `--permission-mode plan`: compliance.supervision.human_in_the_loop === 'always' 시
   - `--allowedTools`: skills의 allowed-tools + tools/*.yaml 이름 수집
   - `--agents`: agents/ 디렉토리의 서브에이전트 config (SOUL.md 포함)
   - `--add-dir`: knowledge/, skills/ 디렉토리
   - `--settings`: hooks/hooks.yaml → Claude Code hook 이벤트 매핑 (임시 JSON 파일)
   - `--append-system-prompt`: 전체 프롬프트
3. `resolveClaudeBinary()` → node_modules/.bin/claude가 아닌 실제 CLI 경로 탐색
4. `spawnSync(claude, args)` → 대화형 세션 시작
5. 임시 파일 cleanup

**Hook 이벤트 매핑** (`buildHooksSettings()`):

| GitAgent Event | Claude Code Event |
|---|---|
| `on_session_start` | `SessionStart` |
| `pre_tool_use` | `PreToolUse` |
| `post_tool_use` | `PostToolUse` |
| `pre_response` | `UserPromptSubmit` |
| `post_response` | `Stop` |
| `on_error` | `PostToolUseFailure` |
| `on_session_end` | `SessionEnd` |

### 5.5 `import` — 외부 포맷 변환

다음 외부 포맷에서 GitAgent 형식으로 변환합니다.

- claude: Claude Code 설정에서 시스템 프롬프트 추출 → SOUL.md, 규칙 → RULES.md
- cursor: .cursor/rules/*.mdc 파싱
- crewai: CrewAI YAML agent/task 정의 변환
- opencode: `AGENTS.md` + `opencode.json` → GitAgent 구조
- gemini: `GEMINI.md` + `.gemini/settings.json` → GitAgent 구조
- codex: `AGENTS.md` + `codex.json` → GitAgent 구조

### 5.6 `audit` — 컴플라이언스 점검

`src/commands/audit.ts`에서 규제 준수 체크리스트를 생성합니다.

- FINRA 3110/4511 점검
- SR 11-7 모델 리스크 요소 확인
- SEC Reg S-P 데이터 거버넌스
- SOD 역할 분리 상태 보고
- 갭 식별 및 권고사항

---

## 6. Skill 시스템

### 6.1 Agent Skills Open Standard

GitAgent는 agentskills.io 표준을 채택하여 스킬을 정의합니다.

**SKILL.md 구조**:

```yaml
---
name: code-review              # kebab-case, <=64자, -- 불가
description: Reviews code...   # <=1024자
license: MIT
allowed-tools: lint-check complexity-analysis  # 공백 구분
metadata:
  author: gitagent-examples
  category: developer-tools
  risk_tier: high
  regulatory_frameworks: finra,sec
---

# Skill Instructions (markdown)
...
```

**디렉토리 구조**:

```text
skills/<name>/
├── SKILL.md          # Required: frontmatter + instructions
├── scripts/          # 실행 가능 헬퍼
├── references/       # 보조 문서
├── assets/           # 템플릿, 스키마
├── examples/         # 입출력 예시
└── agents/           # 프레임워크별 설정
```

### 6.2 스킬 검색 우선순위

1. `<agentDir>/skills/` (agent-local, 최고 우선순위)
2. `<agentDir>/.agents/skills/` (Agent Skills 표준)
3. `<agentDir>/.claude/skills/` (Claude Code 표준)
4. `<agentDir>/.github/skills/` (GitHub 표준)
5. `~/.agents/skills/` (personal, 최저 우선순위)

### 6.3 마켓플레이스 연동

`gitagent skills search/install/list/info` 명령으로 외부 레지스트리(skillsmp, github, local)에서 스킬을 검색하고 설치합니다.

---

## 7. Tool 시스템

MCP 호환 도구를 YAML로 정의합니다.

```yaml
name: search-regulations
description: Search regulatory databases
version: 1.0.0
input_schema:
  type: object
  properties:
    query: { type: string }
    framework: { type: string, enum: [finra, sec, federal_reserve] }
  required: [query]
output_schema:
  type: object
  properties:
    results: { type: array }
implementation:
  type: script          # script | mcp_server | http
  path: search-regulations.py
  runtime: python3
  timeout: 30
annotations:
  requires_confirmation: false
  read_only: true
  cost: low
  compliance_sensitive: true
  idempotent: false
```

**Implementation 타입**: script(로컬 실행), mcp_server(MCP 서버 엔드포인트), http(REST API)

---

## 8. Workflow 시스템

결정론적 다단계 절차를 YAML로 정의합니다. LLM이 아닌 명시적 의존성 그래프가 실행 순서를 제어합니다.

핵심 기능:

- **depends_on**: 스텝 간 명시적 순서 제어
- **데이터 흐름**: `${{ steps.X.outputs.Y }}` 템플릿 표현식
- **조건 실행**: `conditions` 필드로 특정 조건에서만 스텝 실행
- **에이전트 위임**: 스텝에서 `agent:` 필드로 서브에이전트에 위임
- **에러 핸들링**: per-step retry + workflow-level escalation
- **컴플라이언스 추적**: per-step audit level

---

## 9. Hook 시스템

### 9.1 이벤트 타입

7가지 라이프사이클 이벤트를 지원합니다:

| 이벤트 | 시점 | 주 용도 |
|---|---|---|
| `on_session_start` | 세션 시작 | 컴플라이언스 컨텍스트 로딩, 메모리 복원 |
| `pre_tool_use` | 도구 호출 전 | 감사 로깅, 권한 검증 |
| `post_tool_use` | 도구 호출 후 | 출력 검증, PII 확인 |
| `pre_response` | 응답 생성 전 | 커뮤니케이션 컴플라이언스 체크 |
| `post_response` | 응답 전송 후 | 감사 기록 |
| `on_error` | 에러 발생 | 감독자 에스컬레이션 |
| `on_session_end` | 세션 종료 | 메모리 업데이트, 감사 마무리 |

### 9.2 I/O 프로토콜

hook 스크립트는 JSON over stdin/stdout 프로토콜을 사용합니다:

**입력**: `{ event, timestamp, data: { tool_name, arguments }, session: { id, agent, model_version } }`

**출력**: `{ action: "allow"|"block"|"modify", modifications, audit: { logged, log_id } }`

### 9.3 fail_open / fail_closed

각 hook에 `fail_open` 플래그로 hook 실패 시 동작을 제어합니다:

- `fail_open: false` (기본): hook 실패 시 실행 중단 — 컴플라이언스 필수 hook에 적합
- `fail_open: true`: hook 실패 시 계속 진행 — 비필수 로깅 hook에 적합

---

## 10. Memory 시스템

계층적 메모리 구조로 세션 간 상태를 유지합니다.

```yaml
# memory/memory.yaml
layers:
  - name: index
    path: MEMORY.md          # 현재 상태 요약, max 20 lines
  - name: context
    path: context.md         # 프로젝트 컨텍스트, max 100 lines, always load
  - name: key-decisions
    path: key-decisions.md   # 아키텍처 결정, max 200 lines
  - name: daily-log
    path: daily-log/         # 일별 로그, 30일 후 압축, 90일 보존

update_triggers:
  - on_session_end
  - on_explicit_save
```

패턴: 에이전트는 시작 시 MEMORY.md를 읽어 이전 컨텍스트를 복원하고, 세션 종료 시 상태를 업데이트합니다.

---

## 11. Compliance 모델 상세

### 11.1 Risk Tier 기반 요구사항

| Tier | 추가 요구사항 |
|---|---|
| low | 없음 |
| standard | 권고 사항만 |
| high | human_in_the_loop 필수, audit_logging 필수, quarterly 이상 검증 |
| critical | high와 동일 + compliance/ 디렉토리 권고 |

### 11.2 프레임워크별 규칙

| Framework | 규칙 ID | 필수/권고 요구사항 |
|---|---|---|
| FINRA | 2210 | fair_balanced=true, no_misleading=true |
| FINRA | 3110 | supervision 섹션 권고 |
| FINRA | 4511 | recordkeeping 섹션 권고 |
| Federal Reserve | SR 11-7 | model_risk 섹션 필수, ongoing_monitoring=true |
| SEC | 17a-4 | audit_logging 권고 |
| SEC | Reg S-P | pii_handling='allow' 시 경고 |
| CFPB | - | bias_testing 권고 |

### 11.3 Segregation of Duties (SOD)

멀티에이전트 시스템에서 역할 분리를 강제합니다:

- **roles**: 최소 2개, 고유 ID, permissions 목록
- **conflicts**: 동일 에이전트가 동시에 보유할 수 없는 역할 쌍
- **assignments**: 에이전트별 역할 매핑, 충돌 자동 탐지
- **handoffs**: 다중 역할 승인이 필요한 액션 정의
- **isolation**: state(full/shared/none), credentials(separate/shared)
- **enforcement**: strict(충돌 시 에러) / advisory(경고만)

---

## 12. 어댑터 시스템

### 12.1 Export 어댑터 (13개)

| Adapter | 출력 | Fidelity | 주 대상 |
|---|---|---|---|
| `system-prompt` | 플레인 텍스트 연결 | Complete | 모든 LLM |
| `claude-code` | CLAUDE.md + 메타데이터 | High | Claude Code |
| `openai` | Python SDK 코드 | Medium | OpenAI Agents SDK |
| `crewai` | YAML config | Medium | CrewAI |
| `gemini` | GEMINI.md + settings.json | Medium | Gemini CLI |
| `cursor` | .cursor/rules/*.mdc | Medium | Cursor IDE |
| `opencode` | Instructions + config | Medium | OpenCode |
| `github` | Actions workflow YAML | Low | GitHub Actions |
| `copilot` | Copilot instructions | Low | VS Code Copilot |
| `lyzr` | Studio agent JSON | Low | Lyzr Studio |
| `openclaw` | OpenClaw format | Low | OpenClaw |
| `nanobot` | Nanobot manifest | Low | Nanobot |
| `codex` | Codex format | Low | Codex |

### 12.2 Import 어댑터

| Source | 변환 내용 |
|---|---|
| `claude` | Claude Code 설정 → SOUL.md, RULES.md, tools/ |
| `cursor` | .cursor/rules/*.mdc → GitAgent 구조 |
| `crewai` | CrewAI YAML → agent.yaml + 스킬 |
| `opencode` | `AGENTS.md` + `opencode.json` → agent.yaml, SOUL.md, RULES.md |
| `gemini` | `GEMINI.md` + `.gemini/settings.json` → agent.yaml, SOUL.md, RULES.md |
| `codex` | `AGENTS.md` + `codex.json` → agent.yaml, SOUL.md, RULES.md |

### 12.3 Runner 어댑터

| Adapter | 실행 방식 |
|---|---|
| `claude` | Claude Code CLI 생성(`spawnSync`), system prompt + 모든 플래그 |
| `openai` | Python SDK 코드 생성, Agent + function tools |
| `crewai` | CrewAI YAML 생성, agents + tasks |
| `gemini` | GEMINI.md + settings.json 생성 |
| `github` | GitHub Actions workflow 등록 |
| `opencode` | OpenCode config 생성 |
| `openclaw` | OpenClaw 포맷 출력 |
| `nanobot` | Nanobot manifest 빌드 |
| `lyzr` | Lyzr Studio agent 생성/업데이트 |
| `git` | 프레임워크 자동 감지 후 적합한 runner 호출 |
| `prompt` | system prompt만 stdout으로 출력 |

---

## 13. Git-native 아키텍처 패턴 (13개)

| # | 패턴 | 설명 |
|---|---|---|
| 1 | Human-in-the-Loop for RL | 에이전트가 브랜치+PR 생성 → 사람이 리뷰 후 merge |
| 2 | Segregation of Duties | 역할 분리, 충돌 매트릭스, 단일 에이전트 통제 방지 |
| 3 | Live Agent Memory | memory/ 폴더 (daily-log, key-decisions, context)가 세션 간 유지 |
| 4 | Agent Versioning | 모든 변경이 git commit, 전체 undo 히스토리, 롤백 가능 |
| 5 | Shared Context via Monorepo | 루트 레벨 리소스를 모든 에이전트가 공유 |
| 6 | Branch-based Deployment | dev → staging → main 프로모션 파이프라인 |
| 7 | Knowledge Tree | 계층적 엔티티 관계, 임베딩 지원(향후) |
| 8 | Agent Forking & Remixing | 공개 에이전트 레포 fork → 도메인 커스텀 → 업스트림 PR |
| 9 | CI/CD for Agents | `gitagent validate`를 GitHub Actions에서 실행, 나쁜 merge 차단 |
| 10 | Agent Diff & Audit Trail | `git diff`로 정확한 변경 확인, `git blame`으로 작성자 추적 |
| 11 | Tagged Releases | 안정 버전(v1.1.0) 태그, 프로덕션은 태그 고정 |
| 12 | Secret Management | .env는 로컬(.gitignore), 에이전트 설정은 공유 가능 |
| 13 | Agent Lifecycle with Hooks | bootstrap.md, teardown.md로 시작/종료 제어 |

---

## 14. JSON Schema 체계

| Schema 파일 | 검증 대상 | 적용 시점 |
|---|---|---|
| `agent-yaml.schema.json` | agent.yaml 전체 | validate 명령 |
| `skill.schema.json` | SKILL.md YAML frontmatter | validate + skill loader |
| `tool.schema.json` | tools/*.yaml | validate 명령 |
| `workflow.schema.json` | workflows/*.yaml | validate 명령 |
| `hooks.schema.json` | hooks/hooks.yaml | validate 명령 |
| `hook-io.schema.json` | hook stdin/stdout JSON | 런타임 |
| `memory.schema.json` | memory/memory.yaml | validate 명령 |
| `knowledge.schema.json` | knowledge/index.yaml | validate 명령 |
| `config.schema.json` | config/*.yaml | validate 명령 |
| `marketplace.schema.json` | 스킬 배포 매니페스트 | registry 명령 |

---

## 15. 기술 스택

| 구분 | 기술 |
|---|---|
| 언어/런타임 | TypeScript, Node.js (>=18) |
| CLI 프레임워크 | commander v12 |
| 스키마 검증 | ajv v8 + ajv-formats |
| 데이터 포맷 | YAML (js-yaml v4), Markdown |
| 터미널 출력 | chalk v5 |
| 사용자 입력 | inquirer v9 |
| 패키징 | npm (`@shreyaskapale/gitagent` v0.1.7) |
| 테스트 | Node.js 내장 test runner |

---

## 16. 강점과 트레이드오프

### 강점

- **이식성**: 하나의 정의로 13개 플랫폼 지원, 프레임워크 lock-in 최소화
- **협업 친화**: 에이전트 정의를 PR/리뷰/diff/blame으로 관리하는 자연스러운 워크플로우
- **규제 준수**: FINRA/SEC/Federal Reserve 등 규제 요구를 머신 체크 가능한 구성으로 구조화
- **점진적 채택**: minimal(2파일) → standard → full로 점진 확장 가능
- **스킬 생태계**: Agent Skills open standard + 마켓플레이스 연동

### 트레이드오프

- **런타임 품질 의존**: 실제 동작 품질은 어댑터/실행 엔진 품질에 의존
- **어댑터 Fidelity 편차**: 포맷별 기능 손실(lossy) 관리 필요
- **문서 유지 비용**: 표준 구조가 풍부해질수록 초기 작성/갱신 비용 증가
- **초기 단계**: v0.1.x — 스펙과 스키마가 아직 변경 가능
- **런타임 격차**: hook I/O 프로토콜의 프레임워크별 매핑 완전성 차이

---

## 17. 이 프로젝트에 주는 시사점

이 저장소(agentic-workflows) 관점에서 GitAgent는 다음 참고 가치를 제공합니다:

1. **"에이전트 정의 레이어"와 "실행 레이어" 분리 패턴** — 메타 표준 전략
2. **규제/감사 요구를 스키마로 승격하는 방법** — compliance-first 설계
3. **Progressive disclosure를 통한 컨텍스트 효율화** — 토큰 예산 관리
4. **Git 기반 에이전트 운영(versioning, branching, CI/CD)의 구체적 구현**
5. **다중 프레임워크 어댑터의 실용적 변환 전략과 한계 문서화**

단일 에이전트 구현체 분석을 넘어, 여러 에이전트 런타임을 아우르는 **메타 표준 전략** 사례로 볼 수 있습니다.

---

## 18. 참고 소스

- 홈페이지: <https://www.gitagent.sh/>
- 저장소: <https://github.com/open-gitagent/gitagent>
- 스펙: `spec/SPECIFICATION.md`
- 코드 진입점: `src/index.ts`
- 핵심 명령: `src/commands/validate.ts`, `src/commands/run.ts`, `src/commands/export.ts`, `src/commands/import.ts`
- 어댑터: `src/adapters/claude-code.ts`, `src/adapters/system-prompt.ts`
- 러너: `src/runners/claude.ts`, `src/runners/git.ts`
- 유틸: `src/utils/loader.ts`, `src/utils/skill-loader.ts`
