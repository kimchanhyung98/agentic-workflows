# Aperant 분석

`AndyMik90/Aperant`의 설계와 실행 플로우를 공개 코드 기준으로 정리한 문서입니다.

Aperant는 Electron 40 기반 데스크톱 애플리케이션 위에 Vercel AI SDK v6, XState task state machine, git worktree를 결합해 스펙 생성부터 구현, QA, human review까지 이어지는 자율 코딩 런타임을 구성합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/aperant/00-diagram.md) | 전체 계층 구조, TASK_START 분기, spec/build/QA 흐름, worktree 생명주기 |
| [설계 및 실행 플로우 분석](/aperant/01-analysis.md) | 구조 분해, 상태기계, 오케스트레이션 파이프라인, 도구/보안/프로바이더 시스템, 트레이드오프 |

---

## 아키텍처 개요

```text
Electron Renderer (React 19 + Zustand)
    ↓ Preload API + IPC
Electron Main (ipc-handlers/* + taskStateManager/XState)
    ↓
Task Runtime (AgentManager + AgentProcessManager)
    ├── AgentEvents (phase protocol / task-event parsing)
    ├── SpecOrchestrator / BuildOrchestrator / QALoop
    ├── Semantic Merge (35+ 변경 타입, AutoMerger + AI resolver)
    └── WorkerBridge + runContinuableSession()/runAgentSession()
    ↓
Provider Registry (11 providers) + Auth Resolver + Phase Config
    ↓
ToolRegistry (9개 내장 도구 + MCP 도구) + BashValidator
    ↓
Memory System (libSQL, 16종 메모리 타입, BM25 + 임베딩 검색)
    ↓
Git 작업공간
    ├── .auto-claude/specs/{specId}
    └── .auto-claude/worktrees/tasks/{specId}
```

### 핵심 설계 포인트

- **모듈형 IPC + 상태기계**: 도메인별 IPC 모듈과 `taskStateManager`가 UI 상태, worker 이벤트, plan 파일을 함께 동기화합니다.
- **complexity-adaptive spec pipeline**: `SpecOrchestrator`가 `complexity_assessment` 이후 simple/standard/complex 경로로 분기합니다.
- **worktree 격리 + handler-driven merge/cleanup**: 구현과 QA는 기본적으로 worktree에서 실행되고, merge/discard/cleanup은 별도 IPC 핸들러가 통제합니다.
- **멀티 프로바이더 추상화**: 현재 코드 기준 11개 프로바이더를 단일 레지스트리로 관리하고, 계정 우선순위 큐와 레거시 profile fallback을 지원합니다.
- **복원력 중심 운영**: rate limit/auth failure 감지, auto-swap restart, stale exit 방지, startup recovery, pause/resume이 결합돼 있습니다.
- **다층 도구 안전장치**: bash denylist, 명령어별 validator, write-path containment, path traversal 방지, human review gate가 함께 적용됩니다.
- **Intent-aware semantic merge**: 35+ 변경 타입 분류, deterministic AutoMerger, AI 기반 충돌 해결, 충돌 심각도 평가를 결합한 병합 시스템입니다.
- **libSQL 기반 메모리 그래프**: 16종 메모리 타입, BM25 + 임베딩 검색, 관계 그래프, trust gate/decay 기반의 세션 간 지식 유지 시스템입니다.

---

## 참고 자료

- [Aperant 저장소](https://github.com/AndyMik90/Aperant)
- [루트 README](https://github.com/AndyMik90/Aperant/blob/main/README.md)
- [앱 구조 README](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/README.md)
- [Main Process 진입점](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/index.ts)
- [IPC 설정 진입점](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ipc-setup.ts)
- [Task 실행 IPC 핸들러](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ipc-handlers/task/execution-handlers.ts)
- [Task 상태 관리자](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/task-state-manager.ts)
- [Task 상태기계](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/shared/state-machines/task-machine.ts)
- [AgentManager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/agent/agent-manager.ts)
- [AgentQueueManager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/agent/agent-queue.ts)
- [AI 세션 런너](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/session/runner.ts)
- [Worker 진입점](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/agent/worker.ts)
- [BuildOrchestrator](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/orchestration/build-orchestrator.ts)
- [SpecOrchestrator](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/orchestration/spec-orchestrator.ts)
- [Agent 설정 레지스트리](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/config/agent-configs.ts)
- [Provider Registry](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/providers/registry.ts)
- [Provider Factory](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/providers/factory.ts)
- [Bash Validator](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/security/bash-validator.ts)
- [도구 레지스트리](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/tools/build-registry.ts)
- [Tool 정의 래퍼](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/tools/define.ts)
- [Worktree Manager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/worktree/worktree-manager.ts)
- [Worktree Path 유틸리티](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/worktree-paths.ts)
- [메모리 서비스](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/memory/memory-service.ts)
- [메모리 타입 정의](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/memory/types.ts)
- [Merge Orchestrator](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/merge/orchestrator.ts)
- [Merge 타입/전략](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/merge/types.ts)
- [에러 분류기](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/session/error-classifier.ts)
- [Phase Config](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/config/phase-config.ts)
