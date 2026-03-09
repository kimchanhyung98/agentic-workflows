# 맞춤 로직 패턴 (Custom Logic Pattern)

## 개요

맞춤 로직 패턴은 조건문 등 코드를 사용하여 여러 분기 경로가 있는 복잡한 워크플로를 구현하는 패턴입니다. 표준 패턴으로는 표현하기 어려운 고유한 비즈니스 로직을 직접 설계할 때 사용합니다.

**핵심 특징:**

- 코드 기반의 조건 분기 로직으로 세밀한 실행 제어
- 여러 표준 패턴(순차, 병렬, 루프)의 혼합 사용
- 미리 정의된 규칙과 모델 추론의 결합
- 최대 유연성 제공

**적합한 상황:**

- 선형 시퀀스를 넘어선 복잡한 분기 로직이 필요할 때
- 표준 패턴 템플릿에 맞지 않는 워크플로
- 비즈니스 규칙에 따른 조건부 처리가 필요한 경우
- 최대한의 실행 제어가 필요할 때

---

## 아키텍처

### 고객 환불 프로세스 예시

```mermaid
flowchart TD
    User([고객 요청]) --> Coordinator

    Coordinator["코디네이터<br/>고객 환불 에이전트"]

    Coordinator --> ParallelCheck

    subgraph ParallelCheck["병렬 검증"]
        V1["구매자 검증<br/>에이전트"]
        V2["환불 자격 확인<br/>에이전트"]
    end

    V1 --> Gather[결과 수집]
    V2 --> Gather

    Gather --> Condition{"환불 자격<br/>충족?"}

    Condition -- "✅ 자격 충족" --> RefundPath
    Condition -- "❌ 자격 미충족" --> CreditPath

    subgraph RefundPath["환불 처리 경로"]
        Refund[환불 처리 에이전트]
        Refund --> ProcessRefund[환불 실행 도구]
    end

    subgraph CreditPath["스토어 크레딧 경로"]
        Credit1["스토어 크레딧<br/>에이전트"]
        Credit1 --> Credit2["크레딧 결정<br/>처리 에이전트"]
    end

    ProcessRefund --> Response["최종 응답<br/>에이전트"]
    Credit2 --> Response

    Response --> Output([고객 응답])
```

### 일반화된 맞춤 로직 흐름

```mermaid
flowchart TD
    Input([입력]) --> Logic

    subgraph CustomLogic["맞춤 로직 워크플로"]
        Logic["비즈니스 로직<br/>코드 기반 분기"]

        Logic --> |조건 A| Path1[순차 처리]
        Logic --> |조건 B| Path2[병렬 처리]
        Logic --> |조건 C| Path3[루프 처리]

        subgraph Path1["경로 A: 순차"]
            S1[에이전트 1] --> S2[에이전트 2]
        end

        subgraph Path2["경로 B: 병렬"]
            P1[에이전트 3]
            P2[에이전트 4]
        end

        subgraph Path3["경로 C: 루프"]
            L1[에이전트 5] --> L2{조건 충족?}
            L2 -- "아니오" --> L1
            L2 -- "예" --> L3[완료]
        end

        S2 --> Merge[결과 통합]
        P1 --> Merge
        P2 --> Merge
        L3 --> Merge
    end

    Merge --> Output([최종 출력])
```

### 작동 흐름

```mermaid
sequenceDiagram
    participant U as 고객
    participant C as 코디네이터
    participant V1 as 구매자 검증
    participant V2 as 자격 확인
    participant R as 환불 처리
    participant SC as 크레딧 처리

    U->>C: 환불 요청

    par 병렬 검증
        C->>V1: 구매자 신원 확인
        C->>V2: 환불 자격 확인
    end

    V1-->>C: 검증 결과
    V2-->>C: 자격 결과

    Note over C: 비즈니스 로직 평가<br/>(조건부 분기)

    alt 환불 자격 충족
        C->>R: 환불 처리 요청
        R-->>C: 환불 완료
    else 자격 미충족
        C->>SC: 스토어 크레딧 처리
        SC-->>C: 크레딧 발급
    end

    C-->>U: 최종 응답
```

---

## 사용 예시

### 1. 환불 프로세스 자동화

위의 아키텍처 다이어그램과 같이:

- 구매자 검증과 환불 자격 확인을 **병렬**로 실행
- 결과에 따라 환불 경로 또는 스토어 크레딧 경로로 **조건 분기**
- 각 경로 내에서 **순차적** 처리

### 2. 보험 청구 처리

복잡한 규칙 기반 의사결정:

- **병렬**: 서류 유효성 검증 + 보험 가입 이력 확인 + 사고 사실 확인
- **조건 분기**: 청구 금액에 따라 자동 승인 / 전문가 심사 / 현장 조사
- **루프**: 추가 서류 요청 시 서류 제출까지 반복

### 3. 채용 프로세스 자동화

다단계 채용 파이프라인:

- **순차**: 이력서 스크리닝 → 기술 평가 → 면접 일정 조율
- **조건 분기**: 경력 수준에 따라 주니어/시니어 평가 트랙 분리
- **병렬**: 레퍼런스 체크 + 백그라운드 체크 동시 실행

---

## 장단점

| 구분    | 내용                        |
|-------|---------------------------|
| ✅ 장점  | 세밀한 실행 제어로 복잡한 비즈니스 로직 구현 |
| ✅ 장점  | 여러 표준 패턴의 자유로운 혼합         |
| ✅ 장점  | 고유한 요구사항에 맞춤 최적화          |
| ⚠️ 단점 | 개발 및 유지보수 복잡성 증가          |
| ⚠️ 단점 | 오류 발생 가능성 높음              |
| ⚠️ 단점 | 표준 패턴 대비 개발 노력 증가         |
| ⚠️ 단점 | 워크플로 변경 시 코드 수정 필요        |

---

## 설계 고려사항

- **표준 패턴 우선 검토**: 맞춤 로직 전에 표준 패턴으로 해결 가능한지 확인
- **모듈화**: 각 분기 경로를 독립적 모듈로 설계하여 유지보수성 확보
- **에러 핸들링**: 모든 분기 경로에 대한 예외 처리 정의
- **테스트 전략**: 모든 분기 조합에 대한 테스트 케이스 작성

---

## 참고 자료

- [Google Cloud: Agentic AI Design Patterns](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
- [Google ADK: Custom Agents](https://google.github.io/adk-docs/agents/custom-agents/)
