# Oh My OpenAgent 설계 및 실행 플로우 분석

## 1. 프로젝트 개요

- 저장소: `code-yeongyu/oh-my-openagent`
- 패키지명: `oh-my-opencode` (`package.json`)
- 런타임: Bun + TypeScript 기반 OpenCode 플러그인
- 목표: 단일 에이전트/단일 모델 호출을 넘어서, **멀티 에이전트 + 멀티 모델 오케스트레이션** 제공

공식 문서에서는 이를 "계획과 실행의 분리(Planning/Execution Separation)"로 설명하며, Prometheus(계획)와 Atlas(실행)를 중심으로 구성합니다.

---

## 2. 플러그인 초기화 파이프라인

OpenCode CLI가 시작되면 `OhMyOpenCodePlugin`이 초기화됩니다. 이 과정은 5단계로 분리됩니다.

### 2.1 설정 로드 및 병합

`initConfigContext` + `loadPluginConfig`가 **3단계 설정 병합**을 수행합니다.

1. **Project 설정** — 프로젝트 루트의 로컬 설정 (최우선)
2. **User 설정** — 사용자 전역 설정
3. **Defaults** — 플러그인 기본값

이 병합 순서로 프로젝트별 커스터마이징과 사용자 기본값이 자연스럽게 공존합니다.

### 2.2 매니저 생성

설정 병합 후 4개의 매니저가 생성됩니다.

| 매니저                  | 역할                             |
|----------------------|--------------------------------|
| `TmuxSessionManager` | 터미널 세션 관리, interactive bash 지원 |
| `BackgroundManager`  | 백그라운드 태스크 관리 (동시성 제한: 5/모델)    |
| `SkillMcpManager`    | 스킬 및 MCP 서버 통합 관리              |
| `ConfigHandler`      | 런타임 설정 변경 처리                   |

### 2.3 도구 등록

매니저 생성 후 **26개 도구**가 등록됩니다. 스킬 컨텍스트와 카테고리 기반으로 동적 툴셋이 구성됩니다.

### 2.4 훅 생성

도구 등록 후 **46개 훅**이 생성됩니다.

훅은 3개 카테고리로 분류됩니다:

- **코어 훅 (37개)**: Session 관리, ToolGuard, Transform 등 기본 런타임 제어
- **연속 훅 (7개)**: Boulder(연속 실행), Atlas(오케스트레이션), Ralph(자기 참조 루프)
- **스킬 훅 (2개)**: 스킬 시스템 연동

### 2.5 플러그인 인터페이스 반환

모든 훅과 도구가 등록되면 플러그인 인터페이스가 반환되고 사용자 입력 대기 상태로 진입합니다.

---

## 3. 메시지 처리 파이프라인

사용자 메시지 입력부터 API 호출, 응답 반환까지 3단계로 처리됩니다.

### 3.1 1단계: 사전 개입 (chat.message)

`chat.message` 핸들러에서 아래 순서로 처리됩니다.

1. **세션 에이전트 설정** — 현재 세션의 에이전트 컨텍스트 확정
2. **First-Message Variant Gate** — 첫 메시지 여부에 따른 분기 처리
3. **모델 폴백 확인** — 보류 중인 폴백이 있으면 폴백 모델 적용, 없으면 세션 모델 설정
4. **stopContinuationGuard** — 연속 실행 중단 조건 확인
5. **backgroundNotificationHook** — 완료된 백그라운드 태스크 결과를 메인 세션에 알림
6. **keyword-detector** — `ultrawork`, `search`, `analyze` 등 특수 키워드 감지
7. **start-work 훅** — 작업 시작 전처리
8. **Atlas 훅** — 세션 유형 판별, 실패 횟수 확인, 에이전트 매칭

### 3.2 2단계: 메시지 전처리 (messages.transform)

사전 개입 완료 후 메시지 자체를 변환합니다.

- **contextInjectorMessagesTransform** — `AGENTS.md`, `README.md` 등 컨텍스트 파일을 메시지에 주입
- **thinkingBlockValidator** — 사고 블록(thinking block)의 구조적 유효성 검증

### 3.3 3단계: API 호출

변환된 메시지를 LLM에 전달합니다.

1. **system.transform** — 시스템 프롬프트 변환
2. **chat.params** — 헤더, 파라미터 설정
3. **LLM API 호출** — 모델별 프로바이더를 통해 실제 호출

응답은 3가지 경로로 분기됩니다:

- **텍스트** → 사용자에게 직접 표시
- **도구 호출** → 도구 실행 파이프라인으로 진입
- **에러** → 에러 처리 흐름으로 진입

---

## 4. 도구 실행 파이프라인

LLM이 도구 호출을 반환하면 Before → Execute → After 3단계로 처리됩니다.

### 4.1 Before 훅 (10개)

도구 실행 전 가드와 주입을 수행합니다.

| 순서 | 훅                         | 역할                               |
|----|---------------------------|----------------------------------|
| 1  | `writeExistingFileGuard`  | Write/Edit 전 Read 선행 여부 확인       |
| 2  | `claudeCodeHooks`         | settings.json 호환성 처리             |
| 3  | `commentChecker`          | AI 생성 코멘트 차단                     |
| 4  | `directoryAgentsInjector` | 디렉토리별 `AGENTS.md` 자동 주입          |
| 5  | `directoryReadmeInjector` | 디렉토리별 `README.md` 자동 주입          |
| 6  | `rulesInjector`           | 조건부 규칙 주입                        |
| 7  | `tasksTodowriteDisabler`  | 태스크 시스템 활성 시 TodoWrite 차단        |
| 8  | `sisyphusJuniorNotepad`   | 서브에이전트용 노트패드 주입                  |
| 9  | `atlasHook`               | Boulder 상태 관리                    |
| 10 | task 도구 분기                | task 도구면 서브에이전트 위임 처리, 아니면 직접 실행 |

`writeExistingFileGuard`는 파일 덮어쓰기 사고를 방지하는 안전장치입니다. `commentChecker`는 AI가 생성하는 불필요한 코멘트를 사전에 차단합니다.

### 4.2 도구 실행

실제 실행되는 도구는 4개 카테고리로 분류됩니다.

- **파일 조작**: Read, Write, Edit, Bash
- **정밀 분석**: LSP 6종, AST-grep
- **터미널**: Tmux `interactive_bash`
- **위임**: Task, `call_omo_agent`

### 4.3 After 훅 (8개)

실행 결과에 대한 후처리와 복구를 수행합니다.

| 순서 | 훅                           | 역할                   |
|----|-----------------------------|----------------------|
| 1  | `toolOutputTruncator`       | 출력 크기 제한             |
| 2  | `commentChecker`            | 사후 검증 (before에서도 동작) |
| 3  | `emptyTaskResponseDetector` | 빈 응답 감지              |
| 4  | `editErrorRecovery`         | 편집 실패 시 자동 재시도       |
| 5  | `delegateTaskRetry`         | 위임 실패 시 재시도          |
| 6  | `hashlineReadEnhancer`      | Read 출력에 라인 해시 추가    |
| 7  | `jsonErrorRecovery`         | JSON 파싱 에러 복구        |
| 8  | `atlasHook`                 | Boulder 상태 업데이트      |

After 훅의 핵심은 **자동 복구**입니다. `editErrorRecovery`와 `delegateTaskRetry`가 일시적 실패를 자동으로 재시도하며, `jsonErrorRecovery`가 파싱 오류를
보정합니다. 결과는 LLM의 다음 단계로 반환됩니다.

---

## 5. 에이전트 오케스트레이션

### 5.1 에이전트 계층 구조

시스템은 메인 오케스트레이터 **Sisyphus**를 정점으로 9개 전문 에이전트를 위임 체계로 운영합니다.

| 에이전트              | 역할                | 모델                            |
|-------------------|-------------------|-------------------------------|
| 🪨 **Sisyphus**   | 메인 오케스트레이터        | claude-opus-4-6 max           |
| 🔨 Hephaestus     | 자율 딥 워커 (심층 코딩)   | gpt-5.3-codex medium          |
| 🔥 Prometheus     | 전략 기획자            | claude-opus-4-6 max           |
| 🧠 Metis          | Pre-Planning 컨설턴트 | claude-opus-4-6 max, temp 0.3 |
| 🎭 Momus          | 플랜 리뷰어            | gpt-5.4 xhigh                 |
| 🔮 Oracle         | 읽기 전용 컨설턴트        | gpt-5.4 high                  |
| 🔍 Explore        | 코드베이스 검색          | grok-code-fast-1              |
| 📚 Librarian      | 외부 문서/코드 검색       | gemini-3-flash                |
| 👁️ Looker        | 이미지/PDF 분석        | gpt-5.3-codex medium          |
| ⚡ Sisyphus-Junior | 카테고리 실행자          | claude-sonnet-4-6             |

Sisyphus가 태스크 성격에 따라 적절한 에이전트에 위임하며, 모든 위임은 Sisyphus → 에이전트 단방향입니다.

**Atlas**(🗺️, claude-sonnet-4-6)는 Todo 오케스트레이터로, Sisyphus에게 Boulder 강제 실행을 지시하는 특수 위치에 있습니다.

### 5.2 도구 제한 정책

에이전트별로 사용 가능한 도구가 엄격히 제한됩니다.

| 에이전트      | 제한 사항                                |
|-----------|--------------------------------------|
| Oracle    | write, edit, task, call_omo_agent 금지 |
| Librarian | write, edit, task, call_omo_agent 금지 |
| Explore   | write, edit, task, call_omo_agent 금지 |
| Looker    | read 외 전부 금지                         |
| Momus     | write, edit, task 금지                 |

읽기 전용 에이전트(Oracle, Librarian, Explore)는 코드를 변경할 수 없고, Looker는 파일 읽기만 가능합니다. 이 제한은 에이전트 간 책임 분리와 안전성을 보장합니다.

### 5.3 에이전트 간 역할 분담 패턴

일반적인 작업 흐름에서 에이전트 간 역할 분담은 다음과 같습니다:

- **계획 수립**: Metis(사전 컨설팅) → Prometheus(전략 기획) → Momus(플랜 검토)
- **정보 수집**: Oracle(읽기 전용 자문) + Explore(코드 탐색) + Librarian(외부 문서)
- **실행**: Hephaestus(심층 코딩) + Sisyphus-Junior(카테고리별 실행)
- **시각 분석**: Looker(이미지/PDF)

---

## 6. 모델 폴백 체인

각 에이전트는 주 모델 실패 시 대체 모델로 자동 전환됩니다.

### 폴백 체인 구성

| 에이전트       | 1차                   | 2차             | 3차               | 4차         |
|------------|----------------------|----------------|------------------|------------|
| Sisyphus   | claude-opus-4-6 max  | kimi-k2.5      | gpt-5.4          | glm-5      |
| Hephaestus | gpt-5.3-codex medium | gpt-5.4 medium | -                | -          |
| Oracle     | gpt-5.4 high         | gemini-3.1-pro | claude-opus-4-6  | -          |
| Explore    | grok-code-fast-1     | minimax-m2.5   | claude-haiku-4-5 | gpt-5-nano |

### 에러 분류 및 처리

API 에러 발생 시 3단계로 분류됩니다:

1. **재시도 가능** — 같은 모델로 재시도 (일시적 오류, rate limit 등)
2. **폴백 필요** — 체인의 다음 모델로 전환 (모델 다운, 지속적 실패)
3. **치명적** — 실패 보고 후 중단 (인증 오류 등 복구 불가)

재시도 실패 시 자동으로 폴백 체인이 진행됩니다. 다양한 프로바이더(Anthropic, OpenAI, Google, xAI 등)를 섞어 단일 프로바이더 장애에 대한 복원력을 확보합니다.

---

## 7. Boulder 연속 실행 메커니즘

`todo-continuation-enforcer`로 구현된 Boulder는 미완료 TODO가 남아 있으면 LLM 작업을 자동으로 재개하는 메커니즘입니다.

### 7.1 기본 동작 흐름

1. **세션 대기(Idle)** 상태에서 `session.idle` 이벤트 발생
2. 미완료 TODO 존재 여부 확인
3. TODO가 있으면 **2초 카운트다운** 시작 (사용자 취소 가능)
4. 카운트다운 완료 후 **연속 프롬프트 주입**
5. LLM 작업 재개
6. 작업 완료 후 다시 Idle로 돌아가 반복

### 7.2 지수 백오프 (정체 감지)

작업이 진전 없이 반복 실패하면 지수 백오프가 적용됩니다.

| 실패 횟수 | 대기 시간   |
|-------|---------|
| 1회    | 30초     |
| 2회    | 60초     |
| 3회    | 120초    |
| 4회    | 240초    |
| 5회 이상 | 5분 일시정지 |

대기 후 다시 복구(Recovery)를 시도합니다. 사용자 취소 또는 에이전트 에러 시 즉시 중단됩니다.

---

## 8. Atlas 마스터 오케스트레이터

Atlas는 `session.idle` 이벤트를 받아 7단계 의사결정 게이트를 통해 다음 행동을 결정합니다.

### 의사결정 게이트 흐름

1. **세션 유형 판별** — `primary` 세션만 처리, `subagent` 세션은 스킵
2. **중단 조건 확인** — 중단이 필요하면 세션 중단
3. **실패 횟수 확인** — 임계값 초과 시 쿨다운 대기
4. **백그라운드 태스크 확인** — 완료 대기 중인 태스크가 있으면 대기
5. **에이전트 매칭** — 적절한 에이전트 매칭 시도, 실패 시 기본 행동
6. **플랜 완료도 확인** — 미완료면 Boulder 연속 실행, 완료면 다음 단계
7. **쿨다운 확인** — 쿨다운 중이면 대기, 아니면 작업 완료 처리

Atlas는 Boulder의 상위 제어자로서, Boulder가 "어떻게 연속 실행할지"를 담당한다면 Atlas는 "연속 실행을 할지 말지"를 결정합니다.

---

## 9. 백그라운드 태스크 병렬 실행

### 9.1 스폰 과정

`task()` 도구 호출 시 `LaunchInput`(description, prompt, category, subagent_type)을 구성하고, 3단계 검증을 거칩니다.

1. **스폰 예산 확인** — 초과 시 스폰 거부
2. **중첩 깊이 확인** — 초과 시 스폰 거부
3. **동시성 한도 확인** — 모델당 5개 제한, 초과 시 대기열 진입

검증 통과 후 서브에이전트가 스폰되어 **격리된 백그라운드 세션**에서 독립 실행됩니다.

### 9.2 실행 및 안전장치

백그라운드 세션은 자체 컨텍스트에서 독립적으로 실행됩니다. **서킷 브레이커**가 반복적 도구 사용 패턴을 감지하여 무한 루프를 방지합니다.

실패 시 폴백 가능 여부를 판단하여:

- 폴백 가능 → 폴백 모델로 재시도
- 폴백 불가 → 실패 결과 반환

### 9.3 결과 반환 경로

완료/실패/강제 중단 모두 `backgroundNotificationHook`을 통해 메인 세션에 알림됩니다.

1. **이력 저장** — `background tasks json`에 기록
2. **메인 세션 알림** — `chat.message` 응답 사이클에 결과 주입
3. **컨텍스트 업데이트** — Sisyphus가 결과를 받아 후속 작업 재개

이 구조로 메인 에이전트는 백그라운드 태스크 완료를 기다리지 않고 다른 작업을 수행할 수 있습니다.

---

## 10. Ralph Loop (자기 참조 개발 루프)

`/ralph-loop` 또는 `/ulw-loop` 명령으로 시작되는 자기 참조 개발 루프입니다.

### 동작 방식

1. **상태 초기화** — `.sisyphus/ralph-loop.local.md`에 상태 저장
2. **반복 시작** — 최대 100회 반복
3. **연속 프롬프트 빌드** — continuation prompt builder로 다음 프롬프트 구성
4. **LLM 실행 → 응답 분석**
5. **종료 판단** — `promise DONE` 태그 감지 시 루프 완료, 미감지 시 다음 반복

### 종료 조건

- **정상 종료**: `promise DONE` 태그 감지
- **최대 반복 초과**: 100회 도달
- **사용자 중단**: `/stop-continuation` 또는 `cancelLoop`
- **비정상 중단**: `MessageAbortedError` 발생

---

## 11. End-to-End 파이프라인 요약

전체 파이프라인은 4개 Tier로 구성됩니다.

### Tier 1-3: 사전 처리

```text
chat.message (10단계 처리)
  → messages.transform (컨텍스트 주입 + 검증)
  → system.transform (시스템 프롬프트)
  → LLM API 호출
```

### Tier 2: 도구 실행 (반복)

```text
LLM 도구 호출 응답
  → before 훅 (가드 + 주입)
  → 도구 실행
  → after 훅 (복구 + 검증)
  → 결과를 LLM에 반환 → 다시 API 호출
```

도구 실행은 LLM이 텍스트 응답을 반환할 때까지 반복됩니다.

### 에러 복구

```text
에러 발생 → 에러 분류 → 모델 폴백 / 런타임 폴백 → 재시도
```

### Tier 4: 연속 실행

```text
세션 대기(Idle)
  → Atlas 의사결정 (7단계 게이트)
  → Boulder 연속 실행 (지수 백오프)
  → Ralph Loop (자기 참조)
  → TODO 남으면 다시 API 호출, 완료면 종료
```

사용자는 `/stop-continuation`으로 언제든 연속 실행을 중단할 수 있습니다.

---

## 12. 강점과 트레이드오프

### 강점

1. **깊은 오케스트레이션**: 9개 전문 에이전트와 역할별 도구 제한으로 계획-실행-검증 분리가 체계적
2. **다중 복원력**: 모델 폴백 체인(다중 프로바이더), 도구 실행 후 자동 복구 훅, 지수 백오프가 겹겹이 적용
3. **자율 연속 실행**: Atlas → Boulder → Ralph Loop의 3계층 연속 실행으로 장시간 자율 작업 가능
4. **병렬 처리**: 백그라운드 태스크의 격리 실행과 서킷 브레이커로 안전한 병렬 작업 지원
5. **실무 도구 통합**: LSP 6종, AST-Grep, Tmux, 멀티모달(이미지/PDF) 분석까지 포괄

### 트레이드오프

1. **복잡도**: 46개 훅, 26개 도구, 9개 에이전트로 구성된 시스템은 초기 학습 비용이 높음
2. **디버깅 난이도**: 훅 체인(before 10개 + after 8개)과 다중 폴백이 겹치면 문제 원인 추적이 어려움
3. **설정 의존성**: 모델 프로바이더 상태, 사용자 환경에 따라 체감 품질 편차 발생
4. **리소스 오버헤드**: 멀티 모델/멀티 에이전트 구조로 API 비용과 지연 시간이 단일 에이전트 대비 높음

---

## 13. 적용 인사이트

- **계획-실행 분리**: Metis(사전 컨설팅) → Prometheus(전략) → Momus(검토) → Hephaestus(실행) 흐름은 복잡한 코드 변경에서 재현성이 높음
- **카테고리 기반 라우팅**: 모델명 직접 지정 대신 카테고리(`visual-engineering`, `ultrabrain`, `quick`, `deep`) 기반 매핑으로 모델 잠금(lock-in) 감소
- **안전 장치 다층화**: `writeExistingFileGuard`(사전), `editErrorRecovery`(사후), 서킷 브레이커(백그라운드)처럼 각 계층마다 독립적 안전 장치 배치
- **자율 실행의 제어 가능성**: `/stop-continuation`으로 언제든 중단 가능한 구조는 자율성과 제어 사이의 균형점

---

## 참고 링크

- [Repository](https://github.com/code-yeongyu/oh-my-openagent)
- [README (Korean)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/README.ko.md)
- [Overview Guide](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/overview.md)
- [Orchestration Guide](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/orchestration.md)
- [Entry Point (
  `src/index.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/index.ts)
- [Chat Message Handler (
  `src/plugin/chat-message.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/chat-message.ts)
- [Event Handler (
  `src/plugin/event.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/event.ts)
- [Tool Registry (
  `src/plugin/tool-registry.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/tool-registry.ts)
