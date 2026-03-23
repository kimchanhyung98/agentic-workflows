# 관련 자료 및 레퍼런스

## 프로젝트

| 프로젝트                                                                            | 설명                                   | 핵심 개념                    |
|---------------------------------------------------------------------------------|--------------------------------------|--------------------------|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch)               | AI 에이전트가 자율적으로 LLM 학습을 실험하고 개선하는 시스템 | program.md 기반 자율 실험 루프   |
| [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 목표를 하위 작업으로 분해하여 자율 실행하는 범용 에이전트     | 작업 분해, 자율 실행, 도구 사용      |
| [yoheinakajima/babyagi](https://github.com/yoheinakajima/babyagi)               | 작업 생성-우선순위-실행 루프의 자기 구축 에이전트 프레임워크   | 작업 큐, 우선순위 관리, 자기 구축     |
| [noahshinn/reflexion](https://github.com/noahshinn/reflexion)                   | 자기 반성을 통한 언어 에이전트 강화 학습              | Self-reflection, 언어적 피드백 |

## 논문

| 논문                                                                                                        | 저자                   | 핵심 기여                    |
|-----------------------------------------------------------------------------------------------------------|----------------------|--------------------------|
| [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)            | Yao et al. (2022)    | 추론과 행동의 인터리빙 패턴 제시       |
| [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)         | Shinn et al. (2023)  | 자기 반성 메모리를 통한 에이전트 성능 개선 |
| [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) | Wei et al. (2022)    | 사고 사슬 프롬프팅의 추론 능력 향상     |
| [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)         | Schick et al. (2023) | LLM의 자율적 도구 사용 학습        |

## 기술 문서 및 블로그

| 자료                                                                                           | 출처        | 주요 내용                    |
|----------------------------------------------------------------------------------------------|-----------|--------------------------|
| [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Anthropic | 에이전트 워크플로우 패턴 6가지 분류     |
| [Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)     | LangGraph | 워크플로우 패턴, 에이전트 루프, 도구 호출 |

## 핵심 용어

| 용어                      | 설명                                                                  |
|-------------------------|---------------------------------------------------------------------|
| **Agent Loop**          | 에이전트가 관찰-판단-행동-피드백을 반복하는 실행 루프                                      |
| **Auto Improve Loop**   | AI가 자율적으로 실험-측정-판단을 반복하여 시스템을 개선하는 루프                               |
| **program.md**          | autoresearch에서 사람이 작성하는 목표, 수정 범위, 평가 보호, 로그 포맷, 루프 규칙 등을 포함한 운영 문서 |
| **ReAct**               | Reasoning + Acting. 추론과 행동을 교차 실행하는 에이전트 패턴                         |
| **OODA Loop**           | Observe-Orient-Decide-Act. 군사 전략 기반 의사결정 루프                         |
| **Reflexion**           | 실패 경험을 자기 반성으로 변환하여 다음 시도에 반영하는 패턴                                  |
| **Evaluator-Optimizer** | 생성과 평가를 분리하여 반복 개선하는 패턴                                             |
| **Rollback**            | 실패한 변경을 이전 상태로 되돌리는 메커니즘                                            |
| **val_bpb**             | Validation Bits Per Byte. autoresearch의 평가 지표                       |
