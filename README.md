# Agentic Workflows

AI 에이전트 시스템의 설계 패턴, 워크플로우, 프로덕션 사례를 체계적으로 정리한 문서 모음입니다.

## 문서 구성

### 설계 패턴 및 워크플로우

| 디렉토리                                            | 설명                                                   | 주요 출처                       |
|-------------------------------------------------|------------------------------------------------------|-----------------------------|
| [agentic-workflow](/agentic-workflow/README.md) | Agentic AI 핵심 개념, 에이전트 구성 요소, 4대 핵심 패턴, 구현 패턴        | Samsung SDS, IBM, Andrew Ng |
| [design-pattern](/design-pattern/README.md)     | Google Cloud 기반 12가지 에이전틱 AI 설계 패턴 (단일/멀티/반복/특수)     | Google Cloud                |
| [effective-agents](/effective-agents/README.md) | Anthropic의 Effective Agents 6가지 패턴 (체이닝, 라우팅, 병렬화 등) | Anthropic                   |

### 프로덕션 사례 분석

| 디렉토리                                              | 설명                                               | 분석 대상                 |
|---------------------------------------------------|--------------------------------------------------|-----------------------|
| [stripe-minions](/stripe-minions/README.md)       | One-Shot E2E 코딩 에이전트, 6레이어 아키텍처, Devbox 격리       | Stripe Minions        |
| [coinbase-cloudbot](/coinbase-cloudbot/README.md) | Slack 네이티브 백그라운드 에이전트, MCP 통합, AI 에코시스템          | Coinbase Cloudbot     |
| [open-swe](/open-swe/README.md)                   | LangGraph 기반 자율 SWE 에이전트, 5계층 아키텍처, 샌드박스         | LangChain Open SWE    |
| [pinterest-mcp](/pinterest-mcp/README.md)         | 도메인별 MCP 서버 생태계, 2층 보안 모델, 중앙 레지스트리, 통합 배포 파이프라인 | Pinterest Engineering |

### 도구 및 프레임워크 분석

| 디렉토리                                              | 설명                                                             | 분석 대상             |
|---------------------------------------------------|----------------------------------------------------------------|-------------------|
| [langchain](/langchain/README.md)                 | Skill 기반 코딩 에이전트 성능 향상, 평가 방법론                                 | LangChain Skills  |
| [oh-my-openagent](/oh-my-openagent/README.md)     | 카테고리 기반 멀티 모델 오케스트레이션 플러그인                                     | Oh My OpenAgent   |
| [opencode-worktree](/opencode-worktree/README.md) | AI 개발 세션용 격리된 git worktree 자동 관리                               | OpenCode Worktree |
| [aperant](/aperant/README.md)                     | Electron 기반 자율 멀티에이전트 코딩 앱, 다단계 오케스트레이션, 멀티 프로바이더, worktree 격리 | Aperant           |

### 자율 개선 루프

| 디렉토리                                    | 설명                                | 주요 출처                 |
|-----------------------------------------|-----------------------------------|-----------------------|
| [auto-improve](/auto-improve/README.md) | AI가 자율적으로 코드를 수정·실험·측정하는 반복 루프 설계 | karpathy/autoresearch |

## 라이선스

[MIT](/LICENSE)
