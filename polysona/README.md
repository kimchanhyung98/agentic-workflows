# Polysona 분석

`LilMGenius/polysona`의 에이전트 하네스, 코드 구조, 실행 플로우를 공개 저장소 기준으로 정리한 문서입니다.

Polysona는 단일 에이전트 페르소나 템플릿이 아니라, **다중 페르소나 데이터(PLOON) + 5개 역할 에이전트 + CLI 호스트별 하네스(Codex/Claude)**를 결합해 인터뷰부터 콘텐츠 발행까지 반복 루프를 구성합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/polysona/00-diagram.md) | 시스템 계층, 인터뷰→콘텐츠 파이프라인, 스킬/에이전트 라우팅, 대시보드 데이터 흐름 |
| [설계 및 실행 플로우 분석](/polysona/01-analysis.md) | 하네스 구조, 5개 에이전트 책임 분리, PLOON 데이터 모델, 코드/운영 트레이드오프, 활용 사례 |
| [코드 심층 분석](/polysona/02-code-analysis.md) | 10-Framework 심리학, 5-에고 레이어, GAP 분석, 대시보드 코드, 플러그인/훅, 아키텍처 평가 |
| [종합 리서치 리포트](/polysona/03-research.md) | 생태계 비교, 경쟁 도구, 심리학 배경, Ralphthon 발표, 개발 궤적 |

---

## 아키텍처 개요

```text
CLI Host (Codex / Claude Code)
    ↓
Skill Layer (skills/*/SKILL.md, command protocol)
    ↓
Agent Layer (profiler / trendsetter / content-writer / virtual-follower / admin)
    ↓
Data Layer (personas/*/*.md, content/{trends,drafts,qa,published})
    ↓
Dashboard (Hono API + React/Vite UI)
```

### 핵심 설계 포인트

- **이중 하네스 지원**: Codex(`AGENTS.md`, `agents/openai.yaml`, `.agents/skills`)와 Claude(`.claude-plugin`, `hooks/hooks.json`)를 동시에 지원합니다.
- **역할 고정형 멀티에이전트**: 5개 에이전트가 파이프라인 단계별 책임을 명확히 분리합니다.
- **파일 시스템 기반 상태관리**: Git 친화적 Markdown(PLOON) 저장소를 단일 진실 공급원(SSOT)으로 사용합니다.
- **저장 강제 프로토콜**: trend/content/qa/publish 스킬이 결과 파일 Write→Read 검증을 강제해 허위 성공 응답을 줄입니다.
- **로컬 퍼스트 대시보드**: Hono API가 persona/콘텐츠 상태를 집계하고 React 대시보드가 시각화합니다.

---

## 참고 자료

- [Polysona 저장소](https://github.com/LilMGenius/polysona)
- [Polysona README](https://github.com/LilMGenius/polysona/blob/main/README.md)
- [Polysona AGENTS](https://github.com/LilMGenius/polysona/blob/main/AGENTS.md)
- [Codex agent 정의](https://github.com/LilMGenius/polysona/blob/main/agents/openai.yaml)
- [스킬 디렉토리](https://github.com/LilMGenius/polysona/tree/main/skills)
- [에이전트 프롬프트 디렉토리](https://github.com/LilMGenius/polysona/tree/main/agents)
- [대시보드 서버 진입점](https://github.com/LilMGenius/polysona/blob/main/server/index.ts)
- [대시보드 API](https://github.com/LilMGenius/polysona/blob/main/server/routes/api.ts)
- [PLOON 파서](https://github.com/LilMGenius/polysona/blob/main/server/lib/ploon.ts)
- [Claude hooks 설정](https://github.com/LilMGenius/polysona/blob/main/hooks/hooks.json)
- [스킬 동기화 스크립트](https://github.com/LilMGenius/polysona/blob/main/scripts/sync-codex-skills.mjs)
- [CHANGELOG](https://github.com/LilMGenius/polysona/blob/main/CHANGELOG.md)
