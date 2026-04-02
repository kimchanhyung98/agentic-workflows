# OpenSpace 분석

`HKUDS/OpenSpace`의 구조와 동작 원리를 공개 문서 기준으로 정리한 문서입니다.

OpenSpace는 기존 코딩 에이전트(Claude Code, Codex, OpenClaw 등)에 MCP + Skill 엔진을 붙여, 작업 수행 중 스킬을 자동 수정(FIX)·파생(DERIVED)·추출(CAPTURED)하는 **자기 진화형 에이전트 런타임**을 지향합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/openspace/00-diagram.md) | 계층 구조, 실행 흐름, 진화 루프, 벤치마크 2단계 흐름 |
| [아키텍처/워크플로우 분석](/openspace/01-analysis.md) | 핵심 개념, 모듈 구성, 진화 엔진, 운영/도입 관점 분석 |

---

## 아키텍처 개요

```text
Host Agent (Claude Code/Codex/OpenClaw 등)
    ↓ MCP
OpenSpace MCP Server (openspace-mcp)
    ↓
Grounding Agent Runtime
    ├─ Backend: shell / gui / mcp / web / system
    ├─ Tool Search & Quality Tracking
    └─ Recording (task/session traces)
    ↓
Skill Engine
    ├─ Registry/Ranker (BM25 + embedding)
    ├─ Analyzer (post-execution)
    ├─ Evolver (FIX / DERIVED / CAPTURED)
    └─ Store (SQLite lineage/metrics)
    ↓
Cloud Skill Community (선택)
```

### 핵심 설계 포인트

- **Self-Evolving Skill**: 실패/성공 실행 기록 기반으로 스킬을 자동 갱신
- **다중 트리거 진화**: 실행 후 분석, 도구 품질 저하, 메트릭 저하를 각각 독립 트리거로 사용
- **호스트 에이전트 확장형 구조**: 기존 에이전트를 대체하지 않고 MCP/Skill 형태로 부착
- **로컬 우선 + 클라우드 선택**: 로컬 실행만으로 동작하고, 필요 시 cloud skill 공유를 추가

---

## 참고 자료

- [OpenSpace 저장소](https://github.com/HKUDS/OpenSpace)
- [OpenSpace README](https://github.com/HKUDS/OpenSpace/blob/main/README.md)
- [GDPVal 벤치마크 안내](https://github.com/HKUDS/OpenSpace/blob/main/gdpval_bench/README.md)
- [설정 가이드](https://github.com/HKUDS/OpenSpace/blob/main/openspace/config/README.md)
- [PyTorch KR 소개 글](https://discuss.pytorch.kr/t/openspace-ai-feat-hkuds/9476)
