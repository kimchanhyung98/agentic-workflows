# Polysona 종합 리서치 보고서

> 작성일: 2026-04-03
> 대상: https://github.com/LilMGenius/polysona

---

## 1. 프로젝트 개요

### 1.1 기본 정보

| 항목 | 내용 |
|---|---|
| 이름 | Polysona (Polygonal Persona) |
| 태그라인 | "Build and run multiple personas across any AI agent." |
| 설명 | 메타인지 기반 다중 페르소나 추출 및 오케스트레이션 시스템 |
| 저장소 | https://github.com/LilMGenius/polysona |
| 버전 | v1.3.0 |
| 라이선스 | MIT |
| 생성일 | 2026-03-29 |
| 스타 | 30 |
| 포크 | 7 |
| 기여자 | 1명 (LilMGenius, 45 커밋) |
| 주요 언어 | HTML (61.6%), TypeScript (36.2%), Python, Shell, JavaScript |
| 기술 스택 | Bun, Hono, React 19, Vite 7, Tailwind CSS 4 |

### 1.2 창작자 정보

| 항목 | 내용 |
|---|---|
| GitHub | LilMGenius |
| 소속 | CEO/CAIO @ defytheodd |
| 바이오 | "The positive energies of the entire multiverse're concentrated here." |
| 공개 저장소 | 4개 |
| 팔로워 | 27명 |
| 주요 프로젝트 | polysona, win-hooks (20 stars), oh-my-opencode |
| 발표 이력 | 랄프톤 서울 (2026-03-29) 최종 발표 |

### 1.3 핵심 가치 제안

Polysona의 핵심 메시지는 README 첫 줄에 집약되어 있다:

> "gstack은 개리 탄(Garry Tan)의 뇌를 줍니다. **polysona는 당신의 뇌를 넣습니다.**"

기존 AI 에이전트 도구들이 템플릿 기반의 범용 응답을 제공하는 반면, polysona는 사용자 개인의 심리적 구조를 추출하여 AI 에이전트에 주입하는 "페르소나 레이어"를 구축한다.

---

## 2. 아키텍처 및 기술 분석

### 2.1 5-에이전트 파이프라인

Polysona는 콘텐츠 생성을 위한 5단계 에이전트 파이프라인을 구현한다:

| 순서 | 에이전트 | 역할 | 명령어 |
|---|---|---|---|
| 1 | **Profiler** | 10가지 심리학 프레임워크 기반 심층 인터뷰 | `$interview` / `/interview` |
| 2 | **Trendsetter** | 도메인 트렌드 탐지 및 페르소나 적합도 필터링 | `$trend` / `/trend` |
| 3 | **Content-Writer** | 페르소나 조건부 플랫폼별 콘텐츠 생성 (3개 변형) | `$content` / `/content` |
| 4 | **Virtual-Follower** | 가상 팔로워 QA 시뮬레이션 (TOP 5 추천) | `$qa` / `/qa` |
| 5 | **Admin** | 게시, 스케줄링, 성과 추적, 피드백 루프 | `$publish` / `/publish` |

추가 유틸리티: `$introduce` (페르소나 세션 주입), `$status` (상태 확인), `$export` (다른 워크스페이스로 내보내기)

### 2.2 PLOON 데이터 포맷

Polysona는 자체 데이터 포맷인 PLOON(Polysona Lightweight Object-Oriented Notation으로 추정)을 사용한다. 웹에서 별도 문서화는 발견되지 않으며, 프로젝트 내부 전용 포맷으로 보인다.

**형식**: `[table#N](col1,col2,...)` + 파이프 구분 행

**예시**:
```
[table#1](layer,value,source)
unconscious-self|빠른 실행과 반복을 통해 의미를 만드는 사람|McAdams Life Story
conscious-ideal|단순하고 명확한 것을 추구하는 미니멀리스트|Laddering
```

이 포맷은 마크다운 파일 내에서 기계 판독 가능하면서도 사람이 읽을 수 있는 구조화된 데이터를 표현하기 위해 설계되었다. Git을 데이터베이스 및 이력 원장으로 사용하는 설계 철학과 일치한다.

### 2.3 페르소나 데이터 구조

각 페르소나는 `personas/{id}/` 디렉토리 아래 3개 파일로 구성된다:

| 파일 | 역할 | 주요 섹션 |
|---|---|---|
| **persona.md** | 핵심 정체성 | core (자아 레이어), decide (의사결정 방식), energy (에너지원), blind (사각지대), interview-log |
| **nuance.md** | 표현 방식 | voice (문체/레지스터), platform (플랫폼별 톤), phrasing (선호/기피 표현) |
| **accounts.md** | 관계/벤치마크 | rolemodel (롤모델 계정), virtual (가상 팔로워 프로필) |

### 2.4 5-자아 레이어 모델 (Ego Layers)

Polysona의 고유 모델로, 사용자의 정체성을 5개 층으로 분해한다:

| 레이어 | 설명 | 출처 프레임워크 | 데이터 대상 |
|---|---|---|---|
| 1. others-see-me | 타인이 보는 나 | Johari Window, 五倫 | persona.md blind |
| 2. want-to-be-seen | 보여지고 싶은 나 | Goffman front stage | nuance.md voice |
| 3. conscious-ideal | 의식적 이상 | 직접 입력 | accounts.md ideal |
| 4. rolemodel | 구체적 벤치마크 | 계정/인물 분석 | accounts.md rolemodel |
| 5. unconscious-self | 무의식적 자아 | McAdams, Laddering, IFS, Zen Koan | persona.md core |

**GAP Discovery Protocol**: 이 5개 레이어 사이의 모순을 탐지하고 명시적으로 기록한다.
- 예: `~2026-03-29: GAP: conscious-ideal(minimalism) vs unconscious-self(complexity accumulation under pressure)`

### 2.5 멀티 플랫폼 지원

Polysona는 두 가지 AI 에이전트 플랫폼을 동시에 지원한다:

| 플랫폼 | 통합 방식 | 파일 |
|---|---|---|
| **OpenAI Codex** (primary) | AGENTS.md 자동 인식 + `.agents/skills` 자동 탐지 | `AGENTS.md`, `agents/openai.yaml` |
| **Claude Code** | 플러그인 마켓플레이스 + hooks | `.claude-plugin/marketplace.json`, `hooks/hooks.json` |

목표 콘텐츠 플랫폼 (MVP 5개): X, Threads, LinkedIn, 네이버 블로그, 브런치

### 2.6 대시보드

로컬 퍼스트 풀스택 대시보드를 제공한다:
- **서버**: Hono (Bun 런타임)
- **클라이언트**: React 19 + Tailwind CSS 4
- **빌드**: Vite 7
- **API**: `GET /api/personas`, `GET /api/status`
- **디자인**: 딥 틸(deep teal) + 인디고 팔레트, Pretendard 폰트

---

## 3. 심리학 프레임워크 심층 분석

Polysona의 가장 차별화된 핵심은 10가지 심리학 프레임워크를 체계적으로 결합한 인터뷰 엔진이다. 이는 서양 심층(6), 서양 보충(2), 동양 성찰(2)로 분류된다.

### 3.1 서양 심층 프레임워크 (Western Depth) - 6개

#### (1) McAdams Life Story (서사 정체성)
- **출처**: Dan McAdams, Northwestern University (1993)
- **목적**: 삶의 서사 구조 추출 - 챕터, 전환점, 의미 부여 패턴
- **핵심 질문**: "당신의 인생을 5-7개 챕터로 나누면?" / "가장 높은 점, 낮은 점, 전환점은?"
- **AI 적용 연구**: 최근 LLM 기반 접근이 생애 내러티브에서 FFM 성격 특성을 예측하는 데 정량적 엄밀성을 달성함 (arxiv.org/html/2506.19258v1)
- **출력 대상**: `persona.md core`

#### (2) Laddering (+MI+ACT) (가치 위계)
- **출처**: 1960년대 임상심리학에서 최초 도입
- **목적**: 표면 선호에서 종말 가치(terminal value)까지의 가치 계층 추출
- **핵심 원리**: Means-End Theory - 속성(A) -> 결과(C) -> 가치(V) 체인
- **Polysona 적용**: MI(동기 면담)과 ACT(수용전념치료)를 결합하여 방어적 반응을 줄이면서 심층 가치를 추출
- **출력 대상**: `persona.md decide`

#### (3) Clean Language (은유 경관)
- **출처**: David Grove, 1980년대
- **목적**: 무의식적 언어 구조와 자기 생성 상징 추출
- **핵심 원칙**: 참가자의 은유를 인터뷰어의 은유로 대체하지 않음 (어휘 오염 최소화)
- **AI 적용**: AI가 중립적 Clean Language 원칙을 유지하면서 대화 패턴 추적, 반복 은유 강조, 질문 제안 등에 활용 가능
- **출력 대상**: `nuance.md voice`

#### (4) Johari Window (사각지대 탐지)
- **출처**: Joseph Luft & Harry Ingham, 1955 (UCLA)
- **4분면**: Open Area (공개), Blind Area (사각), Hidden Area (숨김), Unknown Area (미지)
- **목적**: 자기 이미지와 타인 관찰 사이의 불일치 탐지
- **출력 대상**: `persona.md blind (johari)`

#### (5) IFS - Internal Family Systems (내면 파트)
- **목적**: 내면 파트(보호자/추방자/소방관)의 보호 논리와 촉발 상태 전이 추출
- **AI 적용**: IFS Buddy, Seekr, Sentur 등 다수의 AI 기반 IFS 도구가 이미 존재. AI가 치료사나 워크시트가 하는 스캐폴딩과 안내를 수행하여 내담자가 더 깊이 들어갈 수 있게 함
- **출력 대상**: `persona.md blind (defense)`

#### (6) Repertory Grid (개인 구성 체계)
- **출처**: George Kelly, 1955
- **목적**: 개인의 양극 판단 차원(bipolar constructs)과 의사결정 휴리스틱 추출
- **특징**: 이론적 범주에 분류하는 것이 아니라 개인의 고유한 구성 과정을 탐색하는 구성주의적 평가
- **출력 대상**: `persona.md decide`

### 3.2 서양 보충 프레임워크 (Western Supplement) - 2개

#### (7) Object Relations (대상 관계)
- **목적**: 초기 관계 템플릿, 전이 반향, 현재 팀/파트너에서 반복되는 애착 스크립트 추출
- **출력 대상**: `persona.md core (relationship origin)`

#### (8) Projective Technique (투사 기법)
- **목적**: 모호성을 통한 무의식적 반응, 방어 스타일, 리허설된 자기 서술을 우회하는 상징적 주제 추출
- **출력 대상**: `persona.md blind (defense)`

### 3.3 동양 성찰 프레임워크 (Eastern Reflection) - 2개

#### (9) Zen Koan (선불교 화두)
- **목적**: 전개념적(pre-conceptual) 반응 패턴, 모순 내성, 역설을 통한 방어 우회
- **대표 질문**: "오늘 보호할 정체성이 없다면, 어떤 결정이 먼저 바뀌나요?" / "성공과 실패가 사라지면, 무엇이 할 만한 가치로 남나요?"
- **출력 대상**: `persona.md core (intuitive response)`

#### (10) 五倫+陰陽 (오륜+음양)
- **목적**: 핵심 역할 쌍(mentor-peer-junior-family)에 걸친 관계적 자기 위치, 극성의 과용과 그림자 보상 추출
- **대표 질문**: "어떤 덕목을 과용해서 부채가 되나요?" / "조화와 진실이 충돌할 때 무엇을 먼저 보호하나요?"
- **출력 대상**: `persona.md core (relational self)`

### 3.4 10가지 인터뷰 설계 원칙

**추출 원칙 (HOW)**:
1. 은유 선행 (Metaphor-first)
2. 역설 배치 (Paradox-placement)
3. 깊이 나선 (Depth-spiral) - 점진적 심화
4. 대극 탐색 (Polarity-exploration) - 모든 강점에 대해 비용/그림자 탐색
5. 관계 거울 (Relationship-mirror) - 자기 보고 편향 감소

**구조 원칙 (WHAT)**:
6. 서사 우선 (Narrative-first)
7. 파트 분리 (Part-separation)
8. 격자 구축 (Grid-building)

**안전 원칙 (GUARD)**:
9. 비유도 원칙 (Non-leading) - 선호하는 결론 유도 금지
10. 축적 원칙 (Accumulation) - 반복 인터뷰를 통한 점진적 축적

### 3.5 인터뷰 흐름

| 단계 | 시간 | 내용 |
|---|---|---|
| Warm-up | 10분 | 라포 형성, McAdams-lite 개방형 서사 |
| Deep-dive | 30분 | 프레임워크 순환 적용 (McAdams -> Laddering -> Clean Language -> Johari -> IFS -> Repertory Grid -> Object Relations -> Projective -> Zen Koan -> 五倫+陰陽) |
| Closure | 10분 | 인사이트 통합, GAP 식별, 다음 세션 목표 설정 |

---

## 4. 경쟁 환경 분석

### 4.1 직접 경쟁자: gstack (Garry Tan)

| 항목 | gstack | polysona |
|---|---|---|
| 제작자 | Garry Tan (YC CEO) | 이선민 (defytheodd CEO/CAIO) |
| GitHub 스타 | 10,000+ (48시간 내) | 30 |
| 접근법 | 역할 기반 개발 페르소나 (CEO, Eng Manager, QA 등) | 심리학 기반 개인 페르소나 추출 |
| 대상 도메인 | 소프트웨어 개발 | SNS 콘텐츠 생성 |
| 페르소나 원천 | Garry Tan의 경험/판단 체계 | 사용자 고유 심리 구조 |
| 플랫폼 | Claude Code 전용 | Codex + Claude Code |
| 핵심 차이 | "다른 사람의 뇌" | "당신의 뇌" |

출처: https://github.com/garrytan/gstack

### 4.2 유사 프로젝트 비교

#### (1) persona-agent (memenow)
- **기술**: AutoGen + MCP 통합 Python API 서버
- **접근**: REST API 기반 페르소나 에이전트 생성/관리
- **차이**: 범용 에이전트 프레임워크. 심리학 기반 추출 없음
- 출처: https://github.com/memenow/persona-agent

#### (2) Persona (JasperHG90)
- **기술**: 역할(Role)과 스킬(Skill)을 LLM 제공자/앱에서 분리하는 표준
- **접근**: `.persona` 디렉토리에 마크다운 기반 역할/스킬 저장
- **차이**: 포터빌리티에 집중하지만 심리학 추출은 없음. 인프라 레이어에 가까움
- 출처: https://github.com/JasperHG90/persona

#### (3) TinyTroupe (Microsoft)
- **기술**: GPT-4 기반 다중 에이전트 페르소나 시뮬레이션
- **접근**: TinyPerson 에이전트가 TinyWorld에서 상호작용
- **차이**: 비즈니스 인사이트/상상력 증강 목적. "실제 사용자의 페르소나"가 아닌 합성 페르소나 시뮬레이션
- 출처: https://github.com/microsoft/TinyTroupe

#### (4) Fleek persona-generator
- **기술**: 자연어 -> 구조화된 JSON 캐릭터 프로필 변환
- **접근**: Eliza 프레임워크의 캐릭터파일 생성
- **차이**: 자동 생성 중심. 심리학 인터뷰 기반 추출이 아닌 입력 기반 변환
- 출처: https://github.com/fleek-platform/persona-generator

#### (5) oh-my-openagent (omo)
- **기술**: OpenCode 기반 멀티 에이전트 엔지니어링 시스템
- **접근**: Sisyphus 오케스트레이터 + 11개 전문 에이전트
- **차이**: 소프트웨어 엔지니어링 특화. 페르소나보다는 태스크 오케스트레이션
- **관계**: polysona 제작자가 oh-my-opencode 포크도 관리 (연관 프로젝트)
- 출처: https://github.com/code-yeongyu/oh-my-openagent

### 4.3 학술 연구 맥락

#### Anthropic Persona Vectors (2025)
- LLM 활성화 공간에서 성격 특성을 제어하는 "페르소나 벡터" 발견
- 악의성, 아첨, 환각 성향 등의 특성을 모니터링/조정 가능
- Polysona와의 관계: 모델 내부 수준의 페르소나 제어 vs. Polysona는 프롬프트/컨텍스트 수준의 페르소나 주입
- 출처: https://www.anthropic.com/research/persona-vectors

#### NeurIPS 2025 PersonaLLM Workshop
- LLM 페르소나 모델링에 관한 첫 공식 워크숍
- 합성 페르소나의 한계, 페르소나 벡터, 성격 특성 조향(steering) 등 논의
- 출처: https://personallmworkshop.github.io/

#### Persona Selection Model (Anthropic, 2026)
- LLM이 사전훈련 중 다양한 캐릭터를 시뮬레이션하도록 학습한다는 이론
- 후속 훈련이 특정 "Assistant" 페르소나를 유도/정제
- 출처: https://alignment.anthropic.com/2026/psm/

### 4.4 한국 SNS 콘텐츠 자동화 시장

Polysona가 MVP 대상으로 삼는 한국 SNS 콘텐츠 시장의 주요 플레이어:

| 도구 | 특징 | 차이점 |
|---|---|---|
| **톡탁 (TokTak)** | URL 하나로 숏폼/카드뉴스/블로그 동시 생성 + 자동 배포 | 페르소나 없음, 상품 기반 콘텐츠 |
| **HYDRA** | AI 영상 자동화, 브랜드 IP 기반 숏폼 대량 생성 | 기업/브랜드 특화, 개인 페르소나 없음 |
| **Content Genie MCP** | 한국 콘텐츠 크리에이터용 MCP 서버 (17개 도구) | 도구 모음, 통합 파이프라인이 아님 |
| **Polysona** | 심리학 기반 페르소나 추출 + 멀티 플랫폼 콘텐츠 생성 | 유일하게 "사용자의 정체성"에서 출발 |

---

## 5. AI 에이전트 생태계 맥락

### 5.1 Claude Code 플러그인 생태계 (2026)

- Anthropic이 공식 마켓플레이스를 운영하며 커뮤니티 마켓플레이스도 확산 중
- 2026년 3월 기준 150개 이상 스킬이 등록됨
- 340개 플러그인 + 1,367개 에이전트 스킬 카탈로그 존재
- Polysona는 로컬 마켓플레이스 방식으로 Claude Code에 설치 가능
- 출처: https://code.claude.com/docs/en/discover-plugins

### 5.2 OpenAI Codex 에이전트 스킬 생태계 (2026)

- Agent Skills 사양이 Anthropic과 OpenAI가 공유하는 개방 표준으로 발전
- AGENTS.md 파일이 Codex의 행동 지침 역할
- Polysona는 Codex를 "primary" 통합 대상으로 지정하며 `AGENTS.md` 및 `.agents/skills` 구조를 완전 지원
- 출처: https://developers.openai.com/codex/skills

### 5.3 멀티 에이전트 오케스트레이션 트렌드

- 2026년까지 기업 AI 워크플로의 45% 이상이 에이전트 오케스트레이션 프레임워크 채택 예상
- 자율 AI 에이전트 시장은 2026년 85억 달러, 2030년 350억 달러 예상
- CrewAI, LangGraph 등이 역할 기반 멀티 에이전트 오케스트레이션을 주도
- Polysona는 "콘텐츠 생성"이라는 특정 도메인에 심리학 레이어를 추가한 것이 차별점

---

## 6. 발표 및 데모 자료

### 6.1 랄프톤 서울 발표 (2026-03-29)

Polysona는 랄프톤(Ralphthon) 서울에서 최종 발표되었다.

**랄프톤이란?**
- "인간은 퇴근하고 AI가 코딩한다"는 콘셉트의 해커톤
- Team Attention(정구봉 대표) 주최, 서울/샌프란시스코 동시 개최
- 참가자가 아이디어/설계만 제시하면 AI 에이전트가 실제 코딩 수행
- 스폰서: Kakao Ventures, OpenAI, Naver D2SF, Hangang Partners, Base Ventures
- 출처: https://www.eomag.io/article/ralphthon

**발표 구성 (5슬라이드)**:

| 슬라이드 | 제목 | 핵심 메시지 |
|---|---|---|
| 1 | Cover | Polysona: Polygon + Persona |
| 2 | Problem | "에이전트는 일을 하지만 '나'를 모른다" - 기존 에이전트 스택은 화자의 심리, 말투, 가면, 관계 맥락을 재현하지 못함 |
| 3 | Why Now | 페르소나 맞춤 콘텐츠가 실제 반응(팔로워 50명 증가)을 만들고, AX 컨설팅 고객사가 AI 인플루언서 운영 자동화를 직접 원함 |
| 4 | Solution | 심리학적 Agent Harness 기반 멀티 페르소나 운영 시스템 |
| 5 | Ralph Setup | 멀티 에이전트 운영력 - oh-my-openagent, Codex, Claude Code 활용 |

**타깃 고객**: 여러 플랫폼에서 AI 인플루언서 계정을 동시에 운영하려는 개인/에이전시

### 6.2 데모 덱 자산

- `decks/` 디렉토리에 5개 HTML 슬라이드 + PDF 버전 포함
- 디자인: 어두운 배경(#06101b) + 틸/인디고 액센트 + Pretendard 폰트
- `viewer.html`로 로컬 슬라이드 뷰어 제공

---

## 7. 로드맵 분석

### v1: 한국어 핵심 + 제품 품질 (현재)

| 버전 | 목표 | 상태 |
|---|---|---|
| v1.0 | 텍스트 콘텐츠 생성 (X, Threads, LinkedIn, 네이버 블로그, 브런치) | 완료 |
| v1.1 | 페르소나 -> CLAUDE.md/AGENTS.md 추출 + 멀티 CLI 마켓플레이스 | 완료 |
| v1.2 | 로컬 퍼스트 풀스택 대시보드 기반 | 완료 |
| v1.3 | 대시보드 확장 + 파이프라인 가시화 + 제품 polish | 완료 (현재) |
| v1.4 | 트렌드 지식 적재 루프 + 품질 검증 강화 | 예정 |
| v1.5 | 풀버전 대시보드 + 데모 polish | 예정 |
| v1.6 | 외부 SaaS 연동 (MCP 지원) | 예정 |

### v2: 한국어 미디어 확장
- v2.0: 카드뉴스 (이미지 + 텍스트)
- v2.1: 숏폼 영상 스크립트 (Reels, Shorts, TikTok)
- v2.2: 롱폼 영상 스크립트 (YouTube, Podcast)

### v3: 글로벌 확장
- v3.0-3.3: 영어 텍스트 -> 카드뉴스 -> 숏폼 -> 롱폼

---

## 8. Polysona의 고유성 분석

### 8.1 기존 접근과의 핵심 차별점

1. **심리학 기반 추출 (Psychology-driven Extraction)**
   - 기존 도구: 사용자가 직접 페르소나를 정의하거나 자동 생성
   - Polysona: 10가지 심리학 프레임워크를 사용한 체계적 인터뷰로 의식/무의식 패턴 추출
   - 이는 "페르소나 생성"이 아닌 "페르소나 발굴"에 가까움

2. **GAP Discovery (간극 발견)**
   - 의식과 무의식, 자기 인식과 타인 인식 사이의 모순을 명시적으로 탐지
   - 이 모순 자체가 콘텐츠의 깊이와 진정성을 만드는 원천

3. **동서양 프레임워크 통합**
   - Carl Jung, IFS, Repertory Grid 등 서양 심리학과 선불교 화두, 五倫+陰陽 등 동양 철학을 결합
   - AI 페르소나 시스템에서 동양 철학을 명시적으로 통합한 사례는 매우 드묾

4. **에이전트 이식성 (Agent Portability)**
   - 추출된 페르소나가 특정 도구에 종속되지 않음
   - Codex AGENTS.md, Claude Code CLAUDE.md 등으로 내보내기 가능
   - JasperHG90의 Persona 프로젝트와 유사한 철학이나, 심리학 추출 엔진이 결합된 점이 다름

5. **Virtual Follower QA 시스템**
   - 가상 팔로워 프로필(20대 여성 직장인, 30대 남성 개발자 등)이 콘텐츠를 평가
   - 롤모델 갭 분석을 통한 품질 보증
   - 콘텐츠 생성 파이프라인에 내장된 QA는 비교적 독특한 접근

6. **PLOON 포맷**
   - 마크다운 내 구조화 데이터의 자체 포맷
   - Git을 데이터베이스로 사용하는 설계 - 외부 DB 의존성 제거
   - "코드로서의 페르소나(Persona-as-Code)" 패러다임

### 8.2 리스크 및 한계

1. **초기 단계**: 단일 기여자(45 커밋), 30 스타. 아직 커뮤니티 검증 초기
2. **npm/PyPI 패키지 없음**: 패키지 매니저를 통한 배포 미구현 (2026-04-03 기준)
3. **인터뷰 의존성**: 심리학 인터뷰 품질이 전체 파이프라인 품질을 좌우
4. **한국어 우선**: MVP가 한국어 콘텐츠에 집중되어 글로벌 확장까지 시간 필요
5. **gstack 대비 인지도 격차**: gstack의 10,000+ 스타 vs polysona의 30 스타

---

## 9. 결론

Polysona는 AI 에이전트 생태계에서 독특한 위치를 점하고 있다. "페르소나 레이어"라는 콘셉트를 통해 AI 에이전트에 사용자 고유의 심리적 구조를 주입하는 접근은 기존의 템플릿 기반 도구(gstack), 합성 페르소나 시뮬레이션(TinyTroupe), 범용 페르소나 관리(persona-agent, JasperHG90/persona)와 명확히 구분된다.

특히 10가지 심리학 프레임워크의 체계적 결합, 5-자아 레이어 모델, GAP Discovery Protocol은 학술 연구와 실용 도구 사이의 간극을 메우는 시도로 평가할 수 있다. 랄프톤 서울에서의 발표와 실제 고객 신호(AX 컨설팅 고객사의 AI 인플루언서 운영 자동화 수요)는 시장 적합성의 초기 신호를 보여준다.

향후 관전 포인트는 (1) 커뮤니티 성장과 기여자 확보, (2) 인터뷰 엔진의 품질 검증, (3) v2-v3로의 미디어/글로벌 확장 실행력이 될 것이다.

---

## Sources

### 프로젝트 직접 자료
- [Polysona GitHub Repository](https://github.com/LilMGenius/polysona)
- [LilMGenius GitHub Profile](https://github.com/LilMGenius)

### 경쟁/유사 프로젝트
- [gstack - Garry Tan's Claude Code setup](https://github.com/garrytan/gstack)
- [gstack is not a dev tool. It's Garry Tan's brain on AI (Medium)](https://medium.com/@luongnv89/gstack-is-not-a-dev-tool-its-garry-tan-s-brain-on-ai-b813e09b32c7)
- [GStack Tutorial: Garry Tan's Claude Code Workflow (SitePoint)](https://www.sitepoint.com/gstack-garry-tan-claude-code/)
- [persona-agent (memenow/AutoGen+MCP)](https://github.com/memenow/persona-agent)
- [Persona toolkit (JasperHG90)](https://github.com/JasperHG90/persona)
- [Microsoft TinyTroupe](https://github.com/microsoft/TinyTroupe)
- [Fleek persona-generator](https://github.com/fleek-platform/persona-generator)
- [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)

### 심리학 프레임워크
- [McAdams Life Story Interview II](https://cpb-us-e1.wpmucdn.com/sites.northwestern.edu/dist/4/3901/files/2020/11/The-Life-Story-Interview-II-2007.pdf)
- [Personality Prediction from Life Stories using Language Models](https://arxiv.org/html/2506.19258v1)
- [Clean Language and AI (Clean Coaching)](https://cleancoaching.com/the-power-of-clean-language-and-ai-shaping-meaningful-conversations/)
- [Johari Window (The Decision Lab)](https://thedecisionlab.com/reference-guide/psychology/johari-window)
- [IFS Buddy - AI IFS Chatbot](https://www.ifsbuddy.chat/)
- [PARTS & SELF - Expanding IFS Through AI](https://partsandself.org/expanding-internal-family-systems-through-ai-limitless-possibilities-for-integration/)
- [Repertory Grid (Wikipedia)](https://en.wikipedia.org/wiki/Repertory_grid)
- [Laddering Interview Technique (UXmatters)](https://www.uxmatters.com/mt/archives/2009/07/laddering-a-research-interview-technique-for-uncovering-core-values.php)
- [ShadowWork.io - AI-Guided Shadow Work](https://shadowwork.io/)

### AI 페르소나 연구
- [Anthropic Persona Vectors](https://www.anthropic.com/research/persona-vectors)
- [Anthropic Persona Selection Model](https://alignment.anthropic.com/2026/psm/)
- [NeurIPS 2025 PersonaLLM Workshop](https://personallmworkshop.github.io/)
- [Beyond Fixed Psychological Personas (arxiv)](https://arxiv.org/html/2601.15395)

### AI 에이전트 생태계
- [Claude Code Plugin Marketplace Docs](https://code.claude.com/docs/en/discover-plugins)
- [OpenAI Codex Agent Skills](https://developers.openai.com/codex/skills)
- [AGENTS.md Guide (OpenAI)](https://developers.openai.com/codex/guides/agents-md)
- [Claude Code Skills Marketplace (daymade)](https://github.com/daymade/claude-code-skills)
- [A Mental Model for Claude Code (Level Up Coding)](https://levelup.gitconnected.com/a-mental-model-for-claude-code-skills-subagents-and-plugins-3dea9924bf05)

### 한국 SNS 콘텐츠 자동화
- [톡탁(TokTak) AI EXPO KOREA 2026](https://www.aitimes.kr/news/articleView.html?idxno=38832)
- [Content Genie MCP](https://github.com/MUSE-CODE-SPACE/content-genie-mcp)

### 해커톤/이벤트
- [Ralphthon - Where You Find Out How (eomag)](https://www.eomag.io/article/ralphthon)
- [Korean AI Hackathon Ralphthon Expands to US (Seoul Economic Daily)](https://en.sedaily.com/finance/2026/03/24/korean-ai-hackathon-ralphthon-expands-to-us-as-naver-kakao)

### 멀티 에이전트 오케스트레이션
- [AI Agent Orchestration (IBM)](https://www.ibm.com/think/topics/ai-agent-orchestration)
- [AI Agent Orchestration (Deloitte)](https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/ai-agent-orchestration.html)
- [CrewAI - Multi-Agent Platform](https://crewai.com/)
