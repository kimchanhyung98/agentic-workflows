# HyperAgents 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `facebookresearch/HyperAgents` — 2,340★ / 296 fork (2026-04-19 기준)
- 공식 설명: "Self-referential self-improving agents that can optimize for any computable task"
- 런타임: **Python 3.12 + Docker**, 생성일 2026-03-19, 최근 push 2026-04-14
- 라이선스: **CC BY-NC-SA 4.0** (비상업·공유조건부 변경허락)
- 논문: "Hyperagents" (Zhang et al., [arXiv 2603.19461](https://arxiv.org/abs/2603.19461), 2026-03-19)

HyperAgents는 **task agent와 meta agent를 하나의 편집 가능한 프로그램**으로 통합해, 에이전트가 자신의 메타 개선 절차 자체를 수정하도록 만듭니다. 구체 시스템 이름은 **DGM-H (
DGM-Hyperagents)** 이며, Darwin Gödel Machine (Zhang et al., [arXiv 2505.22954](https://arxiv.org/abs/2505.22954))의
self-referential 확장입니다.

### DGM과의 차이

| 항목     | DGM (2025)          | HyperAgents / DGM-H (2026) |
|--------|---------------------|----------------------------|
| 메타 절차  | 사람이 손으로 작성한 고정 메커니즘 | 편집 가능한 코드베이스에 포함           |
| 도메인 확장 | 새 도메인마다 메타 재작업 필요   | 메타 자체가 도메인 간 전이            |
| 전이 대상  | 태스크 지식              | 메타 레벨 개선(기억, 추적 등) 누적      |

---

## 2. 프로젝트 구조 분석

```text
루트 스크립트
├─ generate_loop.py        # 세대 루프 진입점
├─ meta_agent.py           # MetaAgent 구현
├─ task_agent.py           # TaskAgent 구현
├─ run_meta_agent.py       # 메타 에이전트 단독 실행 (diff 생성)
├─ run_task_agent.py       # 태스크 에이전트 단독 실행
├─ select_next_parent.py   # 다음 부모 선택 유틸
├─ ensemble.py             # patch 앙상블 평가
├─ setup_initial.sh        # 초기 에이전트 셋업
└─ Dockerfile              # 격리 실행 컨테이너 빌드

agent/                     # 파운데이션 모델 래퍼
├─ base_agent.py           # AgentSystem 베이스 클래스
├─ llm.py                  # 공통 LLM 호출
├─ llm_withtools.py        # chat_with_agent (tool-using chat loop)
└─ tools/                  # 도구 모음

analysis/                  # 실험 분석·시각화
├─ analysis_utils.py
├─ plot_comparison.py / plot_progress.py / plot_testevals.py
├─ transfer_utils.py
└─ visualize_archive.py

baselines/                 # 비교군
├─ dgm/                    # Darwin Gödel Machine 재현
├─ ai_reviewer/
├─ imo_proof/ · imo_grading/
├─ genesis_go2walking/
└─ sft_openai/

domains/                   # 평가 도메인
├─ harness.py / report.py / run_eval.py   # 공용
├─ polyglot/   (코딩)
├─ paper_review/
├─ imo/        (수학 증명)
├─ genesis/    (로보틱스 보상 설계)
├─ balrog/
└─ search_arena/

utils/                     # 공통 유틸
├─ common.py · constants.py
├─ docker_utils.py         # build/apply_diffs/copy/log
├─ domain_utils.py         # 도메인 동적 로딩, eval 분할
└─ gl_utils.py             # 아카이브·부모 선택·patch 조작
```

### 구조적 특징

1. **단일 루프 오케스트레이터**: `generate_loop.py`가 세대 생성·격리·평가·아카이브를 모두 조율.
2. **tool-using chat loop**: `MetaAgent.forward`는 `chat_with_agent(instruction, model, tools_available='all')`로 LLM + 도구
   루프를 돌려 `model_patch.diff`를 만든다.
3. **격리 계층 명시적**: Docker 컨테이너에서 조상 patch 체인을 순차 적용해 재현성 확보.
4. **아카이브 기반 탐색**: 단일 최신이 아닌 계보 전체가 부모 후보이며, `select_parent` / `select_next_parent`로 전략 교체 가능.
5. **도메인 서브패키지화**: 각 `domains/<domain>/`에 자체 `harness.py`·`report.py` — `utils/domain_utils`가 동적 로딩.

---

## 3. 하네스 관점 핵심 분석

### 3.1 목적

HyperAgents는 단일 태스크 성능보다, **"개선하는 방법"을 개선**하는 자기참조 루프를 실험하기 위한 코드베이스입니다.

| 문제       | DGM 접근  | HyperAgents 접근        |
|----------|---------|-----------------------|
| 메타 로직 수정 | 사람이 재작성 | 에이전트가 자신의 루프 코드를 수정   |
| 도메인 전이   | 수작업 적응  | 메타 개선이 도메인을 넘어 누적     |
| 성능 추적    | 외부 로깅   | 편집 가능한 지속 기억·추적으로 내재화 |

### 3.2 노드 조합 전략

- **지능 구간**: `chat_with_agent` 기반 도구 사용 루프 — 코드 탐색·수정·테스트 실행.
- **결정 구간**: Docker 빌드/diff 적용/컨테이너 정리, staged→full eval 승급 규칙, 부모 선택 알고리즘.
- **실험 제어**: baseline 옵션, `ensemble.py`, staged eval 임계값(예: polyglot `test_more_threshold = 0.4` — DGM과 동일 설정).

---

## 4. 대표 실행 플로우

### 4.1 `generate_loop.py` 세대 처리

1. **초기 세대 준비**: 출력 디렉토리·아카이브 초기화, 필요 시 meta patch 선적용 (`setup_initial_gen`).
2. **부모 선택**: `select_parent` / `get_latest_can_select_parent` — 점수 기반·랜덤·최신 전략 교체 가능.
3. **세대 생성**: Docker 컨테이너 빌드 → 조상 patch 체인 적용 (`apply_diffs_container`) → `MetaAgent.forward()` 실행 → `model_patch.diff`
   회수.
4. **Staged eval**: 도메인별 소규모 subset 실행. polyglot의 경우 `./domains/polyglot/subsets/small.json` 태스크, 임계값 `0.4` 이상일 때만 다음
   단계로.
5. **Full eval**: 전체 task 실행 (`harness_polyglot(num_samples=-1)` 등) 후 `report` 생성.
6. **아카이브 업데이트**: `update_and_save_archive`, `update_node_metadata`, 시각화(`visualize_archive_single/together`), 진척도 플롯(
   `plot_progress_single/together`).
7. **다음 세대로 반복** (최대 세대 한도까지).

### 4.2 도메인별 평가 도메인

| 도메인            | 성격          | 비고                                      |
|----------------|-------------|-----------------------------------------|
| `polyglot`     | 코딩 벤치마크     | DGM과 직접 비교 기준                           |
| `paper_review` | 논문 리뷰 품질    | 비코딩 태스크 전이 검증                           |
| `imo`          | 수학 올림피아드 증명 | `baselines/imo_proof`·`imo_grading`과 대응 |
| `genesis`      | 로보틱스 보상 설계  | `baselines/genesis_go2walking`          |
| `balrog`       | 게임/의사결정     |                                         |
| `search_arena` | 검색·탐색       |                                         |

### 4.3 베이스라인

| 베이스라인                                 | 용도                      |
|---------------------------------------|-------------------------|
| `baselines/dgm`                       | Darwin Gödel Machine 재현 |
| `baselines/ai_reviewer`               | 리뷰 에이전트 단일 구현           |
| `baselines/imo_proof` · `imo_grading` | IMO 증명 생성/채점 파이프라인      |
| `baselines/genesis_go2walking`        | 로보틱스 보상 태스크             |
| `baselines/sft_openai`                | SFT 비교군                 |

---

## 5. 운영/보안 관점 체크포인트

1. **실행 안전성**
    - 공식 README가 경고: "executing untrusted, model-generated code". 외부 공개 서비스에 직접 배포하지 말 것.
    - Docker 격리가 기본이며 `--network=host` 빌드는 **빌드 시점에만** 필요.

2. **API 키·비용**
    - `.env`에 `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` 세 종 필요.
    - 세대 수·도메인 수·ensemble 규모에 따라 토큰 비용이 누적.

3. **시스템 요구사항**
    - Python 3.12, graphviz, cmake, ninja-build 등 네이티브 빌드 의존성.
    - 초기화: `bash ./setup_initial.sh` → 진입점 `python generate_loop.py --domains <domain>`.
    - 출력 기본 경로: `outputs/`.

4. **라이선스 제약**
    - CC BY-NC-SA 4.0: 상업 사용 금지, 2차 저작물은 동일 라이선스 승계.

---

## 6. 적용 인사이트

- **연구용 프레임워크**: 자기참조·자기개선 루프 실험 환경. 실서비스용 에이전트 런타임이 아님.
- **평가 인프라 재사용 가치**: 도메인 서브패키지 + staged/full eval + archive 시각화 구조는 다른 진화적 탐색 실험에도 이식 가능.
- **DGM 비교군 기본 내장**: baseline을 동일 리포에서 돌려 정량 비교가 쉬움.
- **확장 포인트**: 새로운 도메인은 `domains/<name>/` 에 `harness.py`·`report.py` 쌍을 두고 `utils/domain_utils` 규약에 맞추면 루프에 합류.

요약하면 HyperAgents는 에이전트 앱이 아니라, **"에이전트 개선 방법을 에이전트가 편집하게 만드는" 연구용 진화 루프**입니다.

---

## 참고 링크

- [Repository](https://github.com/facebookresearch/HyperAgents)
- [arXiv — Hyperagents (2603.19461, 2026-03-19)](https://arxiv.org/abs/2603.19461)
- [arXiv — Darwin Gödel Machine (2505.22954)](https://arxiv.org/abs/2505.22954)
- [HuggingFace Papers — Hyperagents](https://huggingface.co/papers/2603.19461)
- [VentureBeat — "Meta researchers introduce hyperagents"](https://venturebeat.com/orchestration/meta-researchers-introduce-hyperagents-to-unlock-self-improving-ai-for-non-coding-tasks)
- [Jenny Zhang 저자 X 쓰레드](https://x.com/jennyzhangzt/status/2036099940456206759)
