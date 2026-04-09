# 용어 사전

문서군 간 동일 용어가 다른 의미로 쓰이는 것을 방지하기 위한 canonical term 정의입니다.

---

## Execution Unit (실행 단위)

| 용어 | 소속 | 정의 |
|------|------|------|
| **phase** | workflow | 워크플로우의 실행 단위. plan, review, approve, impl, verify, test, done |
| **stage** | analysis | 분석 파이프라인의 처리 단계. Stage 1 (파일별), Stage 2 (단위 합성), Stage 3 (교차 검증) |
| **mode** | multi-agent | 다중 에이전트 실행 모드. solo, quick, precise, cross, critical |

---

## Evaluator (평가자)

| 용어 | 소속 | 정의 |
|------|------|------|
| **gate** | workflow | Phase 완료 후 pass_conditions를 평가하는 결정론적 관문 |
| **judge** | 공통 | 결과를 종합하여 판정하는 추상 역할. 하위 유형으로 analysis judge, multi-agent judge가 존재 |
| **analysis judge** | analysis | Writer 출력을 병합하고 일관성을 검증하는 synthesis 역할. evidence를 변조하지 않음 |
| **multi-agent judge** | multi-agent | 에이전트 결과를 다단계 규칙으로 PASS/FAIL 판정하는 verdict engine |

---

## Severity (심각도)

| 용어 | 소속 | 체계 | 용도 |
|------|------|------|------|
| **escape severity** | workflow | advisory / degraded / warning / critical | Worker escape 시 자동 판정 규칙 입력 |
| **finding severity** | multi-agent | CRITICAL / HIGH / MAJOR / MEDIUM / LOW | Judge Rules 판정 기준 |

---

## Collaboration Pattern (협업 패턴)

| 용어 | 정의 |
|------|------|
| **서브에이전트** | 부모 세션 안에서 실행되는 자식 에이전트. 결과만 부모에게 반환. 기본 워커 패턴 |
| **에이전트 팀** | 독립 컨텍스트의 동료 에이전트. 직접 메시지로 토론/반박. 설계 리뷰, QA에 적합 |
| **A2A** | 외부 시스템의 에이전트와 표준 프로토콜로 연동. Agent Card 기반 발견 |
| **human arbiter** | 사람이 최종 승인/판단을 내리는 역할. judge와 다른 개념 |

---

## Risk (위험도)

| 용어 | 소속 | 정의 |
|------|------|------|
| **change class** | workflow | concept 텍스트의 위험도 분류. small / standard / high_risk. 한국어 병기: 변경 등급 |

### 변경 등급별 적용 기준

| 등급 | review depth | 승인 | 격리 |
|------|-------------|------|------|
| small | gate만 | auto 가능 | local |
| standard | gate + AI 리뷰 | auto 조건부 | worktree |
| high_risk | gate + AI 리뷰 다수 + 사람 | 사람 필수 | isolated worktree |

---

## Classification Criteria (분류 기준)

패턴 문서 정제 시 어떤 내용을 남기고, 어떤 내용을 다른 문서로 이동할지 판정하는 기준입니다.

### 분류 축

| 분류 | 정의 | 판정 질문 | 처리 규칙 |
|------|------|----------|----------|
| **불변식 (Invariant)** | 구현 방식이 바뀌어도 반드시 성립해야 하는 규칙 | 이 문장이 미래 구현에서도 반드시 참이어야 하는가? | 패턴 문서에 유지 |
| **파생규칙 (Derived Rule)** | 불변식에서 파생된 정책 또는 설계 규칙 | 이 규칙이 바뀌더라도 상위 불변식은 유지되는가? | 패턴 문서에 최소한만 유지 |
| **구현세부 (Implementation Detail)** | 특정 파일, 함수, 경로에 의존하는 설명 | 파일명, 함수명, JSON 키 경로가 등장하는가? | 패턴 문서에서 제거 |
| **운영값 (Operational Value)** | 수치, timeout, retry 횟수, threshold | 이 값이 바뀌어도 설계의 본질은 유지되는가? | 별도 reference 문서로 이동 |

### 판정 결과

| 결과 | 의미 |
|------|------|
| keep | 패턴 문서에 유지 |
| rewrite | 패턴 문서에 남기되 추상적 규범 문장으로 재작성 |
| move_to_status | 현재 구현 설명으로 이동 |
| move_to_reference | 운영값 또는 상세 표로 이동 |
| drop | 중복 또는 저가치 예시라 삭제 |

### 패턴 문서에 남기는 것

- 핵심 설계 원칙
- 시스템 불변식
- 최소한의 파생 규칙
- 용어 정의

### 패턴 문서에서 빼는 것

- 현재 코드 구조
- 미구현/known gap
- 수치 중심 운영 표
- 장황한 구현 예시

---

## 문서 역할 분리

| 문서 | 역할 |
|------|------|
| patterns | 목표 설계 |
| status | 현재 구현 사실 |
| gaps | pattern과 status의 차이 |
| tests | pattern 달성 여부를 판정하는 acceptance criteria |

---

## 참고 자료

- [01-principles.md](01-principles.md) — 설계 원칙 상세
- [02-architecture.md](02-architecture.md) — 아키텍처 구성요소
- [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md)
