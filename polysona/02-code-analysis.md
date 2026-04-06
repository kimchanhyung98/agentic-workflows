# Polysona 코드 심층 분석

> 5개 전문 에이전트(아키텍트, 풀스택 엔지니어, 리서처, 심리학 전문가, 콘텐츠 전략 분석가)의 병렬 분석을 종합한 문서입니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [5개 에이전트 파이프라인](#2-5개-에이전트-파이프라인)
3. [10-Framework 심리학 인터뷰 시스템](#3-10-framework-심리학-인터뷰-시스템)
4. [페르소나 데이터 모델](#4-페르소나-데이터-모델)
5. [콘텐츠 파이프라인](#5-콘텐츠-파이프라인)
6. [대시보드 & 서버](#6-대시보드--서버)
7. [플러그인 & 훅 시스템](#7-플러그인--훅-시스템)
8. [피치 덱 & 포지셔닝](#8-피치-덱--포지셔닝)
9. [생태계 비교](#9-생태계-비교)
10. [아키텍처 평가](#10-아키텍처-평가)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 저장소 | [LilMGenius/polysona](https://github.com/LilMGenius/polysona) |
| 버전 | 1.3.0 |
| 라이선스 | MIT |
| GitHub Stars | ~30 / Forks 7 |
| 언어 | TypeScript (서버/클라이언트), Markdown (에이전트/스킬/페르소나) |
| 스택 | Bun + Hono (서버), React 19 + Vite 7 + Tailwind CSS 4 (클라이언트) |
| 파일 수 | 115개 |
| 발표 | Ralphthon Seoul (2026-03-29), 카카오벤처스·OpenAI·네이버D2SF 후원 |

**핵심 명제**: "에이전트는 일을 하지만, '나'를 모른다" — Polysona는 10개 심리학 프레임워크로 인간의 심층 심리를 구조화하고, 5개 전문 에이전트로 콘텐츠 파이프라인을 운영하며, 추출된 페르소나를 어떤 AI 에이전트에도 이식 가능하게 만드는 시스템입니다.

### 핵심 숫자 (CLAUDE.md Key Facts — 절대 변경 불가)

- 심리 프레임워크: **10개** (서양 심층 6 + 서양 보완 2 + 동양 2)
- 인터뷰 원칙: **10개**
- 자아 레이어: **5개**
- MVP 플랫폼: **5개** (X, Threads, LinkedIn, Naver Blog, Brunch)

---

## 2. 5개 에이전트 파이프라인

### 파이프라인 구조

```text
SETUP (1회 또는 주기적 갱신)
  ① Profiler → 인터뷰 로그 추출 → persona.md + nuance.md + accounts.md

LOOP (콘텐츠 사이클마다 반복)
  ② Trendsetter → 트렌드 스캔 + 페르소나 필터링
       ↓
  ③ Content-Writer → 페르소나 + 트렌드 → 플랫폼별 3개 초안
       ↓
  ④ Virtual-Follower → 가상 팔로워 QA 시뮬레이션 (context: fork)
       ↓ 사용자 선택
  ⑤ Admin → 게시 + 성과 추적 + 피드백 루프
```

### 에이전트 1: Profiler (심리 인터뷰어)

- **역할**: 순수 추출(extraction only). 구조화는 Polysona 오케스트레이터가 담당
- **도구**: Read, Write, Bash / **maxTurns**: 50
- **출력 계약**: `~YYYY-MM-DD: FrameworkName: content` (프레임워크 항목), `~YYYY-MM-DD: GAP: description` (모순 항목)
- **엄격한 비책임**: 기존 persona core blocks 재작성 금지, 과거 인터뷰 로그 병합/요약/파괴적 재색인 금지

### 에이전트 2: Trendsetter (트렌드 탐지기)

- **역할**: 실시간 트렌드 스캔 → 페르소나 필터링 → 5개 순위 토픽 출력
- **5단계 필터링**: 도메인 신호 추출 → 플랫폼 집중 추출 → 교집합 필터 → 랭킹 → 폴백
- **폴백 규칙**: 라이브 검색 실패 시 즉시 로컬 파일 기반 토픽 랭킹 (타임아웃보다 빠른 폴백)
- **저장**: `content/trends/YYYY-MM-DD-scan-slug.md`

### 에이전트 3: Content-Writer (콘텐츠 생성기)

- **역할**: 페르소나 + 뉘앙스 + 롤모델 + 트렌드를 결합해 플랫폼별 한국어 초안 생성
- **출력**: 정확히 **3개 초안** 변형
- **7단계 필수 워크플로우**: 파싱 → 3개 생성 → 슬러그 도출 → Write → Read 검증 → 확인된 경로 반환 → 실패 시 실패 보고
- **플랫폼별 리워드 패턴**:

| 플랫폼 | 특성 | 훅 패턴 | 이모지 |
|--------|------|---------|--------|
| X | 짧은 펀치라인, 인용RT 유도 | `솔직히 ~` | 낮음 |
| Threads | 대화형, `너는?`으로 마무리 | `요즘 ~` | 중간 |
| LinkedIn | 캐러셀 스토리텔링, hook→data→CTA | `지난 N년간 ~` | 없음 |
| Naver Blog | 이미지 우선, 리뷰형, 키워드 반복 | `~ 해봤는데` | 높음 |
| Brunch | 롱폼 에세이, 감성, 문학적 | `~ 라는 생각이 들었다` | 0 |

### 에이전트 4: Virtual-Follower (QA 시뮬레이터)

- **역할**: 가상 팔로워 시뮬레이션으로 콘텐츠 품질 평가 + TOP 5 추천
- **핵심 설계**: `context: fork` — 생성 컨텍스트에서 완전히 격리된 독립 평가
- **5개 팔로워 프로파일**: 20대 여성 직장인, 30대 남성 개발자, 40대 자영업자, 스타트업 창업자, 일반 팔로워
- **5개 평가 차원**: Hook strength, Empathy, Share intent, CTA response, Platform fit
- **롤모델 GAP 분석**: accounts.md 롤모델 스타일 큐와 초안 비교 → 유사점(align) + 결핍(missing)

### 에이전트 5: Admin (퍼블리셔 및 트래커)

- **역할**: 최종 콘텐츠 저장, 게시 가이던스, 성과 추적, 피드백 루프
- **메타데이터 계약**: platform, published_at, hook, engagement_target, actual_engagement
- **피드백 루프**: 성과 데이터 → nuance.md 플랫폼 패턴 업데이트 → 다음 초안에 반영

---

## 3. 10-Framework 심리학 인터뷰 시스템

### 3.1 프레임워크 분류

| 분류 | 프레임워크 | 목적 | 데이터 목적지 |
|------|-----------|------|---------------|
| 서양 심층 (6) | McAdams Life Story | 내러티브 정체성, 챕터/전환점 | persona.md core |
| | Laddering + MI + ACT | 가치 위계, 동기 에너지원 | persona.md decide |
| | Clean Language | 은유 공간, 무의식 언어 구조 | nuance.md voice |
| | Johari Window | 사각지대, 자기 이미지 vs 관찰자 이미지 | persona.md blind |
| | IFS (내부 가족 체계) | 내부 파트, 보호자/추방자/소방관 역학 | persona.md blind |
| | Repertory Grid | 개인 구성 체계, 양극 결정 축 | persona.md decide |
| 서양 보완 (2) | Object Relations | 초기 관계 템플릿, 전이 에코 | persona.md core |
| | Projective Technique | 모호성 기반 무의식 반응 | persona.md blind |
| 동양 (2) | Zen Koan | 전개념적 반응, 역설 저항 | persona.md core |
| | 五倫+陰陽 | 관계적 자기 위치, 성격 양극성 | persona.md core |

### 3.2 인터뷰 진행 흐름

**Warm-up (10분)**: 라포 구축 → McAdams-lite 오픈 내러티브 → 인터뷰 경계 명확화 (추출이지 치료가 아님)

**Deep-dive (30분)**: 적응형 나선 깊이로 프레임워크 순환
- McAdams → Laddering → Clean Language → Johari → IFS → Repertory Grid
- Object Relations → Projective Technique → Zen Koan → 五倫+陰陽 통합 점검
- 각 미니 사이클 후: 증거 라인 캡처, 출력 필드 매핑, GAP 신호 점검

**Closure (10분)**: 프레임워크별 최강 통찰 통합 → 명시적 레이어 모순 식별 → 요약 + GAP 라인 추가

### 3.3 10개 인터뷰 설계 원칙

**추출 원칙 (HOW)**:
1. **Metaphor-first**: 직접 추상화 전에 은유를 통해 의미에 진입
2. **Paradox-placement**: 공안 같은 역설로 연습된 답변 중단
3. **Depth-spiral**: 강제적 즉각 깊이가 아닌 반복적 표면→깊이 이동
4. **Polarity-exploration**: 모든 강점에 대해 비용/그림자/반대 극 탐색
5. **Relationship-mirror**: "타인이 당신을 어떻게 보는가" 질문으로 자기보고 편향 감소

**구조 원칙 (WHAT)**:
6. **Narrative-first**: 레이블보다 이야기, 순서, 전환점 우선
7. **Part-separation**: 통합된 목소리를 강요하지 않고 내부 파트 분리
8. **Grid-building**: 구조적 비교로 양극 결정 구성체 구축

**안전 원칙 (GUARD)**:
9. **Non-leading**: 추출할 것. 선호 결론을 유도하지 말 것
10. **Accumulation**: 프로파일링은 반복 인터뷰 걸친 누적적 축적

### 3.4 방어 우회 기법

- **Clean Language 12개 질문**: "[X]"에 피면접자의 정확한 문구 삽입, 면접자 해석 삽입 금지
- **오염 패턴** (절대 금지): "그 배낭이 어린 시절 트라우마군요?", "그러니까 불안하다는 거잖아요?", 클라이언트 은유를 면접자 은유로 교체
- **Zen Koan**: "지킬 정체성이 없다면 오늘 가장 먼저 바뀌는 결정은?" → 정체성 보호 기제 순간 무력화
- **Laddering + MI + ACT 통합**: 계층적 "왜" 상승 + 비심판적 청취 + 이상적 자아 vs 실제 선택 패턴 구분

### 3.5 5개 에고 레이어 모델

```text
Layer 1: others-see-me       ← 타인의 시선 (Johari, 五倫)     → persona.md blind
         ↕ GAP?
Layer 2: want-to-be-seen     ← 보여지고 싶은 모습 (Goffman)   → nuance.md voice
         ↕ GAP?
Layer 3: conscious-ideal     ← 의식적 이상 (직접 입력)         → accounts.md ideal
         ↕ GAP?
Layer 4: rolemodel           ← 벤치마크 인물 (구체적 표준)      → accounts.md rolemodel
         ↕ GAP?
Layer 5: unconscious-self    ← 무의식적 자아 (McAdams/IFS/Koan) → persona.md core
```

### 3.6 GAP 분석

모든 레이어 쌍 간 모순을 감지하여 즉시 기록:

```text
~2026-03-29: GAP: conscious-ideal(minimalism) ↔ unconscious-self(over-engineering under stress)
~2026-03-29: GAP: others-see-me(result-fixated) ↔ want-to-be-seen(process-oriented mentor)
~2026-03-29: GAP: rolemodel(high-risk operator) ↔ unconscious-self(risk-avoidant execution pattern)
```

GAP은 모순을 해소하지 않고 보존합니다. 인간은 모순적이며, 그 모순이 콘텐츠의 심리적 진정성의 원천입니다.

---

## 4. 페르소나 데이터 모델

### 4.1 PLOON 테이블 형식

Polysona 전용 구조화 마크다운 형식:

```markdown
## 섹션명
[table#N](col1,col2,col3)
값1 | 값2 | 값3
값4 | 값5 | 값6

## interview-log
~2026-03-29: McAdams Life Story: 전환점은 첫 프로젝트 실패에서 재건의 여정
~2026-03-29: GAP: conscious-ideal(minimal) vs unconscious-self(complexity under pressure)
```

**설계 원칙**: JSON/DB 없이 순수 Markdown. Git이 데이터베이스이자 이력 원장.

### 4.2 3-파일 데이터 구조

**persona.md** — "이 사람이 누구인가":

```text
## core     → [table#1](layer,value,source)     — 자아 수직 단면
## decide   → [table#1](priority,approach,source) — 의사결정 논리
## energy   → [table#1](source,level,context)     — 동기 에너지 지도
## blind    → [table#1](type,description,source)   — 맹점과 방어기제
## interview-log → ~날짜: Framework: 내용            — 원자료 (append-only)
```

**nuance.md** — "이 사람이 어떻게 말하는가":

```text
## voice    → [table#1](register,style,avoid)         — 어조 레지스터
## platform → [table#1](platform,tone,hook_pattern,emoji_density) — 플랫폼별 조율
## phrasing → [table#1](type,example)                  — 금기어/선호어
```

**accounts.md** — "이 사람이 누구를 벤치마크하는가":

```text
## rolemodel → [table#1](name,platform,why,signal) — 롤모델 목록
## virtual   → [table#1](profile,concern,expectation) — 가상 팔로워 프로파일
```

### 4.3 Voice Mix 개념

콘텐츠 생성 시 세 파일이 동시에 로드되어 교차점에서 콘텐츠가 생성됩니다:
- persona.md → **무엇을** 말할 것인가 (동기, 가치)
- nuance.md → **어떻게** 말할 것인가 (어조, 금기어)
- accounts.md → **어떤 수준으로** 말할 것인가 (롤모델 기준)

---

## 5. 콘텐츠 파이프라인

### 5.1 전체 흐름

```text
/interview → persona.md + nuance.md + accounts.md
    ↓
/trend → content/trends/YYYY-MM-DD-scan-slug.md (5개 순위 토픽)
    ↓
/content [platform] → content/drafts/YYYY-MM-DD-platform-slug.md (3개 초안)
    ↓
/qa → content/qa/YYYY-MM-DD-platform-slug.md (TOP 5 추천)
    ↓ 사용자 선택
/publish → content/published/YYYY-MM-DD-platform-slug.md (최종 + 성과 추적)
    ↓
피드백 루프 → nuance.md 업데이트 → 다음 콘텐츠에 반영
```

### 5.2 Write-then-Read 강제 검증 패턴

모든 데이터 생성 에이전트가 동일하게 따르는 필수 패턴:

```text
Write 도구 → 파일 저장 → Read 도구 → 존재 확인 → 확인된 경로와 함께 응답
쓰기 실패 시: "실패했다고 보고. 성공 주장 금지."
```

이 패턴은 AI 환각(hallucination)을 구조적으로 방지합니다.

### 5.3 Export — 페르소나 이식성

`/export [target]` 명령으로 페르소나를 외부 AI 에이전트 환경에 이식:

| target | 출력 파일 |
|--------|-----------|
| `claude` | `personas/{active}/generated/CLAUDE.generated.md` |
| `agents` | `personas/{active}/generated/AGENTS.generated.md` |
| `both` | 두 파일 모두 |

이것이 "Build and run multiple personas across **any** AI agent" 미션의 기술적 핵심입니다.

---

## 6. 대시보드 & 서버

### 6.1 서버 아키텍처 (Hono + Bun)

```text
server/index.ts (Hono 서버)
├── /api/status              → 시스템 상태
├── /api/personas            → 페르소나 목록 (personas/ 스캔)
├── /api/personas/:id        → 상세 (persona.md + nuance.md + accounts.md 병렬 로드)
├── /api/personas/:id/interview-log  → 인터뷰 로그 항목
├── /api/personas/:id/qa-simulation  → 가상 팔로워 QA 점수
├── /api/content/drafts      → 초안 파일 목록
├── /api/content/published   → 발행 파일 목록
├── /api/agents/status       → 에이전트 상태
└── SPA fallback             → dist/index.html (React Router 지원)
```

### 6.2 PLOON 파서 (`server/lib/ploon.ts`)

마크다운 라인별 상태 기계:

```text
빈 줄     → table/columns 리셋
## 섹션   → scope 전환
[테이블]  → table 이름, columns 배열 설정
파이프행  → columns 매핑으로 레코드 push
~날짜     → scope.entries에 {date, content} push
key:val   → scope[key] = value
```

### 6.3 클라이언트 페이지 구조

```text
/           → Home          — 시스템 상태, 통계, 에이전트 상태 카드
/personas   → Personas      — 페르소나 목록 카드 그리드
/personas/:id → PersonaDetail — 가장 데이터 집약적 페이지
    ├── SelfLayerDiagram     — 5계층 자아 모델 시각화
    ├── GapAnalysis          — Ideal vs Reality 카드 쌍
    ├── VoiceMixBar          — 보이스 믹스 비율 바 차트
    ├── FrameworkCoverage    — 10개 프레임워크 적용 현황
    ├── PloonViewer          — PLOON 데이터 테이블 렌더러
    └── InterviewTimeline    — 인터뷰 로그 타임라인
/content    → ContentPipeline — 콘텐츠 파이프라인 (drafts + published)
/qa         → VirtualFollower — QA 시뮬레이션 (20개 팔로워 원형)
/agents     → AgentMonitor   — 에이전트 파일 존재 여부 및 상태
```

### 6.4 결정론적 QA 점수

`deterministicScore()`: DJB2 변형 해시 알고리즘으로 `personaId + followerId + dimension + contentName` → 범위 [40, 95] 점수 생성. AI 추론 없이 일관된 프레젠테이션 데모용 UX 제공.

### 6.5 빌드 시스템

```text
"dev": "bun run build && bun run server/index.ts"  ← Vite 빌드 후 Bun 서버 실행
"build": "vite build"                                ← client/ → dist/
```

Vite dev server 대신 Bun + Hono가 직접 정적 파일 서빙. HMR 없는 대신 단일 서버 구조.

---

## 7. 플러그인 & 훅 시스템

### 7.1 이중 플랫폼 지원

| 플랫폼 | 인식 파일 | 스킬 경로 | 설치 방법 |
|--------|-----------|-----------|-----------|
| Codex | `AGENTS.md`, `agents/openai.yaml` | `.agents/skills/` | 자동 인식 |
| Claude Code | `.claude-plugin/plugin.json` | `skills/*/SKILL.md` | `claude plugin install polysona` |

Codex 동기화: `node ./scripts/sync-codex-skills.mjs` — `skills/`를 `.agents/skills/`로 미러링

### 7.2 훅 시스템 (hooks/hooks.json)

| 이벤트 | 스크립트 | 기능 |
|--------|---------|------|
| SessionStart | `session-start.sh` | 활성 페르소나 자동 로드 + 핵심 규칙 표시 |
| PreToolUse | `pre-tool-use.sh` | `personas/` 파일에 Write 시도 시 PLOON 덮어쓰기 경고 |
| PostToolUse | `post-tool-use.sh` | AI 슬롭 패턴 탐지 ("certainly", "absolutely", "as an AI" 등) |

**session-start.sh**: `personas/_active.md`에서 활성 페르소나 ID 읽어 자동 컨텍스트 주입
**pre-tool-use.sh**: "Append to interview-log section only. Never overwrite compressed core."
**post-tool-use.sh**: 도구 출력에서 과도한 공손 표현 탐지 → CLAUDE.md "No speculation" 철학 강제

### 7.3 스킬 인라인 프리로드 패턴

모든 스킬 SKILL.md의 핵심:

```bash
!`ACTIVE=$(cat personas/_active.md 2>/dev/null || echo "default");
cat "personas/$ACTIVE/persona.md" 2>/dev/null || echo "No persona found. Run /interview first."`
```

스킬 호출 시 활성 페르소나를 즉시 자동 로드. 각 스킬이 필요한 파일만 선택적으로 로드합니다.

---

## 8. 피치 덱 & 포지셔닝

### 8.1 5슬라이드 구조

```text
Slide 1 (Cover)    → "Polygon처럼 다면적인 자아를 Persona 단위로 구조화"
Slide 2 (Problem)  → "에이전트는 일을 하지만, '나'를 모른다"
Slide 3 (Evidence) → +50 팔로워 (내 말투로 답글 → 실제 성과)
Slide 4 (Solution) → Interview → Structuring → Generation → QA Loop
Slide 5 (Progress) → Ralphthon Seoul 운영 스택 + LIVE 상태
```

### 8.2 한국어 vs 영어 메시지 전략

- 한국어: 감정적 밀도 높음 ("나를 평평하게 소비한다")
- 영어: 기술적 명확성 높음 ("self-projection automation")
- 한국어 Pain Point: `"문서 있음 / 운영 빈도 / 결과"` → 감정 밀도
- 영어 Pain Point: `"Docs exist / Always active / Result"` → 기술 언어

### 8.3 경쟁 포지셔닝

> "gstack gives you Garry Tan's brain. **polysona gives you yours.**"

gstack(Garry Tan 브레인 복제, GitHub Stars 10,000+)이 "유명인의 시선"을 제공하는 반면, Polysona는 "나 자신의 심리적 지문"을 추출하고 운영하는 시스템입니다.

---

## 9. 생태계 비교

### 9.1 Polysona의 고유성

| 특성 | Polysona | gstack | TinyTroupe | 일반 AI 콘텐츠 도구 |
|------|----------|--------|------------|---------------------|
| 페르소나 원천 | 심리학 10-framework 인터뷰 | 유명인 프로필 | 시뮬레이션 에이전트 | 프롬프트 템플릿 |
| 자아 모델 | 5 에고 레이어 + GAP | 단일 레이어 | 행동 시뮬레이션 | 없음 |
| 이식성 | 멀티 런타임 (Codex/Claude) | 특정 도구 종속 | 특정 프레임워크 | 특정 도구 |
| QA | 가상 팔로워 시뮬레이션 | 없음 | 그룹 시뮬레이션 | 없음 |
| 데이터 형식 | PLOON (Markdown) | 구조화 없음 | Python 코드 | JSON/프롬프트 |
| 동서양 통합 | O (선불교, 유교) | X | X | X |

### 9.2 로드맵

**v1 (현재)**: 한국어 텍스트 콘텐츠 — v1.0~v1.3 완료, v1.4 트렌드 지식 루프, v1.6 MCP 지원
**v2**: 한국어 미디어 확장 — 카드뉴스(v2.0), 숏폼 영상 스크립트(v2.1), 롱폼(v2.2)
**v3**: 영어 확장 — 텍스트(v3.0) → 카드뉴스(v3.1) → 숏폼(v3.2) → 롱폼(v3.3)

---

## 10. 아키텍처 평가

### 강점

**심리학적 다층성**: 10개 프레임워크의 통합으로 단일 이론의 맹점을 상호 보완. McAdams는 서사를, Laddering은 가치 위계를, Clean Language는 은유를, IFS는 내적 파트를, Zen Koan은 전개념적 층위를, 五倫+陰陽은 관계적 자아를 탐사합니다.

**GAP 보존 원칙**: 모순을 해소하지 않고 보존하는 것은 심리학적으로 매우 성숙한 설계. "미니멀리즘을 추구하지만 압박 시 과잉 설계"라는 GAP 자체가 콘텐츠의 진정성 원천입니다.

**context: fork 격리**: QA 에이전트가 생성 컨텍스트에서 완전히 독립된 평가 환경에서 실행. 자기 생성 콘텐츠에 대한 자기 평가 편향을 시스템 수준에서 차단합니다.

**Write-then-Read 강제 검증**: AI 환각(hallucination) 방지의 구조적 해법. 파일 저장 없이 성공을 주장하는 것을 원천 차단합니다.

**Append-only 불변성**: interview-log는 절대 덮어쓰지 않고 축적만 합니다. Git이 유일한 이력 원장이며 데이터 무결성의 근간입니다.

**이식성**: `/export`로 페르소나를 CLAUDE.md/AGENTS.md 형식으로 변환. 특정 AI 도구 종속을 탈피하는 실질적 차별점입니다.

### 주의 사항

**실제 파이프라인 산출물 부재**: `content/` 4개 디렉토리 모두 `.gitkeep`만 존재. MVP "동작 중" 클레임과 저장소 상태 사이에 간극이 있습니다.

**결정론적 QA 점수**: 대시보드의 QA 시뮬레이션 점수는 해시 기반 결정론적 값이며 실제 AI 추론 결과가 아닙니다. 프레젠테이션 데모용입니다.

**자기 보고 편향**: 아무리 정교한 질문 기법을 사용해도 인터뷰는 자기 보고 기반. 실제 행동 데이터와의 통합이 있으면 GAP 탐지 정확도가 높아질 것입니다.

**훅 환경 변수 의존**: pre/post-tool-use 훅이 `TOOL_NAME`, `FILE_PATH`, `TOOL_OUTPUT` 환경 변수에 의존. 호스트 런타임이 이를 올바르게 설정하지 않으면 보호 메커니즘이 무력화됩니다.

**Codex 동기화 수동**: `skills/`와 `.agents/skills/` 간 수동 동기화 (`bun run codex:skills:sync`) 요구. 드리프트 위험이 있습니다.

### 설계 패턴 요약

| 패턴 | 적용 위치 | 효과 |
|------|-----------|------|
| Append-only Log | interview-log | 데이터 무결성, 시간별 변화 추적 |
| Write-then-Read | 모든 데이터 생성 에이전트 | 환각 방지 |
| Context Fork | virtual-follower | 생성-평가 편향 격리 |
| SSOT (Single Source of Truth) | 3-파일 페르소나 모델 | 일관성 보장 |
| Inline Shell Preload | 모든 SKILL.md | 자동 컨텍스트 주입 |
| Hook Guards | session-start/pre/post | 런타임 레벨 데이터 보호 |
| Dual Harness | Codex + Claude Code | 런타임 이식성 |
| Deterministic Scoring | QA 대시보드 | 일관된 데모 UX |
| 5-Layer Ego Model | 페르소나 추출 | 심리적 다면성 포착 |
| GAP Preservation | 인터뷰 → 콘텐츠 | 진정성 기반 콘텐츠 |

---

## 참고 자료

- [Polysona 저장소](https://github.com/LilMGenius/polysona)
- [CLAUDE.md](https://github.com/LilMGenius/polysona/blob/main/CLAUDE.md)
- [AGENTS.md](https://github.com/LilMGenius/polysona/blob/main/AGENTS.md)
- [CHANGELOG](https://github.com/LilMGenius/polysona/blob/main/CHANGELOG.md)
- [에이전트 프롬프트](https://github.com/LilMGenius/polysona/tree/main/agents)
- [스킬 디렉토리](https://github.com/LilMGenius/polysona/tree/main/skills)
- [대시보드 서버](https://github.com/LilMGenius/polysona/blob/main/server/index.ts)
- [PLOON 파서](https://github.com/LilMGenius/polysona/blob/main/server/lib/ploon.ts)
