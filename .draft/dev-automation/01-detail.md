# 로컬 개발 자동화 에이전트 — 상세 구현 문서

[워크플로우 다이어그램](/.draft/dev-automation/00-workflow.md)의 7계층 아키텍처를 구현 수준으로 풀어낸 문서이다.
각 레이어별로 **무엇을 구현해야 하는지**, **어떤 기술 선택지가 있는지**, **구현 시 주의할 점**을 다룬다.

---

## L1: Intake — 요청 수신과 정규화

### 역할

외부 채널에서 들어오는 다양한 형태의 요청을 단일 `task request` 포맷으로 변환한다.
이 레이어 자체는 AI가 필요 없는 결정론적 변환 계층이다.

### 채널별 수신 방식

| 채널                       | 수신 메커니즘                   | 정규화 포인트                           |
|--------------------------|---------------------------|-----------------------------------|
| **CLI 직접 실행**            | 터미널에서 AI CLI 실행           | 명령줄 인자와 stdin을 task request로 매핑   |
| **Web UI**               | HTTP API → 로컬 서버          | JSON body를 task request 스키마로 변환   |
| **메신저 (Slack, Discord)** | 웹훅 → 브릿지 서버 → AI CLI 프로세스 | 메시지 파싱, 멘션 추출, thread context를 포함 |

### task request 스키마

모든 채널의 요청은 아래 포맷으로 정규화되어야 한다.

```yaml
task_request:
    id: string              # 유니크 요청 ID (채널별 생성 규칙)
    source: cli | web | slack | discord
    repo: string            # 대상 저장소 경로 (절대 경로 또는 Git remote URL)
    prompt: string          # 사용자의 원문 요청
    context: # 채널별 부가 정보
        thread_id: string?    # 메신저의 경우 thread ID
        user: string?         # 요청자 식별
        attachments: list?    # 첨부 파일, 스크린샷 등
    options: # 실행 옵션
        mode: human-reviewed | auto
        workspace: worktree | docker | vm
        max_retries: int?     # 기본값: 설정 파일에서 로드
```

### 구현 고려사항

**채널 추가의 확장성**: Intake 레이어는 어댑터 패턴으로 설계한다.
새 채널 추가 시 정규화 어댑터만 작성하면 된다. 하류 레이어는 `task_request` 스키마만 인식한다.

**입력 검증**: 정규화 직후 필수 필드 검증을 수행한다.
`repo`가 유효한 Git 저장소인지, `prompt`가 비어 있지 않은지 등의 기본 검증이다.
검증 실패 시 즉시 reject하고 요청자에게 오류를 반환한다.

**인증과 인가**: 메신저 채널의 경우 웹훅 서명 검증이 필요하다.
CLI 직접 실행은 로컬 사용자이므로 별도 인증이 불필요하다.

---

## L2: Run Control — 상태 관리와 동시 실행 조율

### 역할

`task_request`를 받아 `run`을 생성하고, 실행 상태를 추적하며, 동시 실행을 조율한다.
같은 저장소에 대한 중복 실행을 방지하고, busy 상태일 때 요청을 큐에 적재한다.

### Run 생명주기

```text
task_request 수신
    → run_id 생성 (UUID v7 — 시간 순 정렬 가능)
    → 기존 active run 확인
        → busy: queue에 적재, 대기
        → idle: 즉시 실행
    → run state 초기화 (Received)
    → L3로 run context 전달
```

### State Store 구현

State Store는 run의 전체 생명주기를 추적한다.

```yaml
run_state:
    run_id: string
    session_id: string       # AI CLI 세션 식별자
    status: received | queued | preparing | plan_reviewed | awaiting_approval |
        provisioning | executing | deterministic_checks | ai_review |
        ready_to_publish | publishing | published | escalated
    repo: string
    task_request_id: string
    workspace_ref: string?   # worktree 경로 또는 container ID
    retry_count: int
    max_retries: int
    plan_doc_path: string?
    created_at: timestamp
    updated_at: timestamp
    error_log: list?         # 실패 이력 누적
```

**구현 선택지**:

| 방식               | 장점                     | 단점              | 적합한 경우          |
|------------------|------------------------|-----------------|-----------------|
| **JSON 파일 (로컬)** | 설정 불필요, 디버깅 용이         | 동시성 제어 약함, 락 필요 | 개인 사용, 단일 프로세스  |
| **SQLite**       | ACID 보장, SQL 쿼리, 파일 기반 | 네트워크 공유 어려움     | 개인 사용, 이력 조회 필요 |
| **Redis**        | 빠른 읽기/쓰기, pub/sub, TTL | 외부 서비스 의존       | 멀티 인스턴스, 팀 환경   |

초기 구현은 **SQLite**를 권장한다.
파일 기반이라 배포가 간단하고, 트랜잭션으로 동시성 문제를 해결하며, run 이력 조회에 SQL을 쓸 수 있다.

### 동시 실행 정책

같은 repo에 대해 동시에 여러 run이 실행되면 workspace 충돌이 발생한다.

```text
정책 1: 직렬 (기본값)
    → 같은 repo에 active run이 있으면 queue 적재
    → 선행 run 완료 후 dequeue

정책 2: 병렬 (worktree 격리 시)
    → 각 run이 별도 worktree를 사용하면 병렬 실행 가능
    → 단, 같은 브랜치 기반의 worktree는 충돌 위험

정책 3: Interrupt
    → 새 요청이 기존 run보다 우선순위 높으면 기존 run을 중단
    → 위험도가 높으므로 명시적 사용자 옵션으로만 허용
```

### 큐 구현

큐는 State Store와 동일한 저장소에 구현한다.
복잡한 메시지 브로커(RabbitMQ, Kafka)는 초기에 불필요하다.
SQLite 테이블 하나(`pending_tasks`)로 FIFO 큐를 구현하고, polling으로 dequeue한다.

---

## L3: Context & Planning — 탐색, 기획, 검증

### 역할

이 레이어는 시스템에서 가장 중요한 레이어이다.
**기획의 품질이 구현의 품질을 결정한다** — Plan Doc이 부실하면 이후 모든 레이어가 무의미해진다.

이 레이어의 AI CLI는 **코드 변경 권한이 없다**. 읽기와 문서 생성만 허용된다.

### 워크플로우 상세

```text
1. 요구사항 분석
    → task_request.prompt에서 의도와 범위 추출
    → 암묵적 요구사항 식별 (예: "로그인 추가" → 세션 관리, 보안 고려)

2. 프로젝트 탐색 (결정론적 + 시맨틱)
    → 정적 탐색: 파일 구조, import 관계, 패턴 매칭
    → 시맨틱 검색: Augment Context MCP로 의미 기반 관련 코드 탐색
    → Git 이력: 관련 파일의 최근 변경, 기존 구현 패턴 파악

3. 추가 조사 (AI 판단 — 선택적)
    → 외부 라이브러리의 최신 사용법
    → 알려진 함정, 엣지케이스
    → 판단 기준: 프로젝트 내부 정보만으로 충분한가?

4. AI 컨텍스트 로딩 (존재 시 — 선택적)
    → 프로젝트에 사전 정의된 도메인/데이터 모델/API 스펙 로딩
    → CLAUDE.md, AGENTS.md 등 기존 AI 컨텍스트 파일 포함

5. Plan Doc 작성
    → 6개 필수 필드를 모두 포함하는 기획 문서 생성
    → 마크다운 파일로 저장 (경로: .agent/plans/{run_id}.md)

6. 멀티 AI 리뷰 (기획 검증)
    → Plan Doc을 복수 모델이 병렬 검증
    → 부족 시: 피드백 반영 → 1단계부터 재탐색
    → 충분 시: L4로 전달
```

### Plan Doc 구현

Plan Doc은 마크다운 파일로 저장하되, 프론트매터에 메타데이터를 포함한다.

```markdown
---
run_id: "01J..."
status: draft | reviewed | approved | rejected
created_at: "2026-03-20T10:00:00Z"
reviewer_models: ["claude-opus-4-6", "gpt-5.4"]
review_result: pass | fail | pending
---

# Plan Doc: {작업 제목}

## 1. 컨텍스트 요약

탐색 결과와 판단 근거를 기록한다.

- 관련 파일 목록과 각 파일의 역할
- Git 이력에서 확인한 기존 패턴
- AI 컨텍스트에서 로딩한 정보 (존재 시)

## 2. 변경 목표

무엇을 왜 바꾸는지 명확히 고정한다.

- 해결하려는 문제
- 기대하는 결과

## 3. 수정 파일 후보

실행 범위를 제한한다. Executor는 여기 명시된 파일만 수정할 수 있다.

- 파일 경로와 변경 유형 (생성 / 수정 / 삭제)

## 4. 테스트 시나리오

Gate에서 검증할 기준을 제공한다.

- 핵심 시나리오 목록
- 기대 결과

## 5. 주의사항 / edge cases

추가 조사와 도메인 지식의 반영 여부를 추적한다.

- 알려진 함정
- 엣지케이스

## 6. 미해결 판단

에이전트가 확신하지 못하는 항목을 분리한다.
사람이 Human Approval 단계에서 결정한다.

- 판단이 필요한 항목과 선택지
```

**저장 경로**: `.agent/plans/{run_id}.md`

- `.agent/` 디렉토리는 `.gitignore`에 추가
- run 종료 후 보관 정책에 따라 정리 (기본: 30일 보관)

### 컨텍스트 수집 전략

**정적 탐색 (결정론적)**:

- `glob`, `grep` 기반 파일 탐색
- import/require 그래프 추적
- 설정 파일(tsconfig, package.json 등) 분석

**시맨틱 검색 (Augment Context MCP)**:

- 키워드 불일치 시에도 의미적으로 관련된 코드 발견
- 정적 탐색으로는 찾기 어려운 간접 의존성 탐지
- 정적 탐색의 결과를 시맨틱 검색의 시드로 활용하면 효과적

**Git 이력 활용**:

- `git log --follow` — 관련 파일의 변경 이력
- `git blame` — 코드 작성 의도 파악
- 최근 변경 패턴에서 프로젝트 관행 추론

### Main AI CLI 실행 구현

Main AI CLI는 일반적인 AI CLI 세션이되, 시스템 프롬프트에 제약을 명시한다.

```text
역할: 오케스트레이터. 코드를 탐색하고 Plan Doc을 작성하라.
권한: 파일 읽기, Plan Doc 작성만 허용. 코드 수정 금지.
입력: task_request, run_context
출력: .agent/plans/{run_id}.md
```

**구현 방식**:

| AI CLI          | 세션 분리 방법                                | 권한 제어 방법                                                      |
|-----------------|-----------------------------------------|---------------------------------------------------------------|
| **Claude Code** | `--system-prompt`로 역할 주입, 별도 프로세스 실행    | 시스템 프롬프트에 제약 명시 + 허용 도구 제한 (hooks의 PreToolUse로 Write/Edit 차단) |
| **Codex**       | `--model`, `--approval-mode` 플래그로 세션 설정 | `--approval-mode suggest`로 코드 수정 제안만 허용, 실제 쓰기 차단             |
| **Gemini CLI**  | 별도 프로세스, 별도 config                      | 시스템 프롬프트 제약 + sandbox 모드                                      |

---

## L4: Approval & Policy — 승인과 정책 적용

### 역할

멀티 AI 리뷰를 통과한 Plan Doc을 사람에게 제시하고, 승인/반려를 받는다.
승인 시 Policy Gate를 거쳐 Execution Grant를 발급한다.

### Human Approval 구현

사람에게 Plan Doc을 제시하는 방식은 진입 채널에 따라 다르다.

| 채널         | 제시 방식                             | 응답 수신                             |
|------------|-----------------------------------|-----------------------------------|
| **CLI**    | 터미널에 Plan Doc 요약 출력 + 전문 파일 경로 제공 | stdin 입력 (approve / reject + 코멘트) |
| **Web UI** | Plan Doc 렌더링 + 승인/반려 버튼           | HTTP 응답                           |
| **메신저**    | Plan Doc 요약을 thread에 게시 + 이모지 반응  | 이모지 또는 스레드 답글로 승인/반려              |

**승인 응답 포맷**:

```yaml
approval:
    run_id: string
    decision: approve | reject
    comment: string?          # 수정 요청 시 피드백
    resolved_decisions: map?  # Plan Doc의 '미해결 판단'에 대한 사람의 결정
    timestamp: timestamp
```

**승인 대기 타임아웃**: 설정 가능한 타임아웃(기본: 24시간)을 두고, 초과 시 run을 `escalated`로 전이한다.

### Policy Gate 구현

Policy Gate는 사람의 승인과 별개로, 시스템이 강제하는 규칙이다.
코드로 구현되며, AI가 우회할 수 없다.

**정책 규칙 예시**:

```yaml
policy:
    # 실행 모드별 권한
    modes:
        human-reviewed:
            require_approval: true
            allowed_workspaces: [ worktree, docker, vm ]
        auto:
            require_approval: false
            allowed_workspaces: [ docker, vm ]  # 로컬 worktree 비허용
            require_isolation: true

    # 금지 경로 — 이 경로의 파일은 수정 불가
    forbidden_paths:
        - ".env*"
        - "*.pem"
        - "*.key"
        - "credentials.*"
        - "secrets.*"

    # 수정 파일 수 제한
    max_files_per_run: 20

    # 위험 패턴 감지 — Plan Doc에서 감지 시 auto 모드 차단
    risk_patterns:
        - "database migration"
        - "authentication"
        - "payment"
        - "delete.*production"
```

**Execution Grant 발급**:

```yaml
execution_grant:
    run_id: string
    approved_by: string        # 사람 ID 또는 "policy-auto"
    workspace_type: worktree | docker | vm
    scope:
        allowed_files: list      # Plan Doc의 수정 파일 후보
        forbidden_paths: list    # 정책에서 가져옴
    secrets_scope: list        # 주입 허용된 환경변수 키 목록
    max_retries: int
    granted_at: timestamp
    expires_at: timestamp      # 유효 기간 (기본: 4시간)
```

### --auto 모드의 조건

`--auto` 모드는 사람 승인을 생략하지만, 아래 조건을 모두 충족해야 한다.

1. workspace가 격리 환경(docker, vm)일 것
2. 멀티 AI 리뷰 통과
3. Policy Gate의 risk_patterns에 해당하지 않을 것
4. 수정 파일 수가 max_files_per_run 이하일 것
5. forbidden_paths에 해당하는 파일이 없을 것

하나라도 위반 시 `human-reviewed` 모드로 fallback한다.

---

## L5: Execution Plane — 격리 실행

### 역할

Execution Grant를 받아 격리된 workspace를 준비하고, Executor AI CLI가 Plan Doc을 기준으로 코드를 수정한다.
이 레이어의 AI CLI는 **승인된 workspace 내부에서만 쓰기 권한**을 가진다.

### Workspace 프로비저닝

#### Git Worktree

```bash
# worktree 생성
git worktree add .agent/workspaces/{run_id} -b agent/{run_id}

# 작업 완료 후 정리
git worktree remove .agent/workspaces/{run_id}
git branch -d agent/{run_id}
```

**장점**: 빠른 생성(< 1초), 원본 repo와 파일 시스템 공유, 별도 도구 불필요
**단점**: 네트워크/프로세스 격리 없음, 로컬 파일 시스템에 대한 접근 가능
**적합한 경우**: 개인 사용, human-reviewed 모드, 빠른 반복

#### Docker Container

```yaml
# docker-compose.agent.yml
services:
    executor:
        build:
            context: .
            dockerfile: .agent/Dockerfile
        volumes:
            - ./:/workspace:ro          # 원본 repo는 읽기 전용 마운트
            - workspace_data:/work      # 작업 디렉토리는 별도 볼륨
        environment:
            - PLAN_DOC_PATH=/workspace/.agent/plans/${RUN_ID}.md
        env_file:
            - .agent/secrets/${RUN_ID}.env   # scoped secrets
        network_mode: "none"          # 네트워크 차단 (또는 allowlist)
        mem_limit: 4g
        cpus: 2
```

**장점**: 네트워크 격리, 프로세스 격리, 재현 가능한 환경
**단점**: 이미지 빌드 시간, 볼륨 마운트 설정 필요
**적합한 경우**: 팀 환경, --auto 모드, 높은 안전성 요구

### Scoped Secrets 주입

Executor에게 주입하는 환경변수는 최소 범위로 제한한다.

```text
주입 허용:
    → 테스트에 필요한 DB 접속 정보 (테스트 DB만)
    → API 테스트용 토큰 (제한된 scope)
    → CI 관련 변수

주입 금지:
    → 프로덕션 DB 접속 정보
    → 프로덕션 API 키
    → 배포 관련 자격증명
    → 개인 SSH 키
```

**구현**: `.agent/secrets/{run_id}.env` 파일을 Execution Grant 발급 시 생성하고, run 종료 시 삭제한다.

### Executor AI CLI 실행

Executor는 Plan Doc을 입력으로 받아 코드를 수정한다.

```text
역할: 코드 실행자. Plan Doc의 수정 계획을 구현하라.
권한: workspace 내부 파일 읽기/쓰기, 테스트 실행, lint 실행.
      workspace 외부 접근 금지. Git push 금지. commit은 로컬만 허용.
입력: Plan Doc, workspace 경로
출력: 수정된 코드 (workspace 내부), workspace 로그
제약: Plan Doc의 '수정 파일 후보'에 명시된 파일만 수정 가능.
```

**AI CLI별 구현**:

| AI CLI          | Executor 실행 방법                                       |
|-----------------|------------------------------------------------------|
| **Claude Code** | 별도 프로세스, `--system-prompt`로 역할 주입, workspace 경로에서 실행 |
| **Codex**       | `--approval-mode full-auto`, workspace 경로 지정         |
| **Gemini CLI**  | 별도 프로세스, workspace 경로에서 실행                           |

**병렬 실행**: Plan Doc의 작업 계획이 독립적인 파일 그룹으로 나뉠 경우, 복수 Executor를 병렬 실행할 수 있다.
단, 파일 간 의존성이 있으면 직렬 실행해야 한다.

---

## L6: Verification & Recovery — 검증과 복구

### 역할

Executor의 결과물을 **내부 루프**(결정론적 Gate)와 **외부 루프**(멀티 AI 리뷰)로 검증한다.
실패 시 구조화된 피드백을 생성하여 Executor에게 수정을 지시한다.

### 내부 루프: Deterministic Gates

Gate는 하드코딩된 스크립트로, AI가 우회할 수 없다.

```bash
#!/bin/bash
# .agent/gates/run-gates.sh
# 종료 코드가 0이 아니면 실패

set -euo pipefail

WORKSPACE=$1

cd "$WORKSPACE"

echo "=== Gate 1: Format ==="
# 프로젝트의 기존 포맷터 사용
make format-check 2>&1 || { echo "GATE_FAIL: format"; exit 1; }

echo "=== Gate 2: Lint ==="
make lint 2>&1 || { echo "GATE_FAIL: lint"; exit 1; }

echo "=== Gate 3: Type Check ==="
make typecheck 2>&1 || { echo "GATE_FAIL: typecheck"; exit 1; }

echo "=== Gate 4: Unit Tests ==="
make test 2>&1 || { echo "GATE_FAIL: test"; exit 1; }

echo "=== All gates passed ==="
exit 0
```

**핵심 원칙**: Gate는 프로젝트의 기존 도구를 그대로 사용한다.
`make check`, `npm run lint`, `pytest` 등 프로젝트에 이미 있는 명령어를 호출한다.
에이전트 전용 검증 도구를 만들지 않는다.

**Gate 실패 시**: 오류 메시지를 Executor에게 전달하고 즉시 수정을 시도한다.
이 내부 루프는 외부 retry 카운트에 포함하지 않는다.
단, 내부 루프도 최대 횟수를 설정한다(기본: 5회). 초과 시 외부 retry로 전이한다.

### Selective / Integration Checks

Gate를 모두 통과한 후, 선택적으로 통합 테스트를 실행한다.

**실행 조건**: 프로젝트에 통합 테스트가 존재하고, Plan Doc의 수정 범위가 통합 테스트 대상에 해당할 때만 실행한다.
모든 run에 통합 테스트를 돌리면 비용과 시간이 과도하다.

**선별 기준**:

- 수정된 파일이 API 엔드포인트에 해당하면 API 통합 테스트 실행
- 수정된 파일이 DB 레이어에 해당하면 DB 통합 테스트 실행
- 수정 범위가 단일 유틸 함수라면 통합 테스트 생략

### 외부 루프: 멀티 AI 리뷰

Gate를 통과한 diff를 복수 AI 모델이 병렬로 검증한다.

#### 리뷰어 실행 구현

각 리뷰어는 독립된 AI CLI 프로세스로 실행된다.

```text
Reviewer A — 기획 대조:
    입력: Plan Doc + diff
    프롬프트: "Plan Doc의 변경 목표와 수정 파일 후보를 기준으로,
              diff가 요구사항을 충족하는지 검증하라.
              누락된 요구사항, 범위 이탈을 식별하라."
    출력: review_a.json (pass/fail + findings)

Reviewer B — 품질 검증:
    입력: diff + gate logs
    프롬프트: "diff에서 경계 조건, 사이드 이펙트, 회귀 위험을 검증하라.
              정적 분석으로 잡을 수 없는 논리 오류를 식별하라."
    출력: review_b.json (pass/fail + findings)

Reviewer C — 테스트 검증:
    입력: diff + Plan Doc의 테스트 시나리오
    프롬프트: "테스트 케이스가 Plan Doc의 테스트 시나리오를 커버하는지 검증하라.
              테스트 누락, 구현 정합성 문제, 잠재적 버그를 식별하라."
    출력: review_c.json (pass/fail + findings)
```

**리뷰 문서 포맷**:

```yaml
review:
    reviewer: "A" | "B" | "C"
    model: string              # 사용된 모델 (예: claude-opus-4-6)
    verdict: pass | fail
    confidence: high | medium | low
    findings:
        -   severity: critical | major | minor | info
            category: requirement_gap | logic_error | edge_case | test_gap | regression_risk
            location: string        # 파일:라인 또는 함수명
            description: string
            suggestion: string?     # 수정 제안 (있는 경우)
    summary: string             # 한 줄 요약
```

#### Judge Controller 구현

Judge는 복수 리뷰 결과를 종합하여 최종 판정을 내린다.
Judge 자체는 결정론적 규칙으로 구현하거나, AI를 사용할 수 있다.

**결정론적 판정 규칙 (기본)**:

```text
1. 어떤 리뷰어든 critical finding이 있으면 → fail
2. major finding이 2개 이상이면 → fail
3. 리뷰어 간 verdict가 불일치하면 (2:1 split) → 보수적 fail
4. 모든 리뷰어가 pass이면 → pass
5. 실패 시 retry_count 확인:
    → retry_count < max_retries: fix (구조화된 피드백 생성)
    → retry_count >= max_retries: escalate
```

**구조화된 피드백 생성**:

Judge가 fail을 판정하면, 모든 리뷰어의 findings를 수정 가능한 피드백으로 변환한다.

```yaml
fix_feedback:
    run_id: string
    retry_attempt: int
    issues:
        -   priority: 1           # 가장 먼저 수정
            file: string
            description: string
            suggestion: string
        -   priority: 2
            ...
    context: string            # 이전 시도에서 반복된 문제가 있으면 명시
```

### 재시도 카운트 관리

```text
내부 루프 (Gate 실패):
    → 별도 카운트 (기본 max: 5)
    → Gate 실패는 명확한 오류이므로 즉시 수정 가능
    → 내부 루프 초과 시 외부 retry 1회로 전이

외부 루프 (AI 리뷰 실패):
    → 외부 retry 카운트 (기본 max: 3)
    → 구조화된 피드백 기반 수정
    → 초과 시 escalate → failure report 생성

전체 제한:
    → max_retries는 Execution Grant에 명시
    → 기본값은 프로젝트 설정 파일에서 로드
```

---

## L7: Output & Trace — 산출물 발행과 추적

### 역할

검증을 통과한 결과물을 commit/PR로 발행하거나, 실패 리포트를 작성한다.
**publish 권한은 이 레이어만 보유한다.**

### Commit / PR 생성

```text
1. workspace의 diff를 원본 repo의 agent 브랜치에 적용
    → worktree: 이미 브랜치가 존재 (agent/{run_id})
    → docker: diff를 추출하여 원본 repo에 적용

2. commit 메시지 생성
    → Plan Doc의 변경 목표를 기반으로 작성
    → 자동 생성 표시 포함

3. PR 생성 (설정에 따라)
    → PR 본문에 Plan Doc 요약 포함
    → Gate 결과와 리뷰 결과 첨부
    → 라벨 자동 추가 (예: agent-generated)
```

**commit 메시지 포맷**:

```text
{type}: {Plan Doc 변경 목표 요약}

Plan: .agent/plans/{run_id}.md
Gate: all passed (format, lint, typecheck, test)
Review: 3/3 reviewers passed

Generated-by: local-dev-agent
Run-ID: {run_id}
```

### Failure Report 생성

retry 초과 또는 escalate 판정 시 실패 리포트를 작성한다.

```markdown
# Failure Report: {run_id}

## 요청

{원본 task_request.prompt}

## 시도 이력

- Attempt 1: {gate 결과} → {review 결과} → {판정}
- Attempt 2: {gate 결과} → {review 결과} → {판정}
- Attempt 3: {gate 결과} → {review 결과} → {escalate 사유}

## 미해결 문제

{마지막 시도의 review findings 중 해결되지 않은 것}

## 권장 조치

{Judge가 생성한 사람을 위한 조언}
```

**저장 경로**: `.agent/reports/{run_id}-failure.md`

### Artifact Store

모든 run의 산출물을 보관한다. 디버깅, 감사, 학습에 활용한다.

```text
.agent/
├── plans/            # Plan Doc
│   └── {run_id}.md
├── reviews/          # 리뷰 문서
│   └── {run_id}/
│       ├── review_a.json
│       ├── review_b.json
│       ├── review_c.json
│       └── judge_result.json
├── reports/          # 실패 리포트
│   └── {run_id}-failure.md
├── logs/             # Gate 실행 로그
│   └── {run_id}/
│       ├── gate.log
│       └── executor.log
├── workspaces/       # 활성 workspace (임시)
│   └── {run_id}/
├── secrets/          # scoped secrets (임시)
│   └── {run_id}.env
└── config.yaml       # 프로젝트 설정
```

**보관 정책**:

- 성공한 run: plan, review, judge_result만 30일 보관
- 실패한 run: 전체 artifact 90일 보관
- workspace와 secrets: run 종료 즉시 삭제

### 알림 발송

산출물 완성 후 요청자에게 알림을 보낸다. 진입 채널에 따라 방식이 다르다.

| 채널         | 성공 시                           | 실패 시                       |
|------------|--------------------------------|----------------------------|
| **CLI**    | 터미널 출력 (PR URL 또는 commit hash) | 터미널 출력 (실패 리포트 경로)         |
| **Web UI** | 웹 알림 (PR 링크)                   | 웹 알림 (실패 리포트 링크)           |
| **메신저**    | 원본 thread에 완료 메시지 + PR 링크      | 원본 thread에 실패 메시지 + 리포트 요약 |

---

## 프로젝트 설정

프로젝트별 설정은 `.agent/config.yaml`에 저장한다.

```yaml
# .agent/config.yaml
agent:
    # 기본 실행 모드
    default_mode: human-reviewed    # human-reviewed | auto

    # 기본 workspace 유형
    default_workspace: worktree     # worktree | docker | vm

    # 재시도 설정
    retry:
        inner_max: 5                  # Gate 실패 시 내부 루프 최대 횟수
        outer_max: 3                  # AI 리뷰 실패 시 외부 루프 최대 횟수

    # 승인 대기 타임아웃
    approval_timeout: 24h

    # Execution Grant 유효 기간
    grant_ttl: 4h

    # AI CLI 설정
    cli:
        main: claude-code             # 오케스트레이터용
        executor: claude-code         # 코드 실행용
        reviewer_models: # 멀티 AI 리뷰어
            - claude-opus-4-6
            - gpt-5.4
            - gpt-5.3-codex

    # Gate 명령어 (프로젝트의 기존 도구)
    gates:
        format: "make format-check"
        lint: "make lint"
        typecheck: "make typecheck"
        test: "make test"
        integration: "make test-integration"   # 선택적

    # Policy 설정
    policy:
        forbidden_paths:
            - ".env*"
            - "*.pem"
            - "*.key"
        max_files_per_run: 20
        risk_patterns:
            - "database migration"
            - "authentication"
            - "payment"

    # 보관 정책
    retention:
        success_days: 30
        failure_days: 90

    # Artifact 경로 (기본값)
    paths:
        plans: ".agent/plans"
        reviews: ".agent/reviews"
        reports: ".agent/reports"
        logs: ".agent/logs"
        workspaces: ".agent/workspaces"
        secrets: ".agent/secrets"
```

---

## 하네스 구현 우선순위

전체 시스템을 한 번에 구축하는 것은 비현실적이다.
아래 순서로 점진적으로 구현한다.

### Phase 1: 최소 루프 (코어)

- L3: Main AI CLI로 Plan Doc 작성 (수동 실행)
- L4: CLI에서 Plan Doc 확인 후 수동 승인
- L5: Git worktree 기반 Executor 실행 (수동 실행)
- L6: Gate 스크립트 실행 (기존 `make check` 활용)
- L7: 수동 commit/PR

이 단계에서는 하네스 코드가 거의 없다.
AI CLI를 수동으로 실행하되, Plan Doc 작성 → 승인 → 실행 → Gate의 흐름을 사람이 조율한다.
**핵심은 흐름을 먼저 검증하는 것**이다.

### Phase 2: 자동화 (하네스)

- L1: CLI 진입점 구현 (task_request 생성)
- L2: SQLite 기반 State Store, 동시 실행 방지
- L3-L7: 하네스 스크립트가 AI CLI 프로세스를 자동 실행
- Gate 실패 시 자동 수정 루프

이 단계에서 사람은 Plan Doc 승인만 하고, 나머지는 자동이다.

### Phase 3: 멀티 AI 리뷰

- L3: 기획 검증용 멀티 AI 리뷰 추가
- L6: 코드 검증용 멀티 AI 리뷰 + Judge 판정
- 리뷰 결과 저장과 Artifact Store

### Phase 4: 격리와 확장

- L5: Docker 기반 격리 실행 환경
- L4: Policy Gate 구현, --auto 모드
- L1: Web UI, 메신저 채널 추가
- L2: 큐잉, 병렬 실행

---

## 검토 사항

### 결정 필요

- 내부 루프(Gate 실패) 최대 횟수: 5회가 적절한가?
- 외부 루프(AI 리뷰 실패) 최대 횟수: 3회가 적절한가? Minions는 2회
- 리뷰어 모델 구성: 프로젝트별 설정인가, 전역 고정인가?
- Judge 판정을 결정론적 규칙으로 할 것인가, AI로 할 것인가?

### 미결정 사항

- 리뷰 문서 수집 타임아웃: 리뷰어 하나가 응답하지 않으면?
- 비용 추적: 모델별 API 호출 비용을 run 단위로 추적할 것인가?
- 학습 피드백: 성공/실패 패턴에서 프롬프트를 개선하는 루프가 필요한가?
- 멀티 repo 지원: 하나의 task가 여러 repo에 걸칠 때의 처리

---

## 참고 자료

- [워크플로우 다이어그램](/.draft/dev-automation/00-workflow.md)
- [Stripe Minions 개요](/stripe-minions/01-stripe-minions.md)
- [Stripe Minions 시스템 설계](/stripe-minions/02-stripe-minions-part2.md)
- [Auto Improve Loop](/auto-improve/01-auto-improve-loop.md)
- [에이전틱 AI 설계 패턴 (Anthropic)](/effective-agents/README.md)
- [에이전트 디자인 패턴 (Google Cloud)](/design-pattern/README.md)
