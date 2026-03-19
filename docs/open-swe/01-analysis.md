# Open SWE 아키텍처 및 워크플로우 분석

## 1. 개요

- 저장소: `langchain-ai/open-swe`
- 성격: LangGraph 기반의 자율 소프트웨어 엔지니어링 에이전트 프레임워크
- 핵심 기반: LangGraph 런타임 + Deep Agents harness (`create_deep_agent`)
- 주요 목표: Slack/Linear/GitHub에서 `@openswe` 호출 → 격리된 샌드박스에서 코드 수정 → Draft PR 생성까지 파이프라인화

Open SWE의 핵심은 Deep Agents의 범용 코딩 루프를 재사용하면서, 조직별 외부 시스템 연동과 결정적 안전장치를 얹는 구조다.

### 기술 스택

| 구분         | 기술                                                        |
|------------|-----------------------------------------------------------|
| 에이전트 프레임워크 | LangGraph, Deep Agents (`create_deep_agent`)              |
| LLM        | Anthropic Claude Opus 4.6 (기본), OpenAI 호환                 |
| 웹 서버       | FastAPI                                                   |
| 샌드박스       | LangSmith (기본), Daytona, Modal, Runloop, Local            |
| 인증         | GitHub App (JWT), GitHub OAuth (LangSmith 경유), Fernet 암호화 |
| 외부 연동      | GitHub REST/GraphQL API, Linear GraphQL API, Slack API    |
| 모니터링       | LangSmith 트레이싱                                            |

### 배포 구성 (`langgraph.json`)

```json
{
    "graphs": {
        "agent": "agent.server:get_agent"
    },
    "http": {
        "app": "agent.webapp:app"
    },
    "python_version": "3.12",
    "dependencies": [
        "."
    ],
    "env": ".env"
}
```

- `agent.server:get_agent`: LangGraph 플랫폼이 런을 실행할 때 호출하는 에이전트 팩토리
- `agent.webapp:app`: FastAPI 앱으로 웹훅 엔드포인트 제공 (직접 `get_agent()` 호출 안함)
- `make dev`: `langgraph dev`
- `make run`: `uvicorn agent.webapp:app --reload --port 8000`

---

## 2. 아키텍처 계층

시스템은 5개 계층으로 구성되며, 의존 방향은 상위 → 하위로 단방향이다.

### 2.1 Ingress 계층 — `webapp.py`

외부 webhook payload를 받아 내부 실행 문맥으로 변환하는 진입점이다.

| 엔드포인트                   | 트리거 조건                                 | 처리 함수                                                    |
|-------------------------|----------------------------------------|----------------------------------------------------------|
| `POST /webhooks/slack`  | 앱 멘션 또는 봇 태그 포함                        | `process_slack_mention()`                                |
| `POST /webhooks/linear` | `@openswe` 포함 코멘트 생성                   | `process_linear_issue()`                                 |
| `POST /webhooks/github` | `@openswe`/`@open-swe` 태그 포함 이슈/PR 코멘트 | `process_github_issue()` / `process_github_pr_comment()` |
| `GET /health`           | -                                      | 헬스체크                                                     |

**핵심 역할:**

- source별 서명 검증 (HMAC-SHA256, Slack 서명)
- 이벤트 유형 필터링 및 봇 메시지 무시
- 결정론적 thread ID 생성
- `runs.create()` 또는 `store.put_item()` 호출 (직접 에이전트를 실행하지 않음)

중요한 점은 `webapp.py`가 저장소를 직접 수정하거나 `get_agent()`를 직접 호출하지 않는다는 것이다. 실제 저장소 조작은 LangGraph Runtime이 `server.py:get_agent`를
호출한 뒤 샌드박스 안에서만 일어난다.

### 2.2 Thread 조율 계층 — LangGraph

작업의 지속 상태를 관리하는 계층이다.

| 상태                                                                                                            | 저장 위치                       | 수명      | 용도                         |
|---------------------------------------------------------------------------------------------------------------|-----------------------------|---------|----------------------------|
| 대화 히스토리                                                                                                       | LangGraph Thread (messages) | 스레드 수명  | LLM 컨텍스트                   |
| source별 실행 문맥 (`source`, `repo`, `linear_issue`, `slack_thread`, `github_issue`, `github_login`, `pr_number`) | LangGraph configurable      | run 수명  | source별 컨텍스트 전달            |
| thread metadata (`sandbox_id`, `repo_dir`, `github_token_encrypted`, `repo`)                                  | LangGraph thread metadata   | 스레드 수명  | 샌드박스 재연결, 저장소 위치, 인증 토큰 유지 |
| 샌드박스 인스턴스                                                                                                     | `SANDBOX_BACKENDS` (메모리)    | 프로세스 수명 | 빠른 재사용                     |
| 큐 메시지 (`("queue", thread_id) / pending_messages`)                                                             | LangGraph Store             | 소비 시 삭제 | busy 상태의 후속 요청 전달          |
| Git branch (`open-swe/{thread_id}`)                                                                           | Git branch                  | PR 수명   | PR follow-up의 thread 복구 기준 |
| 저장소 코드                                                                                                        | 샌드박스 파일시스템                  | 샌드박스 수명 | 코드 수정/실행                   |

**상태 변화의 3가지 축:**

1. **외부 이벤트 → 내부 실행 문맥**: webhook payload가 `configurable`과 prompt로 변환
2. **thread 상태 축적**: repo 선택, sandbox ID, encrypted token, queued message가 thread에 누적
3. **sandbox 작업 → 외부 반영**: sandbox 내부 Git 변경 → branch push → Draft PR → source 채널 회신

### 2.3 Agent Runtime 계층 — `server.py`, `prompt.py`, `middleware/`

`get_agent(config)` 함수가 핵심 진입점이다. LangGraph 플랫폼이 런을 실행할 때 이 함수를 호출한다.

**처리 순서:**

1. 스레드 메타데이터에서 `sandbox_id` 조회
2. 캐시된 샌드박스 확인 → 없으면 새로 생성
3. 저장소 클론 또는 최신 변경사항 pull
4. 시스템 프롬프트 구성 (AGENTS.md 포함)
5. `create_deep_agent(model, system_prompt, tools, backend, middleware)` 호출

**주요 상수:**

- `DEFAULT_RECURSION_LIMIT = 1_000`: 최대 ReAct 루프 횟수
- `SANDBOX_CREATION_TIMEOUT = 180`: 샌드박스 생성 대기 최대 시간(초)
- `SANDBOX_CREATING = "__creating__"`: 샌드박스 생성 중 센티널 값

### 2.4 Tool / Integration 계층

#### 도구 (6종)

| 도구                   | 기능                                    | 실행 환경              |
|----------------------|---------------------------------------|--------------------|
| `commit_and_open_pr` | git add → commit → push → Draft PR 생성 | 샌드박스 + GitHub API  |
| `fetch_url`          | URL 페치 후 HTML → Markdown 변환           | 에이전트 프로세스          |
| `http_request`       | 범용 HTTP 요청 (SSRF 보호 내장)               | 에이전트 프로세스          |
| `github_comment`     | GitHub 이슈/PR에 코멘트 작성                  | GitHub API         |
| `linear_comment`     | Linear 이슈에 코멘트 작성                     | Linear GraphQL API |
| `slack_thread_reply` | Slack 스레드에 답변 작성                      | Slack API          |

이 커스텀 도구에 Deep Agents 내장 도구(파일, 셸, 계획, 서브에이전트)가 합쳐져 실제 작업 루프를 구성한다.

#### 미들웨어 (4종)

| 미들웨어                               | 시점                | 역할                                                                                               |
|------------------------------------|-------------------|--------------------------------------------------------------------------------------------------|
| `check_message_queue_before_model` | `@before_model`   | Store에서 큐 메시지를 가져와 대화에 주입                                                                        |
| `ToolErrorMiddleware`              | `AgentMiddleware` | 도구 예외를 JSON ToolMessage로 변환하여 크래시 방지                                                             |
| `ensure_no_empty_msg`              | `@after_model`    | 도구 호출 없는 빈 응답에 `no_op` 주입하여 조기 종료 방지                                                             |
| `open_pr_if_needed`                | `@after_agent`    | `commit_and_open_pr` 관련 payload를 메시지에서 찾은 경우에만 후처리를 시도. 이미 `success` 필드가 있거나 도구 호출 기록이 없으면 skip |

미들웨어는 비결정적 LLM 루프 주위에 결정적 제어를 추가하는 설계다. "모델이 잘하면 좋고, 못해도 시스템이 망가지지 않게" 만드는 실무형 접근이다.

#### 샌드박스 백엔드

| 백엔드       | 용도                  |
|-----------|---------------------|
| LangSmith | 기본 cloud sandbox    |
| Daytona   | 대체 sandbox provider |
| Modal     | 대체 sandbox provider |
| Runloop   | 대체 sandbox provider |
| Local     | 로컬 셸 (개발 전용)        |

설계 원칙: **경계 밖 권한 최소화, 경계 안 실행 자유도 최대화**. 스레드 단위로 샌드박스를 재사용해 후속 지시를 같은 작업 문맥에서 처리한다.

### 2.5 External Systems 계층

GitHub API, Slack API, Linear GraphQL API, LangSmith, sandbox provider 등 외부 서비스.

---

## 3. 워크플로우 분석

### 3.1 공통 실행 흐름

모든 source는 세부 사항은 다르지만 같은 큰 흐름으로 수렴한다.

1. **웹훅 수신**: `webapp.py`가 외부 이벤트를 수신
2. **요청 검증**: source별 서명 검증과 이벤트 유형 필터링
3. **저장소 및 thread 결정**: source별 규칙으로 `repo.owner/name`과 결정론적 thread ID 생성
4. **run 생성 또는 큐잉**: idle이면 새 LangGraph run 생성, busy면 큐에 적재 (Slack은 interrupt)
5. **에이전트 준비**: `get_agent()`가 GitHub 토큰 해석, sandbox 연결/생성, repo clone/pull, AGENTS.md 로드, 프롬프트 구성
6. **ReAct 루프**: 파일 탐색, 코드 수정, 외부 댓글 응답, PR 생성 등 수행
7. **결과 전파**: 변경사항이 있으면 보통 `commit_and_open_pr`로 PR을 만들고, 결과를 원본 채널에 회신

### 3.2 source별 차이점

#### Slack

- **저장소 결정 우선순위**: 메시지 내 `repo:owner/name` → GitHub URL 패턴 → 기존 thread metadata → 환경변수 기본값
- **컨텍스트 선택**: 마지막 봇 멘션 이후 메시지(`last_mention`) 또는 스레드 전체(`full_thread`)
- **busy 처리**: 기존 런을 interrupt하고 새 런 시작 (`multitask_strategy="interrupt"`)
- **추가 회신**: run 생성 후 Slack thread에 trace URL과 선택된 저장소 안내를 남김
- 선택된 저장소는 thread metadata에 저장되어 이후 메시지에서 재사용

#### Linear

- **트리거 조건**: `Comment create` 이벤트이면서 `@openswe`가 포함된 코멘트만 처리
- **저장소 결정**: `LINEAR_TEAM_TO_REPO` 매핑으로 팀/프로젝트에서 GitHub 저장소 결정. 중첩 매핑(팀 → 프로젝트 → 저장소)과 단일 매핑(팀 → 저장소) 모두 지원
- **사용자 식별**: 코멘트 작성자 → 이슈 생성자 → 담당자 순으로 이메일을 해석
- **멀티모달 지원**: description과 최근 코멘트에서 이미지 URL을 추출하여 시각 컨텍스트로 전달
- **busy 처리**: 큐에 텍스트/이미지 payload를 저장하여 다음 모델 호출 전에 주입
- **추가 회신**: run 생성 후 Linear 이슈에 LangSmith trace URL 코멘트를 남김

#### GitHub Issue

- **이벤트 유형**: `issue_comment`, `issues` (opened/edited/reopened)
- **트리거 조건**: issue 본문 또는 comment에 `@openswe`/`@open-swe`가 있을 때만 처리
- **thread 분기**: 기존 thread가 없으면 전체 이슈 컨텍스트 프롬프트, 있으면 후속 코멘트/업데이트 프롬프트
- **보안**: `GITHUB_USER_EMAIL_MAP`에 없는 작성자의 코멘트 본문은
  `<dangerous-external-untrusted-users-comment>` 태그로 래핑되어 프롬프트 인젝션 위험을 낮춘다

#### GitHub PR 코멘트

- **thread 복구**: 브랜치명(`open-swe/{uuid}`)에서 thread_id를 추출하여 기존 샌드박스 재사용
- **이벤트 유형**: `pull_request_review_comment`, `pull_request_review`, PR 위의 `issue_comment`
- **초기 반응**: 처리 시작 시 GitHub 코멘트에 👀 reaction을 남김
- **코멘트 수집**: `fetch_pr_comments_since_last_tag()`가 3개 소스(일반 코멘트, 인라인 리뷰 코멘트, 리뷰 본문) 병합
- 브랜치명에 thread ID가 없으면 처리하지 않음

### 3.3 thread ID 생성 방식

| 트리거          | 생성 방식                                         |
|--------------|-----------------------------------------------|
| Linear       | `SHA256("linear-issue:{issue_id}")` → UUID 형식 |
| GitHub Issue | `SHA256("github-issue:{issue_id}")` → UUID 형식 |
| GitHub PR    | 브랜치명(`open-swe/{uuid}`)에서 UUID 추출             |
| Slack        | `MD5("{channel_id}:{thread_ts}")` → UUID      |

### 3.4 샌드박스 생명주기

1. **캐시 확인**: `SANDBOX_BACKENDS` 메모리 딕셔너리에서 `thread_id → SandboxBackendProtocol` 조회
2. **메타데이터 확인**: 캐시 없으면 thread metadata의 `sandbox_id`로 재연결 시도
3. **신규 생성**: sandbox_id가 없으면 `create_sandbox()` → 저장소 클론
4. **동시성 보호**: 한 스레드에서 생성 중(`__creating__`)이면 다른 런은 1초 간격 폴링 대기 (최대 180초)
5. **장애 복구**: `SandboxClientError` 발생 시 캐시 비우고 `_recreate_sandbox()`로 새로 생성
6. **종료**: 에이전트 종료 시 메모리에 캐싱하여 동일 thread 재실행 시 재사용

### 3.5 인증 데이터 흐름

**GitHub 소스만 thread 토큰 캐시를 먼저 조회한다.**

- `source == "github"`일 때만 `get_github_token_from_thread(thread_id)`로 기존 `github_token_encrypted`를 먼저 복호화해 재사용한다.
- 캐시가 없으면 `github_login`을 `GITHUB_USER_EMAIL_MAP`으로 이메일에 매핑한 뒤, 그 이메일로 LangSmith 기반 GitHub OAuth 토큰을 해결하고 다시 thread metadata에 저장한다.

**Slack/Linear는 매번 이메일 기반 인증 경로를 탄다.**

- Slack/Linear run은 `configurable.user_email`을 사용해 `save_encrypted_token_from_email(...)`를 호출한다.
- 성공 시 새 `github_token_encrypted`가 thread metadata에 저장되지만, 다음 Slack/Linear run이 시작될 때 이 값을 먼저 재사용하는 cache-first 흐름은 아니다.
- bot-token-only mode에서는 소스와 무관하게 GitHub App installation token을 발급해 thread metadata에 저장한다.

**인증 실패 응답은 source별로 다르다.**

- Slack/Linear는 `leave_failure_comment()`가 채널/이슈에 실패 안내를 남긴다.
- GitHub-triggered run은 토큰이 없으면 댓글을 남길 수 없어, 이메일 매핑 누락이나 OAuth 실패 같은 경로에서 로그만 남기고 사용자에게 가시적인 댓글을 남기지 않을 수 있다.

---

## 4. Deep Agents 결합 방식

Open SWE는 독자 에이전트 루프를 구현하지 않고, Deep Agents의 `create_deep_agent`에 모델/도구/미들웨어/백엔드를 주입하는 방식이다.

### 4.1 에이전트 조립

`get_agent()` → `create_deep_agent(model, system_prompt, tools, backend, middleware)` 호출. Deep Agents가 제공하는 기본 역량:

- **Planning**: `write_todos` (계획 수립 및 진행 추적)
- **Filesystem**: `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`
- **Shell**: `execute` (셸 명령 실행)
- **Sub-agent**: `task` (서브에이전트 위임)
- **Context Management**: 긴 대화/대출력 자동 요약 및 컨텍스트 유지

### 4.2 확장 포인트

Open SWE가 Deep Agents 위에 추가하는 것:

- 커스텀 도구 6종 (PR 생성, 외부 API 댓글 등)
- 미들웨어 4종 (큐 주입, 오류 처리, 빈 응답 방지, PR 후처리 분기)
- 샌드박스 백엔드 추상화 (5종 provider)
- source별 인증 체인

### 4.3 LangGraph 런타임 계승

Deep Agents가 LangGraph 기반이므로 스트리밍, 체크포인트, Thread 지속성, Store, LangSmith 트레이싱 등 런타임 기능을 그대로 활용한다.

---

## 5. 보안 설계

| 보안 영역       | 구현                                                         | 코드 위치                                         |
|-------------|------------------------------------------------------------|-----------------------------------------------|
| 웹훅 서명 검증    | GitHub HMAC-SHA256, Slack 서명 검증, Linear HMAC-SHA256        | `github_comments.py`, `slack.py`, `webapp.py` |
| SSRF 방지     | `_is_url_safe()`로 사설 IP/루프백/링크로컬 차단                        | `tools/http_request.py`                       |
| 토큰 보호       | Fernet 대칭 암호화, `sandbox.write()` 사용 (셸 히스토리 미노출)           | `encryption.py`, `utils/github.py`            |
| 자격증명 정리     | `cleanup_git_credentials()`로 `/tmp/.git-credentials` 즉시 삭제 | `utils/github.py`                             |
| 프롬프트 인젝션 방지 | 미등록 사용자 코멘트를 XML 태그로 래핑                                    | `github_comments.py`                          |
| 태그 새니타이즈    | 사용자 입력에서 신뢰 래퍼 태그 제거하여 위장 방지                               | `github_comments.py`                          |
| 조직 허용목록     | `ALLOWED_GITHUB_ORGS`로 접근 가능 저장소 제한                        | `webapp.py`                                   |

---

## 6. 디렉토리 구조

```
open-swe/
├── agent/                        # 핵심 애플리케이션
│   ├── server.py                 # 에이전트 팩토리 (get_agent)
│   ├── webapp.py                 # FastAPI 웹훅 핸들러
│   ├── prompt.py                 # 시스템 프롬프트 구성
│   ├── encryption.py             # Fernet 토큰 암호화/복호화
│   ├── middleware/               # 에이전트 미들웨어 (4종)
│   │   ├── tool_error_handler.py # 도구 실행 오류 핸들링
│   │   ├── ensure_no_empty_msg.py# 빈 응답 방지
│   │   ├── check_message_queue.py# 큐 메시지 주입
│   │   └── open_pr.py           # PR 후처리 미들웨어
│   ├── tools/                    # 커스텀 도구 (6종)
│   │   ├── commit_and_open_pr.py # 커밋 → 푸시 → Draft PR
│   │   ├── fetch_url.py          # URL → Markdown 변환
│   │   ├── http_request.py       # 범용 HTTP (SSRF 보호)
│   │   ├── github_comment.py     # GitHub 코멘트
│   │   ├── linear_comment.py     # Linear 코멘트
│   │   └── slack_thread_reply.py # Slack 스레드 답변
│   ├── integrations/             # 샌드박스 백엔드 (5종)
│   │   ├── langsmith.py          # LangSmith (기본)
│   │   ├── daytona.py
│   │   ├── modal.py
│   │   ├── runloop.py
│   │   └── local.py              # 로컬 (개발 전용)
│   └── utils/                    # 유틸리티 (18개 모듈)
│       ├── auth.py               # 인증 체인
│       ├── sandbox.py            # 샌드박스 팩토리
│       ├── sandbox_state.py      # 스레드별 캐싱
│       ├── sandbox_paths.py      # 경로 해석
│       ├── model.py              # LLM 초기화
│       ├── github.py             # Git 래퍼 + GitHub PR API
│       ├── github_app.py         # GitHub App JWT
│       ├── github_token.py       # 토큰 조회
│       ├── github_comments.py    # 코멘트 처리/서명 검증
│       ├── github_user_email_map.py # 로그인 → 이메일 매핑
│       ├── slack.py              # Slack API
│       ├── linear.py             # Linear GraphQL
│       ├── linear_team_repo_map.py  # 팀 → 저장소 매핑
│       ├── comments.py           # 코멘트 필터링
│       ├── messages.py           # 메시지 정규화
│       ├── multimodal.py         # 이미지 URL 추출/Base64
│       ├── langsmith.py          # LangSmith 통합
│       └── agents_md.py          # AGENTS.md 읽기
├── tests/
├── static/
├── langgraph.json
├── pyproject.toml
├── Dockerfile
└── Makefile
```

---

## 7. 환경변수

### 필수

| 변수명                    | 용도              |
|------------------------|-----------------|
| `TOKEN_ENCRYPTION_KEY` | Fernet 토큰 암호화 키 |
| `LANGSMITH_API_KEY`    | LangSmith API 키 |

### 샌드박스

| 변수명            | 용도                          |
|----------------|-----------------------------|
| `SANDBOX_TYPE` | 샌드박스 백엔드 선택 (기본: langsmith) |

### GitHub 연동

| 변수명                          | 용도                       |
|------------------------------|--------------------------|
| `GITHUB_APP_ID`              | GitHub App ID            |
| `GITHUB_APP_PRIVATE_KEY`     | GitHub App RSA 개인키 (PEM) |
| `GITHUB_APP_INSTALLATION_ID` | GitHub App 설치 ID         |
| `GITHUB_WEBHOOK_SECRET`      | GitHub 웹훅 HMAC 시크릿       |
| `ALLOWED_GITHUB_ORGS`        | 허용 GitHub 조직 (쉼표 구분)     |

### Slack 연동

| 변수명                                    | 용도                                 |
|----------------------------------------|------------------------------------|
| `SLACK_BOT_TOKEN`                      | Bot OAuth 토큰                       |
| `SLACK_SIGNING_SECRET`                 | 서명 검증 시크릿                          |
| `SLACK_BOT_USER_ID`                    | 봇 사용자 ID                           |
| `SLACK_BOT_USERNAME`                   | 봇 사용자명                             |
| `SLACK_REPO_OWNER` / `SLACK_REPO_NAME` | 기본 저장소 (기본: langchain-ai/open-swe) |

### Linear 연동

| 변수명                     | 용도           |
|-------------------------|--------------|
| `LINEAR_API_KEY`        | Linear API 키 |
| `LINEAR_WEBHOOK_SECRET` | 웹훅 HMAC 시크릿  |

### LangSmith 인증

| 변수명                                 | 용도                                    |
|-------------------------------------|---------------------------------------|
| `LANGSMITH_API_KEY_PROD`            | 프로덕션 API 키 (사용자 OAuth 조회)             |
| `LANGSMITH_URL_PROD`                | LangSmith 프로덕션 URL (trace URL 생성)     |
| `LANGSMITH_TENANT_ID_PROD`          | LangSmith 테넌트 ID (trace URL 생성)       |
| `LANGSMITH_TRACING_PROJECT_ID_PROD` | LangSmith 트레이싱 프로젝트 ID (trace URL 생성) |
| `GITHUB_OAUTH_PROVIDER_ID`          | LangSmith GitHub OAuth 프로바이더 ID       |
| `X_SERVICE_AUTH_JWT_SECRET`         | LangSmith 연계 서비스 인증용 JWT 시크릿          |

### 런타임 / 배포

| 변수명                     | 용도                        |
|-------------------------|---------------------------|
| `LANGGRAPH_URL`         | LangGraph 플랫폼 URL         |
| `LANGGRAPH_URL_PROD`    | 프로덕션 LangGraph 플랫폼 URL    |
| `LANGCHAIN_REVISION_ID` | 배포 리비전 ID (에이전트 버전 메타데이터) |

---

## 8. 장점과 트레이드오프

### 장점

1. **빠른 내부 도입**: 트리거-샌드박스-PR 루프가 이미 연결되어 있어 조직 내부 코딩 에이전트를 빠르게 구축할 수 있다
2. **안전한 실행 경계**: 샌드박스 격리, 조직 허용목록, SSRF 보호, 프롬프트 인젝션 방지 등 다층 보안
3. **작업 연속성**: thread를 기준으로 sandbox와 인증 상태를 재사용하며, 실행 중 후속 메시지 주입 가능
4. **구성 가능한 기반**: 샌드박스/모델/도구/트리거/미들웨어를 교체할 수 있는 플러그 구조
5. **결정적 안전장치**: 미들웨어가 LLM의 비결정적 행동에 결정적 제어를 추가 (PR 후처리 분기, 오류 변환)

### 트레이드오프

1. **운영 복잡도**: GitHub App, OAuth, 3종 Webhook, 샌드박스 인프라, 암호화 키 등 초기 설정 부담
2. **도구/통합 품질 의존성**: GitHub/Slack/Linear API 연동 품질과 조직별 내부 도구 품질이 전체 성능에 직접 영향
3. **검증 자동화 한계**: 강한 결정론 검증(CI 게이트)을 추가하지 않으면 결과 품질 편차 가능

---

## 9. 참고 링크

- [Open SWE 저장소](https://github.com/langchain-ai/open-swe)
- [Open SWE Announcement](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/)
- [Open SWE README](https://raw.githubusercontent.com/langchain-ai/open-swe/main/README.md)
- [Open SWE Customization Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/CUSTOMIZATION.md)
- [Open SWE Installation Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/INSTALLATION.md)
- [Deep Agents 저장소](https://github.com/langchain-ai/deepagents)
- [Deep Agents 문서](https://docs.langchain.com/oss/python/deepagents/overview)
- [open-swe 소개](https://news.hada.io/topic?id=27604)
