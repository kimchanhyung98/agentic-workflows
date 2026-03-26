# GitAgent 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `open-gitagent/gitagent`
- 성격: git-native 에이전트 표준 + CLI 구현체
- 핵심 목표: **에이전트 정체성/규칙/도구를 코드 리포지토리처럼 선언·버전관리·이식**

GitAgent는 런타임 프레임워크 자체를 통일하려는 접근이 아니라, **에이전트 정의 레이어를 표준화**해 Claude Code/OpenAI/CrewAI 등으로의 이동 비용을 줄이는 방향을 취합니다.

---

## 2. 핵심 설계 원칙

### 2.1 Git-native 표준화

`agent.yaml` + `SOUL.md`를 최소 단위로 두고, 나머지 구조를 선택적으로 확장합니다.

- 장점: 최소 진입장벽(2개 파일) + 점진적 확장
- 효과: 버전 히스토리, 브랜치 기반 실험, PR 리뷰, 롤백을 에이전트 운영에 직접 적용

### 2.2 Framework-agnostic + Adapter

동일 원본 정의를 여러 포맷으로 변환하는 `export/import` 구조를 채택합니다.

- 설계 의도: 실행 엔진(lock-in)보다 정의 자산의 재사용성 극대화
- 결과: 조직별 도구 스택이 달라도 동일 에이전트 자산 공유 가능

### 2.3 Compliance-first 확장

`agent.yaml`에 `compliance`와 `segregation_of_duties`를 1급 필드로 포함합니다.

- 일반 AI 에이전트 도구가 후순위로 다루는 규제/감사 요구를 사전 구조화
- 특히 금융권(감독, 기록보존, 모델리스크, 업무분리) 요구사항에 맞춘 정책 선언 가능

---

## 3. 표준 파일 모델

### 3.1 필수 파일

1. `agent.yaml`: manifest, 모델/스킬/도구/규제 설정
2. `SOUL.md`: 에이전트 정체성과 커뮤니케이션 스타일

### 3.2 주요 선택 파일/디렉토리

- `RULES.md`: 강제 제약(반드시/금지)
- `DUTIES.md`: 역할 분리 및 권한 경계
- `AGENTS.md`: 프레임워크 비종속 보조 지침
- `skills/`, `tools/`, `workflows/`, `agents/`: 능력 모듈/합성
- `memory/`, `knowledge/`: 상태 지속과 레퍼런스
- `compliance/`: 감사/규제 산출물

이 구조는 "프롬프트 파일 + 코드" 혼합형 프로젝트를 **명시적 도메인 경계**를 가진 리포지토리로 바꿔줍니다.

---

## 4. 실행 플로우 (CLI 관점)

### 4.1 `init` — 스캐폴딩

`src/commands/init.ts` 기준으로 `minimal/standard/full` 템플릿을 생성합니다.

- minimal: `agent.yaml`, `SOUL.md`
- standard: RULES/AGENTS + skills/knowledge 뼈대
- full: compliance, hooks, memory, config 등 운영용 구조까지 생성

즉, 템플릿이 곧 조직 성숙도(개인 실험 ↔ 규제 환경) 선택지 역할을 합니다.

### 4.2 `validate` — 정적 품질 게이트

`src/commands/validate.ts`는 다층 검증을 수행합니다.

1. AJV로 `agent.yaml` 스키마 검증
2. `SOUL.md` 존재/내용 검증
3. manifest가 참조한 `skills/tools/agents` 실체 검증
4. `skills/*/SKILL.md` frontmatter 규칙 검증
5. `--compliance` 시 risk/framework/SOD 추가 검증

CI에서 `gitagent validate`를 강제하면 "실행 전에 깨지는 구성"을 대부분 사전에 차단할 수 있습니다.

### 4.3 `export`/`run` — 실행 환경 연결

- `export`: 표준 정의 → 타깃 포맷 변환
- `run`: 로컬/원격 소스를 어댑터와 연결해 실행

핵심은 GitAgent가 실행 엔진 자체가 아니라 **정의 계층 + 변환 계층**이라는 점입니다.

---

## 5. 컴플라이언스 및 SOD 모델

`validate`의 컴플라이언스 로직은 다음 점검을 포함합니다.

- risk tier 기반 최소 요구사항
- framework(FINRA/Federal Reserve/SEC/CFPB)별 권고/오류 규칙
- SOD role 중복/충돌 탐지
- handoff의 역할 유효성 검증

실무 관점에서 이는 "문서로만 존재하던 통제정책"을 **머신 체크 가능한 구성 파일**로 끌어내린다는 의미가 있습니다.

---

## 6. 강점과 트레이드오프

### 강점

- 정의 자산의 이식성과 버전관리성이 매우 높음
- 조직 협업 방식(PR, 리뷰, 감사 로그)과 자연스럽게 결합
- 규제형 도메인에 필요한 제약 모델을 표준 레벨에서 지원

### 트레이드오프

- 런타임 동작 품질은 어댑터/실행 엔진 품질에 의존
- 표준 문서가 풍부해질수록 초기 작성/유지 비용 증가
- 다중 프레임워크 동시 지원 시 포맷별 기능 편차 관리 필요

---

## 7. 이 프로젝트에 주는 시사점

이 저장소 관점에서 GitAgent는 다음 참고 가치를 제공합니다.

1. **"에이전트 정의 레이어"와 "실행 레이어" 분리 패턴**
2. **규제/감사 요구를 스키마로 승격하는 방법**
3. **GitHub Actions 기반 검증 게이트를 통한 운영 안정화**

즉, 단일 에이전트 구현체 분석을 넘어, 여러 에이전트 런타임을 아우르는 **메타 표준 전략** 사례로 볼 수 있습니다.

---

## 8. 참고 소스 (검증 기준)

- 홈페이지: <https://www.gitagent.sh/>
- 저장소: <https://github.com/open-gitagent/gitagent>
- 스펙: `spec/SPECIFICATION.md`
- 코드 진입점: `src/index.ts`
- 핵심 명령: `src/commands/init.ts`, `src/commands/validate.ts`
