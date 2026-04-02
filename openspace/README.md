# OpenSpace 분석

`HKUDS/OpenSpace`의 소스 코드를 전수 분석하고, 웹 리서치를 통해 최신 정보를 수집하여 구조화한 문서입니다.

OpenSpace는 기존 코딩 에이전트(Claude Code, Codex, OpenClaw 등)에 MCP + Skill 엔진을 붙여, 작업 수행 중 스킬을 자동 수정(FIX)·파생(DERIVED)·추출(CAPTURED)하는 **자기 진화형 에이전트 런타임**입니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/openspace/00-diagram.md) | 시스템 계층 구조, 2단계 실행 파이프라인, 3중 진화 트리거, Provider 아키텍처, 검색 파이프라인, 벤치마크 흐름, 데이터 모델, 보안 계층 |
| [코드 기반 심층 분석](/openspace/01-analysis.md) | 151개 소스 파일 전수 분석 — 엔트리포인트, Agent Runtime, LLM Client, Backend Provider, Skill Engine, Quality Tracking, MCP 통합, 벤치마크, 설정, 보안, 설계 패턴 |
| [전략적 도입 분석](/openspace/02-strategic-analysis.md) | 경쟁 프레임워크 7종 비교, 실무 도입 분석, SWOT, 아키텍처 독창성 평가 |
| [종합 리서치 보고서](/openspace/03-research-report.md) | 학술 논문, GitHub 활동(~3,500 stars), 커뮤니티 반응, HKUDS 생태계, 경쟁 비교, 미디어 보도, 연구 동향 |

---

## 아키텍처 개요

```text
Host Agent (Claude Code / Codex / OpenClaw / nanobot / Cursor)
    ↓ MCP (stdio / SSE)
OpenSpace MCP Server (openspace-mcp, FastMCP)
    ↓
OpenSpace Orchestrator (tool_layer.py)
    ├─ Phase 1: Skill-Guided Execution
    ├─ Phase 2: Tool-Fallback Execution
    └─ Post-Execution Pipeline
    ↓
GroundingAgent Runtime
    ├─ LLMClient (litellm 래퍼, 다중 모델 지원)
    ├─ GroundingClient (Provider Registry + Tool Cache)
    │   ├─ ShellProvider (Local/Server, subprocess/HTTP)
    │   ├─ GUIProvider (Anthropic Computer Use, PyAutoGUI)
    │   ├─ MCPProvider (stdio/HTTP/WS/Sandbox, 도구 캐시 2계층)
    │   ├─ WebProvider (Deep Research, Perplexity sonar)
    │   └─ SystemProvider (메타 도구)
    ├─ SearchCoordinator (BM25 + embedding + LLM + 품질)
    └─ RecordingManager (conversations.jsonl / traj.jsonl)
    ↓
Skill Engine
    ├─ SkillRegistry (발견 / 선택 / 주입)
    ├─ SkillRanker (BM25 + embedding 하이브리드)
    ├─ ExecutionAnalyzer (사후 실행 분석, 우선순위 기반 대화 절삭)
    ├─ SkillEvolver (3중 트리거: Post-Execution / Tool Degradation / Metric Monitor)
    │   ├─ FIX (in-place 수정, 새 skill_id)
    │   ├─ DERIVED (파생 스킬, 새 디렉토리)
    │   └─ CAPTURED (신규 패턴 포착)
    ├─ SkillStore (SQLite WAL, Version DAG, 원자적 트랜잭션)
    └─ ToolQualityManager (성공률/지연시간 추적, 적응형 진화 사이클)
    ↓
Cloud Skill Community (선택)
    ├─ 업로드 / 다운로드 / 검색
    ├─ BM25 + vector 하이브리드 검색
    └─ open-space.cloud API
```

### 핵심 설계 포인트

- **Self-Evolving Skill**: 실패/성공 실행 기록 기반으로 스킬을 자동 갱신 (3모드: FIX/DERIVED/CAPTURED)
- **3중 진화 트리거**: 실행 후 분석, 도구 품질 저하, 메트릭 악화를 각각 독립 트리거로 사용
- **2단계 실행 파이프라인**: Skill-Guided → Tool-Fallback, Phase 1 실패 시 아티팩트 정리 후 풀 예산 재실행
- **호스트 에이전트 확장형 구조**: 기존 에이전트를 대체하지 않고 MCP + host_skills 형태로 부착
- **로컬 우선 + 클라우드 선택**: 로컬 실행만으로 동작하고, 필요 시 cloud skill 공유를 추가
- **Cascade Evolution**: 도구 품질 저하 감지 → 의존 스킬 자동 수정 (Circuit Breaker 패턴 차용)

---

## 핵심 수치

| 지표 | 값 |
|------|-----|
| Python 소스 파일 | 151개 |
| 벤치마크 태스크 | 50개 (9 산업, 44 직업군) |
| 생성 스킬 (50 태스크 후) | 226개 (활성 206개) |
| 토큰 절감 | 45.9% (Phase 2 vs Phase 1) |
| 수입 향상 | 4.2x (ClawWork 대비) |
| GitHub Stars | ~3,500 |

---

## 참고 자료

- [OpenSpace 저장소](https://github.com/HKUDS/OpenSpace)
- [OpenSpace README](https://github.com/HKUDS/OpenSpace/blob/main/README.md)
- [GDPVal 벤치마크 안내](https://github.com/HKUDS/OpenSpace/blob/main/gdpval_bench/README.md)
- [설정 가이드](https://github.com/HKUDS/OpenSpace/blob/main/openspace/config/README.md)
- [PyTorch KR 소개 글](https://discuss.pytorch.kr/t/openspace-ai-feat-hkuds/9476)
