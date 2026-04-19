# Archon 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `coleam00/Archon` — 18,842★ / 2,919 fork (2026-04-19 기준)
- 공식 설명: "The first open-source harness builder for AI coding. Make AI coding deterministic and repeatable."
- 런타임: **Bun + TypeScript**, 최신 릴리스 **Archon CLI v0.3.6** (2026-04-12)
- 주요 특성: YAML DAG, worktree 격리, 멀티 플랫폼 어댑터, 스트리밍 기반 실행

Archon은 "에이전트가 무엇을 할지"보다, **어떤 순서와 게이트로 실행할지**를 고정하는 데 초점을 둡니다. 즉흥 프롬프트를 반복하는 방식 대신, 팀이 합의한 워크플로우를 코드처럼 버전 관리하는 운영 모델입니다.

### 버전 전환 안내 (2026-04-07)

Archon은 2026-04-07에 **전면 재작성**(v2)을 공지했습니다. 본 문서는 v2(Bun/TypeScript 기반 워크플로우 엔진)를 대상으로 합니다.

- **v1 (Python 기반 task management + RAG)**: [`archive/v1-task-management-rag`](https://github.com/coleam00/Archon/tree/archive/v1-task-management-rag) 브랜치에 보존
- **v2 (현재 main)**: YAML 워크플로우 엔진, 이 문서의 분석 대상

---

## 2. Archon 프로젝트 구조 분석

공개 저장소 기준 상위 구조는 아래와 같이 역할이 분리되어 있습니다.

```text
.archon/
├─ workflows/defaults/   # 번들 워크플로우 YAML 20개 (idea-to-pr, fix-github-issue 등)
├─ commands/defaults/    # 번들 커맨드 프롬프트 템플릿 35개
├─ config.yaml           # 런타임 설정
└─ scripts/              # 보조 스크립트

packages/                # 모노레포 워크스페이스 11개
├─ core/                 # 공통 타입, orchestrator, 세션/상태, AI 클라이언트 인터페이스
├─ workflows/            # DAG 실행/검증 엔진, 노드 디스패처
├─ providers/            # Claude Code / Codex 어댑터 (IAssistantClient)
├─ isolation/            # 격리 프로바이더 (worktree/container/VM/remote)
├─ adapters/             # CLI/Web/Slack/Telegram/GitHub 등 플랫폼 어댑터
├─ server/               # HTTP 서버, 웹훅 라우팅
├─ cli/                  # `archon` 바이너리 진입점
├─ web/                  # 대시보드용 Vite 기반 프런트엔드
├─ git/                  # git 조작 유틸(워크트리, 브랜치, PR 연계)
├─ paths/                # `~/.archon` 디렉토리 및 경로 해석
└─ docs-web/             # archon.diy 문서 소스
```

### 구조적 특징

1. **워크플로우 정의와 실행 엔진 분리**
   - `.archon/workflows/*.yaml`는 "무엇을 어떤 순서로 할지"를 정의
   - `packages/workflows`는 DAG 실행, 조건 분기, 루프, 트리거 룰을 처리

2. **어댑터/프로바이더 인터페이스 기반**
   - 플랫폼(입력 채널)과 AI 런타임(Claude/Codex)을 각각 플러그인처럼 교체 가능

3. **격리 계층 독립**
   - `packages/isolation`으로 분리되어 프로바이더 교체(worktree/container/VM/remote)가 용이

---

## 3. AI 하네스 관점 핵심 분석

### 3.1 하네스 목적

Archon의 목표는 모델 추론 품질 자체보다, **개발 프로세스의 재현성과 통제성**을 높이는 것입니다.

| 문제 | 일반 에이전트 사용 | Archon 접근 |
|---|---|---|
| 실행 순서가 매번 달라짐 | 계획/검증/리뷰 누락 가능 | YAML DAG로 단계 고정 |
| 병렬 작업 충돌 | 같은 브랜치/작업공간 경쟁 | worktree 격리 실행 |
| 프로세스 표준화 어려움 | 개인 프롬프트 의존 | 워크플로우를 저장소에 커밋해 팀 표준화 |
| 결과 추적 어려움 | 대화 로그 중심 | 워크플로우 이벤트/아티팩트 중심 추적 |

### 3.2 노드 조합 전략

- **AI 노드** (`command`, `prompt`, `loop`): 계획/구현/리뷰처럼 지능이 필요한 구간
- **결정론 노드** (`bash`, `approval`, `cancel`): 테스트, 승인, 종료 같은 통제 구간

실무적으로는 "AI가 잘하는 것(탐색/요약/리뷰) + 시스템이 강제해야 하는 것(검증/게이트)"을 분리하는 구조가 핵심입니다.

---

## 4. 대표 워크플로우 플로우

### 4.1 `archon-idea-to-pr`

핵심 단계:

1. `create-plan`: 코드베이스 분석 기반 계획 수립
2. `plan-setup`, `confirm-plan`: 범위/전제 정렬
3. `implement-tasks`: 구현 (Opus 1M 모델 지정)
4. `validate`: 검증
5. `finalize-pr`: PR 정리
6. `code-review-agent` / `error-handling-agent` / `test-coverage-agent` / `comment-quality-agent` / `docs-impact-agent`: 5개 병렬 리뷰
7. `synthesize` (`trigger_rule: one_success`) → `implement-fixes`: 리뷰 합성 후 수정
8. `workflow-summary`: 최종 보고

특징:
- **리뷰 병렬 fan-out + synthesize fan-in** 패턴
- 각 노드는 `context: fresh`로 독립 세션 실행
- 구현 뒤 검증, PR 뒤 리뷰를 분리해 운영 품질 확보

### 4.2 `archon-fix-github-issue`

핵심 단계:

1. 이슈 추출/분류(bug/feature 등)
2. 웹 리서치 + investigate/plan 분기
3. 구현 및 validate
4. Draft PR 생성
5. 스마트 리뷰 + self-fix + simplify
6. 이슈 완료 리포트

특징:
- 이슈 유형에 따른 **조건 분기**
- 리뷰 결과를 자동 수정 루프로 연결

### 4.3 번들 워크플로우 일람 (20개)

| 워크플로우 | 용도 |
|---|---|
| `archon-idea-to-pr` | 아이디어/PRD → 계획 → 구현 → 검증 → PR → 리뷰 → 수정 |
| `archon-plan-to-pr` | 기존 계획을 받아 PR까지 실행 |
| `archon-feature-development` | 피처 단위 개발 라이프사이클 |
| `archon-fix-github-issue` | 이슈 분류·조사 후 수정 → Draft PR |
| `archon-create-issue` | 이슈 생성/정리 |
| `archon-issue-review-full` | 이슈 리뷰 전체 루프 |
| `archon-smart-pr-review` | 단일 에이전트 스마트 리뷰 |
| `archon-comprehensive-pr-review` | 다중 에이전트 종합 리뷰 |
| `archon-validate-pr` | PR 검증 |
| `archon-resolve-conflicts` | 머지 컨플릭트 해소 |
| `archon-refactor-safely` | 안전 리팩토링 |
| `archon-architect` | 아키텍처 설계 지원 |
| `archon-assist` | 범용 보조 |
| `archon-adversarial-dev` | 적대적 리뷰·검증 |
| `archon-interactive-prd` | 인터랙티브 PRD 작성 |
| `archon-workflow-builder` | 워크플로우 자체 작성/개선 |
| `archon-piv-loop` | Plan-Implement-Validate 루프 |
| `archon-ralph-dag` | Ralph 패턴 DAG |
| `archon-test-loop-dag` | 테스트 반복 루프 |
| `archon-remotion-generate` | Remotion 기반 결과 렌더 |

---

## 5. 운영/보안 관점 체크포인트

1. **권한 모델**
   - Archon은 자동 실행 목적상 강한 권한으로 동작하므로, 배포 환경의 접근 제어가 필수
   - 플랫폼별 허용 사용자(whitelist) 설정 권장

2. **격리 계층 선택**
   - 기본은 git worktree (`~/.archon/workspaces/<owner>/<repo>/worktrees/<branch>/`)
   - 민감 작업은 `container`/`VM`/`remote` 프로바이더로 확장 가능
   - 병렬 워크플로우에서는 `--no-worktree`보다 기본 격리 전략이 안전

3. **환경변수 경계 관리**
   - Archon 설정과 대상 저장소 `.env`를 분리해 의도치 않은 누출 방지
   - 데이터는 기본 SQLite, PostgreSQL은 `docker compose --profile with-db` 또는 외부 DB(Supabase/Neon 등) 연결로 전환

4. **워크플로우를 코드로 관리**
   - `.archon/workflows`, `.archon/commands`를 저장소에 커밋해 팀 공통 실행 규약으로 유지
   - 번들 20종 워크플로우는 프로젝트별로 덮어쓰기 가능

---

## 6. 런타임 및 배포

- **런타임**: Bun + TypeScript, 모노레포 (`bun install`)
- **배포 경로**: 공식 `curl https://archon.diy/install | bash`, `brew install coleam00/archon/archon`, Docker (`ghcr.io/coleam00/archon:latest`), 플랫폼별 바이너리(`archon-darwin-arm64` 등)
- **컨테이너 실행**: `docker compose up -d` (SQLite 기본), `--profile with-db` (PostgreSQL), `--profile cloud` (Caddy TLS)
- **스키마**: `migrations/000_combined.sql` ~ `019_*.sql`까지 증분 마이그레이션, 주요 테이블 7종 (codebases/conversations/sessions/isolation_environments/workflow_runs/workflow_events/messages)

---

## 7. 적용 인사이트

- **팀 표준화**: "누가 실행해도 같은 단계"를 보장해야 하는 조직형 개발에 적합
- **리스크 제어**: 승인 노드/검증 노드/분기 노드로 자동화 범위를 세밀하게 조절 가능
- **확장성**: 플랫폼 어댑터(입력 채널)와 프로바이더(LLM 런타임)를 분리해 도입 리스크를 줄임

요약하면 Archon은 단일 에이전트 앱보다는, **에이전트 기반 개발 프로세스를 운영 체계로 승격하는 하네스**에 가깝습니다.

---

## 참고 링크

- [Repository](https://github.com/coleam00/Archon)
- [Latest Release — Archon CLI v0.3.6 (2026-04-12)](https://github.com/coleam00/Archon/releases/tag/v0.3.6)
- [v1 아카이브 브랜치 (Python, task management + RAG)](https://github.com/coleam00/Archon/tree/archive/v1-task-management-rag)
- [재작성 공지 — Issue #957](https://github.com/coleam00/Archon/issues/957)
- [Getting Started - Installation](https://archon.diy/getting-started/installation/)
- [Getting Started - Concepts](https://archon.diy/getting-started/concepts/)
- [Architecture Reference](https://archon.diy/reference/architecture/)
- [Security Reference](https://archon.diy/reference/security/)
- [Troubleshooting Reference](https://archon.diy/reference/troubleshooting/)
