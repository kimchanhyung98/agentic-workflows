# Open SWE 분석

`langchain-ai/open-swe`의 아키텍처와 실행 워크플로우를 분석한 문서입니다.
핵심 기반인 **Deep Agents** 구성까지 포함해 정리했습니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](./00-diagram.md) | Open SWE 전체 구성요소, 실행 흐름, Deep Agents 결합 지점 |
| [아키텍처/워크플로우 상세 분석](./01-analysis.md) | 레이어별 설계 의도, 도구/미들웨어, 트리거 흐름, 확장 포인트 |

---

## 핵심 요약

- Open SWE는 **LangGraph + Deep Agents** 위에 구성된 내부 코딩 에이전트 프레임워크입니다.
- 호출 표면은 Slack/Linear/GitHub이며, 각 작업은 **격리된 샌드박스**에서 실행됩니다.
- `create_deep_agent(...)`를 중심으로 모델/도구/미들웨어를 조합해 조직별 커스터마이징이 가능합니다.
- Deep Agents의 기본 도구(`read_file`, `write_file`, `edit_file`, `execute`, `task`, `write_todos` 등)를 활용해 계획-실행-위임 루프를 구현합니다.

---

## 참고 자료

- [Open SWE 저장소](https://github.com/langchain-ai/open-swe)
- [Open SWE README](https://raw.githubusercontent.com/langchain-ai/open-swe/main/README.md)
- [Open SWE Customization Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/CUSTOMIZATION.md)
- [Open SWE Installation Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/INSTALLATION.md)
- [Deep Agents 저장소](https://github.com/langchain-ai/deepagents)
- [Deep Agents 문서](https://docs.langchain.com/oss/python/deepagents/overview)
- [뉴스 하다: open-swe 소개](https://news.hada.io/topic?id=27604)
