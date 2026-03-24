# Aperant: 설계 및 실행 플로우 분석

## 1. 개요

Aperant는 Electron 기반 데스크톱 애플리케이션 위에 AI 에이전트 실행 런타임을 얹은 구조다.
핵심은 **UI 이벤트를 IPC로 수집한 뒤, main process에서 작업 상태·인증·worktree를 조정하고,
worker 기반 에이전트 세션을 실행**하는 파이프라인이다.

공개 코드 기준으로 보면 다음 3가지가 중심 설계다.

1. **모듈형 IPC 오케스트레이션** (`ipc-handlers/*`)
2. **task별 git worktree 격리 실행** (`createOrGetWorktree`)
3. **실패 복원(재시도) 자동화** (rate limit/auth failure → auto-swap restart)

---

## 2. 구조적 분해

### 2.1 UI/IPC 계층

- Renderer는 `TASK_START`, `TASK_STOP`, `TASK_REVIEW` 같은 IPC 이벤트를 발행한다.
- Main의 `task/execution-handlers.ts`가 선행 검증(git repo 여부, 커밋 존재, 인증 상태)과 상태 전이를 수행한다.
- Task 관련 핸들러가 CRUD/Execution/Worktree/Logs/Archive 모듈로 분리되어 있다.

**의도:** giant handler를 도메인 단위로 분리해 변경 충돌과 인지 부하를 줄인다.

### 2.2 Agent Runtime 계층

- `AgentManager`는 실행 진입점 facade 역할을 맡는다.
- `startSpecCreation`, `startTaskExecution`, `startQAProcess`로 phase별 세션을 분리한다.
- 내부적으로 모델/프로바이더/auth를 해석하고 worker 실행 config를 생성한다.

### 2.3 Execution 계층

- `createOrGetWorktree()`가 `auto-claude/{specId}` 브랜치 + task worktree를 준비한다.
- `AgentProcessManager.spawnWorkerProcess()`가 `WorkerBridge`를 통해 AI 세션을 실행한다.
- worker에서 올라오는 log/progress/task-event/exit를 EventEmitter contract로 UI에 전달한다.

---

## 3. 핵심 실행 플로우

## 3.1 TASK_START → 스펙 생성/실행 분기

`TASK_START` 이벤트 처리 시 실행 경로는 아래처럼 갈린다.

1. task/project 조회
2. git 초기 조건 검증(리포지토리/초기 커밋)
3. 인증 검증(profile auth 또는 provider account)
4. plan/subtask 상태 확인
5. `spec.md` 부재 시 `startSpecCreation`
6. spec 존재 시 `startTaskExecution` (planner/build orchestrator 경로)

이때 `taskStateManager`와 실제 plan 파일(`implementation_plan.json`)을 함께 확인해
UI 상태와 실제 실행 상태 불일치를 줄이려는 설계가 보인다.

## 3.2 task execution 시 worktree 기본 사용

`startTaskExecution()`은 기본적으로 worktree를 생성/재사용한다.

- 위치: `.auto-claude/worktrees/tasks/{specId}`
- 브랜치: `auto-claude/{specId}`
- 실패 시 main project 경로로 fallback

그리고 worker session의 `toolContext.cwd`와 `projectDir`를 worktree로 전환해
실제 코드 변경이 격리된 작업공간에서 일어나도록 구성한다.

## 3.3 QA/Review 플로우

`TASK_REVIEW`는 human decision을 강제하는 분기점이다.

- 승인: QA report 기록 후 done 처리
- 반려: main 작업공간 변경 되돌림 + fix request 기록 + QA process 재시작

이 구조는 "에이전트가 제안하고 인간이 승인/재요청한다"는 운영 모델에 맞춰져 있다.

---

## 4. 신뢰성/복원성 설계

## 4.1 auto-swap restart

`AgentProcessManager`는 실행 로그를 기반으로 rate limit/auth failure를 감지하고,
`auto-swap-restart-task` 이벤트를 통해 `AgentManager.restartTask()`를 트리거한다.

`restartTask()`는:

- swap count 상한(무한 루프 방지)
- 현재 프로세스 종료
- stuck subtask reset
- 동일 task context로 재실행

을 순서대로 수행한다.

## 4.2 stale exit 방지

`taskExecutionContext.generation`을 사용해 이전 실행의 지연된 exit callback이
새로운 실행 컨텍스트를 청소하지 않도록 방어한다.

## 4.3 startup recovery

앱 시작 시 `runStartupRecoveryScan()`으로 프로젝트의 plan 파일을 스캔해
stuck subtask를 초기화한다. 비정상 종료 이후 복구를 의도한 설계다.

---

## 5. 보안/안전 관련 포인트

공개 코드에서 확인 가능한 안전장치는 아래와 같다.

- **경로 안전성 검사**: `findTaskWorktree/findTerminalWorktree`에서 path traversal 방지
- **작업 경로 격리**: task 변경을 worktree로 분리
- **security profile 주입**: session `toolContext.securityProfile`로 실행 제약 전달
- **리뷰 게이트**: task 완료 전 `TASK_REVIEW` 단계에서 human decision 필요
- **이미지 피드백 처리 방어**: MIME 타입/파일명/경로 검증 후 저장

---

## 6. 장점과 트레이드오프

| 관점        | 장점                                              | 트레이드오프                                  |
|-----------|-------------------------------------------------|-------------------------------------------|
| 구조        | IPC/Agent/Worktree 책임이 분리되어 유지보수성이 높음               | 모듈 수가 많아 전체 흐름 추적 시 진입 비용 증가                |
| 안정성       | auto-swap, stuck reset, startup recovery로 복원력 강화 | 상태 동기화 로직이 복잡해 edge case 검증 부담 증가           |
| 개발 안전성    | worktree 기반 격리로 main 오염 위험 감소                   | worktree/branch 정리 실패 시 운영자가 수동 정리할 가능성 존재 |
| 운영 통제     | review 승인/반려 흐름이 명시적                            | 완전 자동 merge 대비 human step으로 리드타임 증가        |
| 확장성       | provider/model/auth 해석 계층이 있어 멀티 모델 확장에 유리      | 설정 조합이 늘수록 디버깅 난이도 상승                       |

---

## 7. 요약

Aperant의 실행 플로우는 단순 "프롬프트 실행기"가 아니라
**(1) IPC 상태기계 + (2) 격리된 git 작업공간 + (3) 실패 자동 복원 + (4) human review gate**
를 결합한 형태다.

특히 task를 worktree에 고립시키고, 실패 시 profile swap으로 복구하는 설계는
실서비스 환경에서 에이전트 실행을 운영 가능한 형태로 만들기 위한 선택으로 해석된다.
