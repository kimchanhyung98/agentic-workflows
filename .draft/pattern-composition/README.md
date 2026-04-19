# 패턴 조합 (Pattern Composition)

이 레포의 base 패턴 문서([설계 패턴](/design-pattern/README.md))는 개별 패턴의 정의와 적합 상황을 다룹니다.
이 문서는 그 다음 단계 — 패턴을 조합할 때 base 문서에 명시되지 않은 계약과, 조합에서 발생하는 실패 양상을 정리합니다.
단일 프로덕션 시스템의 코드 감사에서 도출한 참고 사례이며, 보편 법칙이 아닙니다.

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| [조합 다이어그램](/pattern-composition/00-diagram.md) | 기본 패턴 → 조합 패턴 매핑, 계약 인터페이스, 실패 유형 분포 |
| [패턴 조합 사례](/pattern-composition/01-composition.md) | 3가지 조합 사례와 각 base 패턴의 역할, 조합으로 필요해지는 것 |
| [조합 계약](/pattern-composition/02-contracts.md) | Agent Card, Result Envelope, State Schema — base 패턴 문서에 없는 인터페이스 |
| [실패 분류](/pattern-composition/03-failure-taxonomy.md) | 12개 실패 유형, 26건 실증 데이터, 방법론과 한계 |

---

## 이 문서가 다루지 않는 것

- 개별 패턴의 정의와 작동 방식 → [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md)
- 특정 도구나 프레임워크 사용법
- 보편적 소프트웨어 설계 이론

---

## 참고 자료

- [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md) — base 패턴 카탈로그
- [Effective Agents 패턴](/effective-agents/README.md) — Anthropic의 실용 패턴
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Google Cloud: Choose a design pattern for an agentic AI system](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
