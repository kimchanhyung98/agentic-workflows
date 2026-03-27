# The AI Scientist 아키텍처 다이어그램

## 1. 전체 파이프라인

```mermaid
flowchart TD
    INPUT["연구 주제 입력\n(Markdown / 코드 템플릿)"] --> P1

    subgraph P1["Phase 1: Idea Generation"]
        IG1["LLM 브레인스토밍"] --> IG2["Semantic Scholar\n신규성 검증"]
        IG2 --> IG3["Reflection 반복 개선"]
        IG3 --> IG4["구조화된 JSON 출력\n(가설 + 실험 계획)"]
    end

    P1 --> P2

    subgraph P2["Phase 2: Experiment Execution"]
        EX1["Experiment Manager\n(전담 에이전트)"] --> EX2["Agentic Tree Search\n(BFTS 병렬 탐색)"]
        EX2 --> EX3["코드 생성 및 실행\n(Sandbox 환경)"]
        EX3 --> EX4["결과 수집 및\n시각화"]
    end

    P2 --> P3

    subgraph P3["Phase 3: Paper Writing"]
        PW1["LaTeX 구조 생성\n(학회 논문 형식)"] --> PW2["섹션별 내용 작성"]
        PW2 --> PW3["Semantic Scholar\n자동 인용 (20 라운드)"]
        PW3 --> PW4["Vision-LM\nFigure 피드백 루프"]
        PW4 --> PW5["최종 PDF 생성"]
    end

    P3 --> P4

    subgraph P4["Phase 4: Automated Review"]
        AR1["5개 독립 리뷰 생성"] --> AR2["Area Chair\n앙상블 결정"]
        AR2 --> AR3["Accept / Reject"]
    end
```

## 2. Agentic Tree Search (BFTS) 상세

```mermaid
flowchart TD
    ROOT["Root Node\n(연구 가설)"] --> W1["Worker 1"]
    ROOT --> W2["Worker 2"]
    ROOT --> W3["Worker 3"]
    W1 --> A["Approach A\n(실험 변형 1)"]
    W2 --> B["Approach B\n(실험 변형 2)"]
    W3 --> C["Approach C\n(실험 변형 3)"]
    A --> A1["A-1\nScore: 0.82"]
    A --> A2["A-2\nScore: 0.65"]
    B --> B1["B-1\nScore: 0.71"]
    C --> C1["C-1\n❌ 실패"]
    C --> C2["C-2\nScore: 0.88"]
    C1 --> DBG["Debug Mechanism\n(max_debug_depth=3)"]
    DBG --> C1R["C-1 재시도\nScore: 0.74"]

    subgraph MGR["Experiment Manager"]
        M1["노드 우선순위 평가"]
        M2["탐색 전략 조율"]
        M3["실패 노드 디버깅 결정"]
        M4["병렬 워커 관리"]
    end

    MGR -.-> W1
    MGR -.-> W2
    MGR -.-> W3
```

## 3. Automated Reviewer 구조

```mermaid
flowchart TD
    PDF["생성된 논문 PDF"] --> R1["Review 1\n(독립)"]
    PDF --> R2["Review 2\n(독립)"]
    PDF --> R3["Review 3\n(독립)"]
    PDF --> R4["Review 4\n(독립)"]
    PDF --> R5["Review 5\n(독립)"]
    R1 --> AC["Area Chair\n(앙상블 결정)"]
    R2 --> AC
    R3 --> AC
    R4 --> AC
    R5 --> AC
    AC --> DEC{"Accept / Reject"}
    DEC -->|" NeurIPS 가이드라인\n기반 평가 "| RESULT["최종 판정\nBalanced Accuracy: 69%\nF1 > 인간 리뷰어 간 일치도"]
```

## 4. v1 vs v2 아키텍처 비교

```mermaid
flowchart LR
    subgraph V1["v1 (2024.08) — 템플릿 기반"]
        V1A["코드 템플릿\n(nanoGPT 등)"] --> V1B["LLM 코드 수정"]
        V1B --> V1C["순차 실험 실행"]
        V1C --> V1D["결과 시각화"]
        V1D --> V1E["LaTeX 논문 생성"]
        V1E --> V1F["Automated Reviewer"]
    end

    subgraph V2["v2 (2025.04) — 템플릿 프리"]
        V2A["연구 주제\n(Markdown)"] --> V2B["LLM 브레인스토밍\n+ Semantic Scholar"]
        V2B --> V2C["Experiment Manager\n+ BFTS 병렬 탐색"]
        V2C --> V2D["Vision-LM\nFigure 피드백"]
        V2D --> V2E["LaTeX 논문\n+ 자동 인용"]
        V2E --> V2F["Automated Reviewer\n(Vision 포함)"]
    end
```

## 5. Paper Writing 피드백 루프

```mermaid
flowchart TD
    EXP["실험 결과 + 분석 노트"] --> STRUCT["LaTeX 구조 생성\n(학회 논문 형식)"]
    STRUCT --> WRITE["섹션별 내용 작성\n(LLM)"]
    WRITE --> CITE["Semantic Scholar\n인용 자동 추가\n(최대 20 라운드)"]
    CITE --> VFIG["Vision-Language Model\nFigure 피드백"]
    VFIG --> EVAL{"Figure 품질\n충분한가?"}
    EVAL -- " 불충분 " --> VFIG
    EVAL -- " 충분 " --> FINAL["최종 PDF 생성"]
```

## 6. Foundation Model별 논문 품질 스케일링

```mermaid
quadrantChart
    title "Foundation Model 성능 vs 생성 논문 품질"
    x-axis "낮은 모델 성능" --> "높은 모델 성능"
    y-axis "낮은 논문 품질" --> "높은 논문 품질"
    "Llama-3": [0.25, 0.2]
    "DeepSeek": [0.35, 0.3]
    "GPT-4o": [0.6, 0.55]
    "Claude Sonnet": [0.7, 0.7]
    "o1-preview": [0.8, 0.75]
```

## 7. 시스템 구성 요소 맵

```mermaid
flowchart TD
    subgraph CORE["The AI Scientist v2"]
        IDE["Ideation\n• LLM 브레인스토밍\n• Semantic Scholar 신규성 검증"]
        ENG["Experiment Engine\n• Experiment Manager\n• BFTS 병렬 탐색\n• 3+ 병렬 워커\n• 자동 디버깅"]
        WRT["Paper Writer\n• LaTeX 생성\n• 자동 인용\n• Vision-LM Figure 피드백"]
    end

    subgraph FM["Foundation Models"]
        GPT["GPT-4o"]
        CS["Claude Sonnet"]
        O1["o1-preview"]
        O3["o3-mini"]
        DS["DeepSeek"]
    end

    subgraph EXT["외부 서비스"]
        SS["Semantic Scholar API"]
        SB["Sandbox (Docker)\n코드 실행 환경"]
        AR["Automated Reviewer\n• 5개 독립 리뷰\n• Area Chair 앙상블\n• NeurIPS 가이드라인"]
    end

    IDE --> FM
    ENG --> FM
    WRT --> FM
    IDE --> SS
    ENG --> SB
    WRT --> AR
```

## 8. 타임라인

```mermaid
timeline
    title The AI Scientist 주요 이벤트
    2024.08: v1 arXiv 프리프린트 공개
        : 오픈소스 릴리스
        : IEEE Spectrum 보도
    2025.02: Beel et al. 독립 평가 논문
    2025.03: v2 생성 논문 ICLR 2025 워크숍 피어 리뷰 통과
        : 수락 후 자발적 철회
    2025.04: v2 기술 보고서 arXiv 공개
    2026.03: Nature 게재
        : Nature Editorial 동시 게재
```

## 9. 독립 평가 결과 요약

```mermaid
flowchart TD
    subgraph EVAL["Beel et al. 독립 평가 (2025.02)"]
        LIT["문헌 조사 품질\n14개 아이디어 전부\n'novel'로 오판"]
        EXP["실험 실행\n12개 중 5개 실패\n(42% 실패율)"]
        PAP["논문 품질\n57% 환각 수치\n중간값 인용 5개"]
        REV["Automated Reviewer\n10편 중 9편 reject\n보수적 편향"]
    end

    subgraph VERDICT["종합 판정"]
        COST["비용: $6-15/편\n속도: 인간 대비 3-11x"]
        QUALITY["품질: '마감에 쫓기는\n학부생' 수준"]
        FUTURE["전망: 중요한 도약이나\n현재 학술 기준 미달"]
    end

    LIT --> VERDICT
    EXP --> VERDICT
    PAP --> VERDICT
    REV --> VERDICT
```
