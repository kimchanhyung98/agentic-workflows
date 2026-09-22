# Jev와 유사 프로젝트 비교

> 확인일: 2026-09-22 · 공식 문서 기반 역할 비교 · 동일 데이터셋 성능 비교 미수행

## 1. 같은 판단이라도 맡는 단계가 다르다

아래 프로젝트는 Jev의 일대일 대체품 목록이 아님. 출력 형식, 학습 분류, 경로 선택 중 어느 문제를 해결하는지에 따라 비교 단위가 달라짐.

| 접근 | 입력 → 출력 | 준비·운영 부담 | Jev와 비교할 부분 |
| --- | --- | --- | --- |
| Jev | 문맥 + 요청별 질문·기준 → Choice·Score·Noul | API 연동·질문 설계·업무 평가 | 좁은 의미 판단과 불확실성 활용 |
| Outlines | 프롬프트 + 출력 타입 → 제약된 생성 결과 | 생성 모델·백엔드·스키마 선택 | 허용된 선택지·구조로 결과 반환 |
| SetFit | 텍스트 → 학습한 클래스·클래스 확률 | 라벨 학습·평가·모델 배포와 갱신 | 고정 업무의 분류 |
| Semantic Router | 질의 + 경로 예문 → 처리 경로 또는 미매칭 | 예문·encoder·index·임계값 관리 | 문의를 적절한 처리기로 분배 |

Jev는 고객별 모델 학습 대신 요청의 상태·질문·기준으로 동작을 조정한다고 설명함. 같은 분류 결과를 만들 수 있다는 사실이 같은 학습·운영 방식을 뜻하지는 않음. [Jev Models](https://docs.typesafe.ai/models). 다른 프로젝트의 근거와 제한은 아래에 구분했음.

## 2. 출력 제약: Outlines

Outlines는 `Literal`·`Enum`·`Choice`, JSON Schema, 정규식·문법 등으로 생성 가능한 형태를 제한하는 도구임. 로컬·원격 모델을 연결할 수 있지만, 지원하는 출력 타입은 백엔드에 따라 다름. [출력 타입](https://dottxt-ai.github.io/outlines/main/features/core/output_types/), [백엔드](https://dottxt-ai.github.io/outlines/main/features/advanced/backends/)

Jev와의 비교에서는 기존 생성 모델에 출력 제약을 적용한 뒤 같은 분류 과제를 평가할 수 있음. Outlines 자체를 판단 모델로 세거나, JSON 숫자 필드가 있다는 이유만으로 보정된 확률을 제공한다고 취급하지 않음. 형식에 맞는 오답과 형식 오류를 따로 집계해야 함.

이 방식은 의미 판단을 기존 생성 모델에 맡기면서 허용되지 않은 라벨·구조를 줄이고 싶은 경우의 비교 후보임. 이는 기능 차이에서 도출한 선정 기준이지 속도·정확도 우위 주장과는 다름.

## 3. 고정 라벨 분류: SetFit

SetFit은 Sentence Transformer와 분류 헤드를 결합하며 기본 헤드는 logistic regression임. 업무의 라벨 예시로 학습하고, `predict`로 클래스, `predict_proba`로 클래스 확률을 얻음. 다국어 checkpoint도 사용할 수 있음. [개요](https://huggingface.co/docs/setfit/index), [분류 헤드](https://huggingface.co/docs/setfit/how_to/classification_heads), [예측 API](https://huggingface.co/docs/setfit/reference/main#SetFitModel.predict_proba)

라벨이 안정적인 반복 업무와 자체 모델 실행이 필요한 조건에서는 기준선으로 검토할 수 있음. 반대로 판단 질문이 요청마다 달라지면 학습·재평가 부담까지 비교해야 함. 다국어 모델과 클래스 확률을 제공한다는 사실은 한국어 정확도나 보정 품질을 보장하지 않음.

평가 비용에는 추론뿐 아니라 라벨 작성·학습·배포·새 라벨 반영 비용을 포함함. Jev의 요청당 질문 변경과 SetFit의 분류 체계 갱신을 같은 작업으로 취급하지 않는 것이 핵심임.

## 4. 처리 경로 선택: Semantic Router

Semantic Router는 질의와 경로별 예문을 embedding으로 표현하고 유사도·임계값으로 경로를 고름. 기준을 넘지 못하면 미매칭으로 남길 수 있으며, 라벨링된 질의로 경로별 임계값을 조정하는 기능도 제공함. [라우팅 개념](https://docs.aurelio.ai/docs/semantic-router/user-guide/concepts/overview), [임계값 최적화](https://docs.aurelio.ai/docs/semantic-router/user-guide/features/threshold-optimization)

로컬 Hugging Face·FastEmbed encoder와 원격 embedding API 등을 선택할 수 있음. 라이브러리를 로컬 실행하는 것만으로 데이터가 외부로 나가지 않는다고 볼 수 없으며 encoder와 index 구성을 함께 확인해야 함. [Encoder 종류](https://docs.aurelio.ai/docs/semantic-router/user-guide/components/encoders)

고객 문의를 결제·배송·로그인 흐름으로 보내는 문제에서는 Jev Choice와 비교할 수 있음. 그러나 유사도는 경로 선택이 맞을 확률이 아니며, 복합 업무 조건이 참인지 묻는 Noul의 출력과도 다름. 두 시스템의 숫자에 동일한 임계값을 적용하지 않음.

## 5. 확률·유사도·형식 보장을 섞지 않기

| 반환값·보장 | 의미 | 보장하지 않는 것 |
| --- | --- | --- |
| Outlines의 출력 제약 | 허용한 구조·값으로 생성 범위 제한 | 내용의 사실성·업무 정답 |
| SetFit의 클래스 확률 | 학습한 클래스별 확률 추정 | 대상 업무에서 검증된 보정 |
| Semantic Router의 유사도 | 질의와 경로 예문의 표현상 가까움 | 경로 선택의 정답 확률 |
| Jev의 확률·confidence | 판단 분포와 별도의 분포 요약 | 검증된 업무 정확도·실행 권한 |

확률을 출력하는 것과 확률이 잘 보정된 것은 다름. 보정 평가와 Brier score의 해석은 [평가 문서](03-evaluation.md)에 정리했음.

## 6. 비교 후보를 선택하는 기준

다음은 위 역할 차이에서 도출한 평가 후보 선정안임. 서로 다른 프로젝트가 발표한 속도·비용 배수로 순위를 매기지 않음.

| 현재 문제 | 비교에 포함할 후보 | 같은 조건으로 맞출 결과 |
| --- | --- | --- |
| 계산·권한·중복 처리 검사 | 코드 기반 처리 | 확정적 업무 규칙 준수 |
| 생성 결과의 JSON·선택지 형식 오류 | 생성 모델 + Outlines | 형식 준수와 의미 정확도를 별도 측정 |
| 고정 라벨의 반복 분류 | SetFit과 Jev | 클래스별 오류·보류 후 오류 |
| 알려진 기능으로 문의 배분 | Semantic Router와 Jev | 올바른 경로·미매칭·오분배 |

모든 도구를 한꺼번에 도입하는 구조를 제안하는 것은 아님. 먼저 업무 하나를 고르고, 같은 사람 라벨·보류 정책·최종 결과를 기준으로 필요한 후보만 비교함. 자체 실행 후보는 학습·embedding·인프라 비용을, API 후보는 사용료·재시도·외부 전송 조건을 포함해야 함.
