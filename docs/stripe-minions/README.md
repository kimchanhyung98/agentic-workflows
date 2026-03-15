# Agent Examples

실제 프로덕션 환경에서 운영되는 AI 코딩 에이전트 시스템의 설계와 구현 사례를 분석한 문서입니다.

---

## 문서 구성

| 문서                                                    | 내용                                                                      |
|-------------------------------------------------------|-------------------------------------------------------------------------|
| [Stripe Minions 개요](./01-stripe-minions.md)           | 핵심 공식, Stripe 환경의 세 기둥, 6개 레이어 아키텍처, Entry Point, Context Hydration     |
| [Stripe Minions 시스템 설계](./02-stripe-minions-part2.md) | Devbox 격리 환경, Agent Core(Goose Fork), Feedback Loop, PR Output, 설계 인사이트 |

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

- **One-Shot 실행**: 작업 수신 후 인간 개입 없이 PR까지 자율 완료 (주당 1,000+ PR)
- **6개 레이어 아키텍처**: Entry Point → Context Hydration → Devbox → Agent Core → Feedback Loop → Output
- **기존 인프라 활용**: 에이전트 전용 도구 없이, 인간 엔지니어와 동일한 개발 환경 사용
- **구조적 안전장치**: 격리된 VM, 결정론적 게이트, 제한된 재시도로 안전성 확보

---

## 참고 자료

- [Stripe: Minions — Stripe's one-shot, end-to-end coding agents](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
- [Stripe: Minions — Stripe's one-shot, end-to-end coding agents (Part 2)](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
