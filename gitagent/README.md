# GitAgent 분석

`open-gitagent/gitagent`의 설계 및 실행 플로우를 공개 문서와 소스 기준으로 정리한 문서입니다.

GitAgent는 "리포지토리 자체를 에이전트 정의"로 취급하는 **git-native, framework-agnostic 에이전트 표준 + CLI**를 제공합니다.

---

## 문서 구성

| 문서 | 내용 |
|---|---|
| [아키텍처 다이어그램](/gitagent/00-diagram.md) | 7-Layer 파일 구조, CLI 명령 체계, validate 파이프라인, export/run 흐름, SOD 검증, hook 매핑, 전체 라이프사이클 |
| [설계 및 실행 플로우 분석](/gitagent/01-analysis.md) | 설계 원칙, 7-Layer 파일 모델, CLI 소스 구조, 명령별 실행 플로우, Skill/Tool/Workflow/Hook/Memory/Compliance 시스템, 어댑터 체계, 아키텍처 패턴 |

---

## 아키텍처 개요

```text
Git 리포지토리 (agent 정의)
  ├─ Layer 1: agent.yaml + SOUL.md (필수)
  ├─ Layer 2: RULES.md / DUTIES.md / AGENTS.md (정책/행동)
  ├─ Layer 3: skills/ tools/ workflows/ agents/ (능력/합성)
  ├─ Layer 4: knowledge/ memory/ (지식/상태)
  ├─ Layer 5: hooks/ config/ examples/ (라이프사이클/운영)
  ├─ Layer 6: compliance/ (규제/거버넌스)
  └─ Layer 7: .gitagent/ (런타임 상태, gitignored)
        ↓
gitagent CLI (Node.js + TypeScript)
  ├─ init: 템플릿 스캐폴딩 (minimal/standard/full)
  ├─ validate: 스키마 + 참조 + Skills + SOD/규제 검증
  ├─ export: 다양한 포맷 변환
  ├─ import: 외부 포맷 가져오기
  ├─ run: 어댑터 기반 실행
  ├─ install: git 기반 의존성 설치
  ├─ audit: 컴플라이언스 점검 리포트
  └─ skills: 마켓플레이스 검색/설치/조회
        ↓
타깃 런타임 (어댑터별 실행)
  ├─ Claude Code (High fidelity)
  ├─ OpenAI / CrewAI / Gemini (Medium)
  └─ GitHub Actions / Cursor / Copilot / ... (Low, lossy)
```

### 핵심 설계 포인트

- **표준 중심 구조**: 에이전트 정체성, 규칙, 도구를 파일 시스템으로 선언해 이식성 확보
- **Git 우선 운영**: 버전관리, diff, 브랜치, PR, 태그 릴리스를 에이전트 운영 체계로 직접 활용
- **강한 검증 계층**: `validate`가 스키마, 파일 참조, Skills 형식, 규제/SOD까지 6단계 점검
- **어댑터 기반 확장**: 하나의 정의를 여러 실행 환경 포맷으로 export/import/run
- **컴플라이언스 내장**: FINRA/Federal Reserve/SEC/CFPB 규제 정책을 머신 체크 가능한 구성으로 구조화
- **Progressive Disclosure**: 스킬을 3단계(메타데이터/전체/리소스)로 나눠 토큰 효율 최적화

### 기술 스택

| 구분 | 기술 |
|---|---|
| 언어/런타임 | TypeScript, Node.js (>=18) |
| CLI 프레임워크 | commander v12 |
| 스키마 검증 | ajv v8, ajv-formats |
| 데이터 포맷 | YAML (`js-yaml`), Markdown |
| 터미널 출력 | chalk v5 |
| 사용자 입력 | inquirer v9 |
| 패키징 | npm (`@shreyaskapale/gitagent` v0.1.7) |

---

## 참고 자료

- [GitAgent 공식 사이트](https://www.gitagent.sh/)
- [GitAgent 저장소](https://github.com/open-gitagent/gitagent)
- [Specification v0.1.0](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md)
- [CLI 진입점](https://github.com/open-gitagent/gitagent/blob/main/src/index.ts)
- [validate 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/validate.ts)
- [export 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/export.ts)
- [import 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/import.ts)
- [run 명령](https://github.com/open-gitagent/gitagent/blob/main/src/commands/run.ts)
- [Claude Code 어댑터](https://github.com/open-gitagent/gitagent/blob/main/src/adapters/claude-code.ts)
- [Claude Code 러너](https://github.com/open-gitagent/gitagent/blob/main/src/runners/claude.ts)
- [Git auto-detect runner](https://github.com/open-gitagent/gitagent/blob/main/src/runners/git.ts)
