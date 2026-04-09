# 코드 분석 파이프라인 (Analysis Pipeline)

4-Layer 아키텍처와 Writer/Judge 패턴을 결합한 AI 기반 코드 분석 파이프라인입니다.
관찰(사실 수집)과 판단(평가)을 구조적으로 분리하여 확증 편향을 방지하고, 규모에 비례하는 비용 투자로 효율적인 분석을 수행합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/analysis-pipeline/00-diagram.md) | 4-Layer 구조, 상태 머신, 규모 기반 라우팅, Writer/Judge 흐름 |
| [파이프라인 개요](/analysis-pipeline/01-overview.md) | 4-Layer 아키텍처, 관찰/판단 분리, XML 번들 구조, 분석 목적별 산출물 |
| [3-Stage 처리 상세](/analysis-pipeline/02-stages.md) | 파일별 분석, Writer/Judge 합성, 교차 검증, Fanout 병렬화 |
| [재개 및 비용 최적화](/analysis-pipeline/03-resume-optimization.md) | 점진적 재개, Drift 감지, Observation 캐시, 지식 축적, 원자적 상태 관리 |

---

## 핵심 설계 원칙

| ID | 원칙 |
|----|------|
| A1 | 파이프라인은 4개 독립 Layer와 명확한 입출력 계약으로 구성됩니다 |
| A2 | 관찰(Layer 2)과 판단(Layer 3)은 구조적으로 분리되어야 합니다 |
| A3 | 실패 시 마지막 완료 Stage 이후부터 재개합니다 (전체 재실행 없음) |
| A4 | 상태 파일 갱신은 원자적이어야 합니다 (중간 상태 노출 금지) |
| A5 | Writer/Judge는 분리 실행되며, Analysis Judge는 Writer의 evidence를 변조하지 않습니다 |
| A6 | 각 mode는 고정된 산출물 집합을 정의하며, Writer 구성과 산출물은 mode에 의해 쌍으로 결정됩니다 |

---

## 아키텍처 개요

```text
Layer 1: Input (탐색)
    소스코드 수집 → 분석 단위 식별 → 규모 판정 → 분석 목적 결정
    ↓
Layer 2: Bundle (관찰 수집)
    파일별 번들 생성 → 관찰 추출 (사실만, 판단 없음)
    ↓
Layer 3: Analyze (판단)
    Stage 1: 파일별 분석 → Stage 2: Writer/Judge 합성 → Stage 3: 교차 검증 (조건부)
    ↓
Layer 4: Output (산출물)
    결과 병합 → 산출물 생성 → 프로젝트 지식 갱신
```

### 핵심 설계 포인트

- **관찰과 판단의 분리**: 사실 수집(Layer 2)과 평가(Layer 3)를 격리하여 확증 편향을 방지합니다.
- **규모 비례 투자**: 분석 대상 크기에 따라 Provider 등급과 비용을 차등 배분합니다.
- **Writer/Judge 패턴**: 다중 Writer가 독립적으로 분석하고, Analysis Judge가 충돌을 해소합니다.
- **점진적 재개**: 실패 시 마지막 완료 지점부터 재개하며, 해시 기반 변경 감지로 중복 분석을 방지합니다.
- **상태 외부화**: 모든 진행 상태를 파일 시스템에 기록하여 원자적 복원이 가능합니다.

---

## 참고 자료

- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Google Cloud: Choose a design pattern for an agentic AI system](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
