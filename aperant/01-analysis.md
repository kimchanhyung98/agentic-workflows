# Aperant 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `AndyMik90/Aperant`
- 성격: Electron 기반 자율 코딩 데스크톱 앱
- 핵심 기반: Vercel AI SDK v6 (`streamText`) + XState 상태기계 + git worktree 격리
- 주요 목표: UI 이벤트를 IPC와 상태기계로 정리한 뒤, worker thread에서 다단계 에이전트 파이프라인을 실행하고, human review gate로 통제

공개 코드 기준으로 보면 다음 5가지가 중심 설계다.

1. **모듈형 IPC + XState 상태기계** — `ipc-handlers/*`, `taskStateManager`, `task-machine.ts`
2. **task별 git worktree 격리 실행** — `createOrGetWorktree()`로 구현/QA 작업공간을 분리
3. **complexity-adaptive 오케스트레이션** — spec 생성은 complexity-first, build는 planning → coding → QA
4. **실패 복원 자동화** — rate limit/auth failure 감지, auto-swap restart, pause/resume, startup recovery
5. **멀티 프로바이더 추상화** — 11개 프로바이더와 계정 우선순위 큐를 하나의 실행 인터페이스로 통합

### 기술 스택

| 계층 | 기술 |
|---|---|
| 프레임워크 | Electron 40 |
| UI | React 19, Zustand, Tailwind CSS v4 |
| AI 런타임 | Vercel AI SDK v6 (`streamText`) |
| 상태 관리 | XState task machine + plan file persistence |
| 언어 | TypeScript (strict) |
| 플랫폼 | Windows, macOS, Linux |

---

## 2. 구조적 분해

### 2.1 UI/IPC 계층

- Renderer는 preload API를 통해 `TASK_START`, `TASK_STOP`, `TASK_REVIEW` 같은 IPC 이벤트를 발행한다.
- `ipc-setup.ts`는 실제 구현을 `ipc-handlers/*` 도메인 모듈로 위임한다.
- `task/execution-handlers.ts`는 git repo 여부, 초기 커밋 존재, 인증 상태, spec/plan 파일 상태를 확인하고 실행 분기를 결정한다.
- `agent-events-handlers.ts`는 worker에서 올라오는 `task-event`, `execution-progress`, `result`, `exit` 메시지를 받아 UI와 plan 파일을 갱신한다.
- `taskStateManager`는 XState actor를 통해 `backlog → planning → plan_review → coding → qa_review → qa_fixing → human_review` 흐름을 관리하고, `xstateState`/`executionPhase`를 `implementation_plan.json`에 동기화한다.

**의도:** UI 상태, worker 이벤트, plan 파일 상태를 한 곳에서 정렬해 "카드 위치는 바뀌었는데 실제 plan은 다른 상태" 같은 불일치를 줄이는 데 초점이 있다.

### 2.2 Task Runtime 계층

- `AgentManager`는 task/spec/QA 실행의 진입점 facade다.
- `AgentProcessManager`는 worker thread spawn, 종료, 재시작, event relay를 담당한다.
- `AgentEvents`는 worker의 structured progress를 우선 사용하고, 필요할 때만 로그 텍스트를 fallback으로 파싱해 phase를 추정한다.
- `taskExecutionContext` Map에는 `projectPath`, `specId`, `options`, `swapCount`, `generation`, `projectId` 등이 저장되어 restart 시 동일 컨텍스트를 재구성한다.
- `AgentQueueManager`는 이름과 달리 일반 task 빌드 큐가 아니라 **roadmap / ideation 러너의 queue와 progress persistence**를 담당한다.

### 2.3 AI 실행 계층

- build 실행 시 `createOrGetWorktree()`가 `.auto-claude/worktrees/tasks/{specId}` 아래 worktree를 준비한다.
- `worker.ts`는 serialized session config를 받아 security profile과 tool context를 복원하고, MCP clients를 초기화한 뒤 agent type별 실행 경로를 선택한다.
- `build_orchestrator`, `qa_reviewer`, `spec_orchestrator`는 각각 `BuildOrchestrator`, `QALoop`, `SpecOrchestrator`로 라우팅된다.
- 그 외 agent type은 단일 세션 경로를 타며, `runContinuableSession()`이 내부적으로 AI session runner를 감싼다.
- `ToolRegistry`는 내장 도구 9개와 MCP 도구를 합성하고, `Tool.define`은 security hook과 write-path containment를 적용한다.

### 2.4 오케스트레이션 계층

에이전트 하나가 전체 작업을 끝내는 구조가 아니라, phase별 agent와 orchestrator가 파일 산출물 중심으로 이어 붙는 구조다.

**SpecOrchestrator** — complexity-first spec 생성:

1. `complexity_assessment`를 먼저 실행한다.
2. complexity가 `simple`이면 `quick_spec → validation`
3. complexity가 `standard`이면 `discovery → requirements → spec_writing → planning → validation`
4. complexity가 `complex`이면 `discovery → requirements → research → context → spec_writing → self_critique → planning → validation`
5. phase 산출물(`requirements.json`, `context.json`, `research.json`, `spec.md`, `implementation_plan.json`)은 다음 phase의 prompt에 누적 주입된다.

추가로 `useAgenticOrchestration`이 켜진 경우 `spec_orchestrator_agentic` 프롬프트와 `SpawnSubagent` 도구를 사용해 AI 주도형 spec orchestration 경로를 탈 수 있다.

**BuildOrchestrator** — spec를 구현으로 전환:

1. `planner`가 `implementation_plan.json`을 생성하거나 정규화한다.
2. `coder`가 `SubtaskIterator`를 통해 subtask를 순차/병렬로 수행한다.
3. `qa_reviewer`가 결과를 검증한다.
4. 실패 시 `qa_fixer`가 수정하고 다시 QA를 돈다.
5. QA 통과 후 최종 human review 단계로 넘어간다.

**QALoop** — review/fix 반복:

- `qa_reviewer → qa_fixer → qa_reviewer` 루프를 돌며 반복 검증한다.
- 반복 실패, recurring issue, consecutive error가 일정 수준을 넘으면 escalation 쪽으로 빠진다.
- `QA_FIX_REQUEST.md`가 있으면 human feedback를 먼저 처리하고 QA를 재개한다.

### 2.5 Provider 추상화 계층

현재 코드는 11개 프로바이더를 지원한다.

| 프로바이더 | 인증 / 특징 |
|---|---|
| Anthropic | OAuth 토큰 + API key |
| OpenAI | API key + 파일 기반 OAuth (Codex) |
| Google (Gemini) | API key |
| AWS Bedrock | region + AWS credential chain |
| Azure OpenAI | API key + deployment/baseURL |
| Mistral | API key |
| Groq | API key |
| xAI | API key |
| OpenRouter | API key |
| ZAI | API key + OpenAI-compatible endpoint |
| Ollama | 로컬 OpenAI-compatible endpoint, 기본적으로 무인증 |

- `providers/registry.ts`는 provider SDK를 묶어 unified registry를 만든다.
- `providers/factory.ts`는 provider별 quirks를 숨긴다.
  - OpenAI Codex OAuth 계정은 `.responses()` 경로를 사용한다.
  - Azure는 deployment name 기반으로 `.chat()`을 호출한다.
  - Ollama와 ZAI는 OpenAI-compatible adapter를 사용한다.
- `resolveAuthFromQueue()`는 `providerAccounts + globalPriorityOrder`를 순회하며 계정을 선택한다.
- 적절한 account를 찾지 못하면 레거시 Claude profile auth로 fallback한다.
- `PhaseConfig`는 spec / planning / coding / QA 단계별 모델과 thinking level을 분리한다.

---

## 3. 핵심 실행 플로우

### 3.1 `TASK_START` → spec 생성 / 실행 분기

`TASK_START` 이벤트 처리 시 실행 경로는 아래처럼 갈린다.

1. task와 project를 조회한다.
2. git 초기 조건을 검증한다.
   - 저장소가 아니면 실행 거부
   - 초기 커밋이 없으면 실행 거부
3. 인증 상태를 검증한다.
   - 활성 Claude profile auth 또는 provider account가 하나 이상 있어야 한다.
4. `implementation_plan.json`의 실제 subtask 유무를 먼저 확인한다.
   - in-memory `task.subtasks`보다 plan 파일이 더 신뢰 가능한 source로 취급된다.
5. 현재 XState 상태에 따라 `PLANNING_STARTED`, `PLAN_APPROVED`, `USER_RESUMED` 중 하나를 `taskStateManager`에 보낸다.
6. file watcher를 시작한다.
   - worktree spec dir가 이미 있으면 worktree 쪽을 우선 감시한다.
7. `spec.md`가 없으면 `startSpecCreation()`을 호출한다.
8. `spec.md`는 있지만 plan이 없거나 subtask가 비어 있으면 `startTaskExecution()`을 호출해 planner부터 다시 탄다.
9. spec와 plan이 모두 있으면 기존 build 파이프라인을 바로 재개한다.

이 흐름은 "task 카드의 상태"보다 "실제 spec/plan 파일 상태"를 우선시해 재시작 시 drift를 줄이도록 설계되어 있다.

### 3.2 build/QA 시 worktree 기본 사용

`startTaskExecution()`은 기본적으로 worktree를 사용한다 (`useWorktree !== false`).
반면 spec 생성은 main project 경로의 spec dir에서 시작하고, 구현/QA 단계부터 worktree로 진입한다.

- 위치: `.auto-claude/worktrees/tasks/{specId}`
- 브랜치: `auto-claude/{specId}`
- 기준 브랜치: task metadata의 `baseBranch` 또는 project 설정의 main branch

생성 과정은 멱등적으로 설계되어 있다.

1. `git worktree prune`
2. 기존 worktree가 git에 등록되어 있으면 재사용
3. 디렉토리만 남은 stale 상태면 삭제 후 재생성
4. `origin/{baseBranch}` fetch 시도 (non-fatal)
5. 기존 branch 재사용 또는 `git worktree add -b auto-claude/{specId}`
6. gitignored인 spec dir를 main project에서 worktree로 copy

추가 포인트:

- `pushNewBranches`가 활성화돼 있으면 새 branch를 origin에 push하고 upstream을 잡는다.
- worker session의 `cwd`, `projectDir`, `specDir`는 worktree 기준으로 바뀐다.
- worktree에서 실행할 때 `sourceSpecDir`는 main project spec dir를 가리켜 spec 동기화에 사용된다.

### 3.3 AI 세션 실행 상세

worker 경로의 세션 실행은 `runContinuableSession()`과 `runAgentSession()`을 중심으로 돌아간다.

- 기본 max step은 500이다.
- 메모리 컨텍스트가 있으면 step limit이 calibration factor에 따라 조정된다.
- `streamText()` 기반 tool loop를 사용한다.
- `ProgressTracker`가 stream event를 phase/usage 정보로 변환한다.
- MCP clients는 agent type별 설정에 맞춰 동적으로 붙는다.

실행 중 핵심 제약:

- **컨텍스트 윈도우 관리**: 85%에서 경고, 90%에서 abort/continuation
- **수렴 유도**: `qa_reviewer`, `qa_fixer`, `spec_validation`, `pr_reviewer` 같은 agent는 step의 75% 부근에서 마무리 nudge를 받는다
- **인증 갱신**: 401이면 `onAuthRefresh()` 또는 `onAccountSwitch()`를 시도한다
- **계정 전환**: 429 / 401이면 priority queue에서 다음 account를 찾아 provider/model을 교체한다
- **실행 결과 전달**: worker는 `task-event`, `execution-progress`, `stream-event`, `result`, `exit`를 main thread에 전달한다

### 3.4 QA / human review 플로우

Aperant에는 review gate가 두 개 있다.

1. **plan review**
   - planning 완료 후 `requireReviewBeforeCoding`이 켜져 있으면 `plan_review` 상태로 들어간다.
   - 사용자가 승인해야 coding으로 넘어간다.
2. **final human review**
   - QA 통과 후 `human_review` 상태로 들어간다.
   - `TASK_REVIEW`가 승인/반려를 결정한다.

`TASK_REVIEW`의 실제 동작:

- 승인
  - main spec dir의 `qa_report.md`에 APPROVED 기록
  - `MARK_DONE` 이벤트 전송
- 반려
  - worktree가 있다면 main 작업공간에 반영된 merge 흔적을 `git reset`, `git checkout -- .`, `git clean -fd -e .auto-claude`로 되돌린다
  - `QA_FIX_REQUEST.md`와 `feedback_images/`는 worktree spec dir가 있으면 그쪽에 기록한다
  - `startQAProcess()`는 **build가 실제로 실행된 경로**를 기준으로 다시 시작한다
  - `USER_RESUMED`를 보내 XState를 coding 쪽으로 되돌린다

주의할 점은 "승인 = 항상 worktree 즉시 삭제"가 아니라는 점이다.

- full merge handler는 성공 후 cleanupWorktree를 시도한다.
- stage-only merge나 `keepWorktree` 선택 시 worktree를 남길 수 있다.
- task를 `done`으로 옮길 때도 worktree가 남아 있으면 추가 cleanup confirmation이 필요하다.

### 3.5 상태기계와 phase protocol

Aperant 문서를 이해할 때 가장 빠지기 쉬운 부분이 **XState state**와 **execution phase**의 이중 구조다.

1. **XState task machine**
   - 상태: `backlog`, `planning`, `plan_review`, `coding`, `qa_review`, `qa_fixing`, `human_review`, `error`, `creating_pr`, `pr_created`, `done`
   - 이벤트: `PLANNING_STARTED`, `PLAN_APPROVED`, `CODING_STARTED`, `QA_STARTED`, `QA_PASSED`, `QA_FAILED`, `USER_RESUMED`, `MARK_DONE` 등
2. **Execution phase protocol**
   - phase: `planning`, `coding`, `rate_limit_paused`, `auth_failure_paused`, `qa_review`, `qa_fixing`, `complete`, `failed`
   - worker 로그 안의 `__EXEC_PHASE__:` structured marker를 우선 사용한다

`AgentEvents`의 역할:

- structured progress가 있으면 그것을 그대로 사용한다
- structured marker가 없을 때만 로그 문자열을 fallback으로 파싱한다
- phase regression을 막는다
- pause phase나 terminal phase는 fallback 텍스트로 덮어쓰지 않는다

`taskStateManager`의 역할:

- worker `task-event`를 XState actor에 보낸다
- legacy UI status (`in_progress`, `ai_review`, `human_review`, `done`)와 review reason을 계산한다
- `xstateState`와 `executionPhase`를 main spec dir와 worktree spec dir의 `implementation_plan.json`에 함께 기록한다

즉, Aperant는 "단순한 progress bar"가 아니라 **XState 상태기계 + structured phase protocol + plan file persistence**를 동시에 돌리는 구조다.

---

## 4. 도구 시스템

### 4.1 내장 도구 + MCP 도구

내장 도구는 총 9개다.

| 도구 | 설명 |
|---|---|
| Read | 파일 읽기 |
| Write | 파일 쓰기 |
| Edit | 파일 편집 |
| Bash | 셸 명령 실행 |
| Glob | 파일 패턴 매칭 |
| Grep | 내용 검색 |
| WebFetch | 웹 콘텐츠 가져오기 |
| WebSearch | 웹 검색 |
| SpawnSubagent | 서브에이전트 세션 실행 |

여기에 agent type별 MCP 도구가 더해진다.

- `context7`
- `memory`
- `linear`
- `electron` / `puppeteer`
- `auto-claude` 전용 MCP 도구 (`update_subtask_status`, `get_build_progress`, `record_discovery`, `update_qa_status` 등)

핵심은 "모든 agent가 같은 도구를 쓰는 것"이 아니라, `AGENT_CONFIGS`가 **agent type → builtin tools → MCP servers → autoClaude tools** 매핑을 중앙에서 관리한다는 점이다.

### 4.2 보안 훅과 경로 제어

`Tool.define`은 모든 non-readonly 도구에 대해 공통 보안 훅을 적용한다.

- `bashSecurityHook()` 실행
- `allowedWritePaths` 검사
- file path sanitization (`sanitizeFilePathArg`)
- 문자열 결과 안전 절단

특히 spec 관련 agent는 `allowedWritePaths: [session.specDir]`가 적용되어 spec dir 밖으로 deliverable을 쓰지 못한다.

### 4.3 Bash 보안 검증

현재 bash 보안 모델은 **denylist 기반 allow-by-default**다.

처리 흐름:

1. command name 추출
2. `BLOCKED_COMMANDS` 확인
3. validator가 등록된 명령이면 segment 단위 검증
4. 아니면 허용

차단 대상 예시:

- 시스템 종료: `shutdown`, `reboot`, `poweroff`
- 디스크 파괴: `dd`, `mkfs`, `fdisk`
- 권한 상승: `sudo`, `su`, `doas`, `chown`
- 시스템 설정: `systemctl`, `service`, `crontab`

명령어별 validator 예시:

- `rm` → 루트/위험 경로 삭제 방지
- `chmod` → 과도한 권한 변경 방지
- `git` → `git config user.*` 같은 위험 설정 변경 방지
- `bash/sh/zsh` → `-c` 내부 명령 재귀 검증
- `psql/mysql/mongosh/redis-cli` → 위험한 DB 명령 검증
- `kill/pkill/killall` → 프로세스 종료 검증

중요한 점은 `securityProfile`이 여전히 worker context에 실려 다니지만, **실제 allow/deny 판단의 주체는 더 이상 security profile command set이 아니라 denylist + validator**라는 점이다.

---

## 5. 에이전트 설정 시스템

### 5.1 에이전트 타입 (현재 33개)

`AgentType` union 기준으로 현재 33개 agent type이 정의돼 있다.

| 범주 | 에이전트 타입 | 역할 |
|---|---|---|
| 스펙 생성 | `spec_orchestrator`, `spec_discovery`, `spec_gatherer`, `spec_researcher`, `spec_context`, `spec_writer`, `spec_critic`, `spec_validation`, `spec_compaction` | spec 파이프라인 및 보조 phase |
| 빌드 / QA | `build_orchestrator`, `planner`, `coder`, `qa_reviewer`, `qa_fixer` | 구현 계획, 구현, 검증, 수정 |
| PR / 리뷰 | `pr_reviewer`, `pr_finding_validator`, `pr_orchestrator_parallel`, `pr_followup_parallel`, `pr_followup_extraction`, `pr_security_specialist`, `pr_quality_specialist`, `pr_logic_specialist`, `pr_codebase_fit_specialist`, `pr_template_filler` | PR 분석, 병렬 리뷰, finding 검증 |
| 유틸리티 / 분석 | `insights`, `analysis`, `batch_analysis`, `batch_validation`, `merge_resolver`, `commit_message`, `roadmap_discovery`, `competitor_analysis`, `ideation` | 코드 탐색, 유틸리티 생성, 로드맵/아이데이션 |

과거 요약처럼 agent 수를 대략적으로 뭉뚱그릴 수도 있지만, 최신 구현을 설명하려면 **spec/PR/utilities까지 포함한 33개 agent type**이라고 보는 편이 정확하다.

### 5.2 Phase별 모델 선택

`PhaseConfig`는 같은 task 안에서도 phase(spec / planning / coding / qa)별 모델과 thinking level을 다르게 준다.

**모델 해석 우선순위:**

1. CLI override (`--model`)
2. `task_metadata.json`의 `phaseModels[phase]` (auto profile 모드)
3. `task_metadata.json`의 `model` (non-auto profile 모드)
4. `DEFAULT_PHASE_MODELS[phase]`

**모델 shorthand:**

| shorthand | 실제 모델 | 비고 |
|---|---|---|
| `opus` | `claude-opus-4-6` | adaptive thinking 지원 |
| `opus-1m` | `claude-opus-4-6` | 1M context window (beta) |
| `opus-4.5` | `claude-opus-4-5-20251101` | |
| `sonnet` | `claude-sonnet-4-6` | 기본 모델 |
| `haiku` | `claude-haiku-4-5-20251001` | |

**프로바이더 자동 감지:**

모델 ID 접두사로 프로바이더를 자동 판별한다: `claude-` → Anthropic, `gpt-`/`o1-`/`o3-` → OpenAI, `gemini-` → Google, `mistral-` → Mistral, `llama-` → Groq, `grok-` → xAI, `glm-` → ZAI

### 5.3 Thinking Level 시스템

thinking level은 4단계로, 각 단계별 토큰 예산이 정해져 있다.

| 레벨 | 토큰 예산 |
|---|---|
| `low` | 1,024 |
| `medium` | 4,096 |
| `high` | 16,384 |
| `xhigh` | 32,768 |

**Spec phase별 기본 thinking:**

- `discovery`, `spec_writing`, `self_critique` → `high`
- `requirements`, `research`, `context`, `planning`, `validation` → `medium`

**Build phase별 기본 thinking:**

- `spec` → `medium`, `planning` → `high`, `coding` → `medium`, `qa` → `high`

**Adaptive thinking:**

`claude-opus-4-6`만 `maxThinkingTokens`와 `effortLevel`을 동시에 지원한다.
다른 모델은 `maxThinkingTokens`만 사용한다.

CLI override(`--thinking`)가 있으면 이것이 우선한다.

---

## 6. 신뢰성 / 복원성 설계

### 6.1 auto-swap restart

`AgentProcessManager`는 429/401을 감지하면 `auto-swap-restart-task` 이벤트를 올리고, `AgentManager.restartTask()`가 이를 받아 재시작을 수행한다.

순서:

1. swap count 상한 확인 (최대 2회)
2. 현재 프로세스 종료
3. `generation` 증가
4. stuck subtask reset
5. 동일 task context로 재실행

### 6.2 stale exit 방지

`taskExecutionContext.generation`이 이전 실행의 늦은 exit callback이 새 실행 컨텍스트를 청소하지 못하게 막는다.
종료 후 fallback timer도 별도로 있어 "프로세스는 끝났는데 상태가 active로 남는" 경우를 완화한다.

### 6.3 startup recovery

앱 시작 시 `runStartupRecoveryScan()`이 모든 project의 `implementation_plan.json`을 훑어 `in_progress`로 남았지만 실제 프로세스가 없는 subtask를 `pending`으로 되돌린다.

### 6.4 pause / resume

pause는 단순 로그 메시지가 아니라 phase protocol의 일부다.

- `rate_limit_paused`
- `auth_failure_paused`

pause 시 sentinel file이 spec dir에 기록되고, `TASK_RESUME_PAUSED`는 `RESUME` 파일을 써서 backend 재개를 신호한다.

### 6.5 에러 분류 체계

`error-classifier.ts`는 8개 에러 코드로 세분화해 적절한 복구 경로를 선택한다.

| 에러 코드 | HTTP | 설명 | 복구 경로 |
|---|---|---|---|
| `rate_limited` | 429 | 일시적 rate limit | auto-swap / 대기 후 재시도 |
| `billing_error` | 429 | 잔액 부족, 크레딧 소진 | account 전환 (일시적이지 않음) |
| `auth_failure` | 401 | 인증 만료/실패 | 토큰 갱신 → account 전환 |
| `concurrency_error` | 400 | 도구 동시 실행 충돌 | 자동 재시도 |
| `tool_execution_error` | — | 도구 실행 예외 | 에이전트에 에러 전달 |
| `aborted` | — | 사용자/시스템 취소 | 정리 후 종료 |
| `max_steps_reached` | — | step 상한 도달 | continuation 또는 종료 |
| `generic_error` | — | 기타 | 에러 보고 |

`billing_error`와 `rate_limited`의 구분이 중요하다.
둘 다 429지만, "insufficient balance", "credits exhausted" 같은 키워드가 있으면 `billing_error`로 분류된다.
`billing_error`는 일시적이지 않으므로 대기 후 재시도가 의미 없다.

### 6.6 세션 내 인증 갱신

실행 중 401이 발생하면:

1. `onAuthRefresh()`로 토큰 갱신
2. 성공 시 `onModelRefresh()`로 모델 인스턴스 교체
3. 실패 시 `onAccountSwitch()`로 다음 provider account 시도
4. 이것도 실패하면 error 반환

---

## 7. 보안 / 안전 설계

공개 코드에서 확인 가능한 안전장치는 아래와 같다.

- **경로 안전성 검사**: `findTaskWorktree()` / `findTerminalWorktree()`에서 path traversal 방지
- **작업 경로 격리**: 구현과 QA를 worktree에서 실행해 main working tree 오염을 줄임
- **bash denylist + validator**: 파괴적/system-level 명령 차단
- **write-path containment**: spec agent 등은 허용된 디렉토리 밖으로 쓰기 불가
- **human review gate**: `plan_review`, `human_review`가 XState에 명시적으로 존재
- **이미지 피드백 검증**: MIME type, filename, resolved path 검사 후 저장
- **git env isolation**: worktree 정리/merge 시 git 환경변수 누수 방지
- **원자적 파일 쓰기**: `atomic-file.ts`, `writeFileAtomicSync`, retry writer 사용
- **JSON repair / validation**: malformed JSON 자동 수리 및 schema validation

---

## 8. 환경변수 우선순위

worker 프로세스 생성 시 환경변수는 다층 우선순위로 해석된다.

1. worker 직렬화 config
2. 활성 provider/profile 환경변수
3. OAuth 모드 정리 변수
4. profile별 환경변수
5. Python 관련 환경
6. `.env`
7. `process.env`
8. 기본값 / 시스템 환경

이 우선순위는 멀티 계정과 파일 기반 OAuth를 섞어 쓰는 환경에서 충돌을 줄이는 역할을 한다.

---

## 9. 부가 시스템

### 9.1 메모리 시스템 (libSQL 기반)

`ai/memory/`는 **libSQL(Turso)** 위에 구축된 자체 knowledge graph 시스템이다.
단순한 key-value 저장이 아니라 16종의 메모리 타입, 관계 그래프, 다채널 검색을 갖추고 있다.

**메모리 타입 (16종):**

| 범주 | 타입 |
|---|---|
| 핵심 인사이트 | `gotcha`, `decision`, `preference`, `pattern`, `requirement`, `error_pattern`, `module_insight` |
| 실행 최적화 | `prefetch_pattern`, `work_state`, `causal_dependency`, `task_calibration` |
| 전문 추적 | `e2e_observation`, `dead_end`, `work_unit_outcome`, `workflow_recipe`, `context_cost` |

**검색 파이프라인:**

- BM25 full-text search (`memories_fts` 테이블)
- 1024차원 semantic embedding 검색 (`memory_embeddings` 테이블)
- query classifier → HyDE 확장 → dense/sparse 검색 → RRF fusion → reranker → context packer

**메모리 관계:**

메모리 간 관계를 `required_with`, `conflicts_with`, `validates`, `supersedes`, `derived_from` 타입으로 연결하며, 각 관계에 confidence score가 붙는다.

**운영 메커니즘:**

- **Observer**: 세션 이벤트를 감시해 메모리를 자동 추출 (scratchpad → trust gate → promotion)
- **Dead-end detector**: 비생산적 경로를 감지해 `dead_end` 메모리로 기록
- **Decay half-life**: 오래된 메모리의 신뢰도를 시간에 따라 감쇄
- **Injection**: `runAgentSession()`의 `prepareStep` 콜백으로 스텝 사이에 검색된 메모리를 주입
- **Scope**: `global`, `module`, `work_unit`, `session` 단위로 메모리 유효 범위를 구분
- **Source tracking**: 메모리 출처를 `agent_explicit`, `observer_inferred`, `qa_auto`, `mcp_auto`, `commit_auto`, `user_taught`로 분류

### 9.2 Semantic Merge 시스템

`ai/merge/`는 멀티 task worktree에서 main으로 변경 사항을 통합할 때 사용되는 **intent-aware semantic merge** 시스템이다.

**병합 파이프라인:**

1. `file-evolution.ts`가 baseline과 각 task 버전의 파일 변경 이력을 로드한다.
2. `semantic-analyzer.ts`가 변경 의도를 35+ 변경 타입으로 분류한다.
3. `conflict-detector.ts`가 겹치는 변경 영역을 식별한다.
4. `auto-merger.ts`가 호환 가능한 변경에 대해 deterministic 전략을 적용한다.
5. 모호한 충돌은 `merge_resolver` 에이전트를 호출해 AI가 해결한다.
6. `orchestrator.ts`가 전체 병합 보고서를 생성한다.

**변경 타입 (35+):**

import 추가/제거/수정, 함수 추가/제거/수정/이름변경, React hook/JSX 조작, 변수/상수/클래스/메서드/속성 추가/수정, TypeScript 타입/인터페이스 추가/수정, Python decorator 추가/제거, 코멘트 추가/수정, 포매팅 전용 변경 등

**병합 전략:**

| 전략 | 적용 대상 |
|---|---|
| `COMBINE_IMPORTS` | import 문 통합 |
| `HOOKS_FIRST`, `HOOKS_THEN_WRAP` | React hook + JSX 래핑 |
| `APPEND_FUNCTIONS`, `APPEND_METHODS` | 함수/메서드 추가 |
| `COMBINE_PROPS` | JSX prop 통합 |
| `ORDER_BY_DEPENDENCY` | 의존 관계 기반 정렬 |
| `AI_REQUIRED` | AI 해결 필요 |
| `HUMAN_REQUIRED` | 사람 확인 필요 |

**충돌 심각도:** `NONE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

**병합 보고서:**

```text
tasksMerged, filesProcessed, filesAutoMerged, filesAiMerged,
filesNeedReview, conflictsDetected, conflictsAutoResolved, conflictsAiResolved
```

### 9.3 MCP 클라이언트

`ai/mcp/`는 agent type별로 필요한 MCP server를 연결한다.
`mcp-handlers.ts`는 health check, server 등록, 설정 관리 같은 IPC를 제공한다.

### 9.4 Roadmap / Ideation queue

`AgentQueueManager`는 roadmap와 ideation을 위한 별도 runner 계층이다.

- progress를 파일과 이벤트로 persist
- abort controller 기반 취소
- runner 출력(text delta, phase start/complete)을 UI에 중계

### 9.5 터미널 / PTY

`terminal/`은 PTY daemon과 session persistence를 갖춘 별도 서브시스템이다.
Electron main이 재시작돼도 터미널 세션을 살려 두는 방향으로 설계돼 있다.

### 9.6 외부 서비스 통합

GitHub, GitLab, Linear, changelog, insights, roadmap, ideation이 각각 독립 IPC 모듈과 러너를 가진다.
즉 Aperant는 task build app이면서 동시에 여러 AI utility feature를 품은 데스크톱 허브에 가깝다.

### 9.7 크로스 플랫폼 / i18n

`platform/` 계층이 shell detection, 실행 파일 탐색, OS별 차이를 숨기고, renderer는 `react-i18next` 기반 다국어 리소스를 사용한다.

---

## 10. Spec 디렉토리 구조

spec dir 내용은 complexity tier와 실행 경로에 따라 조금씩 달라지지만, 대표적인 산출물은 아래와 같다.

```text
.auto-claude/specs/001-feature-name/
├── spec.md
├── requirements.json
├── context.json
├── project_index.json
├── complexity_assessment.json
├── research.json
├── implementation_plan.json
├── qa_report.md
├── QA_FIX_REQUEST.md
└── metadata.json
```

`project_index.json`, `complexity_assessment.json`, `research.json`은 항상 생기는 파일이 아니라 spec pipeline의 complexity/path에 따라 달라진다.

---

## 11. 장점과 트레이드오프

| 관점 | 장점 | 트레이드오프 |
|---|---|---|
| 상태 일관성 | XState + plan file persistence로 UI/worker/file 상태를 맞추기 쉽다 | 상태 원천이 여러 층(XState, execution phase, plan file)이라 디버깅 진입 비용이 높다 |
| spec 파이프라인 | complexity에 따라 빠른 경로와 정밀 경로를 나눌 수 있다 | phase 수가 많아질수록 spec 생성 흐름을 추적하기 어렵다 |
| 개발 안전성 | worktree 격리, merge/discard 핸들러, path safety로 main 오염을 줄인다 | merge 이후 cleanup은 handler와 사용자 선택에 따라 달라져 운영 규칙 이해가 필요하다 |
| 확장성 | 11개 provider, phase별 모델 선택, MCP 조합으로 확장성이 높다 | provider/account 조합이 늘수록 테스트 매트릭스가 커진다 |
| 복원력 | auto-swap, startup recovery, pause/resume, stale exit guard가 있다 | 상태 복원 로직이 복잡해 edge case 검증 부담이 커진다 |
| 도구 보안 | denylist, validator, write-path containment이 결합돼 있다 | allow-by-default bash 모델이라 새 위험 패턴이 나오면 validator/denylist 갱신이 필요하다 |

---

## 12. 핵심 상수 / 임계값

| 상수 | 값 | 용도 |
|---|---|---|
| `DEFAULT_MAX_STEPS` | 500 | 에이전트 step 기본 상한 |
| `MAX_AUTH_RETRIES` | 1 | 401 인증 재시도 횟수 |
| `MAX_PLANNING_VALIDATION_RETRIES` | 3 | planning schema 검증 재시도 |
| `MAX_SUBTASK_RETRIES` | 3 | subtask별 실패 재시도 |
| `MAX_QA_ITERATIONS` | 50 | QA review/fix 루프 상한 |
| `MAX_CONSECUTIVE_ERRORS` | 3 | QA escalation 트리거 |
| `RECURRING_ISSUE_THRESHOLD` | 3 | 반복 이슈 escalation 트리거 |
| `DEFAULT_MAX_CONCURRENCY` | 3 | 병렬 subtask 동시 실행 수 |
| `CONTEXT_WINDOW_THRESHOLD` | 85% | 컨텍스트 윈도우 경고 |
| `CONTEXT_WINDOW_ABORT_THRESHOLD` | 90% | 컨텍스트 윈도우 중단/continuation |
| `CONVERGENCE_NUDGE` | 75% steps | 마무리 유도 시점 |
| `RATE_LIMIT_BASE_DELAY_MS` | 30,000 | rate limit 대기 기본값 |
| `RATE_LIMIT_MAX_DELAY_MS` | 300,000 | rate limit 대기 최대값 |
| `AUTO_CONTINUE_DELAY_MS` | 3,000 | orchestrator 자동 진행 딜레이 |
| `ERROR_RETRY_DELAY_MS` | 5,000 | 에러 재시도 딜레이 |
| `STREAM_INACTIVITY_TIMEOUT_MS` | 60,000 | 스트림 비활성 타임아웃 |
| `POST_STREAM_TIMEOUT_MS` | 10,000 | 스트림 후 promise 타임아웃 |

---

## 13. 요약

Aperant의 실행 플로우는 단순한 "프롬프트 실행기"가 아니라,
**(1) IPC + XState 상태기계, (2) complexity-adaptive 오케스트레이션, (3) 격리된 git 작업공간, (4) 멀티 프로바이더 인증/모델 추상화, (5) 자동 복원과 pause/resume, (6) human review gate**
를 결합한 구조다.

특히 중요한 점은 다음 세 가지다.

1. **상태를 파일만으로 보지 않는다.** `taskStateManager`, phase protocol, plan persistence가 함께 돌아간다.
2. **spec와 build의 흐름이 다르다.** spec는 complexity-first, build는 planning/coding/QA 중심이다.
3. **worktree는 단순 생성으로 끝나지 않는다.** merge, reject, discard, cleanup confirmation까지 후속 핸들러가 이어진다.

즉 Aperant는 "코드를 자동으로 써 주는 데스크톱 앱"이라기보다,
에이전트 실행을 실제 운영 가능한 형태로 만들기 위해 상태기계, review gate, worktree, provider queue를 함께 묶은 실행 시스템에 가깝다.
