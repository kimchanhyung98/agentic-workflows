# 다중 에이전트 오케스트레이션 (Multi-Agent Orchestration)

작업의 위험도와 복잡도에 따라 5가지 실행 모드를 선택하고, 결정론적 Judge Rules로 품질을 보장하는 멀티에이전트 오케스트레이션 패턴입니다.

핵심 설계 원칙은 세 가지입니다.

1. **비용 인식**: 저비용 모드를 기본으로 사용하고, 필요할 때만 고비용 모드로 승격합니다.
2. **결정론적 판정**: Judge는 확률적 판단이 아닌, 순서가 있는 규칙 체인으로 작동합니다.
3. **Fallback 보장**: 고급 모드 실패 시 하위 모드로 강등하여 작업 완료를 보장합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/multi-agent-orchestration/00-diagram.md) | 5-Mode 의사결정, 병렬/순차 흐름, 승격/강등 상태 다이어그램 |
| [개념 개요](/multi-agent-orchestration/01-overview.md) | 5가지 실행 모드, Policy 기반 승격/강등, Provider 추상화, 역할 기반 프로토콜 |
| [Judge Rules](/multi-agent-orchestration/02-judge-rules.md) | 결정론적 5단계 판정 규칙, Severity 계층, 중복 제거, Tie-Breaking |
| [Provider Routing](/multi-agent-orchestration/03-provider-routing.md) | Fallback 체인, Timeout Budget, Synthesis 패턴, Finding 피드백 루프 |

---

## 핵심 불변식

| ID | 불변식 |
|----|--------|
| M1 | 작업의 위험도/복잡도에 따라 5가지 실행 모드 중 하나를 선택합니다 |
| M2 | cross mode는 병렬 독립 평가 후 Judge로 판정합니다 |
| M3 | critical mode는 이전 결과를 다음 입력에 누적하는 순차 체인입니다 |
| M4 | Judge는 결정론적 규칙 체인으로 작동합니다 (확률적 판단 아님) |
| M5 | 오케스트레이터는 Provider Protocol 뒤에 provider를 추상화합니다 |
| M6 | 3가지 synthesis 패턴으로 워크플로우와 통합합니다 |

---

## 모드 비교

| 모드 | 에이전트 수 | 실행 방식 | 적합한 상황 |
|------|-----------|----------|------------|
| solo | 1 | 단독 실행 | 저위험 일반 작업, 기본 모드 |
| quick | 1 | 읽기 전용 | 빠른 분석, 비용 최소화 |
| precise | 2 | 순차 검증 | 중요 작업의 이중 확인 |
| cross | 2 + Judge | 병렬 교차 검증 | 보안 검증, 독립적 다중 관점 |
| critical | 3 + Judge | 순차 심층 체인 | 프로덕션 배포, 최고 신뢰도 |

---

## 참고 자료

- [에이전틱 AI 시스템 설계 패턴](/design-pattern/) -- 단일/멀티 에이전트 패턴 카탈로그
- [Google Cloud: Choose a design pattern for an agentic AI system](https://docs.google.com/architecture/choose-design-pattern-agentic-ai-system)
- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents)
