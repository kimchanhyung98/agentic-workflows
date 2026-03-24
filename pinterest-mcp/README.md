# Pinterest MCP 분석

Pinterest Engineering의 블로그 글과 공개 자료를 바탕으로, Pinterest 내부 MCP 생태계의 설계, 운영 구조, 보안 모델을 정리한 문서입니다.

Pinterest는 "MCP가 흥미해 보인다"는 시작점에서 출발해, 다수의 도메인별 MCP 서버, 중앙 레지스트리, IDE·사내 챗·AI 에이전트에 걸친 프로덕션 통합을 운영하는 단계까지 도달했습니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/pinterest-mcp/00-diagram.md) | MCP 생태계 구조, 요청 처리 흐름, 보안 계층, 배포 파이프라인 |
| [설계 및 운영 분석](/pinterest-mcp/01-analysis.md) | 도입 배경, 서버별 상세, 보안/거버넌스 모델, 배포 전략, 운영 지표, 시사점 |

---

## 운영 지표

| 항목 | 수치 |
|---|---|
| 월간 MCP 호출 수 | 66,000+ |
| 월간 활성 사용자 | 844명 |
| 월간 절감 시간 (추정) | ~7,000시간 |

## 핵심 MCP 서버

| 서버 | 역할 |
|---|---|
| Presto MCP | 최고 트래픽 서버. 에이전트가 Presto 기반 데이터를 직접 조회 |
| Spark MCP | Spark 작업 실패 진단, 로그 요약, 구조화된 근본 원인 분석 |
| Knowledge MCP | 사내 문서/디버깅 질문 대응 범용 지식 엔드포인트 |
| Airflow MCP | 워크플로우 오케스트레이션 도구 연동 |

## 핵심 설계 포인트

- **도메인별 소형 서버 전략**: 서버마다 적은 수의 관련 도구만 소유해, 서버별 접근 제어 적용과 모델 컨텍스트 오염 방지
- **2층 인증 모델**: end-user JWT + SPIFFE mesh identity로 "누가 무엇을 했는지"를 항상 추적
- **중앙 MCP Registry**: 승인된 서버의 source of truth, Web UI + API로 인간과 AI 클라이언트 모두 서버 발견
- **통합 배포 파이프라인**: 팀이 도구 로직만 정의하면 플랫폼이 인프라·배포·스케일링을 처리
- **human-in-the-loop 원칙**: 민감하거나 비용이 큰 작업은 자동 실행 전 사람 승인 필수

---

## 참고 자료

- [Pinterest Engineering: Building an MCP Ecosystem at Pinterest](https://medium.com/pinterest-engineering/building-an-mcp-ecosystem-at-pinterest-d881eb4c16f1)
- [News.Hada 요약: Building an MCP Ecosystem at Pinterest](https://news.hada.io/topic?id=27775)
- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/introduction)
- [Model Context Protocol GitHub](https://github.com/modelcontextprotocol)
- [Anthropic: Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
