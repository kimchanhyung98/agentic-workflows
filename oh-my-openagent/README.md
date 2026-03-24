# Oh My OpenAgent 분석

`oh-my-openagent`(패키지명 `oh-my-opencode`)의 설계와 실행 플로우를 정리한 문서입니다.

---

## 문서 구성

| 문서                                                   | 내용                                 |
|------------------------------------------------------|------------------------------------|
| [아키텍처 다이어그램](/oh-my-openagent/00-diagram.md)         | 플러그인 초기화, 에이전트 오케스트레이션, 런타임 이벤트 흐름 |
| [설계 및 실행 플로우 상세 분석](/oh-my-openagent/01-analysis.md) | 핵심 모듈 구조, 요청 처리 단계, 강점/트레이드오프      |

---

## 요약

Oh My OpenAgent는 OpenCode 플러그인 형태로 동작하며, 단일 모델 중심 실행 대신 **카테고리 기반 멀티 모델 오케스트레이션**을 제공합니다.
핵심 아이디어는 다음과 같습니다.

- **초기화 분리**: `config → managers → tools → hooks → plugin-interface`
- **실행 분리**: 계획(Prometheus)과 실행(Atlas/Task Worker)의 역할 분리
- **런타임 복원력**: 이벤트 기반 훅 체인과 모델 폴백/연속 실행 제어

---

## 참고 자료

- [code-yeongyu/oh-my-openagent (GitHub)](https://github.com/code-yeongyu/oh-my-openagent)
- [Overview](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/overview.md)
- [Orchestration Guide](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/orchestration.md)
