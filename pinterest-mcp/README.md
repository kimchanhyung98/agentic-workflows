# Pinterest MCP 분석

Pinterest Engineering 글(참고 링크)과 공개 MCP 문서를 바탕으로, Pinterest의 MCP 생태계 구축 방향과 운영 워크플로우를 정리한 문서입니다.

## 문서 구성

| 문서                              | 내용                                              |
|---------------------------------|-------------------------------------------------|
| [아키텍처 다이어그램](/pinterest-mcp/00-diagram.md) | MCP 생태계 구조, 요청 처리 흐름, 운영 피드백 루프 요약          |
| [설계/운영 분석](/pinterest-mcp/01-analysis.md)      | MCP 도입 배경, 작동 방식, 보안/거버넌스, 단계별 확장 전략 정리 |

## 핵심 요약

- **목표**: 에이전트가 사내 도구를 일관된 인터페이스(MCP)로 호출하도록 표준화
- **운영 포인트**: 서버 등록/발견, 권한 정책, 호출 관측성, 실패 복구를 플랫폼 관점에서 통합
- **워크플로우 핵심**: 요청 수집 → 도구 선택/실행 → 결과 반환 → 로그/평가 반영 → 서버 품질 개선

## 참고 자료

- [Pinterest Engineering: Building an MCP ecosystem at Pinterest](https://medium.com/pinterest-engineering/building-an-mcp-ecosystem-at-pinterest-d881eb4c16f1)
- [News.Hada 요약: Building an MCP ecosystem at Pinterest](https://news.hada.io/topic?id=27775)
- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/introduction)
- [Model Context Protocol 스펙/리소스](https://github.com/modelcontextprotocol)
- [Anthropic: Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
