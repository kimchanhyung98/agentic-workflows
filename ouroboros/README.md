# Ouroboros 분석

`joi-lab/ouroboros`(Colab/Telegram)와 `joi-lab/ouroboros-desktop`(Desktop/Web UI)를 중심으로, **자기개선형 AI agent harness(하니스)** 구조와 운영 패턴을 정리한 문서입니다.

요청에 따라 `LilMGenius/polysona` 코드와 플로우도 함께 분석해, 멀티 페르소나 오케스트레이션 관점에서 비교 가능한 형태로 구성했습니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/ouroboros/00-diagram.md) | Ouroboros 하니스 계층, 태스크 실행 루프, 자기개선 루프, Polysona 플로우 및 호스트 연동 |
| [설계/활용 사례 분석](/ouroboros/01-analysis.md) | 하니스 구성요소, 운영 시나리오, Polysona 코드 구조·명령 체계, 비교 시사점 |

---

## 아키텍처 개요

```text
사용자/트리거 (Desktop UI, Telegram)
    ↓
Ingress (server.py / telegram entry)
    ↓
Supervisor (queue, workers, state, budget)
    ↓
Agent Core (task pipeline, LLM loop, tool dispatch, safety, memory)
    ↓
Self-Modification Layer (repo_write, review, git commit/push, restart/evolve)
    ↓
Persistent Storage (state, logs, memory, knowledge, git history)
```

Polysona는 다른 축에서,

```text
Persona Setup (interview) → Persona Data Structuring
    ↓
Trend → Content Draft → QA Persona Evaluation → Publish/Track
    ↓
Codex/Claude/OpenCode 등 여러 에이전트 런타임으로 이식
```

---

## 핵심 설계 포인트

- **Ouroboros 하니스**: 태스크 오케스트레이션 + 안전 레이어 + 메모리/리뷰/진화 루프를 통합한 자기개선 실행기
- **운영 인터페이스 이원화**: 초기 Colab/Telegram 버전과 Desktop/Web UI 버전이 동일 철학(헌법, 자기수정)을 공유
- **Polysona 오케스트레이션**: 페르소나 추출/도입/콘텐츠 생성/QA/발행을 에이전트 명령 체인으로 명시
- **포터블 에이전트 지향**: Polysona는 Codex/Claude/OpenCode를 동시에 타깃으로 하여 도구 종속을 낮춤

---

## 참고 자료

- [joi-lab/ouroboros (GitHub)](https://github.com/joi-lab/ouroboros)
- [joi-lab/ouroboros-desktop (GitHub)](https://github.com/joi-lab/ouroboros-desktop)
- [LilMGenius/polysona (GitHub)](https://github.com/LilMGenius/polysona)
- [Polysona README](https://raw.githubusercontent.com/LilMGenius/polysona/main/README.md)
- [Polysona AGENTS.md](https://raw.githubusercontent.com/LilMGenius/polysona/main/AGENTS.md)
- [Polysona CLAUDE.md](https://raw.githubusercontent.com/LilMGenius/polysona/main/CLAUDE.md)
- [Polysona hooks.json](https://raw.githubusercontent.com/LilMGenius/polysona/main/hooks/hooks.json)
- [Polysona sync-codex-skills.mjs](https://raw.githubusercontent.com/LilMGenius/polysona/main/scripts/sync-codex-skills.mjs)
