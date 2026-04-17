# Archon 분석

`coleam00/Archon`의 공개 코드/문서를 기준으로, AI 코딩 워크플로우 하네스의 구조와 실행 흐름을 정리한 문서입니다.

Archon은 AI 코딩을 **결정적이고 반복 가능하게** 만들기 위해, 프롬프트 기반 작업을 YAML DAG 워크플로우로 명시하고 실행·검증·리뷰·PR 생성까지 자동화하는 엔진입니다.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/archon/00-diagram.md) | 멀티 패키지 구조, 실행 경로, 워크플로우 DAG/루프, 플랫폼 어댑터 계층 |
| [구조/플로우 분석](/archon/01-analysis.md) | 모듈 역할, 런타임 흐름, 핵심 설계 포인트, 운영 관점 트레이드오프 |

## 아키텍처 개요

```text
Platform Adapters (Web/CLI/Slack/Telegram/GitHub/Discord)
    ↓
Server (Hono) + Core Orchestrator
    ↓
Workflow Engine (YAML DAG, loop, gate, router)
    ↓
Provider Layer (Claude/Codex/Community)
    ↓
Isolation Layer (git worktree / copy)
    ↓
Persistence (SQLite/PostgreSQL: conversations/sessions/workflow_runs/events)
```

### 핵심 설계 포인트

- **워크플로우 코드화**: 개발 프로세스를 `.archon/workflows/*.yaml`로 명시해 실행 순서를 고정
- **AI + 결정적 노드 혼합**: prompt 노드와 bash/script/검증 노드를 DAG로 결합
- **격리 실행**: 이슈/작업 단위로 분리된 git worktree에서 병렬 처리
- **다중 인터페이스**: CLI, Web, Chat 플랫폼에서 동일한 엔진 재사용
- **기본 워크플로우 번들**: `archon-fix-github-issue`, `archon-idea-to-pr`, `archon-smart-pr-review` 등 제공

## 참고 자료

- [Archon 저장소](https://github.com/coleam00/Archon)
- [README](https://github.com/coleam00/Archon/blob/dev/README.md)
- [공식 문서](https://archon.diy)
- [릴리즈](https://github.com/coleam00/Archon/releases)
- [기존 Python 버전 브랜치](https://github.com/coleam00/Archon/tree/archive/v1-task-management-rag)
