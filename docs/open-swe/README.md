# Open SWE 분석

`langchain-ai/open-swe` — LangGraph 기반의 자율 소프트웨어 엔지니어링 에이전트 프레임워크를 분석한 문서입니다.

Slack/Linear/GitHub에서 `@openswe`로 호출하면, 격리된 샌드박스에서 코드를 분석·수정하고 자동으로 Draft PR을 생성합니다. Deep Agents의 범용 코딩 루프를 재사용하면서, 조직별 외부 시스템 연동과 결정적 안전장치를 추가한 구조입니다.

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](./00-diagram.md) | 프로젝트 구조, 실행 흐름, 데이터 흐름, 트리거별 분기, 샌드박스 생명주기, 미들웨어 파이프라인, 인증 흐름 |
| [아키텍처/워크플로우 분석](./01-analysis.md) | 5계층 아키텍처, source별 워크플로우, Deep Agents 결합 방식, 보안 설계, 환경변수 |

## 아키텍처 개요

```
외부 트리거 (Slack/Linear/GitHub)
    ↓ webhook
Ingress 계층 (webapp.py) — 서명 검증, thread ID 생성, run 생성/큐잉
    ↓ LangGraph SDK
Thread 조율 계층 (LangGraph) — thread 상태, 메시지 큐, 메타데이터 보존
    ↓ Runtime 호출
Agent Runtime 계층 (server.py) — sandbox·인증·프롬프트 준비, Deep Agent 조립
    ↓ 도구 호출
Tool/Integration 계층 — 커스텀 도구 6종 + Deep Agents 내장 도구 + 미들웨어 4종
    ↓ 외부 연동
External Systems — GitHub API, Slack API, Linear API, LangSmith, sandbox provider
```

### 핵심 설계 포인트

- **thread 기반 상태 재사용**: sandbox, 인증 토큰, 저장소 선택이 thread에 누적되어 후속 요청을 같은 작업 문맥에서 처리
- **source별 intake, 공통 실행**: 트리거별 intake 방식은 다르지만 최종 실행 경로는 `get_agent()` → `create_deep_agent()`로 수렴
- **결정적 안전장치**: 미들웨어가 LLM의 비결정적 행동에 결정적 제어를 추가 (PR 안전망, 오류 변환, 빈 응답 방지)
- **Git branch 기반 연속성**: `open-swe/{thread_id}` 브랜치명으로 PR follow-up 시 thread를 복구

### 기술 스택

| 구분 | 기술 |
|------|------|
| 에이전트 프레임워크 | LangGraph, Deep Agents (`create_deep_agent`) |
| LLM | Anthropic Claude Opus 4.6 (기본) |
| 웹 서버 | FastAPI |
| 샌드박스 | LangSmith (기본), Daytona, Modal, Runloop, Local |
| 인증 | GitHub App (JWT), GitHub OAuth (LangSmith 경유), Fernet 암호화 |
| 외부 연동 | GitHub REST/GraphQL API, Linear GraphQL API, Slack API |

## 참고 자료

- [Open SWE 저장소](https://github.com/langchain-ai/open-swe)
- [Open SWE Announcement](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/)
- [Open SWE Customization Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/CUSTOMIZATION.md)
- [Open SWE Installation Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/INSTALLATION.md)
- [Deep Agents 저장소](https://github.com/langchain-ai/deepagents)
- [Deep Agents 문서](https://docs.langchain.com/oss/python/deepagents/overview)
