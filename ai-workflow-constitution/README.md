# AI 워크플로우 설계 원칙

AI 에이전트 워크플로우의 설계와 구현 판단 기준을 체계화한 헌법(Constitution) 접근법입니다.

---

## 문서 구성

| 문서 | 내용 |
|------|------|
| [아키텍처 다이어그램](/ai-workflow-constitution/00-diagram.md) | 시스템 구조, 역할 분리, 원칙 계층 다이어그램 |
| [설계 원칙](/ai-workflow-constitution/01-principles.md) | C1-C11 설계 원칙 정의, 근거, 위반 신호 |
| [시스템 아키텍처](/ai-workflow-constitution/02-architecture.md) | Config 병합, Provider 추상화, Skill 탐색, Event 시스템 |
| [용어 사전](/ai-workflow-constitution/03-glossary.md) | 용어 사전, 분류 기준 (불변식/파생규칙/구현세부/운영값) |

AI 워크플로우 시스템은 3개 파이프라인(분석, 워크플로우, 멀티에이전트)과 공유 인프라로 구성됩니다. 11개 설계 원칙이 모든 설계와 구현 판단의 기준이 됩니다. 특정 AI 도구나 프레임워크에 종속되지 않는 일반 패턴을 지향합니다.

---

## 참고 자료

- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Google Cloud: Choose a design pattern for an agentic AI system](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
- [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md)
- [Effective Agents 패턴](/effective-agents/README.md)
