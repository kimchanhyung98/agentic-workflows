# HyperAgents 분석

`facebookresearch/HyperAgents`의 공개 코드/문서 기준으로, Meta HyperAgents의 구조와 실행 플로우를 정리한 문서입니다.

HyperAgents는 **self-referential self-improving agents**를 표방하며, 메타 에이전트가 에이전트 코드 자체를 수정하고, 세대별 평가/선택 루프를 통해 다음 세대를 생성합니다.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/hyperagents/00-diagram.md) | 세대 진화 루프, 메타/태스크 에이전트, Docker 평가 파이프라인, 아카이브/부모 선택 구조 |
| [구조/플로우 분석](/hyperagents/01-analysis.md) | 핵심 모듈, 실행 단계, 점수/부모 선택 로직, 안전성/운영 관점 트레이드오프 |

## 아키텍처 개요

```text
generate_loop.py
  → parent 선택 (archive 기반)
  → MetaAgent 코드 수정 패치 생성
  → TaskAgent 평가 (domain harness)
  → score 집계/아카이브 업데이트
  → 다음 generation 반복
```

### 핵심 설계 포인트

- **메타-레벨 수정**: `MetaAgent`가 코드베이스를 직접 수정하는 diff 생성
- **세대 아카이브**: `archive.jsonl`, `metadata.json`으로 lineage 추적
- **도메인별 평가 분리**: search/paper/imo/balrog/genesis/polyglot별 harness + report
- **격리 실행**: Docker 컨테이너 내부에서 patch 적용·평가·정리
- **확장 가능한 LLM 백엔드**: LiteLLM 기반으로 OpenAI/Claude/Gemini 모델 선택 가능

## 추가 조사(웹/생태계)

- 공식 저장소 기준, 릴리즈/태그 없이 커밋 기반으로 업데이트되는 형태입니다.
- GitHub 생태계에서 HyperAgents 아이디어를 참조한 파생 구현(예: OpenClaw 연계 self-improving loop) 사례가 확인됩니다.

## 참고 자료

- [HyperAgents 저장소](https://github.com/facebookresearch/HyperAgents)
- [Meta Publication - Hyperagents](https://ai.meta.com/research/publications/hyperagents/)
- [arXiv 2603.19461](https://arxiv.org/abs/2603.19461)
- [커뮤니티 구현 예시](https://github.com/GnawClawHQ/dgm-hyperagents-openclaw)
