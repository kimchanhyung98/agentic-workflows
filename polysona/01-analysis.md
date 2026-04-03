# Polysona 설계 및 실행 플로우 분석

## 1. 프로젝트 개요

- 저장소: `LilMGenius/polysona`
- 목적: 다중 페르소나를 추출·운영해 AI 에이전트 전반(Codex/Claude/OpenCode)에서 재사용
- 현재 버전: `1.3.0` (`package.json`, `README`, `CHANGELOG`)
- 핵심 도메인: 인터뷰 기반 페르소나 추출 → 트렌드 탐색 → 플랫폼별 콘텐츠 생성 → QA 시뮬레이션 → 게시/추적
- 핵심 제약: 심리 프레임워크 **10개**, 인터뷰 원칙 **10개**, 에고 레이어 **5개**, MVP 플랫폼 **5개**

Polysona의 차별점은 "모델 자체 최적화"가 아니라 **사용자 정체성(페르소나)을 실행 가능한 데이터 계층으로 분리**했다는 점입니다. 10개 심리학 프레임워크로 무의식 패턴까지 추출하고, 5개 에고 레이어 간 모순(GAP)을 보존하며, 그 위에서 콘텐츠를 생성합니다.

---

## 2. AI Agent 하네스 구조 분석

### 2.1 Codex 하네스

- `AGENTS.md`: 시스템 철학(7개), 금지 규칙(4개, no speculation 등), 컨텍스트 로딩 프로토콜, Key Facts(절대 변경 불가 숫자) 정의
- `agents/openai.yaml`: Codex 에이전트 카탈로그(profiler/trendsetter/content-writer/virtual-follower/admin) + 스킬 바인딩
- `skills/*/SKILL.md`: 명령 단위 실행 규약 + 인라인 bash 프리로드
- `scripts/sync-codex-skills.mjs`: `skills/`를 `.agents/skills`로 미러링해 Codex discovery 호환

핵심은 **명령(Skill)과 역할(Agent) 분리**입니다. 사용자는 `/trend` 같은 동작 단위로 호출하고, 내부적으로는 trendsetter가 책임집니다.

### 2.2 Claude 하네스

- `.claude-plugin/plugin.json`: 8개 스킬 + 5개 에이전트 등록
- `.claude-plugin/marketplace.json`: 로컬 마켓플레이스 메타데이터
- `hooks/hooks.json`: SessionStart/PreToolUse/PostToolUse 훅 체인 선언
- `hooks/session-start.sh`: `personas/_active.md`에서 활성 페르소나 자동 로드 + 핵심 규칙 출력
- `hooks/pre-tool-use.sh`: `personas/` 파일 Write 전 PLOON 덮어쓰기 경고 ("Append to interview-log only. Never overwrite compressed core.")
- `hooks/post-tool-use.sh`: AI 슬롭 패턴 탐지 ("certainly", "absolutely", "as an AI" 등)

Claude 경로는 plugin + hooks 조합으로 런타임 가드레일을 구현합니다.

### 2.3 공통 하네스 패턴

1. **SSOT 문서화**: 각 사실의 단일 소유 문서를 강제 (persona.md = 심리, nuance.md = 목소리, accounts.md = 벤치마크)
2. **No-speculation 규칙**: 숫자, 프레임워크 수, 타임라인, 역량 주장 발명 금지
3. **Write-then-Read 검증**: 생성 결과를 파일로 저장 → 즉시 Read → 존재 확인 → 확인된 경로와 함께 응답. 실패 시 실패 보고 (성공 주장 금지)
4. **Git-친화 운영**: 모든 상태를 PLOON Markdown으로 남겨 diff/이력 검증 가능
5. **인라인 프리로드**: 모든 스킬이 bash `!` 명령으로 `personas/_active.md` → 활성 페르소나 컨텍스트 자동 주입

---

## 3. 10-Framework 심리학 인터뷰 시스템

### 3.1 프레임워크 분류

| 분류 | 프레임워크 | 탐사 대상 | 데이터 목적지 |
|------|-----------|-----------|---------------|
| 서양 심층 (6) | McAdams Life Story | 내러티브 정체성, 챕터/전환점, 구원/오염 서사 | persona.md core |
| | Laddering + MI + ACT | 가치 위계, 동기 에너지원, 이상 vs 실제 선택 패턴 | persona.md decide |
| | Clean Language | 은유 공간, 무의식 언어 구조, 목소리 서명 | nuance.md voice |
| | Johari Window | 사각지대, 자기 이미지 vs 관찰자 이미지 | persona.md blind |
| | IFS (내부 가족 체계) | 내부 파트, 보호자/추방자/소방관 역학 | persona.md blind |
| | Repertory Grid | 양극 구성 체계, 의사결정 휴리스틱 | persona.md decide |
| 서양 보완 (2) | Object Relations | 초기 관계 템플릿, 전이 에코 | persona.md core |
| | Projective Technique | 모호성 기반 무의식 반응 투사 | persona.md blind |
| 동양 (2) | Zen Koan | 전개념적 반응, 정체성 보호 기제 무력화 | persona.md core |
| | 五倫+陰陽 | 관계적 자기 위치, 과사용 덕목의 그림자 | persona.md core |

### 3.2 5 에고 레이어 & GAP 모델

| 레이어 | 정의 | 소스 프레임워크 | 데이터 목적지 |
|--------|------|----------------|---------------|
| Layer 1: others-see-me | 타인의 시선 | Johari, 五倫 | persona.md blind |
| Layer 2: want-to-be-seen | 보여지고 싶은 모습 | Goffman 앞무대 | nuance.md voice |
| Layer 3: conscious-ideal | 의식적 이상 | 직접 명시적 입력 | accounts.md ideal |
| Layer 4: rolemodel | 벤치마크 인물 | 구체적 계정/인물 | accounts.md rolemodel |
| Layer 5: unconscious-self | 무의식적 자아 | McAdams, Laddering, IFS, Zen Koan | persona.md core |

**GAP 발견**: 모든 레이어 쌍 간 모순을 감지하여 즉시 기록합니다. 모순은 해소하지 않고 보존합니다 — 인간은 모순적이며, 그 모순이 콘텐츠의 심리적 진정성의 원천입니다.

```
~2026-03-29: GAP: conscious-ideal(minimalism) ↔ unconscious-self(over-engineering under stress)
~2026-03-29: GAP: others-see-me(result-fixated) ↔ want-to-be-seen(process-oriented mentor)
~2026-03-29: GAP: rolemodel(high-risk operator) ↔ unconscious-self(risk-avoidant execution)
```

### 3.3 인터뷰 설계 원칙 (10개, 3개 범주)

**추출 원칙 (HOW)**: Metaphor-first (은유 선행), Paradox-placement (역설 배치), Depth-spiral (깊이 나선), Polarity-exploration (대극 탐색), Relationship-mirror (관계 거울)

**구조 원칙 (WHAT)**: Narrative-first (서사 우선), Part-separation (파트 분리), Grid-building (격자 구축)

**안전 원칙 (GUARD)**: Non-leading (비유도), Accumulation (축적)

### 3.4 방어 우회 기법

- **Clean Language**: 피면접자의 정확한 은유를 오염 없이 따라감. 면접자 해석 삽입, 레이블 대입, 해결 유도 금지
- **Zen Koan**: "지킬 정체성이 없다면 오늘 가장 먼저 바뀌는 결정은?" → 정체성 보호 기제를 순간적으로 무력화
- **Laddering + MI + ACT**: 직접적 "왜" 반복이 심문처럼 느껴지면 MI의 반영적 청취로 방어를 낮추고, ACT로 이상적 자아 언어와 실제 반복 선택 패턴을 구분

---

## 4. 5-에이전트 파이프라인 역할 분해

| 에이전트 | 입력 | 출력 | 저장 위치 | 핵심 특성 |
|---|---|---|---|---|
| profiler | 인터뷰 대화 | 프레임워크별 로그 + GAP | `personas/{id}/persona.md` | 순수 추출, maxTurns 50, append-only |
| trendsetter | persona/accounts 맥락 | 주제 랭킹 5개 | `content/trends/` | 5단계 필터링, 즉시 폴백 |
| content-writer | 주제 + persona/nuance/accounts | 플랫폼별 Draft 3종 | `content/drafts/` | Voice Mix 적용, 7단계 워크플로우 |
| virtual-follower | 최신 draft + accounts | 팔로워 시뮬레이션 TOP 5 | `content/qa/` | **context: fork** 격리 |
| admin | 최종 draft | 게시용 최종본 + 추적 메타데이터 | `content/published/` | 피드백 루프 → nuance.md |

각 에이전트는 **Write → Read 검증**을 필수로 적용하며, 실제 파일 저장 없는 성공 응답을 금지합니다.

### context: fork 격리 설계

Virtual-follower는 `context: fork`로 실행됩니다. 이는 생성 컨텍스트로부터 QA 판단을 완전히 격리하는 아키텍처 결정입니다. 창작자와 비평자는 동일한 인지 공간에 공존하기 어려우며, fork 컨텍스트는 이 역할 분리를 시스템 수준에서 강제합니다.

### Voice Mix 개념

콘텐츠 생성 시 세 파일이 동시에 로드되어 교차점에서 콘텐츠가 생성됩니다:
- **persona.md** → 무엇을 말할 것인가 (동기, 가치)
- **nuance.md** → 어떻게 말할 것인가 (어조, 금기어)
- **accounts.md** → 어떤 수준으로 말할 것인가 (롤모델 기준)

---

## 5. 플랫폼별 콘텐츠 전략

### 5.1 플랫폼 리워드 패턴

| 플랫폼 | 콘텐츠 특성 | 훅 패턴 | 이모지 밀도 |
|--------|-----------|---------|------------|
| X | 짧은 펀치라인, 논란 유발, 인용RT 유도 | `솔직히 ~` | 낮음 |
| Threads | 댓글 유발 질문, 대화형, `너는?`으로 마무리 | `요즘 ~` | 중간 |
| LinkedIn | 캐러셀 스토리텔링, hook→data→CTA | `지난 N년간 ~` | 없음 |
| Naver Blog | 이미지 우선, 리뷰형, 키워드 반복 | `~ 해봤는데` | 높음 |
| Brunch | 롱폼 에세이, 감성 내러티브, 문학적 | `~ 라는 생각이 들었다` | 0 |

### 5.2 한국어 콘텐츠 특수 규칙

- 존댓말 수준은 `nuance.md` voice register 준수: 해요체 vs 합쇼체 vs 반말
- 각 플랫폼 초안은 해당 플랫폼 알고리즘 보상 구조에 맞게 최적화
- Brunch는 이모지 완전 배제, Naver Blog는 고밀도로 차별화

### 5.3 QA 평가 차원 (5개)

1. **Hook strength**: 첫 줄이 스크롤을 멈추게 하는가
2. **Empathy**: 대상 독자가 빠르게 공감하는가
3. **Share intent**: RT/리포스트/공유 의향이 있는가
4. **CTA response**: 댓글/팔로우/클릭 의향이 있는가
5. **Platform fit**: 플랫폼 리워드 패턴에 맞는가

### 5.4 롤모델 GAP 분석

accounts.md 롤모델의 `why`(왜 그 사람인가)와 `signal`(스타일 신호)을 기준으로 초안을 평가합니다:
- **유사성**: 롤모델 신호와 얼마나 일치하는가
- **결핍**: 롤모델 신호에서 무엇이 누락되어 있는가
- **차별화**: 롤모델과 너무 유사해서 독자성을 잃지는 않는가

---

## 6. 코드 관점의 실행 플로우

### 6.1 서버/대시보드 계층

- `server/index.ts`: Hono 엔트리, `/api` 라우팅, 개발/배포 정적 파일 분기, SPA 폴백
- `server/routes/api.ts`: persona/콘텐츠/QA 시뮬레이션/에이전트 상태 API 제공. 20개 가상 팔로워 archetype 하드코딩
- `server/lib/ploon.ts`: PLOON 파서 — 섹션/테이블/entries/key-val을 라인별 상태 기계로 파싱
- `client/src/pages/*`: PersonaDetail(6개 컴포넌트 조합), ContentPipeline, VirtualFollower, AgentMonitor

### 6.2 PLOON 파서(`server/lib/ploon.ts`)

`parsePloon()`은 Markdown 기반 PLOON 포맷을 JSON 유사 객체로 변환합니다.

```
## 섹션명           → 새 scope 전환
[table#N](cols)    → 테이블 헤더, 컬럼 정의
값1 | 값2           → 컬럼 매핑으로 레코드 배열 push
~YYYY-MM-DD: 내용  → entries 배열에 {date, content} push
key: value         → scope[key] = value 직접 할당
빈 줄              → 테이블 컨텍스트 리셋
```

### 6.3 QA 시뮬레이션 점수

`deterministicScore()`: DJB2 변형 해시 알고리즘으로 `personaId + followerId + dimension + contentName` → 범위 [40, 95] 결정론적 점수. AI 추론 없이 일관된 프레젠테이션 데모용 UX를 제공합니다.

### 6.4 주요 대시보드 컴포넌트

| 컴포넌트 | 역할 | 데이터 소스 |
|---------|------|-----------|
| SelfLayerDiagram | 5계층 자아 모델 시각화 | persona blind/core + nuance voice + accounts ideal/rolemodel |
| GapAnalysis | Ideal vs Reality 카드 쌍 | persona.md blind gap + interview-log GAP 항목 |
| VoiceMixBar | 보이스 믹스 비율 바 차트 | nuance.md voice mix 문자열 |
| FrameworkCoverage | 10개 프레임워크 적용 현황 진행 바 | interview-log 키워드 매칭 |
| InterviewTimeline | 중앙 정렬 타임라인 (프레임워크별 색상 배지) | interview-log entries |
| PloonViewer | PLOON 데이터 범용 테이블 렌더러 | 모든 PLOON 섹션 |

---

## 7. Export — 페르소나 이식성

`/export [target]` 명령은 Polysona 안에서 구조화된 페르소나를 외부 AI 에이전트 환경에 이식 가능한 형식으로 변환합니다.

| target | 출력 파일 | 내용 |
|--------|-----------|------|
| `claude` | `CLAUDE.generated.md` | Work philosophy, Decision priorities, Tone rules, Anti-patterns |
| `agents` | `AGENTS.generated.md` | 에이전트 정의, 역할 분할, 호출 방법 |
| `both` | 두 파일 모두 | 양쪽 환경 동시 지원 |

이것이 "Build and run multiple personas across **any** AI agent" 미션의 기술적 핵심입니다. 페르소나가 특정 도구에 종속되지 않고, Codex/Claude/OpenCode 어디서나 동작합니다.

---

## 8. 활용 사례 정리 (실무 적용 관점)

### 8.1 퍼스널 브랜딩/콘텐츠 운영

- 10-framework 인터뷰로 무의식 패턴까지 포함한 페르소나 추출
- 5개 플랫폼별 최적화된 콘텐츠 생성 → QA → 게시 자동화
- 특히 1인 창작자/전문가 계정 운영에 적합

### 8.2 팀 단위 에이전트 운영 가드레일

- no-speculation, Write-then-Read, SSOT 같은 규약을 명시 문서로 강제
- context:fork로 생성-평가 편향 격리
- 훅 시스템으로 런타임 레벨 데이터 보호

### 8.3 에이전트 이식성 실험

- `/export`로 동일 persona를 Codex/Claude/OpenCode에 이식
- "모델 교체 시 정체성 유지" 실험용 베이스로 적합
- 두 런타임에서 결과 편차 비교 가능

---

## 9. 강점과 트레이드오프

### 강점

1. **심리학적 깊이**: 10개 프레임워크 통합으로 표면이 아닌 무의식 패턴까지 추출. 단일 이론의 맹점을 상호 보완
2. **GAP 보존 원칙**: 의식-무의식 간 모순을 해소하지 않고 보존 → 콘텐츠 진정성의 구조적 원천
3. **context:fork QA 격리**: 생성-평가 편향을 시스템 수준에서 차단. 단순 프롬프트 체이닝을 넘어선 아키텍처 결정
4. **Write-then-Read 검증**: AI 환각(hallucination) 방지의 구조적 해법
5. **이식성**: `/export`로 페르소나를 CLAUDE.md/AGENTS.md로 변환. 특정 도구 종속 탈피
6. **데이터 투명성**: 상태가 모두 PLOON Markdown 파일로 남아 감사/재현/회귀 확인 용이
7. **훅 기반 가드레일**: SessionStart/PreToolUse/PostToolUse가 런타임 레벨에서 데이터 보호와 출력 품질 강제

### 트레이드오프

1. **파일 기반 동시성 한계**: 다중 세션 동시 수정 시 충돌 관리가 필요
2. **규칙 의존성**: 에이전트가 스펙을 준수한다는 가정이 강함. 훅 환경 변수(`TOOL_NAME`, `FILE_PATH`, `TOOL_OUTPUT`)가 호스트 런타임에 의존
3. **도메인 편향**: 현재 설계는 콘텐츠 파이프라인에 최적화. 범용 업무에는 추가 추상화 필요
4. **실시간 외부 데이터**: trend 단계 품질은 외부 검색 가용성에 영향받음 (다만 즉시 폴백 규칙 존재)
5. **Codex 동기화 수동**: `skills/`와 `.agents/skills/` 간 수동 동기화 필요. 드리프트 위험
6. **대시보드 QA 점수**: 결정론적 해시 기반 점수이며 실제 AI 추론 결과가 아님 (프레젠테이션 데모용)

---

## 10. 결론

Polysona는 "잘 대답하는 단일 에이전트"보다, **사용자 정체성 데이터를 중심으로 멀티에이전트 워크플로우를 운영하는 하네스**에 가깝습니다.

핵심 가치는 세 가지로 압축됩니다:

1. **심리학적 깊이**: 10개 프레임워크 × 5개 에고 레이어 × GAP 보존으로 표면이 아닌 심층 페르소나 추출
2. **이식성**: Codex/Claude를 넘나드는 persona 실행. `/export`로 어떤 AI 에이전트에도 적용
3. **검증 가능성**: Write-then-Read, context:fork, PLOON으로 결과물과 상태를 파일로 남기는 운영 모델

프로덕션 관점에서는 향후 `content/*`와 `personas/*`의 스키마 진화/마이그레이션 전략, 동시성 제어, SaaS 연동(MCP, v1.6 예정) 단계가 핵심 확장 지점입니다.

---

## 참고 링크

- [Polysona Repository](https://github.com/LilMGenius/polysona)
- [README](https://github.com/LilMGenius/polysona/blob/main/README.md)
- [README (Korean)](https://github.com/LilMGenius/polysona/blob/main/README.ko.md)
- [CLAUDE.md](https://github.com/LilMGenius/polysona/blob/main/CLAUDE.md)
- [AGENTS.md](https://github.com/LilMGenius/polysona/blob/main/AGENTS.md)
- [Codex Agent Map](https://github.com/LilMGenius/polysona/blob/main/agents/openai.yaml)
- [Agents Directory](https://github.com/LilMGenius/polysona/tree/main/agents)
- [Skills Directory](https://github.com/LilMGenius/polysona/tree/main/skills)
- [Hooks Configuration](https://github.com/LilMGenius/polysona/blob/main/hooks/hooks.json)
- [Server Entry](https://github.com/LilMGenius/polysona/blob/main/server/index.ts)
- [API Routes](https://github.com/LilMGenius/polysona/blob/main/server/routes/api.ts)
- [PLOON Parser](https://github.com/LilMGenius/polysona/blob/main/server/lib/ploon.ts)
- [CHANGELOG](https://github.com/LilMGenius/polysona/blob/main/CHANGELOG.md)
