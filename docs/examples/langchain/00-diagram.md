# LangChain Skills Diagram

LangChain Skills 시스템의 구조, 개발 사이클, 평가 파이프라인을 종합한 다이어그램입니다.

---

## 전체 구조

LangChain Skills는 코딩 에이전트의 특정 도메인 성능을 향상시키는 큐레이션된 가이드라인입니다. **Progressive Disclosure** 패턴으로 YAML frontmatter만 먼저 로드하고,
관련성이 확인되면 전체 SKILL.md를 로드합니다. Skills 적용 시 작업 통과율이 크게 향상됩니다(LangChain 블로그 기준 25% → 95%, 평가 블로그 기준 9% → 82%).

```mermaid
graph TB
    subgraph Skills["Skills 카테고리 (11개)"]
        direction TB
        subgraph GS["Getting Started"]
            S1["framework-selection"]
            S2["langchain-dependencies"]
        end
        subgraph LC["LangChain"]
            S3["langchain-fundamentals"]
            S4["langchain-middleware"]
            S5["langchain-rag"]
        end
        subgraph LG["LangGraph"]
            S6["langgraph-fundamentals"]
            S7["langgraph-persistence"]
            S8["langgraph-human-in-the-loop"]
        end
        subgraph DA["Deep Agents"]
            S9["deep-agents-core"]
            S10["deep-agents-memory"]
            S11["deep-agents-orchestration"]
        end
    end

    subgraph Agents["지원 에이전트"]
        A1["Claude Code"]
        A2["Deep Agents CLI"]
        A3["Cursor"]
        A4["Windsurf"]
        A5["Goose"]
    end

    subgraph Tools["LangSmith 도구"]
        LS_CLI["LangSmith CLI"]
        LS_TRACE["langsmith-trace<br/>추적 조회 · 내보내기"]
        LS_DATA["langsmith-dataset<br/>평가 데이터셋 생성"]
        LS_EVAL["langsmith-evaluator<br/>커스텀 평가기"]
    end

    Skills -->|" Progressive Disclosure "| Agents
    Agents -->|" 실행 추적 "| LS_CLI
    LS_CLI --> LS_TRACE & LS_DATA & LS_EVAL
    style Skills fill: #e8f5e9, stroke: #2E7D32
    style Agents fill: #e3f2fd, stroke: #1565C0
    style Tools fill: #fff3e0, stroke: #E65100
    style GS fill: #f1f8e9, stroke: #558B2F
    style LC fill: #f1f8e9, stroke: #558B2F
    style LG fill: #f1f8e9, stroke: #558B2F
    style DA fill: #f1f8e9, stroke: #558B2F
```

## 개발·평가 통합 사이클

Skills 기반 개발은 **정의 → 설치 → 테스트 → 평가 → 개선**의 반복 사이클과, LangSmith를 활용한 **추적 → 디버깅 → 데이터셋 → 평가**의 품질 사이클이 연동됩니다.

```mermaid
flowchart LR
    subgraph DevCycle["Skill 개발 사이클"]
        DEF["📝 정의<br/>SKILL.md 작성"] --> INST["📦 설치<br/>npx / script"]
        INST --> TEST["🧪 테스트<br/>베이스라인 측정"]
        TEST --> EVAL["📊 평가<br/>성능 비교"]
        EVAL -->|" 개선됨 "| DEPLOY["🚀 배포"]
        EVAL -->|" 미흡 "| REFINE["🔄 개선"] --> DEF
    end

    subgraph QualCycle["LangSmith 품질 사이클"]
        CODE["💻 에이전트 코드"] --> TRACE["🔍 추적 확인"]
        TRACE --> DEBUG["🐛 디버깅"]
        DEBUG --> DATASET["📋 데이터셋 생성"]
        DATASET --> RUN_EVAL["⚡ 평가 실행"]
        RUN_EVAL --> IMPROVE["✨ 코드 개선"] --> CODE
    end

    TEST -.->|" 추적 데이터 "| TRACE
    RUN_EVAL -.->|" 결과 반영 "| EVAL
    style DevCycle fill: #e8f5e9, stroke: #2E7D32
    style QualCycle fill: #fff3e0, stroke: #E65100
```
