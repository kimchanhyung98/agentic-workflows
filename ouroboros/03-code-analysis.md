# Ouroboros 코드 심층 분석

> 6개 전문 에이전트(아키텍트, 통합 전문가, 리서처, 평가 전문가, UX 전문가, 요구사항 분석가)의 병렬 분석을 종합한 문서입니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [핵심 도메인 모델](#2-핵심-도메인-모델)
3. [6단계 워크플로우 엔진](#3-6단계-워크플로우-엔진)
4. [오케스트레이터](#4-오케스트레이터)
5. [MCP 시스템](#5-mcp-시스템)
6. [플러그인 시스템](#6-플러그인-시스템)
7. [프로바이더 시스템](#7-프로바이더-시스템)
8. [사용자 인터페이스](#8-사용자-인터페이스)
9. [생태계 비교](#9-생태계-비교)
10. [아키텍처 평가](#10-아키텍처-평가)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 저장소 | [Q00/ouroboros](https://github.com/Q00/ouroboros) |
| 패키지 | `ouroboros-ai` (PyPI) |
| 언어 | Python 3.12+ (코어), Rust (네이티브 TUI) |
| 라이선스 | MIT |
| GitHub Stars | ~1,980 / Forks 182 |
| 최신 릴리스 | v0.27.0 (2026-04-01) |
| 소스 파일 | 622개 |

Ouroboros는 "뱀이 자신의 꼬리를 먹는" 신화에서 이름을 딴 **자기 진화형 AI 워크플로우 엔진**입니다. 단순히 코드를 생성하는 시스템이 아니라, 인터뷰를 통해 요구사항을 정제하고, 실행하고, 평가하고, 그 결과를 다음 세대의 입력으로 되돌리는 **폐쇄 진화 루프**를 구현합니다.

### 1.1 핵심 설계 원칙

1. **불변 시드(Immutable Seed)**: 한 번 생성된 시드는 수정 불가하며, 워크플로우의 "헌법(constitution)"으로 기능
2. **이벤트 소싱(Event Sourcing)**: 모든 상태 변화는 이벤트로 기록되며, 상태는 이벤트 재생으로 재구성
3. **Result 타입**: 예외 대신 `Result[T, E]` 타입으로 예상 가능한 실패를 명시적 처리

### 1.2 주요 의존성

| 패키지 | 목적 |
|---------|------|
| `typer` | CLI 프레임워크 |
| `rich` | 터미널 출력 |
| `structlog` | 구조화된 로깅 |
| `pydantic` | 데이터 검증 (frozen 모델) |
| `sqlalchemy[asyncio]` + `aiosqlite` | 이벤트 스토어 |
| `mcp` | Model Context Protocol |
| `textual` | Python TUI |
| `stamina` | 재시도 로직 |

---

## 2. 핵심 도메인 모델

### 2.1 Result 타입 (`core/types.py`)

Rust의 `Result` 타입을 Python 3.12 제네릭으로 구현. 시스템 전체에서 예외 대신 사용합니다.

```text
Result[T, E]
├── Result.ok(value)    → _is_ok = True
├── Result.err(error)   → _is_ok = False
├── .map(fn)            → Ok에만 fn 적용, Err 통과
├── .map_err(fn)        → Err에만 fn 적용
└── .and_then(fn)       → flatMap / 모나딕 바인드
```

### 2.2 Seed 모델 (`core/seed.py`)

`Pydantic BaseModel(frozen=True)`로 구현된 불변 워크플로우 사양서입니다.

```text
Seed (frozen=True)
├── [방향성 - 절대 불변]
│   ├── goal: str                           # 주요 목표
│   ├── task_type: str                      # 'code' | 'research' | 'analysis'
│   ├── constraints: tuple[str, ...]        # 하드 제약
│   └── acceptance_criteria: tuple[str, ...] # 성공 기준
├── [구조 - 세대 간 진화 가능]
│   └── ontology_schema: OntologySchema
│       ├── name, description
│       └── fields: tuple[OntologyField, ...]
├── [평가]
│   ├── evaluation_principles: tuple[EvaluationPrinciple, ...]
│   └── exit_conditions: tuple[ExitCondition, ...]
├── [브라운필드]
│   └── brownfield_context: BrownfieldContext
└── [메타데이터]
    └── metadata: SeedMetadata
        ├── seed_id, version, created_at
        ├── ambiguity_score: float
        └── parent_seed_id: str | None
```

### 2.3 AC 트리 (`core/ac_tree.py`)

수락 기준(Acceptance Criteria)의 계층적 분해를 관리하는 자료 구조입니다.

```text
ACNode (frozen dataclass)           ACTree (mutable dataclass)
├── id: str                         ├── root_id: str | None
├── content: str                    ├── nodes: dict[str, ACNode]
├── depth: int (0-5)                ├── max_depth: int = 5
├── parent_id: str | None           └── 메서드:
├── status: ACStatus                    ├── add_node()
│   ├── PENDING → ATOMIC               ├── update_node()
│   ├── DECOMPOSED → EXECUTING         ├── get_children()
│   └── COMPLETED / FAILED             ├── get_ancestors()
├── is_atomic: bool                     ├── get_atomic_nodes()
├── children_ids: tuple[str, ...]       └── can_decompose()
└── execution_id: str | None
```

`ACNode`는 불변 dataclass로, 상태 변경은 `with_status()`, `with_atomic()` 등의 메서드가 새 인스턴스를 반환합니다.

### 2.4 계보 추적 (`core/lineage.py`)

진화 루프에서 각 세대의 기록을 추적합니다.

```text
OntologyLineage (frozen Pydantic)
├── lineage_id, goal
├── status: ACTIVE / CONVERGED / EXHAUSTED / ABORTED
├── generations: tuple[GenerationRecord, ...]
│   └── GenerationRecord
│       ├── generation_number, seed_id
│       ├── ontology_snapshot: OntologySchema
│       ├── evaluation_summary: EvaluationSummary | None
│       ├── wonder_questions: tuple[str, ...]
│       └── phase: WONDERING / REFLECTING / SEEDING / EXECUTING / EVALUATING / COMPLETED / FAILED
└── rewind_history: tuple[RewindRecord, ...]

OntologyDelta
├── added_fields, removed_fields, modified_fields
└── similarity: float  # 가중 유사도 (0.5*이름 + 0.3*타입 + 0.2*정확 일치)
```

`OntologyLineage`는 직접 저장되지 않고, 항상 `LineageProjector`에 의해 이벤트 재생으로 재구성됩니다.

### 2.5 이벤트 소싱 (`events/base.py`, `persistence/`)

```text
BaseEvent (frozen=True Pydantic)
├── id: str (UUID4)
├── type: str ("domain.entity.verb_past_tense")
├── timestamp: datetime (UTC)
├── aggregate_type: str
├── aggregate_id: str
├── data: dict[str, Any]
└── consensus_id: str | None

EventStore (SQLAlchemy Core + aiosqlite)
└── events 테이블:
    ├── id, aggregate_type, aggregate_id
    ├── event_type, payload (JSON)
    ├── timestamp (UTC)
    └── 인덱스: ix_events_aggregate_type_id, ix_events_event_type
```

이벤트 네임스페이스: `interview.*`, `execution.*`, `evaluation.*`, `lineage.*`, `decomposition.*`, `orchestrator.*`

### 2.6 컨텍스트 관리 (`core/context.py`)

장기 실행 워크플로우를 위한 컨텍스트 관리. `MAX_TOKENS = 100,000` (NFR7), `MAX_AGE_HOURS = 6`.

- `WorkflowContext`: 가변, 히스토리 축적
- `FilteredContext` (frozen): 불변, 서브에이전트에 전달 → 메인 컨텍스트 오염 방지
- LLM 압축 실패 시 공격적 폴백 (상위 5개 사실만 유지, 최근 3개 히스토리 보존)

---

## 3. 6단계 워크플로우 엔진

### 3.1 Phase 0: Big Bang — 인터뷰 & 시드 생성

#### 소크라테스식 인터뷰 (`bigbang/interview.py`)

```text
사용자 입력 (초기 컨텍스트)
    │
    ▼
InterviewEngine.start_interview()
    ├── InputValidator.validate_initial_context()  # 보안 검증
    ├── detect_brownfield(cwd)                     # 브라운필드 자동 감지
    └── InterviewState 생성
    │
    ▼
[인터뷰 루프]
InterviewEngine.ask_next_question()
    ├── _select_perspectives() → 라운드별 페르소나 선택
    │   ├── 라운드 1-2: RESEARCHER + SIMPLIFIER + BREADTH_KEEPER
    │   ├── 라운드 3-5: + ARCHITECT
    │   └── 라운드 6+:  + SEED_CLOSER (RESEARCHER 제거)
    ├── _build_system_prompt() → 동적 프롬프트 조립 (최대 4,800자 하드캡)
    └── LLM 호출 → 질문 생성
    │
    ▼
AmbiguityScorer.score()
    ├── 그린필드 (3차원): Goal(40%) + Constraint(30%) + Success Criteria(30%)
    ├── 브라운필드 (4차원): Goal(35%) + Constraint(25%) + Success(25%) + Context(15%)
    ├── ambiguity = 1.0 - 가중평균(clarity scores)
    └── AMBIGUITY_THRESHOLD = 0.2
    │
    ▼ (ambiguity_score <= 0.2)
SeedGenerator.generate()
    ├── _extract_requirements() → LLM으로 구조화 추출 (파이프 구분자)
    ├── _parse_extraction_response() → dict 파싱
    └── _build_seed() → Seed 객체 조립 (frozen=True)
```

**핵심 설계 포인트**:
- 인터뷰 라운드 상한 없음 (사용자 제어, 최소 3라운드 권장)
- `decide-later` 항목은 모호성 점수에 영향 없음 (의도적 연기 존중)
- 데드락 복구: 완료되었으나 ambiguity > 0.2이면 `can_reopen` 허용
- 사용자 응답 최대 800자로 제한 (컨텍스트 폭발 방지)

#### PM 인터뷰 (`bigbang/pm_interview.py`)

`PMInterviewEngine`은 `InterviewEngine`을 **컴포지션** 패턴으로 감싸 PM 레이어를 추가합니다.

질문 분류기 (`bigbang/question_classifier.py`)가 3가지로 분류:

| 카테고리 | 처리 방식 |
|----------|-----------|
| PLANNING | 원문 그대로 PM에게 전달 |
| DEVELOPMENT | PM 친화적으로 재구성(REFRAMED) 또는 개발 단계 연기 |
| DECIDE_LATER | decide_later_items에 추가, 연기 선택권 제공 |

PM 인터뷰 완료 시 산출물:
- `~/.ouroboros/seeds/pm_seed_{id}.json`: 개발 인터뷰 핸드오프용 PM 시드
- `.ouroboros/pm.md`: 사람이 읽을 수 있는 제품 요구사항 문서

#### 브라운필드 분석 (`bigbang/brownfield.py`, `bigbang/explore.py`)

`CodebaseExplorer.explore()` 파이프라인:
1. 설정 파일 스캔 → 기술 스택 감지
2. 타입 정의 발견 → 언어별 정규식으로 struct/class/interface/enum 수집
3. 디렉토리 구조 분석 → 아키텍처 패턴 감지
4. LLM 요약 생성 (실패 시 텍스트 기반 폴백)

#### 온톨로지 관리 (`core/ontology_aspect.py`, `core/ontology_questions.py`)

5가지 존재론적 질문 유형 (ESSENCE, ROOT_CAUSE, PREREQUISITES, HIDDEN_ASSUMPTIONS, EXISTING_CONTEXT)을 기반으로 **AOP(Aspect-Oriented) 기반 온톨로지 위버** 구현:

```text
OntologicalAspect.execute(context, core_operation)
    ├── 캐시 확인 (5분 TTL, 최대 100 항목)
    ├── strategy.analyze(context) → AnalysisResult
    ├── is_valid=False + halt_on_violation=True → OntologicalViolationError
    └── core_operation(context) 실행
```

3개 조인 포인트: INTERVIEW (요구사항 명확화), RESILIENCE (정체 복구), CONSENSUS (결과 평가)

### 3.2 Phase 1: PAL 라우터 — 복잡도 기반 모델 선택

#### 복잡도 점수 계산 (`routing/complexity.py`)

```text
complexity_score =
    0.30 × min(token_count / 4000, 1.0)
  + 0.30 × min(tool_count / 5, 1.0)
  + 0.40 × min(ac_depth / 5, 1.0)     ← AC 중첩 깊이가 가장 높은 가중치
```

#### 3티어 라우팅 (`routing/tiers.py`, `routing/router.py`)

| 복잡도 | 티어 | 비용 배수 | 모델 예시 |
|--------|------|-----------|-----------|
| < 0.4 | FRUGAL | 1x | claude-3-5-haiku |
| 0.4~0.7 | STANDARD | 10x | claude-sonnet |
| ≥ 0.7 | FRONTIER | 30x | claude-opus |

`PALRouter`는 완전히 무상태(stateless)이며, 동일 입력이면 동일한 복잡도 점수와 티어 판정이 나온다. 다만 같은 티어 내 개별 모델은 부하 분산을 위해 `random.choice()`로 선택되므로, 최종 모델 선택까지 완전히 결정적이지는 않다.

#### 에스컬레이션 & 다운그레이드

- **에스컬레이션** (`routing/escalation.py`): 연속 실패 2회 → 다음 티어로. Frontier에서도 2회 실패 → `StagnationEvent` 발행
- **다운그레이드** (`routing/downgrade.py`): 연속 성공 5회 → 한 단계 하위 티어. Jaccard 유사도 ≥ 0.80인 패턴은 성공 티어 상속

### 3.3 Phase 2: 실행 — 더블 다이아몬드

#### 4단계 실행 사이클 (`execution/double_diamond.py`)

```text
AC (수락 기준)
    ▼
DISCOVER (발산) → "문제 공간 탐색: 어떤 도전/위험/가정이 있는가?"
    ▼
DEFINE (수렴)   → "인사이트 종합: 무엇이 가장 중요한가?" + 온톨로지 필터
    ▼
DESIGN (발산)   → "다수의 솔루션 옵션 생성: 창의적 대안 탐색"
    ▼
DELIVER (수렴)  → "최적 솔루션 선택 및 구현" + 온톨로지 필터
    ▼
CycleResult (성공/실패 + phase_results)
```

각 단계의 출력(`output_key`)이 다음 단계의 `previous_output`으로 자동 연결되는 선형 체인.

#### 서브에이전트 분리 (`execution/subagent.py`)

- 각 서브에이전트는 `FilteredContext`를 받아 메인 컨텍스트 오염 방지
- 완료 후 `validate_child_result()`로 구조적 검증
- 실패한 서브에이전트는 부모 실행을 중단시키지 않음

#### 의존성 기반 병렬 실행 (`execution/decomposition.py`)

Kahn 알고리즘을 사용한 위상 정렬로 AC 간 의존성 레벨 계산:

```text
레벨 0: [AC_1, AC_3]  ← 의존성 없음, 병렬 실행
레벨 1: [AC_2]        ← AC_1 완료 후 실행
레벨 2: [AC_4, AC_5]  ← AC_2 완료 후 실행
```

각 AC는 2-5개의 하위 AC로 분해 가능, 최대 깊이 5레벨 (NFR10).

### 3.4 Phase 3: 복원력 — 정체 감지 & 측면 사고

#### 4가지 정체 패턴 감지 (`resilience/stagnation.py`)

| 패턴 | 감지 방식 |
|------|-----------|
| SPINNING | 동일 출력 3회 이상 반복 (SHA-256 해시 비교) |
| OSCILLATION | A→B→A→B 교번 패턴 (최근 4개 출력 비교) |
| NO_DRIFT | drift_score 표준편차 < 0.01 |
| DIMINISHING_RETURNS | 선형 회귀 기울기 < 0 |

감지 시 → 이벤트 발행 → Wonder/Reflect로 측면 사고(lateral thinking) 유도

#### 5가지 페르소나 (`skills/unstuck/SKILL.md`)

| 페르소나 | 접근 방식 |
|---------|-----------|
| hacker | "먼저 작동하게, 우아함은 나중에" |
| researcher | "무슨 정보가 부족한가?" |
| simplifier | "범위를 줄여 MVP로" |
| architect | "접근 방식 자체를 재구성" |
| contrarian | "잘못된 문제를 풀고 있지 않은가?" |

### 3.5 Phase 4: 평가 — 3단계 파이프라인

#### Stage 1: 기계적 검증 (`evaluation/mechanical.py`) — 비용 $0

```text
MechanicalVerifier
├── LINT    → 코드 스타일 검사
├── BUILD   → 컴파일 검증
├── TEST    → 단위/통합 테스트
├── STATIC  → 정적 분석 (타입 검사)
└── COVERAGE → 커버리지 (임계값 70%, NFR9)
```

- 비동기 서브프로세스 실행 + 타임아웃 300초
- 언어 자동 감지 (`evaluation/languages.py`): 마커 파일로 언어별 프리셋 명령어 자동 할당
- **하나라도 실패 → 즉시 파이프라인 종료**

#### Stage 2: 의미 평가 (`evaluation/semantic.py`) — Standard 티어

LLM이 7개 필드를 JSON으로 반환:

| 필드 | 설명 |
|------|------|
| `score` (0.0~1.0) | 전체 품질 점수 |
| `ac_compliance` (bool) | AC 충족 여부 |
| `goal_alignment` (0.0~1.0) | 목표 정렬도 |
| `drift_score` (0.0~1.0) | 시드 의도 이탈도 |
| `uncertainty` (0.0~1.0) | 평가 신뢰도 (> 0.3이면 Stage 3 트리거) |
| `reward_hacking_risk` (0.0~1.0) | 평가 속이기 탐지 |
| `reasoning` | 평가 설명 |

통과 기준: `ac_compliance == True AND score >= 0.8`

#### Stage 3: 멀티모델 합의 (`evaluation/consensus.py`) — Frontier 티어, 조건부

**6가지 합의 트리거** (`evaluation/trigger.py`):
1. SEED_MODIFICATION: 불변 시드 변경
2. ONTOLOGY_EVOLUTION: 온톨로지 스키마 변경
3. GOAL_INTERPRETATION: 목표 재해석
4. SEED_DRIFT_ALERT: drift_score > 0.3
5. STAGE2_UNCERTAINTY: uncertainty > 0.3
6. LATERAL_THINKING_ADOPTION: 대안적 사고 채택

**기본 합의 모드 (ConsensusEvaluator)**:
- 멀티모델: 3개 모델 독립 투표 (`asyncio.gather` 병렬)
- 단일모델 폴백: ADVOCATE + DEVIL'S ADVOCATE + JUDGE 3관점
- 모두 **2/3 다수결** (majority_ratio >= 0.66)

**숙의 합의 모드 (DeliberativeConsensus)** — 2라운드:
- Round 1: Advocate(강점) + Devil's Advocate(근본 원인 분석) 병렬
- Round 2: Judge가 양 입장 종합 판결 (approved/rejected/conditional)

Devil's Advocate는 `DevilAdvocateStrategy` (`strategies/devil_advocate.py`)를 사용:
- ROOT_CAUSE: 근본 원인을 해결하는가?
- ESSENCE: 문제의 본질적 속성은 무엇인가?
- SHA256 캐싱으로 동일 아티팩트 중복 LLM 호출 방지

#### 드리프트 감지 (`observability/drift.py`)

PM 13.1 가중 공식:

```text
combined = (goal_drift × 0.5) + (constraint_drift × 0.3) + (ontology_drift × 0.2)
```

- Goal Drift: Jaccard 유사도 (`1 - |intersection| / |union|`)
- Constraint Drift: 위반 수 × 0.1 (최대 1.0)
- Ontology Drift: 사용 중인 개념과 시드 필드 간 Jaccard 거리
- **NFR5: combined > 0.3이면 허용 불가**

#### 검증 아티팩트 수집

- `ArtifactCollector` (`evaluation/artifact_collector.py`): Write/Edit 도구 호출 패턴을 파싱하여 실제 수정 파일 수집 (최대 30개, 파일당 50KB, 전체 150K자)
- `VerificationArtifacts` (`evaluation/verification_artifacts.py`): git status/diff, 기계적 검사 stdout/stderr를 `~/.ouroboros/artifacts/`에 저장
- `SpecVerifier` (`verification/verifier.py`): AC를 4계층 검증 티어(T1 상수→T2 구조→T3 행동→T4 주관)로 분류, T1/T2는 자동 검증

### 3.6 Phase 5: 진화 루프

#### 진화 루프 (`evolution/loop.py`)

```text
EvolutionaryLoop.run(initial_seed)
    │
    ▼  [세대 1: 인터뷰 → 시드 제공됨]
    ├── SEEDING → EXECUTING → EVALUATING → COMPLETED
    │
    ▼  [세대 2+: 자율 진화]
    ├── WONDERING  → WonderEngine: "우리가 아직 모르는 것은?"
    │                {questions, ontology_tensions, should_continue}
    ├── REFLECTING → ReflectEngine: "온톨로지를 어떻게 진화시킬까?"
    │                {refined_goal, refined_acs, ontology_mutations}
    ├── SEEDING    → 부모 Seed + mutations → 새 Seed
    ├── EXECUTING  → OrchestratorRunner.execute_seed()
    ├── EVALUATING → EvaluationPipeline.evaluate()
    └── COMPLETED  → OntologyDelta.compute + 수렴 확인
```

- SIGINT 핸들러: 첫 번째 Ctrl+C → 현재 세대 완료 후 우아한 종료, 두 번째 → 강제 종료
- 각 `evolve_step()`은 완전히 무상태 (매번 이벤트 재생으로 상태 재구성)

#### WonderEngine (`evolution/wonder.py`)

소크라테스식 질문법으로 아직 검증되지 않은 가정을 탐색합니다.

- **SCOPE GUARD**: 시드 목표 범위 밖 질문 생성 차단
- 불완전한 온톨로지는 정상 → 그 자체가 갭이 아님
- LLM 실패 시 `_degraded_output()`: 평가/드리프트 점수 기반 휴리스틱 폴백 질문
- 회귀 탐지 시 `## REGRESSIONS` 섹션 추가

#### ReflectEngine (`evolution/reflect.py`)

"우로보로스가 자신의 꼬리를 먹는" 단계. 출력:
- `ontology_mutations`: add/modify/remove 액션 목록
- 연속 1세대 이상 변경 없으면 `## WARNING: STAGNATION DETECTED` 메시지로 LLM 강제 자극

#### 수렴 판단 (`evolution/convergence.py`) — 5가지 신호

| 신호 | 조건 | 비고 |
|------|------|------|
| 온톨로지 안정 | `similarity >= 0.95` | Eval/Regression/Evolution/Validation 게이트 통과 필요 |
| 정체 | 3세대 연속 similarity >= 0.95 | stagnation_window 설정 가능 |
| 진동 | A→B→A→B 패턴 | sim(Oₙ, Oₙ₋₂) >= 0.95 AND sim(Oₙ₋₁, Oₙ₋₃) >= 0.95 |
| 반복 피드백 | Wonder 질문 70% 이상 겹침 | 이전 3세대와 비교 |
| 소진 | `generation >= max_generations (30)` | 강제 종료 |

**Evolution Gate**: 온톨로지가 한 번도 실제 변경된 적 없으면 수렴 거부 (Wonder/Reflect 오류로 간주)

#### 회귀 감지 (`evolution/regression.py`)

이전에 통과했지만 현재 실패 중인 AC를 `ACRegression`으로 기록. "한 번도 통과하지 않은 AC"는 회귀가 아닌 "지속적 실패"로 구분.

---

## 4. 오케스트레이터

### 4.1 OrchestratorRunner (`orchestrator/runner.py`)

Seed를 받아 Claude Agent SDK를 통해 실제 실행하는 엔진:

```text
OrchestratorRunner.execute_seed(seed, execution_id)
    ├── ExecutionStrategy.get_strategy() → 태스크 유형별 전략
    ├── assemble_session_tool_catalog() → MCP 도구 조립
    ├── WorkflowStateTracker 초기화
    │
    ▼  [에이전트 실행 루프]
    async for message in runtime.stream():
        ├── project_runtime_message() → 정규화
        ├── WorkflowStateTracker.process_runtime_message()
        │   ├── [AC_START: N] 마커 감지 (정규표현식)
        │   └── [AC_COMPLETE: N] 마커 감지
        ├── create_progress_event() → EventStore 저장
        └── heartbeat_lock() → 워크트리 잠금 갱신
```

AC 추적은 마커 기반. 마커 없으면 자연어 패턴으로 휴리스틱 폴백.

### 4.2 LevelCoordinator (`orchestrator/coordinator.py`)

병렬 AC 실행 레벨 간 파일 충돌 감지/해결:
- 충돌 없을 때 → 비용 $0 (Claude 호출 없음)
- 충돌 있을 때만 → Claude 세션 실행 (도구: Read, Bash, Edit, Grep, Glob)

### 4.3 WorkflowState (`orchestrator/workflow_state.py`)

```text
WorkflowState
├── acceptance_criteria: list[AcceptanceCriterion]
├── current_phase: Phase (DISCOVER/DEFINE/DEVELOP/DELIVER, 다이어그램상 DESIGN ≡ DEVELOP)
├── activity: ActivityType (IDLE/EXPLORING/BUILDING/TESTING/DEBUGGING/...)
├── tool_activity_map: {"Read"→EXPLORING, "Edit"→BUILDING, "Bash"→TESTING, ...}
└── 비용 추정: $3/1M input + $15/1M output
```

### 4.4 세션 관리 (`orchestrator/session.py`)

세션은 완전히 이벤트 소싱으로 관리. `SessionRepository`가 `EventStore`에서 이벤트를 재생해 `SessionTracker`를 재구성하여 실행 중단 후 재개(resume) 가능.

---

## 5. MCP 시스템

### 5.1 MCP 서버

#### 프로토콜 (`mcp/server/protocol.py`)

3개의 Protocol 인터페이스: `ToolHandler`, `ResourceHandler`, `PromptHandler`

#### 어댑터 (`mcp/server/adapter.py`)

`MCPServerAdapter`는 FastMCP 위의 어댑터. `inspect.Signature`를 동적으로 합성하여 FastMCP의 `**kwargs` 래핑 버그를 우회.

#### 보안 레이어 (`mcp/server/security.py`) — 4단계 파이프라인

```text
SecurityLayer.check_request()
    1. Authenticator.authenticate()   → API_KEY (SHA-256), BEARER_TOKEN (HMAC-SHA256, 1시간 유효)
    2. RateLimiter.check()            → 토큰 버킷 알고리즘
    3. Authorizer.authorize()         → 도구별 READ/WRITE/EXECUTE/ADMIN 권한
    4. InputValidator.validate()      → 코드 인젝션/경로 순회/셸 메타문자 차단
```

### 5.2 MCP 클라이언트

- `MCPClientAdapter` (`mcp/client/adapter.py`): MCP SDK `ClientSession` 래핑, `stamina` 3회 지수 백오프 재시도
- `MCPClientManager` (`mcp/client/manager.py`): 다중 서버 연결 풀, 60초 간격 헬스 체크, 실패 시 자동 재연결

### 5.3 MCP 도구 — 21개 핸들러

| 카테고리 | 도구 | 역할 |
|---------|------|------|
| 실행 | `ouroboros_execute_seed` | 씨드 기반 작업 실행 (백그라운드) |
| 실행 | `ouroboros_start_execute_seed` | 비동기 실행 시작, job_id 즉시 반환 |
| 쿼리 | `ouroboros_session_status` | 세션 상태 조회 |
| 쿼리 | `ouroboros_query_events` | 이벤트 히스토리 조회 |
| 쿼리 | `ouroboros_ac_dashboard` | AC별 통과/실패 현황 |
| 저작 | `ouroboros_generate_seed` | 인터뷰 → 씨드 YAML 변환 |
| 저작 | `ouroboros_interview` | 요구사항 인터뷰 관리 |
| 저작 | `ouroboros_pm_interview` | PM 관점 인터뷰 |
| 평가 | `ouroboros_measure_drift` | 드리프트 측정 |
| 평가 | `ouroboros_evaluate` | 3단계 평가 파이프라인 |
| 평가 | `ouroboros_lateral_think` | 페르소나 기반 대안적 사고 |
| 진화 | `ouroboros_evolve_step` | 단일 세대 실행 |
| 진화 | `ouroboros_start_evolve_step` | 비동기 세대 실행 |
| 진화 | `ouroboros_evolve_rewind` | 특정 세대로 리와인드 |
| 진화 | `ouroboros_lineage_status` | 계보 상태 조회 |
| 잡 관리 | `ouroboros_job_status/wait/result` | 백그라운드 잡 관리 |
| 잡 관리 | `ouroboros_cancel_job/execution` | 잡/실행 취소 |
| 품질 | `ouroboros_qa` | 아티팩트 품질 검증 |
| 브라운필드 | `ouroboros_brownfield` | 기존 저장소 등록/관리 |

#### 핵심 실행 흐름 (ExecuteSeedHandler)

```text
handle(arguments)
    ├── 경로/내용 해석 + 보안 검증
    ├── 위임 컨텍스트 추출 (_ooo_parent_* 숨겨진 인수)
    ├── yaml.safe_load() → Seed.from_dict()
    ├── EventStore 초기화 + 워크트리 준비
    ├── asyncio.create_task(_run_in_background(...))  ← Fire-and-forget
    └── 즉시 반환: { session_id, execution_id, status="running" }
```

### 5.4 MCP 브리지

Ouroboros MCP 서버가 **다른 MCP 서버의 클라이언트 역할**을 하는 서버-간 연결 관리:

설정 파일 우선순위:
1. `$OUROBOROS_MCP_CONFIG` 환경 변수
2. `~/.ouroboros/mcp_servers.yaml`
3. `{cwd}/.ouroboros/mcp_servers.yaml`

---

## 6. 플러그인 시스템

### 6.1 스킬 레지스트리 (`plugin/skills/registry.py`)

`.claude-plugin/skills/*/SKILL.md`에서 YAML frontmatter + 섹션을 파싱하여 등록:

```text
SkillRegistry.discover_all()
    → glob("*/SKILL.md") 순회
    → _parse_skill_md(content)
    → _index_skill(name, metadata)
        ├── _trigger_index: keyword → set[skill_name]
        └── _prefix_index: prefix → set[skill_name]  ("ooo:{name}", "/ouroboros:{name}")
    → _start_watcher() → watchdog 파일 변경 감시 (핫 리로드)
```

#### 매직 키워드 감지 (`plugin/skills/keywords.py`)

3단계 우선순위:
1. 정확한 접두사 매칭 (confidence=1.0)
2. 자연어 트리거 키워드 매칭 (confidence=0.5~0.9)
3. 폴백 (매칭 없음)

### 6.2 에이전트 레지스트리 (`plugin/agents/registry.py`)

**내장 에이전트 4종**:

| 에이전트 | 역할 | 모델 | 도구 |
|---------|------|------|------|
| executor | EXECUTION | sonnet | Read, Write, Edit, Bash, Glob, Grep |
| planner | PLANNING | sonnet | Read, Glob, Grep |
| verifier | REVIEW | haiku | Read, Bash, Grep |
| analyst | ANALYSIS | haiku | Read, Glob, Grep |

커스텀 에이전트: `.claude-plugin/agents/*.md`에서 자동 발견, 역할 자동 추론, `compose_agent()`로 파생 가능.

### 6.3 에이전트 풀 (`plugin/agents/pool.py`)

```text
상태 머신: IDLE → BUSY → IDLE (성공) / FAILED → RECOVERING → IDLE

AgentPool
├── asyncio.PriorityQueue[tuple[int, TaskRequest]]  (음수 우선순위 = 최대 힙)
├── _task_dispatcher(): 큐 → 유휴 에이전트 배정
├── _scale_monitor(): 부하 기반 자동 확장 (max_instances까지)
└── _health_checker(): 실패 에이전트 복구, 타임아웃 작업 취소
```

### 6.4 오케스트레이션 라우터 (`plugin/orchestration/router.py`)

`ModelRouter` (PAL): 작업 복잡도 + 실패 이력 기반 모델 티어 선택
- 최근 실패 ≥ 2회 → 상위 티어 에스컬레이션
- `cost_optimization=True` → 한 단계 다운그레이드 시도
- 이력 프루닝: 해시당 최대 10개, 전체 최대 1000개

### 6.5 스케줄러 (`plugin/orchestration/scheduler.py`)

의존성 그래프 기반 병렬 실행 엔진:
- 위상 정렬 → 동일 레벨 `asyncio.gather` 병렬 실행
- 의존 작업 실패 시 하위 작업 SKIPPED 전파
- 기본 3회 재시도, 5초 대기

---

## 7. 프로바이더 시스템

### 7.1 LLMAdapter Protocol (`providers/base.py`)

```python
class LLMAdapter(Protocol):
    async def complete(
        messages: list[Message],
        config: CompletionConfig,
    ) -> Result[CompletionResponse, ProviderError]: ...
```

### 7.2 어댑터 비교

| 어댑터 | 백엔드 | 인증 | 특징 |
|--------|--------|------|------|
| `ClaudeCodeAdapter` | Claude Agent SDK | Max Plan (API 키 불필요) | 5회 재시도, JSON 파싱 3회 재시도 |
| `AnthropicAdapter` | Anthropic SDK | `ANTHROPIC_API_KEY` | 지연 초기화, 기본 claude-sonnet-4-6 |
| `LiteLLMAdapter` | LiteLLM | 다중 키 자동 탐색 | stamina 재시도, 응답 길이 검증 |
| `CodexCliAdapter` | Codex CLI 서브프로세스 | OpenAI API 키 | 중첩 깊이 5 제한, tempfile 프롬프트 전달 |

### 7.3 팩토리 (`providers/factory.py`)

| 입력 별칭 | 정규화 결과 |
|----------|-----------|
| `claude`, `claude_code` | `"claude_code"` |
| `codex`, `codex_cli` | `"codex"` |
| `litellm`, `openai`, `openrouter` | `"litellm"` |

---

## 8. 사용자 인터페이스

### 8.1 CLI 명령 체계 (`cli/main.py`)

```text
ouroboros
├── init [start|list]      — 인터뷰 시작/목록
├── run [workflow|resume]   — 워크플로우 실행/재개
├── config [show|backend|init|set|validate]
├── status [executions|execution|health]
├── cancel [execution]     — 대화형/직접/전체 취소
├── mcp [serve|info]       — MCP 서버 관리
├── setup [scan|list|default]  — 환경 설정
├── tui [monitor]          — TUI 대시보드
├── pm                     — PM 인터뷰
└── uninstall              — Ouroboros 제거
```

#### 실시간 워크플로우 디스플레이 (`cli/formatters/workflow_display.py`)

Rich `Live` 기반:
- Double Diamond 단계 표시기 (Discover > Define > Develop > Deliver)
- AC 목록 (○ pending, ⚡ in_progress, ✓ completed, ✗ failed)
- 활동 아이콘 (🔍 탐색, 🛠️ 빌드, 🧪 테스트, 🐛 디버그)
- 메시지 수 / 도구 호출 수 / 토큰 / 비용 하단 메트릭

### 8.2 Python TUI (Textual)

#### 단일 진실 공급원(SSOT) 패턴

```text
EventStore (SQLite) → 0.5초 폴링 → BaseEvent
    → create_message_from_event() → Textual Message
    → OuroborosTUI._update_state_from_event() → TUIState 갱신
    → _forward_to_dashboard() → 활성 화면에 전달
```

#### 화면 내비게이션

```text
SessionSelectorScreen → DashboardScreenV3 (기본)
    ├── [l] LogsScreen       — 실시간 로그
    ├── [d] DebugScreen      — 원시 이벤트 덤프
    ├── [2] ExecutionScreen   — 실행 단계별 상세
    ├── [e] LineageSelector → LineageDetailScreen
    └── [s] SessionSelectorScreen
```

#### DashboardScreenV3 레이아웃

```text
┌──────────────────────────────────────────────────────────────────┐
│  ◆ Discover → ○ Define → ○ Design → ○ Deliver    [2/5 AC] 1m23s│
├────────────────────────────┬─────────────────────────────────────┤
│  ╔══ AC EXECUTION TREE ══╗ │  ╔══ NODE DETAIL ══╗                │
│  ├─ ◐ AC1 (running)       │  │  ID: ac_1                        │
│  │  ├─ ● SubAC1 (done)    │  │  Status: EXECUTING               │
│  │  └─ ○ SubAC2 (wait)    │  │  Content: Process input...        │
│  ├─ ● AC3 (done)          │  │  [Thinking: ...]                  │
│  └─ ○ AC4                 │  │  [Tool History]                   │
├────────────────────────────┴─────────────────────────────────────┤
│  LIVE  AC1 Read: src/main.py  │  AC3 Write: output.txt           │
└──────────────────────────────────────────────────────────────────┘
```

### 8.3 Rust TUI (`crates/ouroboros-tui/`)

SuperLightTUI 프레임워크, Rose Pine 테마, 동일 SQLite DB 공유:
- 4개 탭: Dashboard, Execution, Lineage, Sessions
- 30프레임마다 DB 폴링
- 드리프트 스파크라인 시각화
- `Ctrl+P` 명령 팔레트

### 8.4 Claude Code 스킬 체계

| 스킬 | 별칭 | 핵심 기능 |
|------|------|-----------|
| `/ouroboros:run` | execute | MCP 백그라운드 실행 + 롱폴링 모니터링 |
| `/ouroboros:interview` | socratic | 3경로 라우팅 (코드/인간/혼합) + 변증법적 리듬 가드 |
| `/ouroboros:setup` | - | 6단계 온보딩 마법사 |
| `/ouroboros:ralph` | - | QA 통과까지 무한 반복 루프 |
| `/ouroboros:unstuck` | stuck, lateral | 5가지 페르소나 교착 탈출 |
| `/ouroboros:evolve` | - | 진화 루프 단일 세대 |
| `/ouroboros:evaluate` | eval | 3단계 평가 파이프라인 |
| `/ouroboros:status` | drift | 세션 상태 + 드리프트 확인 |
| `/ouroboros:cancel` | kill, abort | 실행 취소 |
| `/ouroboros:seed` | crystallize | 인터뷰 → 시드 생성 |

**인터뷰 스킬의 변증법적 리듬 가드**: PATH 1 (코드 확인) 답변이 연속 3회 이상이면 강제로 PATH 2 (인간 판단)로 전환 → 코드베이스 스캔이 아닌 인간 대화 보장.

---

## 9. 생태계 비교

### 9.1 Ouroboros의 고유성

| 특징 | Ouroboros | Kiro/Spec Kit/BMAD |
|------|-----------|-------------------|
| 명세 생성 | AI 주도 소크라테스 인터뷰 | 사용자가 직접 작성 |
| 준비도 판단 | 정량적 ambiguity ≤ 0.2 게이트 | 주관적 판단 |
| 진화 루프 | 온톨로지 similarity ≥ 0.95 수렴 | 선형 워크플로우 |
| 비용 최적화 | PAL 3티어 (Frugal 1x → Frontier 30x) | 단일 모델 |
| 평가 파이프라인 | Mechanical($0) → Semantic → Consensus | 수동 리뷰 |
| MCP 통합 | 양방향 (서버 + 클라이언트) | 단방향 소비 |
| 런타임 추상화 | Claude Code / Codex CLI 어댑터 | 특정 런타임 고정 |

### 9.2 경쟁 도구 비교

| 도구 | 접근 방식 | 차별점 |
|------|-----------|--------|
| Devin | 자율 AI 엔진니어 | 자체 실행 환경 내장, 상용 서비스 |
| OpenHands | 오픈소스 AI 에이전트 | Docker 샌드박스, 범용 코딩 |
| SWE-agent | 학술 연구 기반 | GitHub 이슈 해결 특화, 벤치마크 중심 |
| Aider | 채팅 기반 코딩 | 가벼움, git 통합, 단일 파일 편집 |
| **Ouroboros** | **명세 우선 하네스** | **인터뷰→명세→실행→평가→진화 폐쇄 루프** |

---

## 10. 아키텍처 평가

### 10.1 강점

**철저한 불변성 설계**: Seed의 `frozen=True`는 워크플로우 중 요구사항 드리프트를 원천 차단. ACNode의 `with_*()` 메서드로 상태 변경 시 새 인스턴스 생성 → 동시성 안전 + 히스토리 추적 단순화.

**이벤트 소싱으로 완전한 재현성**: 실행 중단 후 정확한 시점부터 재개 가능. `WorkflowStateTracker.replay_progress_events()`와 `SessionRepository.reconstruct_session()`이 뒷받침.

**비용 최적화 설계**: 평가 파이프라인의 단계별 조기 종료, `LevelCoordinator`의 충돌 없을 때 $0 비용, Stage 1 완전 자동화로 LLM 호출 비용 최소화.

**자기 수정 진화 루프**: Wonder → Reflect → Seed 진화 사이클이 평가 결과를 자동으로 다음 세대 입력으로 변환. 인간 개입 없이 온톨로지를 개선하는 구조는 핵심 차별점.

**깊이 있는 방어(Defense in Depth)**: MCP 보안의 4단계 파이프라인 (인증→레이트 제한→인가→입력 검증), 재귀적 문자열 탐색으로 중첩 JSON도 검사.

### 10.2 주의 사항

**AC 트리 순환 감지의 단순성**: `is_cyclic()`이 부모-자식 텍스트 완전 일치만 확인. 의미적으로 동일한 분해는 감지 불가 → 임베딩 기반 유사도 검사가 필요할 수 있음.

**컨텍스트 압축의 공격적 폴백**: LLM 압축 실패 시 히스토리 전체를 버리고 상위 5개 사실만 유지 → 장기 실행에서 중요 컨텍스트 손실 위험.

**보안 약점**: `_authenticate_api_key()`에서 `hmac.compare_digest` 대신 `in` 연산자 사용 → 타이밍 공격에 이론적 취약. 위험 패턴 목록이 정적이며 업데이트 메커니즘 없음.

**단일 테이블 이벤트 저장**: 모든 이벤트가 `events` 단일 테이블 → 장기 실행 시 파티셔닝/아카이빙 전략 필요.

**스킬 실행기 미완성**: `SkillExecutor._execute_skill_impl()`의 실제 실행 부분이 TODO 상태. 현재는 SKILL.md 지침 텍스트를 그대로 반환.

**추출 형식 취약성**: 시드 생성의 파이프(`|`)/콜론(`:`) 구분자 방식은 데이터에 해당 문자 포함 시 파싱 불안정 → 1회 retry로 보완하나 근본 해결은 아님.

### 10.3 설계 패턴 요약

| 패턴 | 적용 위치 | 효과 |
|------|-----------|------|
| Event Sourcing | 전체 시스템 | 재현성, 재개, 감사 추적 |
| Result Monad | 전체 오류 처리 | 명시적 실패 전파 |
| Immutable Objects | Seed, ACNode, Events | 동시성 안전, 히스토리 추적 |
| Strategy Pattern | ExecutionStrategy, DevilAdvocateStrategy | 확장 가능한 실행/평가 |
| Composition over Inheritance | PMInterviewEngine | 레이어 추가 용이 |
| AOP (Aspect-Oriented) | OntologicalAspect | 횡단 관심사 분리 |
| Protocol (Structural Typing) | LLMAdapter, ToolHandler | 느슨한 결합 |
| Fire-and-Forget | ExecuteSeedHandler | MCP 타임아웃 우회 |
| Token Bucket | RateLimiter | 버스트 허용 레이트 제한 |

---

## 참고 자료

- [저장소](https://github.com/Q00/ouroboros)
- [Architecture 문서](https://github.com/Q00/ouroboros/blob/main/docs/architecture.md)
- [Getting Started](https://github.com/Q00/ouroboros/blob/main/docs/getting-started.md)
- [PyPI - ouroboros-ai](https://pypi.org/project/ouroboros-ai/)
- [project-context.md](https://github.com/Q00/ouroboros/blob/main/project-context.md)
