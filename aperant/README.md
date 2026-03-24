# Aperant 분석

`AndyMik90/Aperant`의 설계와 실행 플로우를 공개 코드 기준으로 정리한 문서입니다.

---

## 문서 구성

| 문서                                    | 내용                                              |
|---------------------------------------|-------------------------------------------------|
| [아키텍처 다이어그램](/aperant/00-diagram.md)         | 프로세스 구조, 작업 시작/실행/검토 흐름, auto-swap, worktree 생명주기 |
| [설계 및 실행 플로우 상세 분석](/aperant/01-analysis.md) | 계층 구조, IPC-기반 오케스트레이션, 신뢰성/보안 설계, 트레이드오프     |

---

## 아키텍처 개요

```text
Electron Renderer (React UI)
    ↓ IPC 이벤트
Electron Main (ipc-handlers/*)
    ↓
Agent Runtime (AgentManager + AgentProcessManager)
    ↓
Git Worktree / Local Repo 격리 실행
    ↓
WorkerBridge + Agent Session (planning/coding/qa)
```

### 핵심 설계 포인트

- **IPC 모듈 분리**: 대형 IPC 핸들러를 task/github/linear 등 도메인별 모듈로 분해
- **worktree 기본 격리 실행**: task마다 `auto-claude/{specId}` 브랜치와 worktree를 생성해 main 작업공간 오염 최소화
- **Worker 기반 에이전트 실행**: Python subprocess 경로를 대체해 TypeScript AI SDK worker 파이프라인으로 통합
- **복원력 중심 운영**: rate limit/auth failure 감지 후 profile auto-swap + task restart 지원
- **다층 안전장치**: 경로 순회 방지, security profile 주입, 리뷰 단계에서 명시적 human decision

---

## 참고 자료

- [Aperant 저장소](https://github.com/AndyMik90/Aperant)
- [루트 README](https://github.com/AndyMik90/Aperant/blob/main/README.md)
- [앱 구조 README](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/README.md)
- [Main Process 진입점](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/index.ts)
- [Task 실행 IPC 핸들러](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ipc-handlers/task/execution-handlers.ts)
- [AgentManager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/agent/agent-manager.ts)
- [AgentProcessManager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/agent/agent-process.ts)
- [Worktree Manager](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/ai/worktree/worktree-manager.ts)
- [Worktree Path 유틸리티](https://github.com/AndyMik90/Aperant/blob/main/apps/desktop/src/main/worktree-paths.ts)
