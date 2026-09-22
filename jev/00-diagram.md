# Jev 실행 흐름과 책임 경계

이 문서는 공개 API를 바탕으로 구성한 애플리케이션 설계 예시입니다. Jev의 비공개 모델 구조나 실제 운영 구현을 재현한 그림은 아닙니다. 계약은 [공식 소개](https://docs.typesafe.ai/introduction), [API](https://docs.typesafe.ai/api), [Fan-out](https://docs.typesafe.ai/patterns/fan-out)을 기준으로 합니다.

## 1. 판단과 실행을 분리하기

```mermaid
flowchart TD
    INPUT["업무 텍스트와 확인된 기록"] --> PREP["애플리케이션: 관련 상태 준비"]
    PREP --> MODEL["Jev: Choice · Score · Noul"]
    MODEL --> CHECK["애플리케이션: 응답 검사와 정책 적용"]
    CHECK --> GATE{"정보 · 판단 · 권한이 충분한가?"}
    GATE -- "아니요 또는 판단 충돌" --> HOLD["보류 · 추가 정보 · 사람 검토"]
    GATE -- "예" --> APPROVE{"사람 승인이 필요한 실행인가?"}
    APPROVE -- "예" --> HUMAN["사용자 또는 담당자 승인"]
    HUMAN --> DECISION{"승인됨?"}
    DECISION -- "아니요" --> STOP["실행하지 않음"]
    DECISION -- "예" --> EXEC["업무 도구 실행"]
    APPROVE -- "아니요" --> EXEC
    EXEC --> VERIFY["최종 업무 상태 확인"]
    VERIFY --> RESULT{"요구한 결과가 확인됐는가?"}
    RESULT -- "예" --> DONE["완료 기록"]
    RESULT -- "아니요" --> RECOVER["미완료 기록 · 복구 검토"]
```

높은 확률은 실행 권한이 아닙니다. 보류·승인·복구 정책은 애플리케이션이 정하며, 예외 없이 자동 실행해도 된다는 공급자 보장으로 읽지 않습니다. [환불 사례](02-api-and-integration.md)의 판단도 취소 실행이 아니라 처리 경로 선택에 사용합니다.

## 2. 묶을 수 있는 질문과 다시 관측해야 하는 상태

```mermaid
sequenceDiagram
    participant App as 애플리케이션
    participant Jev as Jev API
    participant Tool as 업무 도구
    App->>App: 같은 시점의 상태 S 준비
    App->>Jev: S와 독립 질문 묶음
    Jev-->>App: 질문 ID별 판단과 분포
    App->>App: 규칙·보류·승인 조건 확인
    alt 실행 조건 충족
        App->>Tool: 허용된 작업 요청
        Tool-->>App: 실행 결과
        App->>App: 변경된 상태 S2 관측
        opt 새 상태에 대한 의미 판단 필요
            App->>Jev: S2와 후속 질문
            Jev-->>App: 새 판단
        end
    else 실행 조건 미충족
        App->>App: 실행하지 않고 보류 경로로 전달
    end
```

같은 입력의 의도·긴급성은 함께 물을 수 있지만, 실행 뒤 나타나는 사실은 미리 알 수 없습니다. 묶음 요청의 성능과 전체 업무 지연을 구분해야 하는 이유입니다.

## 3. 생성 결과 검사와 상위 모델 전환

```mermaid
flowchart LR
    SOURCE["원문"] --> SMALL["작은 생성 모델: 추출"]
    SOURCE --> REVIEW["Jev: 원문과 추출값 비교"]
    SMALL --> REVIEW
    REVIEW --> GATE{"검사 기준 통과?"}
    GATE -- "예" --> CODE["코드 검증 · 업무 정책"]
    GATE -- "아니요" --> FALLBACK["강한 모델 또는 사람 검토"]
    FALLBACK --> CODE
    CODE --> RESULT["처리 결과와 근거 기록"]
```

[SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade)의 역할 분리를 일반화한 그림입니다. 강한 모델로 넘어갔다고 정답이 보장되지는 않습니다. 검사 모델의 오답 통과율과 불필요한 전환율을 함께 평가합니다.
