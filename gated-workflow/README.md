# 게이트 기반 워크플로우 (Gated Workflow)

게이트 기반 N-Phase 파이프라인과 Closed-Loop 의사결정을 결합한 워크플로우 패턴입니다.
각 Phase 사이에 Gate를 배치하여 품질 조건을 충족해야만 다음 단계로 진행합니다.
실패 시 severity와 reason 조합으로 continue, replan, abort, escalate를 자동 판정합니다.

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| [아키텍처 다이어그램](/gated-workflow/00-diagram.md) | 파이프라인 흐름, 상태 머신, Closed-Loop 의사결정 트리, Gate 평가 흐름 다이어그램 |
| [워크플로우 개요](/gated-workflow/01-overview.md) | 7-Phase 구조, Agent Card 계약, Result Envelope, 상태 외부화, 실행 카운터 |
| [Gate와 Closed-Loop](/gated-workflow/02-gates-closed-loop.md) | Gate 평가 절차, Retry Budget, on_fail 라우팅, Closed-Loop 의사결정, 에러 분류 |
| [위험 기반 라우팅](/gated-workflow/03-risk-routing.md) | 변경 등급 감지, 위험 비례 투자, HIL 정책, 전제조건 검증, Replan 방향 제약 |

---

## 핵심 패턴 특성

| 패턴 | 목적 | 핵심 메커니즘 |
|------|------|-------------|
| N-Phase Gate | 단계별 품질 보증 | Phase 간 Gate 배치, 통과 조건 충족 시에만 진행 |
| Closed-Loop Decision | 자동 복구 및 재계획 | severity * reason 규칙으로 자동 판정 |
| Agent Card Contract | Phase별 런타임 계약 | 입출력 명세, Gate 조건, Retry Budget, 라우팅 규칙 |
| Risk-Based Routing | 위험도 비례 검증 | change class에 따라 리뷰 깊이와 승인 경로 차등 |
| State Externalization | LLM 비의존 상태 관리 | 모든 상태를 파일 시스템에 JSON으로 외부화 |

---

## 참고 자료

- [검토-비평 패턴](/design-pattern/05-review-critique.md) — 생성기 + 비평가의 검증 루프
- [인간 참여형 패턴](/design-pattern/11-human-in-the-loop.md) — 워크플로에 인간 개입 체크포인트 통합
- [반복 개선 패턴](/design-pattern/06-iterative-refinement.md) — 다중 사이클에 걸친 점진적 결과물 개선
