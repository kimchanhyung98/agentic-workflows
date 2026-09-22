# Jev 공식 문서와 검증 범위

> 공식 문서 확인일: 2026-09-22 · 변경 가능한 서비스 문서는 확인 시점 기준

## 1. 근거를 읽는 기준

외부 출처 링크는 TypeSafe와 비교 대상 프로젝트의 공식 문서, 직접 확인한 TypeSafe 콘솔만 사용함. 이 디렉토리 안의 문서 링크는 설명을 연결하는 용도이며, 다른 프로젝트의 문서나 로컬 조사 자료를 전제로 하지 않음.

| 근거 종류 | 이 문서에서 말할 수 있는 것 | 대신 증명하지 못하는 것 |
| --- | --- | --- |
| 공식 제품·API 문서 | 공급자가 설명하는 계약·한도·가격 | 모든 요청에서의 실제 품질·가용성 |
| 공식 문서의 평가·cookbook | 공급자가 공개한 실험 조건·결과 | 독립 재현·다른 언어와 업무의 성능 |
| 자체 콘솔 실행 | 해당 입력·화면 조건의 응답·보고된 사용량 | 원시 HTTP 정밀도·일반 정확도·실제 청구액 |
| 자체 직접 HTTP 반복 실험 | 고정 요청의 반복 변동·클라이언트 시간·오류 | 콘솔 실행·내부 변동 원인·운영 SLA |
| 본 문서의 설계·정책 예시 | 계약과 적용 방식을 설명하는 해석 | 실제 업무 완료·운영 정책의 타당성 |

## 2. TypeSafe 제품·API 문서

| 공식 문서 | 확인할 내용 |
| --- | --- |
| [Introduction](https://docs.typesafe.ai/introduction), [System One](https://docs.typesafe.ai/concepts/system-one) | 판단 모델의 역할과 출력 범위 |
| [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer) | 공급자의 RLCD 설명 |
| [API](https://docs.typesafe.ai/api), [Advanced](https://docs.typesafe.ai/primitives/advanced) | 요청·응답과 구조화 기준, 문서 간 차이 |
| [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul) | 각 질문 타입의 의미 |
| [Confidence](https://docs.typesafe.ai/confidence), [State](https://docs.typesafe.ai/concepts/state) | 불확실성 요약과 입력 구성 |
| [Models](https://docs.typesafe.ai/models), [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | 버전·가격·한도·알려진 한계 |

## 3. 공식 문서의 평가·응용 예시

| 공식 문서 | 확인할 내용 |
| --- | --- |
| [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions) | 동일 상태의 질문 묶음과 순차 호출 비교 |
| [Choice consistency](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook) | 최빈 선택 일치율·보류 정책 |
| [Pre-parsed extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook) | 원문 후보 추출과 선택의 분리 |
| [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade), [Fan-out](https://docs.typesafe.ai/patterns/fan-out) | 생성 후 검사·전환과 질문 묶음 |

## 4. 비교·평가에 사용한 공식 문서

- [Outlines 출력 타입](https://dottxt-ai.github.io/outlines/main/features/core/output_types/): 생성 결과의 형식·선택지 제약.
- [SetFit](https://huggingface.co/docs/setfit/index): 고정 라벨 분류 모델의 학습·예측.
- [Semantic Router](https://docs.aurelio.ai/docs/semantic-router/user-guide/concepts/overview): 질의와 예문을 이용한 경로 선택.
- [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html): 보정 곡선·Brier score 해석.

역할별 차이와 적용 한계는 [비교 문서](04-comparison.md)에 정리했음. 이 프로젝트들을 같은 데이터셋으로 실행해 성능을 비교한 것은 아님.

## 5. 핵심 용어

| 용어 | 이 문서에서의 의미 |
| --- | --- |
| 상태, state | 질문에 답할 때 읽는 업무 텍스트·기록 |
| 기준, criteria | 선택지 또는 수준의 의미를 정하는 설명 |
| 확률 보정, calibration | 예측 확률 구간과 실제 사건 빈도의 일치 정도 |
| confidence | Jev가 반환하는 분포의 요약값, 정답 확률과 구분 |
| 보류, abstention | 판단을 바로 실행에 쓰지 않고 검토·추가 정보 경로로 넘김 |
| 자동 처리 비율, coverage | 전체 대상 중 보류 없이 처리한 비중 |
| 선택적 오류율 | 자동 처리한 사례만을 분모로 계산한 오류율 |
| Brier score | 예측 확률과 실제 결과의 제곱 오차 기반 점수, 보정만의 지표는 아님 |
| SDE | Structured Data Extraction, 원문을 필드가 있는 레코드로 추출 |
| cascade | 앞선 결과·검사에 따라 다음 모델이나 검토 단계로 전환 |
| fan-out | 같은 상태에서 여러 독립 질문을 펼쳐 평가 |

## 6. 콘솔 직접 확인과 별도 API 실험

2026-09-22에 로그인된 [TypeSafe Playground 콘솔](https://console.typesafe.ai/playground)에서 가상 고객 문장 10개를 총 14회 실행하고 화면의 JSON 결과를 직접 확인했음. 계정 정보·API 키·고객 개인정보는 문서에 기록하지 않았음.

후속으로 새 합성 사례 100개를 각각 10회 직접 HTTP 호출했음. 정상 응답 1,000개, 529 실패를 포함한 시도 1,001회임. 이는 콘솔 실행이 아닌 API 실험이며, 이전 Playground 결과와 합치지 않고 별도 분석했음.

| 보고서 | 다루는 내용 |
| --- | --- |
| [Playground 실행·분석](06-playground-experiment.md) | 콘솔에서 직접 확인한 실행 과정·관측 결과·한계 |
| [100개 반복 실험 보고서](07-repeatability-experiment.md) | 별도 HTTP 실험의 반복 변동·오분류·시간·한계 |

실험용 코드·테스트·입력 파일·원시 응답·분석 JSON은 저장소에서 제거했음. 위 보고서는 당시 관측과 집계 결과를 정리한 문서이며, 현재 저장소만으로 원문 대조나 재집계는 할 수 없음.
