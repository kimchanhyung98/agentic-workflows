# Archon 분석

`coleam00/Archon`의 AI 코딩 하네스 구조와 실행 플로우를 정리한 문서입니다.

Archon은 모델 자체를 바꾸는 도구라기보다, **YAML 워크플로우로 코딩 프로세스를 고정**해 계획→구현→검증→리뷰→PR 단계를 재현 가능하게 만드는 오케스트레이션 엔진입니다.

> **대상 버전**: 2026-04-07 공지된 **v2 재작성판** (Bun + TypeScript). v1(Python 기반 task management + RAG)은 [
`archive/v1-task-management-rag`](https://github.com/coleam00/Archon/tree/archive/v1-task-management-rag) 브랜치에 보존되어 있으며
> 본 문서의 분석 대상이 아닙니다.

---

## 문서 구성

| 문서                                       | 내용                                                               |
|------------------------------------------|------------------------------------------------------------------|
| [아키텍처 다이어그램](/archon/00-diagram.md)      | 플랫폼 어댑터, 오케스트레이터, 워크플로우 엔진, 격리(worktree), 저장소 계층 구조              |
| [설계 및 실행 플로우 분석](/archon/01-analysis.md) | 프로젝트 구조, 하네스 관점 분석, 대표 워크플로우(20종 일람), 운영/보안 포인트, 런타임·배포, 적용 인사이트 |

---

## 아키텍처 개요

```text
사용자 입력 (CLI/Web/Slack/Telegram/GitHub 등)
    ↓
Platform Adapters
    ↓
Orchestrator (메시지 라우팅, 세션/컨텍스트 관리)
    ↓
Workflow Executor (YAML DAG 실행)
    ↓
AI Providers (Claude/Codex) + Deterministic Nodes (Bash/Approval)
    ↓
Isolation Provider (worktree 기본 · container/VM/remote)
    ↓
SQLite 기본 / PostgreSQL 선택 (conversation/session/workflow events)
```

### 핵심 설계 포인트

- **Deterministic Process**: 워크플로우 파일로 단계/게이트를 고정
- **Composable DAG**: AI 노드와 bash/approval/cancel 노드를 혼합
- **Isolation by default**: 실행 단위 worktree 분리로 병렬성과 안정성 확보
- **Streaming-first**: 플랫폼별 스트리밍/배치 모드를 공통 인터페이스로 처리

---

## 참고 자료

- [Archon 저장소](https://github.com/coleam00/Archon) — 18,842★ (2026-04-19)
- [Archon CLI v0.3.6 릴리스](https://github.com/coleam00/Archon/releases/tag/v0.3.6) (2026-04-12)
- [v2 재작성 공지 — Issue #957](https://github.com/coleam00/Archon/issues/957)
- [Archon 공식 문서](https://archon.diy)
- [Getting Started - Installation](https://archon.diy/getting-started/installation/)
- [Getting Started - Core Concepts](https://archon.diy/getting-started/concepts/)
- [Architecture Reference](https://archon.diy/reference/architecture/)
