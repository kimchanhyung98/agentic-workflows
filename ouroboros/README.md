# Ouroboros 분석

`Q00/ouroboros`의 AI 에이전트 하네스와 실행 플로우를 공개 코드/문서 기준으로 정리한 문서입니다.

Ouroboros는 Claude Code, Codex CLI 같은 런타임 위에서 동작하는 **specification-first 워크플로우 엔진**으로, 인터뷰(명확화) → Seed(명세 고정) → 실행 → 평가 → 진화 루프를 제공합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/ouroboros/00-diagram.md) | 계층 구조, 6-Phase 루프, 런타임 어댑터, MCP 양방향 허브, 평가 게이트 |
| [설계 및 실행 플로우 분석](/ouroboros/01-analysis.md) | 하네스 구조, 코드 모듈, 명령 체계, 활용 사례, 트레이드오프 |

---

## 아키텍처 개요

```text
사용자/에이전트 인터페이스 (ooo skills, ouroboros CLI, MCP clients)
    ↓
Big Bang (Socratic Interview) + Seed 생성/고정
    ↓
Orchestrator (6-Phase: PAL → Double Diamond → Resilience → Evaluation → Secondary Loop)
    ↓
Runtime Abstraction Layer (Claude / Codex)
    ↓
Tool Execution (내장 도구 + 외부 MCP 서버 도구 병합)
    ↓
Persistence / Observability (EventStore, Checkpoint, Drift, Retrospective)
```

### 핵심 설계 포인트

- **명세 우선 하네스**: 인터뷰로 모호성을 낮추고(`ambiguity <= 0.2`) Seed를 고정한 뒤 실행합니다.
- **런타임 분리**: 동일한 워크플로우를 Claude Code/Codex CLI 어댑터로 실행할 수 있습니다.
- **다단계 검증 게이트**: Mechanical → Semantic → Consensus 순으로 비용을 제어하며 품질을 검증합니다.
- **이벤트 소싱 중심 복원력**: append-only 이벤트, 체크포인트, 세션 재개/회고를 기본 제공합니다.
- **MCP 양방향 통합**: Ouroboros 자체를 MCP 서버로 노출하면서, 외부 MCP 도구도 클라이언트로 소비합니다.

---

## 활용 사례 (하네스 관점)

- **아이디어 명확화 기반 구현**: 모호한 요구를 인터뷰로 구조화한 뒤 코드 실행으로 연결
- **런타임 이식성 확보**: 팀/환경에 따라 Claude Code ↔ Codex CLI 전환
- **장기 자율 루프 운영**: `ooo ralph`를 통한 세대 반복 진화 및 수렴 판정
- **브라운필드 점검 자동화**: 기존 코드베이스 설정/제약 탐지 후 명세 기반 실행
- **PM 워크플로우 확장**: `ooo pm`으로 PM 인터뷰 및 PRD 생성

---

## 참고 자료

- [Ouroboros 저장소](https://github.com/Q00/ouroboros)
- [README](https://github.com/Q00/ouroboros/blob/main/README.md)
- [Architecture 문서](https://github.com/Q00/ouroboros/blob/main/docs/architecture.md)
- [CLI Reference](https://github.com/Q00/ouroboros/blob/main/docs/cli-reference.md)
- [Runtime Guide - Claude Code](https://github.com/Q00/ouroboros/blob/main/docs/runtime-guides/claude-code.md)
- [Runtime Guide - Codex CLI](https://github.com/Q00/ouroboros/blob/main/docs/runtime-guides/codex.md)
- [pyproject.toml](https://github.com/Q00/ouroboros/blob/main/pyproject.toml)
- [PyPI - ouroboros-ai](https://pypi.org/project/ouroboros-ai/)
