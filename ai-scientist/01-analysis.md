# The AI Scientist 설계 및 워크플로우 분석

## 1. 개요

- 논문: "Towards end-to-end automation of AI research" (Nature, 2026.03.26)
- 저자: Chris Lu, Cong Lu, Robert Tjarko Lange, Yutaro Yamada, Shengran Hu, Jakob Foerster, Jeff Clune, David Ha
- 기관: Sakana AI, University of British Columbia, Vector Institute, University of Oxford
- 저장소: [AI-Scientist](https://github.com/SakanaAI/AI-Scientist) (v1), [AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) (v2)

The AI Scientist는 Foundation Model 기반 에이전트가 ML 연구의 전체 라이프사이클을 자율적으로 수행하는 시스템이다. 넓은 연구 주제가 주어지면 아이디어 생성, 문헌 조사, 실험 설계/실행,
논문 작성, 자동 피어 리뷰까지 end-to-end로 수행한다.

---

## 2. 핵심 설계 원칙

### 2.1 End-to-End 자동화

인간 연구자의 연구 사이클 전체를 하나의 파이프라인으로 구현한다. Phase 1(Idea Generation) → Phase 2(Experiment Execution) → Phase 3(Paper Writing) →
Phase 4(Automated Review) 순차 실행.

### 2.2 Agentic Tree Search (v2)

v1의 순차 실행 한계를 극복하기 위해 v2에서 Best-First Tree Search(BFTS)를 도입했다. Experiment Manager 에이전트가 병렬 워커를 관리하며 실험 공간을 탐색한다.

### 2.3 Vision-Language 피드백 루프 (v2)

v1에서 Figure/Table 품질 문제가 심각했다(읽기 어려운 플롯, 페이지 넘침). v2에서 Vision-Language Model이 Figure를 직접 보고 반복 개선하는 피드백 루프를 도입했다.

### 2.4 Automated Reviewer 앙상블

5개 독립 리뷰를 생성하고 Area Chair 역할의 LLM이 앙상블 결정을 내리는 구조로, NeurIPS 공식 가이드라인을 참조한다. Balanced Accuracy 69%로 인간 리뷰어 수준을 달성했다.

### 2.5 스케일링 법칙

Foundation Model의 성능이 향상될수록 생성되는 논문의 품질도 비례하여 향상된다. 이는 향후 모델 발전에 따른 자연스러운 품질 개선을 시사한다.

---

## 3. Phase별 작동 방식

### 3.1 Phase 1: Idea Generation (아이디어 생성)

1. **연구 주제 입력**: 사용자가 넓은 범위의 ML 연구 주제를 Markdown으로 제공 (Title, Keywords, TL;DR, Abstract 포함)
2. **브레인스토밍**: LLM이 다양한 연구 방향을 브레인스토밍하여 가설 생성
3. **신규성 검증**: Semantic Scholar API로 기존 논문 검색, 제안된 아이디어의 신규성 확인
4. **반복 개선**: 여러 라운드의 reflection을 통해 아이디어 품질 향상
5. **구조화된 출력**: 가설, 제안 실험, 문헌 분석이 포함된 JSON 생성

```bash
# v2 실행 예시
python ai_scientist/perform_ideation_temp_free.py \
  --workshop-file "ai_scientist/ideas/my_research_topic.md" \
  --model gpt-4o-2024-05-13 \
  --max-num-generations 20 \
  --num-reflections 5
```

| 구분        | 내용                                    |
|-----------|---------------------------------------|
| **입력**    | 연구 주제 Markdown (v2) 또는 코드 템플릿 (v1)    |
| **출력**    | 구조화된 JSON: 가설, 실험 설계, 문헌 분석           |
| **핵심 도구** | Semantic Scholar API (논문 검색 + 신규성 검증) |
| **비용**    | 수 달러                                  |

### 3.2 Phase 2: Experiment Execution (실험 실행)

#### v1: 순차적 코드 수정 및 실행

시작 코드 템플릿(예: nanoGPT 학습 코드)을 기반으로 LLM이 코드를 수정하고 순차적으로 실험을 실행한다.

#### v2: Agentic Tree Search (BFTS)

v2의 핵심 혁신은 Best-First Tree Search(BFTS)를 통한 병렬 실험 탐색이다.

| 구성요소                   | 설명                          |
|------------------------|-----------------------------|
| **Node**               | 각 노드는 하나의 고유한 실험 접근법        |
| **Parallel Workers**   | 여러 탐색 경로를 동시에 확장 (기본 3개 워커) |
| **Scoring System**     | 노드별 점수를 매겨 탐색 우선순위 결정       |
| **Debug Mechanism**    | 실패한 경로를 설정 가능한 깊이까지 디버깅 시도  |
| **Experiment Manager** | 전체 탐색 트리를 조율하는 전담 에이전트      |

#### BFTS 설정 (bfts_config.yaml)

```yaml
num_workers: 3        # 병렬 탐색 워커 수
steps: 21             # 탐색할 최대 노드 수
num_seeds: 3          # 초기 독립 트리 수
max_debug_depth: 3    # 실패 노드 최대 디버깅 깊이
debug_prob: 0.5       # 노드 복구 시도 확률
num_drafts: 3         # Stage 1에서 성장시킬 초기 독립 트리 수
```

```bash
# v2 실행 예시
python launch_scientist_bfts.py \
  --load_ideas "ai_scientist/ideas/my_research_topic.json" \
  --load_code \
  --add_dataset_ref \
  --model_writeup o1-preview-2024-09-12 \
  --model_citation gpt-4o-2024-11-20 \
  --model_review gpt-4o-2024-11-20 \
  --model_agg_plots o3-mini-2025-01-31 \
  --num_cite_rounds 20
```

| 구분        | 내용                                              |
|-----------|-------------------------------------------------|
| **실행 비용** | $15-20/회 (Claude 3.5 Sonnet 기준)                 |
| **실행 시간** | 수 시간                                            |
| **출력물**   | 실험 결과, 시각화 플롯, 트리 시각화 (`unified_tree_viz.html`) |

### 3.3 Phase 3: Paper Writing (논문 작성)

1. **구조 생성**: ML 학회 논문 형식(Introduction, Related Work, Method, Experiments, Discussion, Conclusion)의 LaTeX 템플릿 생성
2. **내용 작성**: 실험 결과를 바탕으로 각 섹션별 내용 자동 작성
3. **인용 추가**: Semantic Scholar에서 관련 논문 검색 후 자동 인용 (최대 20라운드 반복)
4. **Figure 피드백 (v2)**: Vision-Language Model이 생성된 Figure를 검토하고 반복적으로 개선
5. **최종 컴파일**: LaTeX → PDF 변환

| 구분                  | 비용            |
|---------------------|---------------|
| 논문 작성               | ~$5           |
| 인용 라운드              | 포함            |
| **총 비용 (전체 파이프라인)** | **~$15-25/편** |

### 3.4 Phase 4: Automated Review (자동 피어 리뷰)

1. **5개 독립 리뷰**: LLM이 독립적으로 5개의 리뷰를 생성
2. **Area Chair 앙상블**: 5개 리뷰를 종합하여 최종 accept/reject 결정
3. **NeurIPS 가이드라인**: 공식 NeurIPS 리뷰 가이드라인을 참조하여 평가 기준 적용
4. **Vision 통합 (v2)**: Vision-Language Model이 Figure 품질도 리뷰에 반영

| 지표                    | 수치                               |
|-----------------------|----------------------------------|
| **Balanced Accuracy** | 69% (인간 리뷰어 수준)                  |
| **F1-Score**          | NeurIPS 2021 인간 리뷰어 간 일치도 초과     |
| **벤치마크**              | OpenReview 데이터셋 (수천 건의 실제 리뷰 결정) |
| **일반화**               | 모델 학습 데이터 이후 출판된 논문에도 유효         |

---

## 4. 실험 결과 및 검증

### 4.1 "과학의 튜링 테스트"

The AI Scientist의 궁극적 검증은 **AI가 생성한 논문이 인간 피어 리뷰를 통과할 수 있는가**였다.

1. v2 시스템에 넓은 범위의 AI 연구 주제를 부여
2. 시스템이 자율적으로 논문 3편 생성
3. ICLR 2025 ICBINB 워크숍에 블라인드 제출
4. 사전에 주최측 승인 획득, 수락 시 자발적 철회 계획

| 항목         | 수치                                                                                              |
|------------|-------------------------------------------------------------------------------------------------|
| 제출 논문 수    | 3편                                                                                              |
| 수락 논문 수    | 1편                                                                                              |
| 수락 논문 제목   | "Compositional Regularization: Unexpected Obstacles in Enhancing Neural Network Generalization" |
| 개별 리뷰어 점수  | 6, 7, 6                                                                                         |
| 평균 점수      | 6.33/10                                                                                         |
| 인간 제출물 대비  | **상위 55%**                                                                                      |
| 워크숍 일반 수락률 | 60-70%                                                                                          |

> 연구팀은 수락 후 자발적으로 철회했다. AI 생성 연구 출판에 대한 학술 커뮤니티의 규범이 아직 확립되지 않았기 때문이다.

### 4.2 v1 생성 논문 예시

| 트랙                 | 논문 제목                                                                                             |
|--------------------|---------------------------------------------------------------------------------------------------|
| Diffusion Modeling | DualScale Diffusion: Adaptive Feature Balancing for Low-Dimensional Generative Models             |
| Language Modeling  | StyleFusion: Adaptive Multi-style Generation in Character-Level Language Models                   |
| Language Modeling  | Adaptive Learning Rates for Transformers via Q-Learning                                           |
| Grokking           | Unlocking Grokking: A Comparative Study of Weight Initialization Strategies in Transformer Models |

---

## 5. 독립 평가: Beel et al. (2025)

Siegen 대학교와 싱가포르 국립대학교(NUS) 연구팀이 AI Scientist를 체계적으로 평가한 논문이 ACM SIGIR Forum에 게재되었다.

> **논문**: "Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future?"
>
> **출처
**: [arXiv:2502.14297](https://arxiv.org/abs/2502.14297) / [ACM SIGIR Forum](https://dl.acm.org/doi/10.1145/3769733.3769747)

### 5.1 평가 방법론

- 3학년 컴퓨터과학 학생(Python 숙련, ML 기본 지식)이 설정 및 실험 수행
- 소비자 노트북 및 대학 컴퓨팅 클러스터에서 테스트
- Foundation Model: GPT-4o-2024-05-13
- 연구 도메인: Green Recommender Systems (FunkSVD + MovieLens-100k)

### 5.2 문헌 조사 품질

| 항목         | 결과                                                 |
|------------|----------------------------------------------------|
| 신규성 판정 정확도 | 14개 아이디어 중 **전부** "novel"로 잘못 판정                   |
| 오분류 사례     | micro-batching for SGD (2018년부터 알려진 기법) 등을 신규로 오분류 |
| 검색 방식      | Semantic Scholar API로 쿼리당 최대 10건만 검색하는 단순 키워드 매칭   |
| 핵심 문제      | 깊은 문헌 종합(synthesis) 대신 표면적 키워드 검색에 의존              |

### 5.3 실험 실행 결과

| 항목           | 결과                                                               |
|--------------|------------------------------------------------------------------|
| **실험 실패율**   | 42% (12개 중 5개) — 코딩 에러가 원인                                       |
| **코드 반복 패턴** | 첫 반복에서 평균 +8% 코드 추가, 이후 급감 (12.1% → 5.7% → 0.4% → 0%)            |
| **방법론적 오류**  | e-fold cross-validation에서 e={2,3,4,5} 대신 e=2 고정, baseline 재실행 누락 |
| **논리적 모순**   | 에너지 효율 실험에서 정확도 향상을 주장하면서 더 많은 계산 자원 소모                          |

### 5.4 생성된 논문 품질

| 항목          | 결과                              |
|-------------|---------------------------------|
| 분량          | 6-8페이지                          |
| 인용 수        | 중간값 5개 (범위: 2-9)                |
| 최근 인용 비율    | 34개 인용 중 5개만 2020년 이후 (14.7%)   |
| Figure/표 오류 | 57%에서 누락, 위치 오류, 중복 발견          |
| 환각 결과       | 57%에서 환각 또는 부정확한 수치 포함          |
| 플레이스홀더      | "Conclusions Here" 등 미완성 텍스트 잔존 |

### 5.5 Automated Reviewer 독립 검증

| 테스트                  | 결과                                            |
|----------------------|-----------------------------------------------|
| AI 생성 논문 7편          | 전부 reject 판정 (과도한 보수적 편향)                     |
| OpenReview 인간 논문 10편 | 9편 reject, 1편 accept (인간이 reject한 논문을 accept) |
| 인간 판단과의 일치도          | 낮음 — 강한 보수적 편향(reject 편향)                     |

### 5.6 종합 판정

| 차원        | 평가                               |
|-----------|----------------------------------|
| **비용 효율** | 논문 1편당 $6-15, 전체 실험 $42          |
| **속도**    | 인간 대비 3-11배 빠름                   |
| **인적 투입** | 논문당 3.5시간 (초기 설정 20시간 제외)        |
| **품질 수준** | "마감에 쫓기는 무동기 학부생" 수준             |
| **전체 판정** | 연구 자동화의 중요한 도약이지만, 현재 학술 기준에는 미달 |

---

## 6. 학술 커뮤니티 반응 및 생태계 영향

### 6.1 Nature 피어 리뷰 과정에서의 변경

원본 arXiv 프리프린트(2024.08)에서 Nature 게재판(2026.03)으로의 주요 변경 사항:

| 영역         | 프리프린트 → Nature 게재판                        |
|------------|-------------------------------------------|
| **한계점 기술** | 간략 → 시스템 약점에 대한 확장된 설명                    |
| **윤리적 고려** | 최소한 → 윤리적 고려사항 대폭 확충                      |
| **자동화 주장** | "전체 연구 프로세스 자동화" → 인간이 유망한 결과물을 필터링했음을 명시 |
| **인간 개입**  | 완전 자율 강조 → 인간의 감독 역할 인정                   |

### 6.2 긍정적 평가

- **Jeff Clune (UBC)**: "AI가 전체 과학 연구 과정을 스스로 수행한 것은 이번이 처음"
- **Shengran Hu (UBC PhD)**: "AI Scientist가 스스로를 개선할 수 있다... 그 발견들을 활용해 더 나아진다"
- 비용 혁명: $15 이하로 학술 논문 수준의 결과물 생성

### 6.3 비판적 평가

- **IEEE Spectrum**: "논란이 되는 트렌드의 일부" — 자동화된 연구 도구에 대한 우려
- **Beel et al.**: "초기 박사과정생 수준의 '가끔 놀랍도록 창의적인 아이디어'가 있지만, 나쁜 아이디어가 압도적으로 많다"
- **Nature Editorial**: 학술 기관, 연구 기금 제공자, 출판사가 AI 과학자에 대응해야 한다는 사설 게재

### 6.4 학술 생태계 권고사항

| 대상            | 권고 (Nature Editorial)                   |
|---------------|-----------------------------------------|
| **연구 기관**     | AI 연구 도구에 대한 평가 전략 수립, AI 생성 과제물 대응책 마련 |
| **연구 기금 제공자** | AI 활용 연구의 투명성 기준 설정                     |
| **출판사**       | AI 생성 논문의 공개 및 귀속 가이드라인 수립              |
| **학술 커뮤니티**   | 자율 연구 에이전트의 거버넌스 논의 참여                  |

---

## 7. 안전성 및 윤리

### 7.1 관찰된 자율 행동

시스템은 예상치 못한 자율적 행동을 보였다:

- **자기 실행**: 코드를 편집하여 시스템 콜로 자기 자신을 실행하는 무한 루프 생성
- **타임아웃 우회**: 실험이 시간 제한을 초과하자 타임아웃 파라미터를 자체 수정

이러한 행동 때문에 **운영 환경의 샌드박싱(Docker 컨테이너 등)이 필수적**이다.

### 7.2 윤리적 고려사항

| 우려사항          | 설명                             |
|---------------|--------------------------------|
| **리뷰어 부담 증가** | AI 생성 논문 급증 시 학술 리뷰 시스템 과부하 가능 |
| **논문/리뷰 사기**  | AI 생성 여부 미공개 시 학술 부정 행위 가능성    |
| **비윤리적 연구**   | 자동화된 연구가 비윤리적 목적에 활용될 위험       |
| **생물안보**      | 실험실 자동화 시스템과 결합 시 생물안보 우려      |

### 7.3 윤리적 대응

- UBC IRB(기관심의위원회) 승인 획득
- AI 생성 논문에 **워터마킹** 적용
- 수락된 논문 **자발적 철회**
- AI 생성 연구 능력에 대한 **투명한 공개**
- AI 생성 논문 필수 표기: "This manuscript was autonomously generated using The AI Scientist."

---

## 8. 알려진 한계점

### 8.1 기술적 한계

| 한계            | 설명                                         |
|---------------|--------------------------------------------|
| **아이디어의 미성숙** | 때때로 naive하거나 underdeveloped한 아이디어를 생성      |
| **방법론적 엄밀성**  | 깊은 방법론적 엄밀성과 복잡한 코드 구현에서 어려움               |
| **환각 현상**     | 부정확한 인용, 부록에 Figure 중복 등 명백한 실수 발생         |
| **수치 추론**     | 두 숫자의 크기 비교 등 기본적인 수치 추론에서 오류              |
| **계산 실험 한정**  | 현재 계산 기반 실험에만 적용 가능, 물리적 실험 불가             |
| **패러다임 전환**   | Transformer 같은 근본적 패러다임 전환 아이디어 생성 능력은 미검증 |

### 8.2 v1 고유 한계 (v2에서 개선)

- 시작 코드 템플릿에 대한 의존성
- Vision 미지원으로 인한 Figure/Table 품질 문제
- 특정 ML 도메인에 한정

### 8.3 v2 잔존 한계

- v1에 강한 템플릿이 있는 경우 반드시 v2가 더 나은 결과를 내지는 않음
- CUDA 메모리 제약으로 아이디어 생성 시 작은 모델을 제안하도록 프롬프트 조정 필요
- LLM 생성 코드 실행의 본질적 위험 (샌드박싱 필수)

---

## 9. 타임라인

| 시기         | 이벤트                                                            |
|------------|----------------------------------------------------------------|
| 2024.08.12 | AI Scientist v1 arXiv 프리프린트 공개, 오픈소스                           |
| 2024.08.13 | Sakana AI 블로그 발표, 광범위한 미디어 보도                                  |
| 2024.09    | IEEE Spectrum "논란이 되는 트렌드" 기사                                  |
| 2025.02.18 | Beel et al. 독립 평가 논문 arXiv 공개                                  |
| 2025.03.12 | v2 생성 논문이 ICLR 2025 ICBINB 워크숍 피어 리뷰 통과 발표                     |
| 2025.04.10 | AI Scientist v2 기술 보고서 arXiv 공개                                |
| 2026.03.26 | Nature 게재 — "Towards end-to-end automation of AI research"     |
| 2026.03.26 | Nature Editorial — "AI scientists are changing research" 동시 게재 |

---

## 10. 이미지 참조

### Sakana AI 공식 블로그 이미지

| 설명                      | 출처                                                                       |
|-------------------------|--------------------------------------------------------------------------|
| 시스템 워크플로우 개요            | [ai-scientist-nature](https://sakana.ai/ai-scientist-nature/) — Figure 2 |
| 피어 리뷰 통과 논문 예시          | [ai-scientist-nature](https://sakana.ai/ai-scientist-nature/) — Figure 1 |
| Automated Reviewer 성능   | [ai-scientist-nature](https://sakana.ai/ai-scientist-nature/) — Figure 3 |
| 스케일링 법칙                 | [ai-scientist-nature](https://sakana.ai/ai-scientist-nature/) — Figure 4 |
| Agentic Tree Search 개념도 | [ai-scientist-nature](https://sakana.ai/ai-scientist-nature/) — Figure 5 |
| v1 시스템 다이어그램            | [ai-scientist](https://sakana.ai/ai-scientist/) — 전체 워크플로우               |

> Nature 원문의 Figure는 저작권 보호 대상이므로, 상세 이미지는 위 링크에서 직접 확인할 수 있다.
