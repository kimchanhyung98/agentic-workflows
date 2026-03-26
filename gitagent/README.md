# GitAgent 분석

`open-gitagent/gitagent`의 설계 및 실행 플로우를 공개 문서와 소스 기준으로 정리한 문서입니다.

GitAgent는 "리포지토리 자체를 에이전트 정의"로 취급하는 **git-native, framework-agnostic 에이전트 표준 + CLI**를 제공합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/gitagent/00-diagram.md) | 표준 파일 구조, CLI 실행 흐름, 검증/내보내기 파이프라인, 규제 준수 흐름 |
| [설계 및 실행 플로우 분석](/gitagent/01-analysis.md) | 핵심 설계 원칙, 표준 스키마, 명령어 기반 실행 플로우, 컴플라이언스/운영 트레이드오프 |

---

## 아키텍처 개요

```text
Git 리포지토리 (agent 정의)
  ├─ agent.yaml + SOUL.md (필수)
  ├─ RULES.md / DUTIES.md / AGENTS.md (정책/행동)
  ├─ skills/ tools/ workflows/ agents/ (능력/합성)
  └─ memory/ compliance/ hooks/ config/ (운영/거버넌스)
        ↓
gitagent CLI (Node.js + TypeScript)
  ├─ init: 템플릿 스캐폴딩
  ├─ validate: 스키마 + 참조 + SOD/규제 검증
  ├─ export/import: 프레임워크 어댑터 변환
  ├─ run/install: 실행/의존성 설치
  └─ audit: 컴플라이언스 점검 리포트
        ↓
타깃 런타임
  ├─ Claude Code
  ├─ OpenAI / CrewAI / LangChain 등
  └─ GitHub Actions / Gemini CLI / OpenCode 등
```

### 핵심 설계 포인트

- **표준 중심 구조**: 에이전트 정체성·규칙·도구를 파일 시스템으로 선언해 이식성 확보
- **Git 우선 운영**: 버전관리, diff, 브랜치, PR을 에이전트 운영 체계로 직접 활용
- **강한 검증 계층**: `validate`가 스키마, 파일 참조, Skills 형식, 규제/분리의무(SOD)까지 점검
- **어댑터 기반 확장**: 하나의 정의를 다양한 실행 환경 포맷으로 export/import
- **컴플라이언스 내장**: FINRA/Federal Reserve/SEC/CFPB 맥락의 정책 필드와 감사 관점 포함

### 기술 스택

| 구분 | 기술 |
|---|---|
| 언어/런타임 | TypeScript, Node.js (>=18) |
| CLI 프레임워크 | commander |
| 스키마 검증 | ajv, ajv-formats |
| 데이터 포맷 | YAML (`js-yaml`), Markdown |
| 패키징 | npm (`@shreyaskapale/gitagent`) |

---

## 참고 자료

- [GitAgent 공식 사이트](https://www.gitagent.sh/)
- [GitAgent 저장소](https://github.com/open-gitagent/gitagent)
- [README](https://github.com/open-gitagent/gitagent/blob/main/README.md)
- [Specification v0.1.0](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md)
- [CLI 진입점](https://github.com/open-gitagent/gitagent/blob/main/src/index.ts)
- [init 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/init.ts)
- [validate 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/validate.ts)
