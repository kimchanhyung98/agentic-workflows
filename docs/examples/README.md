# Agent Examples

실제 프로덕션 환경에서 운영되는 AI 코딩 에이전트 시스템의 설계와 구현 사례를 분석한 문서입니다.

---

## 문서 구성

| 문서                                                       | 내용                                              |
|----------------------------------------------------------|-------------------------------------------------|
| [Stripe Minions 개요](./01-stripe-minions.md)               | Minions의 핵심 아키텍처, One-Shot 접근 방식, 컨텍스트 수집 전략    |
| [Stripe Minions 시스템 설계](./02-stripe-minions-part2.md) | 에이전트 실행 파이프라인, 코드 편집 전략, 테스트 및 검증, 확장 사례        |

---

## Stripe Minions 개요

Stripe의 Minions는 대규모 모노레포 환경에서 코딩 작업을 **원샷(One-Shot)으로 엔드투엔드(End-to-End) 완료**하는 AI 코딩 에이전트 시스템입니다.

```mermaid
flowchart LR
    Task([작업 입력]) --> Agent[Minions 에이전트]
    Agent --> Context[컨텍스트 수집]
    Context --> Plan[계획 수립]
    Plan --> Implement[코드 구현]
    Implement --> Test[테스트 및 검증]
    Test --> PR([Pull Request])
```

### 핵심 특징

- **One-Shot 실행**: 작업 수신 후 인간 개입 없이 PR까지 자율 완료
- **End-to-End 파이프라인**: 컨텍스트 수집 → 계획 → 구현 → 테스트 → PR 생성
- **대규모 코드베이스 대응**: 수백만 줄의 모노레포에서 정확한 컨텍스트 수집
- **안전성 확보**: 기존 테스트 인프라 활용 및 다층 검증

---

## 참고 자료

- [Stripe: Minions — Stripe's one-shot, end-to-end coding agents](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
- [Stripe: Minions — Stripe's one-shot, end-to-end coding agents (Part 2)](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
