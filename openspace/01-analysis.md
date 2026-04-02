# OpenSpace 코드 기반 심층 분석

> **분석 대상**: [HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace) (commit `f055148`)
> **분석 방법**: 151개 Python 소스 파일 전수 코드 리딩 + 웹 리서치
> **기준일**: 2026-04-02

---

## 목차

1. [개요](#1-개요)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [엔트리포인트 분석](#3-엔트리포인트-분석)
4. [Agent Runtime 계층](#4-agent-runtime-계층)
5. [LLM Client 계층](#5-llm-client-계층)
6. [Backend Provider 계층](#6-backend-provider-계층)
7. [Skill Engine 계층](#7-skill-engine-계층)
8. [Quality Tracking 시스템](#8-quality-tracking-시스템)
9. [MCP 통합 계층](#9-mcp-통합-계층)
10. [Cloud Skill Community](#10-cloud-skill-community)
11. [벤치마크 및 평가 시스템](#11-벤치마크-및-평가-시스템)
12. [설정 시스템](#12-설정-시스템)
13. [보안 아키텍처](#13-보안-아키텍처)
14. [설계 패턴 및 코드 품질](#14-설계-패턴-및-코드-품질)
15. [종합 평가](#15-종합-평가)

---

## 1. 개요

OpenSpace는 "에이전트가 작업을 수행한 뒤, 그 실행 경험 자체를 다음 작업에 반영하도록 구조화"한 **자기 진화형 에이전트 런타임**이다.

### 핵심 문제 정의

1. 반복 작업에서 동일한 시행착오가 재발
2. 성공 패턴이 다음 작업으로 충분히 전이되지 않음
3. 도구/환경 변화로 기존 프롬프트·스킬이 쉽게 노후화

### 해결 전략

| 전략           | 구현                                                      |
|--------------|---------------------------------------------------------|
| Skill 중심 재사용 | SKILL.md 파일 기반, YAML frontmatter + Markdown 본문          |
| 지속 진화        | FIX / DERIVED / CAPTURED 3모드 자동화                        |
| 품질 계측 기반 트리거 | Post-Execution, Tool Degradation, Metric Monitor 3중 트리거 |
| 호스트 에이전트 부착형 | MCP 서버 + host_skills로 기존 에이전트 확장                        |

### 기술 스택

- **언어**: Python 3.12+
- **LLM 통합**: litellm (>=1.70.0, <1.82.7)
- **프로토콜**: MCP (Model Context Protocol), JSON-RPC 2.0
- **저장소**: SQLite WAL 모드
- **프론트엔드**: React 18 + Vite 6 + Tailwind CSS

---

## 2. 프로젝트 구조

```
OpenSpace/
├── pyproject.toml              # 빌드 설정 + 6개 콘솔 엔트리포인트
├── openspace/
│   ├── __init__.py             # Lazy import (__getattr__)
│   ├── __main__.py             # CLI 진입점 (openspace)
│   ├── mcp_server.py           # MCP 서버 진입점 (openspace-mcp)
│   ├── dashboard_server.py     # Dashboard API 서버 (Flask, 포트 7788)
│   ├── tool_layer.py           # 최상위 오케스트레이터 (OpenSpace 클래스)
│   ├── agents/
│   │   ├── base.py             # BaseAgent (ABC) + AgentRegistry
│   │   └── grounding_agent.py  # GroundingAgent (핵심 실행 에이전트)
│   ├── llm/
│   │   └── client.py           # LLMClient (litellm 래퍼)
│   ├── config/
│   │   ├── constants.py        # 상수 정의
│   │   ├── grounding.py        # Pydantic 설정 모델
│   │   ├── loader.py           # JSON 설정 로더 + 싱글턴
│   │   └── utils.py            # 유틸리티
│   ├── grounding/
│   │   ├── core/               # 추상 기반 (Provider, Session, Tool, Security)
│   │   └── backends/           # Shell, GUI, MCP, Web 구현
│   ├── skill_engine/           # 진화 엔진 (Registry, Ranker, Analyzer, Evolver, Store)
│   ├── recording/              # 실행 기록 (JSONL 기반)
│   ├── cloud/                  # 클라우드 스킬 공유
│   ├── host_detection/         # 호스트 에이전트 자동감지
│   ├── prompts/                # 시스템 프롬프트 빌더
│   ├── platforms/              # OS별 스크린샷/녹화
│   ├── local_server/           # Flask 기반 로컬 서버
│   └── utils/                  # 로깅, UI, 텔레메트리
├── frontend/                   # Dashboard 프론트엔드
├── gdpval_bench/               # 벤치마크 스위트
└── showcase/                   # 예제 프로젝트 + 스킬
```

### 모듈 의존성 흐름

```
__main__.py / mcp_server.py
       │
       ▼
  tool_layer.py (OpenSpace)
       │
   ┌───┼───────────────────┐
   ▼   ▼                   ▼
LLMClient  GroundingClient  SkillEngine
              │                │
        ┌─────┼─────┐    ┌────┼────┐
        ▼     ▼     ▼    ▼    ▼    ▼
      Shell  GUI   MCP  Registry Store Evolver
      Prov   Prov  Prov    │
        │     │     │      ▼
        ▼     ▼     ▼   Analyzer
      Session Session Session
        │     │     │
        ▼     ▼     ▼
      Connector  Connector  Connector
```

---

## 3. 엔트리포인트 분석

### 3.1 CLI (`openspace/__main__.py`)

```
엔트리포인트: openspace = "openspace.__main__:run_main"
```

실행 흐름:

1. `argparse`로 CLI 인자 파싱 (모델, 설정, max-iterations, UI 옵션)
2. `refresh-cache` 서브커맨드: MCP 서버별 도구 캐시 갱신
3. `_load_config()`: 호스트 감지 → LLM 자격증명 해석 → `OpenSpaceConfig` 생성
4. `_initialize_openspace()`: `OpenSpace` 인스턴스 생성/초기화
5. 단일 쿼리 모드(`--query`) 또는 대화형 모드 진입

`UIManager`가 라이브 디스플레이와 로그 억제를 관리하며, 실시간 시각화 중에는 로그 레벨을 `CRITICAL`로 올려 터미널 출력 충돌을 방지한다.

### 3.2 MCP 서버 (`openspace/mcp_server.py`)

```
엔트리포인트: openspace-mcp = "openspace.mcp_server:run_mcp_server"
```

FastMCP 기반, stdio(기본) / SSE 두 가지 전송 모드 지원.

**노출 도구 4개:**

| 도구              | 용도                 | 주요 파라미터                                         |
|-----------------|--------------------|-------------------------------------------------|
| `execute_task`  | 전체 그라운딩 엔진으로 작업 실행 | task, workspace_dir, max_iterations, skill_dirs |
| `search_skills` | 로컬 + 클라우드 스킬 검색    | query, source, limit, auto_import               |
| `fix_skill`     | 스킬 수동 수정 (FIX만)    | skill_dir, direction                            |
| `upload_skill`  | 스킬 클라우드 업로드        | skill_dir, visibility, tags                     |

`_MCPSafeStdout`: text 출력을 stderr로, binary(`.buffer`)를 실제 stdout으로 라우팅. stdio 전송 시 JSON-RPC 메시지 오염을 방지한다.

### 3.3 Dashboard 서버 (`openspace/dashboard_server.py`)

```
엔트리포인트: openspace-dashboard = "openspace.dashboard_server:main" (포트 7788)
```

Flask REST API로 프론트엔드에 스킬 목록/상세/계보 그래프, 워크플로우 타임라인, 6단계 파이프라인 시각화를 제공한다.

---

## 4. Agent Runtime 계층

### 4.1 BaseAgent (`agents/base.py`)

- `AgentRegistry`: 클래스 수준 딕셔너리로 에이전트 자동 등록
- `response_to_dict()`: LLM 응답에서 JSON을 방어적으로 추출 (코드펜스 제거, `raw_decode()`로 partial JSON 추출)
- `AgentStatus`: 문자열 상수 클래스 (Enum 미사용 — 경량화)

### 4.2 GroundingAgent (`agents/grounding_agent.py`)

핵심 실행 흐름 (`process()` 메서드):

```
1. 워크스페이스 기존 파일 확인
2. 사용 가능 도구 검색 (SearchCoordinator)
3. 초기 메시지 구성

4. 반복 루프 (max_iterations):
   a. 2회차부터 스킬 컨텍스트 제거 (토큰 절약)
   b. 2회차부터 개별 메시지 크기 캡핑 (30,000자)
   c. 5회차부터 메시지 히스토리 트렁케이션 (120K 토큰 기준)
   d. LLM 호출
   e. 도구 호출 결과 수집
   f. 연속 빈 응답 5회 → 종료
   g. <COMPLETE> 토큰 → 완료
   h. 미완료 시 [INTERNAL ORCHESTRATION NOTE] 주입

5. 최종 결과 빌드
```

핵심 메커니즘:

| 메커니즘       | 설명                                                          |
|------------|-------------------------------------------------------------|
| 스킬 컨텍스트 주입 | 1회차에서만 시스템 프롬프트에 스킬 가이드 삽입, 2회차부터 제거                        |
| 메시지 캡핑     | `_MAX_SINGLE_CONTENT_CHARS = 30,000`자. 대형 도구 결과의 컨텍스트 지배 방지 |
| 트렁케이션      | 시스템 메시지 + 최초 사용자 지시 + 최근 8라운드만 유지                           |
| 가이던스 메시지   | MiniMax 호환을 위해 `user` 역할로 주입 (이전 가이던스 제거 후 추가)              |

### 4.3 OpenSpace 오케스트레이터 (`tool_layer.py`)

2단계 실행 파이프라인:

```
Phase 1: Skill-Guided
  ├── select_and_inject_skills → SkillRegistry.select()
  ├── GroundingAgent.set_skill_context() → 프롬프트에 스킬 주입
  ├── GroundingAgent.process() 실행
  ├── 성공 → 결과 반환
  └── 실패 → 워크스페이스 정리 (실패 아티팩트 삭제)

Phase 2: Tool-Fallback (Phase 1 실패 시)
  ├── clear_skill_context()
  ├── GroundingAgent.process() 재실행 (스킬 없이, 풀 이터레이션 예산)
  └── 결과 반환
```

Phase 1 실패 시 워크스페이스에서 스킬 실행으로 생성된 파일을 삭제하고 Phase 2에 풀 이터레이션 예산을 부여하여, 실패한 스킬의 중간 산물이 Phase 2를 오염시키는 것을 방지한다.

---

## 5. LLM Client 계층

### 5.1 LLMClient (`llm/client.py`)

litellm 래퍼로 단일 라운드 LLM 호출 + 도구 실행을 처리한다.

**지원 모델**: litellm을 통해 모든 주요 제공자 (OpenRouter, Anthropic, OpenAI, MiniMax 등). 게이트웨이 제공자 자동 접두사 (`openrouter/`,
`aihubmix/`).

**`complete()` 메서드 흐름**:

1. 메시지 전처리 (str → List[Dict])
2. 도구 준비: 중복 이름 `server__toolname` 리네임 + 스키마 새니타이징 + 백엔드 라벨 태깅
3. MiniMax 호환 메시지 정규화
4. Rate limit 적용
5. litellm.acompletion 호출 (재시도 포함)
6. 도구 호출 자동 실행 → 결과 메시지 추가
7. 대형 도구 결과 LLM 요약 (200K자 초과 시)

**재시도 전략**:

| 오류 유형      | 간격               |
|------------|------------------|
| Rate limit | 60s → 90s → 120s |
| 서버 과부하     | 5s → 10s → 20s   |
| 연결 오류      | 10s → 20s → 40s  |

---

## 6. Backend Provider 계층

### 6.1 Provider-Session-Connector 3계층 아키텍처

```
GroundingClient
  └── ProviderRegistry
        ├── ShellProvider ── ShellSession ── LocalShellConnector / ShellConnector
        ├── GUIProvider   ── GUISession   ── LocalGUIConnector / GUIConnector
        ├── MCPProvider   ── MCPSession   ── StdioConnector / HttpConnector / WS / Sandbox
        ├── WebProvider   ── WebSession   ── WebConnector
        └── SystemProvider (세션리스)
```

### 6.2 Shell Backend

**이중 모드**: Local (subprocess 직접) / Server (HTTP API)

**노출 도구 5개**: `shell_agent`(LLM 기반 자율 코드 작성/실행, 최대 5스텝), `read_file`, `write_file`, `list_dir`, `run_shell`

`ShellAgentTool` 내부 동작:

- 시스템 프롬프트에 플랫폼/사용자 정보, 작업 디렉토리, conda 환경 주입
- 코드 블록 정규식 추출 (python/bash 패턴)
- `[TASK_COMPLETED]`/`[TASK_FAILED]` 마커로 완료 판정
- 에러와 LLM 완료 선언의 교차 검증

### 6.3 GUI Backend

**이중 모드**: Local (pyautogui 직접) / Server (HTTP 연결)

Anthropic Computer Use 통합 (`AnthropicGUIClient`):

- 모델: `claude-sonnet-4-5`, `computer-use-2025-01-24` API
- 3단계 좌표 변환: Display Size (LLM) → Physical Pixels → PyAutoGUI Logical
- 스크린샷 리사이징: 실제 해상도 → `display_size`(기본 1024x768) 축소
- `only_n_most_recent_images`로 히스토리 이미지 수 제한 (25MB 제한 자동 감소)
- Thinking 모드: `budget_tokens=2048`
- 백업 API 키 폴오버 (`ANTHROPIC_API_KEY_BACKUP`)
- 재시도: 최대 10회, 25MB 초과 시 이미지 수 자동 절반 감소

### 6.4 MCP Backend

가장 복잡한 백엔드. 다중 MCP 서버를 관리하며 4종 커넥터를 제공한다.

**HttpConnector 전송 협상 (3단계 폴백)**:

1. **Streamable HTTP** (신규 MCP 전송) 시도
2. 실패 시 **SSE** (레거시) 폴백
3. 모두 실패 시 **JSON-RPC HTTP** 최종 폴백

**도구 캐시 2계층**: 원본 캐시 (`mcp_tool_cache.json`) + 정제 캐시 (`mcp_tool_cache_sanitized.json`). Claude API 호환을 위한
`_sanitize_mcp_schema()`가 비표준 필드를 제거한다.

**의존성 설치 관리** (`MCPInstallerManager`): npx/uvx/pip 자동 탐지 + 사용자 확인 + 실패 캐시

### 6.5 Web Backend

OpenRouter API를 통해 Perplexity AI의 `sonar-deep-research` 모델로 심층 웹 조사를 수행하고 LLM으로 400~600단어 요약을 생성한다.

### 6.6 Transport Layer

```
BaseConnectionManager (추상)
  ├── AioHttpConnectionManager        (HTTP)
  ├── AsyncContextConnectionManager   (stdio/SSE/StreamableHTTP)
  ├── PlaceholderConnectionManager    (지연 초기화)
  └── NoOpConnectionManager           (로컬 실행)
```

생명주기: `start(timeout)` → `_establish_connection()` → `_ready_event.set()` → 무한 대기 → `stop()` → `_close_connection()`.

---

## 7. Skill Engine 계층

### 7.1 Skill 데이터 모델

**SkillRecord** 핵심 필드:

| 필드                                               | 설명                                                        |
|--------------------------------------------------|-----------------------------------------------------------|
| `skill_id`                                       | 고유 ID (`{name}__imp_{uuid8}` 또는 `{name}__v{gen}_{uuid8}`) |
| `name`                                           | 논리적 이름 (버전 간 공유)                                          |
| `path`                                           | SKILL.md 경로                                               |
| `is_active`                                      | 최신 버전만 True                                               |
| `category`                                       | TOOL_GUIDE / WORKFLOW / REFERENCE                         |
| `lineage`                                        | SkillLineage (Version DAG)                                |
| `total_selections/applied/completions/fallbacks` | 실행 통계                                                     |

**리니지 규칙**:

- IMPORTED / CAPTURED → 루트 노드, `generation=0`
- FIXED → 부모 1개 (동일 스킬), 같은 name/path, 새 skill_id, 이전 `is_active=False`
- DERIVED → 부모 1+개, 새 name/디렉토리, 부모 `is_active` 유지

### 7.2 SkillRegistry + SkillRanker

**스킬 발견**: 스킬 디렉토리에서 `SKILL.md` 파일 순회 → YAML frontmatter 파싱 → `.skill_id` 사이드카 파일 관리

**LLM 기반 스킬 선택 파이프라인**:

```
1. 품질 필터링
   - selections >= 2 이고 completions = 0 → 제거
   - applied >= 2 이고 fallbacks/applied > 0.5 → 제거

2. 사전 필터링 (스킬 10개 초과 시)
   - BM25 + embedding 하이브리드 랭킹
   - 상위 max(15, max_skills x 5)개 추출

3. LLM plan-then-select 프롬프트
   Step 1: 작업 수행 계획 수립
   Step 2: 계획에 매칭되는 스킬 선택
   Step 3: 품질 확인 (저품질 스킬 제외)
   Step 4: 최종 결정 (최대 max_skills개)

4. JSON 응답: {"brief_plan": "...", "skills": ["id1", "id2"]}
```

**SkillRanker 2단계 검색**:

- Stage 1: BM25 러프 랭킹 (`rank_bm25.BM25Okapi`, 토큰 중첩 폴백)
- Stage 2: 임베딩 리랭킹 (`openai/text-embedding-3-small`, 코사인 유사도)
- 임베딩 캐시: 디스크 영속화, 스킬 진화 시 `invalidate_cache()`

### 7.3 ExecutionAnalyzer

**분석 파이프라인**:

```
1. 레코딩 아티팩트 로드 (metadata.json, conversations.jsonl, traj.jsonl)
2. 대화 포맷팅 (우선순위 기반 절삭)
   - P0 CRITICAL: 사용자 지시 → 절삭 안 함
   - P1 CRITICAL: 최종 어시스턴트 응답 → 절삭 안 함
   - P2 HIGH: 도구 호출 + 에러 → 예산 할당
   - P3 HIGH: 비최종 추론 → 한 줄 요약
   - P4 MEDIUM: 도구 성공 결과 → 예산 초과 시 축소
   - SKIP: 스킬 주입 텍스트, 시스템 프롬프트
3. LLM 에이전트 분석 (최대 5반복, 도구 사용 가능)
4. JSON → ExecutionAnalysis 생성
5. DB 영속화 + 스킬 카운터 원자적 업데이트
6. 도구 품질 피드백 (중복 제거 로직 적용)
```

**스킬 ID 교정**: LLM이 hex 접미사를 잘못 생성하는 문제를 편집 거리(Levenshtein) <= 3 기반으로 자동 교정.

### 7.4 SkillEvolver

**3가지 진화 트리거**:

| 트리거              | 진입점                          | 발생 시점                           |
|------------------|------------------------------|---------------------------------|
| Post-Execution   | `process_analysis()`         | 분석 후 evolution_suggestions 존재 시 |
| Tool Degradation | `process_tool_degradation()` | ToolQualityManager 문제 도구 감지 시   |
| Metric Monitor   | `process_metric_check()`     | 주기적 스킬 건강 검사                    |

**각 진화 모드 구현**:

**FIX**: 부모 스킬 in-place 수정 → 에이전트 루프(최대 5반복) → apply-retry(최대 3회) → 새 skill_id 생성 → `SkillStore.evolve_skill()` 원자적
트랜잭션 (새 버전 삽입 + 이전 비활성화) → `.skill_id` 사이드카 업데이트

**DERIVED**: 부모 로드 → 에이전트 루프 → 새 이름 추출 + 위생화(소문자, 하이픈, 50자) → 새 디렉토리 생성 → apply-retry → DB 영속화 (부모 is_active 유지)

**CAPTURED**: 관련 분석에서 패턴 수집 → 에이전트 루프 → 새 디렉토리 생성 → `SkillStore.save_record()` (별도 저장)

**에이전트 루프 종료 제어**: `<EVOLUTION_COMPLETE>` (성공) / `<EVOLUTION_FAILED>` (자기 거부) 토큰 기반. 마지막 반복에서는 도구 비활성화 + JSON 출력 강제.

**패치 시스템** (`patch.py` + `fuzzy_match.py`):

- PATCH (multi-file diff), FULL (완전 내용), DIFF (SEARCH/REPLACE) 3종 자동 감지
- 6단계 퍼지 매칭: 정확 → trim → 블록 앵커(Levenshtein) → 공백 정규화 → 들여쓰기 유연 → trim 경계

**안전장치**:

| 장치        | 메커니즘                                     |
|-----------|------------------------------------------|
| 동시성 제한    | `asyncio.Semaphore(max_concurrent=3)`    |
| 무한 루프 방지  | 에이전트 루프 5회, apply-retry 3회 상한            |
| 자기 거부     | `<EVOLUTION_FAILED>` 토큰 출력               |
| 데이터 부족 보호 | `min_selections(5)` 이하면 재평가 스킵           |
| 반복 처리 방지  | `addressed_degradations` 세트 (도구 회복 시 리셋) |
| 모호한 응답    | 기본적으로 "스킵" 처리                            |
| 이름 위생화    | 매 진화마다 50자, 소문자-하이픈 강제                   |

### 7.5 SkillStore (SQLite)

저장 위치: `<project_root>/.openspace/openspace.db`

**SQLite 설정**: WAL 모드, `busy_timeout=30000ms`, `cache_size=16MB`, 재시도: 지수 백오프 (최대 5회)

**핵심 테이블**: `skill_records`, `skill_lineage_parents` (다대다), `execution_analyses` (task_id UNIQUE), `skill_judgments`,
`skill_tool_deps`, `skill_tags`

**쓰기/읽기 분리**:

- 쓰기: async → `asyncio.to_thread` → sync → `self._mu` 락 → `self._conn`
- 읽기: sync → `self._reader()` → 독립 단기 연결 (WAL 병렬 읽기)

**원자적 트랜잭션 `evolve_skill()`**: FIXED면 부모 `is_active=0` → 새 레코드 삽입 → 리니지 부모 삽입

---

## 8. Quality Tracking 시스템

### 8.1 ToolQualityRecord

키 형식: `{backend}:{server}:{tool_name}`

**페널티 계산**:

```
1. total_calls < 3 → 1.0 (공정한 평가 허용)
2. recent_success_rate >= 0.4 → 1.0
3. 그 외: base_penalty = 0.3 + (success_rate / 0.4) x 0.7
4. 연속 실패 >= 3: extra_penalty = min(0.3, (consec - 2) x 0.1)
5. 최종값 = clamp(base - extra, 0.2, 1.0)
```

### 8.2 ToolQualityManager

**자기 진화 사이클** (트리거: `global_execution_count >= last + evolve_interval(5)`):

1. 도구 변경 감지 (description hash 비교)
2. 재평가 대상 선별 (변경/미평가/불일치)
3. LLM 문서 품질 평가 (최대 5개/사이클, clarity + completeness)
4. 적응형 품질 가중치: `weight = 0.1 + (coverage x 0.5 + richness x 0.5) x 0.4`
5. 문제 도구 추천 → SkillEvolver로 전달

---

## 9. MCP 통합 계층

### 9.1 MCP 서버 (OpenSpace as Server)

`execute_task` 응답 구조:

```json
{
  "status": "success|error|unknown",
  "response": "실행 결과",
  "execution_time": 12.34,
  "iterations": 5,
  "skills_used": ["skill_name"],
  "task_id": "uuid",
  "tool_call_count": 10,
  "tool_summary": [{"tool": "name", "status": "success"}],
  "evolved_skills": [{"skill_dir": "/path", "name": "...", "origin": "derived"}],
  "action_required": "upload 안내"
}
```

**클라우드 스킬 검색 2단계**: Stage 1: 클라우드 BM25 + 임베딩 → 상위 8개 로컬 임포트 → Stage 2: 로컬 BM25 + LLM 최종 선택

### 9.2 MCP 클라이언트 (OpenSpace as Client)

- `MCPClient`: 설정 기반 다중 MCP 서버 관리, 최대 3회 재시도
- `MCPProvider`: 지연/즉시 세션 생성 (`eager_sessions` 설정)
- `MCPSession`: MCP 도구 → 내부 `RemoteTool` 변환

### 9.3 호스트 에이전트 통합

LLM 자격증명 해석 3-Tier:

1. **Tier 1**: `OPENSPACE_LLM_*` 환경변수 (최우선)
2. **Tier 2**: 호스트 설정 자동감지 (`~/.nanobot/config.json`, `~/.openclaw/openclaw.json`)
3. **Tier 3**: Provider 네이티브 환경변수 (litellm 자동 처리)

---

## 10. Cloud Skill Community

### 10.1 업로드 워크플로

```
1. SKILL.md frontmatter에서 name, description 추출
2. origin-parents 유효성 검증
3. POST /artifacts/stage (multipart/form-data) → artifact_id
4. Content diff 계산 (public + 부모 있으면 diff, 없으면 add-all)
5. POST /records → 409 충돌 시 재시도
```

### 10.2 하이브리드 검색 엔진

```
Phase 1: BM25 러프 랭킹 → 상위 limit x 3
Phase 2: 벡터 스코어링 (코사인 유사도)
Phase 3: hybrid_score = vector + lexical_boost
  - slug 토큰 정확 매칭: +1.4
  - slug 토큰 접두사 매칭: +0.8
  - name 토큰 정확 매칭: +1.1
  - name 토큰 접두사 매칭: +0.6
Phase 4: 이름별 중복 제거 + limit
```

### 10.3 보안

- zip 경로 순회 공격 방지: `is_relative_to()` 검증
- API 키 마스킹 (처음 8자만 표시)

---

## 11. 벤치마크 및 평가 시스템

### 11.1 GDPVal 벤치마크

OpenAI `gdpval` 데이터셋에서 **결정론적 50개 서브셋** 선정 (44개 직업군, 9개 산업 커버).

**2-Phase 프로토콜**:

- Phase 1 (Cold Start): 스킬 없이 시작, 순차 실행하며 스킬 축적
- Phase 2 (Warm Rerun): Phase 1 전체 스킬 라이브러리로 동일 태스크 재실행

### 11.2 평가 지표

| 지표               | 산정 방식                                                   |
|------------------|---------------------------------------------------------|
| Quality          | ClawWork `LLMEvaluator`(GPT-4o), 태스크당 평균 48.8개 루브릭, 0~1 |
| Income           | 0.6 Payment Cliff (score < 0.6 → 수입 없음)                 |
| Token Efficiency | 6차원 (전체/에이전트 x prompt/completion/total)                 |
| Value Capture    | Income / Task Value x 100                               |

### 11.3 토큰 추적 (TokenTracker)

litellm `CustomLogger` 콜백으로 모든 LLM 호출 자동 인터셉트. `ContextVar`로 소스 태깅:

- `agent`: 메인 에이전트 루프
- `skill_select`: 스킬 선택
- `analyzer`: 실행 후 분석
- `evolver`: 스킬 진화
- `summarizer`: 도구 결과 요약

### 11.4 스킬 DB 현황 (벤치마크 후)

50개 태스크에서 **226개 스킬** 생성 (활성 206개):

- `captured`: 141개 (62%) — 실행 중 자동 포착
- `derived`: 45개 (20%) — 기존 스킬 파생
- `fixed`: 22개 (10%) — 오류 수정
- `imported`: 18개 (8%) — 외부 임포트

### 11.5 의존성 및 보안

핵심 의존성: litellm(>=1.70.0, <1.82.7), openai, mcp, anthropic, pydantic, flask, pyautogui

litellm 버전 상한 사유: **PYSEC-2026-2** 공급망 공격 (v1.82.7/1.82.8 악성 코드 포함). `pyproject.toml`에서 핀닝으로 대응 완료.

### 11.6 테스트 인프라

현재 단위 테스트 코드 **없음**. 벤치마크 자체가 사실상 통합 테스트 역할을 수행. `--dry-run`, `--max-tasks`, `--no-eval`, `--resume` 등 부분 실행 옵션 제공.

---

## 12. 설정 시스템

### 12.1 설정 파일 구조

| 파일                      | 역할                       |
|-------------------------|--------------------------|
| `config_grounding.json` | 백엔드, 도구 검색, 품질 추적, 스킬 설정 |
| `config_security.json`  | OS별 보안 정책                |
| `config_mcp.json`       | MCP 서버 정의                |
| `config_agents.json`    | 에이전트별 설정                 |
| `config_dev.json`       | 개발 환경 오버라이드              |

### 12.2 Pydantic 설정 모델

```
GroundingConfig (BaseModel)
├── ShellConfig      # mode, conda_env, working_dir
├── WebConfig        # 최소 설정
├── MCPConfig        # servers, sandbox, eager_sessions
├── GUIConfig        # mode, driver_type
├── ToolSearchConfig # embedding_model, hybrid 검색
├── ToolQualityConfig # 품질 추적 + evolve_interval
├── SkillConfig      # skill_dirs, max_select
├── SecurityPolicy   # blocked_commands
└── SessionConfig    # 세션 기본값
```

### 12.3 환경변수 오버라이드

`OPENSPACE_CONFIG_JSON` (인라인 JSON), `OPENSPACE_CONFIG_PATH` (파일 경로), `OPENSPACE_SHELL_*`, `OPENSPACE_SKILLS_*`,
`OPENSPACE_MCP_SERVERS_JSON`, `OPENSPACE_LOG_LEVEL` 등.

---

## 13. 보안 아키텍처

### 13.1 5계층 보안

| 계층        | 내용                                                                                         |
|-----------|--------------------------------------------------------------------------------------------|
| 명령어 검사    | `shlex.split()` 토큰화 → OS별 차단 목록 매칭 → 대화형 프롬프트 (MCP에서 기본 거부)                                |
| 도구 스키마 검증 | `jsonschema.validate()` 파라미터 유효성 검사                                                        |
| 샌드박스 격리   | E2BSandbox (선택적, 기본 비활성)                                                                   |
| 스킬 안전성    | `check_skill_safety()` — 차단: ClawdAuthenticatorTool, 경고: malware/phish/keylogger/api_key 등 |
| 클라우드 보안   | zip 경로 순회 방지 (`is_relative_to`), API 키 마스킹                                                 |

### 13.2 보안 관찰 사항

**강점**: 토큰 수준 명령어 검사 (`shlex.split`)로 공백 삽입 우회 방지. OS별 분리된 차단 목록.

**약점**:

- 기본 `sandbox_enabled = false` — 프로덕션 도입 시 E2B/컨테이너 격리 필수
- `-rf`, `-9` 등 플래그가 독립 토큰으로 차단되어 `ls -9 *.txt` 같은 무해한 명령도 차단 가능
- MCP 서버 환경에서 stdin 없으므로 대화형 프롬프트 불가 → 기본 거부

---

## 14. 설계 패턴 및 코드 품질

### 14.1 핵심 설계 패턴

| 패턴                    | 적용                                                |
|-----------------------|---------------------------------------------------|
| Strategy              | Provider ABC + BackendType으로 백엔드 교체               |
| Registry              | ProviderRegistry, AgentRegistry, SkillRegistry    |
| Template Method       | BaseAgent.process() → GroundingAgent.process()    |
| Observer/Callback     | tool_result_callback, _auto_record_execution()    |
| Facade                | OpenSpace 클래스가 전체 하위 시스템 통합 인터페이스 제공              |
| Builder               | GroundingAgentPrompts.build_system_prompt()       |
| Transport Negotiation | HttpConnector: StreamableHTTP → SSE → JSON-RPC 폴백 |

### 14.2 코드 품질 관찰

**강점**:

- 일관된 로깅 (`Logger.get_logger(__name__)`)
- 비동기 우선 설계 (거의 모든 I/O가 `async/await`)
- 방어적 에러 처리 (초기화 실패 → `non-fatal` 경고, 부분 기능 저하 허용)
- `TYPE_CHECKING` 가드 적극 활용 (순환 임포트 방지)
- 보안 의존성 고정 사유 주석화

**약점**:

- 전역 상태 의존 (`RecordingManager._global_instance`, `_config` 모듈 변수)
- `tool_layer.py`의 `execute()` ~200줄 — 단일 책임 원칙 위반 경향
- 토큰 추정 `len(text) // 4` — 비영어권 텍스트에서 부정확
- `BaseEntity`의 `extra="allow"` — 유연하지만 타입 안전성 약화

---

## 15. 종합 평가

### 15.1 아키텍처 독창성

OpenSpace의 가장 독창적인 설계 결정:

1. **3중 자동 진화 트리거**: Post-Execution, Tool Degradation, Metric Monitor를 독립 트리거로 구성한 것은 기존 어떤 에이전트 프레임워크에도 없는 패턴
2. **Skill을 "살아있는 엔티티"로 취급**: Version DAG, 실행 통계, 품질 지표를 가진 1급 객체
3. **비파괴적 호스트 부착**: 기존 에이전트를 대체하지 않고 MCP + host_skills로 확장
4. **Cascade Evolution**: Circuit Breaker 패턴을 차용한 도구 품질 저하 → 스킬 수정 자동 트리거

### 15.2 핵심 수치

| 지표           | 값                          |
|--------------|----------------------------|
| Python 소스 파일 | 151개                       |
| 벤치마크 태스크     | 50개 (9 산업, 44 직업군)         |
| 생성 스킬        | 226개 (50 태스크 후)            |
| 토큰 절감        | 45.9% (Phase 2 vs Phase 1) |
| 수입 향상        | 4.2x (ClawWork 대비)         |
| GitHub Stars | ~3,500                     |

### 15.3 도입 시 체크 포인트

- [ ] 스킬 저장소 (SQLite + 파일) 백업/보존 정책
- [ ] 진화 허용 범위 (FIX만 vs DERIVED/CAPTURED 포함)
- [ ] 민감 데이터 포함 로그/recording 처리 정책
- [ ] Cloud 공유 시 공개 범위 관리
- [ ] 보안 계층 강화 (E2B 샌드박스, 컨테이너 격리)
- [ ] 품질 KPI 사전 정의 (완료율, 재시도율, 토큰/비용)
- [ ] litellm 버전 상한 추적 및 업데이트 정책
