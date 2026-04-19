# HyperAgents 분석

`facebookresearch/HyperAgents`의 공개 코드와 논문을 기준으로, 자기개선 루프의 구조와 실행 플로우를 정리한 문서입니다.

HyperAgents는 **task agent와 meta agent를 하나의 편집 가능한 프로그램**으로 통합해, 에이전트가 자신의 개선 절차 자체를 수정하도록 만드는 self-referential 진화 루프입니다.
구체 시스템은 **DGM-H (DGM-Hyperagents)** 로, Darwin Gödel Machine의 self-referential 확장입니다.

> **논문**: Zhang et al., "Hyperagents", [arXiv 2603.19461](https://arxiv.org/abs/2603.19461) (2026-03-19). 라이선스는 **CC
BY-NC-SA 4.0**으로 상업 사용이 제한됩니다.

---

## 문서 구성

| 문서                                            | 내용                                                       |
|-----------------------------------------------|----------------------------------------------------------|
| [아키텍처 다이어그램](/hyperagents/00-diagram.md)      | 전체 계층, 세대 실행 시퀀스, 평가·베이스라인 계층                            |
| [설계 및 실행 플로우 분석](/hyperagents/01-analysis.md) | DGM 대비 차이, 프로젝트 구조, 하네스 관점, 도메인/베이스라인 일람, 운영·보안, 적용 인사이트 |

---

## 아키텍처 개요

```text
Generate Loop (generate_loop.py)
    ↓
부모 선택 (select_parent / select_next_parent)
    ↓
Docker 컨테이너 (apply_diffs_container — 조상 patch 체인 적용)
    ↓
MetaAgent (meta_agent.py) → chat_with_agent (tools_available='all')
    ↓
model_patch.diff 생성
    ↓
Domain Harness (domains/<domain>/harness.py + report.py)
    ↓ staged eval → (임계값 통과 시) full eval
    ↓
Archive 업데이트 (utils/gl_utils.update_and_save_archive)
    ↓
다음 세대 반복
```

### 핵심 설계 포인트

- **Self-reference**: 메타 개선 로직이 편집 가능한 코드베이스 내부에 존재 — DGM 대비 핵심 차별점.
- **Docker 격리 실행**: 세대 간 patch 체인을 컨테이너에 누적 적용해 재현성과 안전성 확보.
- **아카이브 기반 탐색**: 단일 최신이 아닌 계보 전체를 부모 후보로 유지.
- **도메인 서브패키지화**: `domains/<name>/harness.py` + `report.py` 규약으로 평가 도메인 확장.
- **DGM 재현 내장**: `baselines/dgm/`로 동일 리포에서 비교 실험 가능.

---

## 참고 자료

- [HyperAgents 저장소](https://github.com/facebookresearch/HyperAgents) — 2,340★ (2026-04-19)
- [논문 — Hyperagents (arXiv 2603.19461)](https://arxiv.org/abs/2603.19461)
- [전신 — Darwin Gödel Machine (arXiv 2505.22954)](https://arxiv.org/abs/2505.22954)
- [VentureBeat 기사 (2026-03)](https://venturebeat.com/orchestration/meta-researchers-introduce-hyperagents-to-unlock-self-improving-ai-for-non-coding-tasks)
- [HuggingFace Papers](https://huggingface.co/papers/2603.19461)
