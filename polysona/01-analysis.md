# Polysona 설계 및 실행 플로우 분석

## 1. 프로젝트 개요

- 저장소: `LilMGenius/polysona`
- 목적: 다중 페르소나를 추출·운영해 AI 에이전트 전반(Codex/Claude/OpenCode)에서 재사용
- 현재 버전: `1.3.0` (`package.json`, `README`, `CHANGELOG`)
- 핵심 도메인: 인터뷰 기반 페르소나 추출 → 트렌드 탐색 → 플랫폼별 콘텐츠 생성 → QA 시뮬레이션 → 게시/추적

Polysona의 차별점은 "모델 자체 최적화"가 아니라 **사용자 정체성(페르소나)을 실행 가능한 데이터 계층으로 분리**했다는 점입니다.

---

## 2. AI Agent 하네스 구조 분석

## 2.1 Codex 하네스

- `AGENTS.md`: 시스템 철학, 금지 규칙(no speculation), 컨텍스트 로딩 프로토콜, 고정 사실(프레임워크 10개 등) 정의
- `agents/openai.yaml`: Codex 에이전트 카탈로그(profiler/trendsetter/content-writer/virtual-follower/admin)
- `skills/*/SKILL.md`: 명령 단위 실행 규약
- `scripts/sync-codex-skills.mjs`: `skills/`를 `.agents/skills`로 미러링해 Codex discovery 호환

핵심은 **명령(Skill)과 역할(Agent) 분리**입니다. 사용자는 `/trend` 같은 동작 단위로 호출하고, 내부적으로는 trendsetter가 책임집니다.

## 2.2 Claude 하네스

- `.claude-plugin/marketplace.json`: 플러그인 등록 메타데이터
- `hooks/hooks.json`: SessionStart/PreToolUse/PostToolUse 훅 체인 선언
- `hooks/session-start.sh`: active persona 프리로드 + 핵심 규칙 출력
- `hooks/pre-tool-use.sh`: persona 파일 Write 전 경고(덮어쓰기 방지)
- `hooks/post-tool-use.sh`: verbosity/slop 패턴 탐지

즉 Claude 경로는 plugin + hooks 조합으로 런타임 가드레일을 구현합니다.

## 2.3 공통 하네스 패턴

1. **SSOT 문서화**: 사실의 단일 소유 문서를 강제
2. **No-speculation 규칙**: 추측 기반 출력 금지
3. **저장 검증 강제**: 생성 결과를 파일로 저장 후 재읽기(Read-back) 확인
4. **Git-친화 운영**: 모든 상태를 Markdown으로 남겨 diff/이력 검증 가능

---

## 3. 5-에이전트 파이프라인 역할 분해

| 에이전트 | 입력 | 출력 | 저장 위치 |
|---|---|---|---|
| profiler | 인터뷰 대화 | 프레임워크별 로그 + GAP | `personas/{id}/persona.md` |
| trendsetter | persona/accounts 맥락 | 주제 랭킹 5개 | `content/trends/` |
| content-writer | 주제 + persona/nuance/accounts | 플랫폼별 Draft 3종 | `content/drafts/` |
| virtual-follower | 최신 draft + accounts | 팔로워 시뮬레이션 TOP5 | `content/qa/` |
| admin | 최종 draft | 게시용 최종본 + 추적 메타데이터 | `content/published/` |

각 에이전트 스펙(`agents/*.md`)은 "반드시 Write 후 Read로 확인" 규칙을 명시해, 실제 파일 저장 없는 성공 응답을 금지합니다.

---

## 4. 코드 관점의 실행 플로우

## 4.1 서버/대시보드 계층

- `server/index.ts`: Hono 엔트리, `/api` 라우팅, 개발/배포 정적 파일 분기
- `server/routes/api.ts`: persona/콘텐츠/QA 시뮬레이션/에이전트 상태 API 제공
- `client/src/pages/*`: Personas, PersonaDetail, ContentPipeline, VirtualFollower, AgentMonitor 등 시각화 화면

구조적으로 Polysona는 "AI 실행 엔진" 자체보다 **데이터/상태 관측(operability)**에 많은 비중을 둡니다.

## 4.2 PLOON 파서(`server/lib/ploon.ts`)

`parsePloon()`은 Markdown 기반 PLOON 포맷을 JSON 유사 객체로 변환합니다.

- `[table#N](...)` 헤더를 표 구조로 파싱
- `~YYYY-MM-DD:` 형식 로그를 entries로 파싱
- 섹션(`##`) 단위 스코프 유지

즉, 사람이 읽기 쉬운 Markdown과 기계 파싱 가능성을 동시에 확보했습니다.

## 4.3 상태 집계 API 특징

- `/api/status`: personas + drafts + published 수량, lastActivity 집계
- `/api/agents/status`: 에이전트/스킬 파일 존재성 점검
- `/api/personas/:id/qa-simulation`: follower archetype 20종 기반 점수 시뮬레이션

실시간 LLM 호출 없이도 로컬 상태를 기반으로 대시보드를 동작시키는 설계입니다.

---

## 5. 웹 리서치 기반 추가 정보

공개 저장소 및 메타데이터 기준 추가로 확인되는 점:

1. **라이선스/공개 상태**: MIT, Public repository
2. **기술 스택**: Bun + Hono + React 19 + Vite + TypeScript
3. **릴리즈 운영 방식**: GitHub Release 태그보다 `CHANGELOG.md` 중심 버전 공지
4. **최근 방향성(v1.3)**: 대시보드 확장, 파이프라인 가시화, persisted storage 강화
5. **확장 로드맵**: 한국어 미디어 확장(v2) 및 영어권 확장(v3) 계획

---

## 6. 활용 사례 정리 (실무 적용 관점)

## 6.1 퍼스널 브랜딩/콘텐츠 운영

- 인터뷰로 페르소나를 추출하고 플랫폼별 글 생성 → QA → 게시까지 자동화
- 특히 1인 창작자/전문가 계정 운영에 적합

## 6.2 팀 단위 에이전트 운영 가드레일

- no-speculation, read-before-write, SSOT 같은 규약을 명시 문서로 강제
- 멀티 에이전트 품질 흔들림을 줄이는 데 유용

## 6.3 에이전트 이식성 실험

- 동일 persona 자산을 Codex/Claude/OpenCode에 공유해 결과 편차 비교 가능
- "모델 교체 시 정체성 유지" 실험용 베이스로 적합

---

## 7. 강점과 트레이드오프

## 강점

1. **하네스 명확성**: Host별 통합 지점(AGENTS/openai.yaml/plugin/hooks)이 분리돼 유지보수가 쉽습니다.
2. **데이터 투명성**: 상태가 모두 파일로 남아 감사/재현/회귀 확인이 쉽습니다.
3. **실행 안전장치**: Write→Read 검증, pre/post hook 경고, no-speculation 규칙이 견고합니다.
4. **운영 가시성**: 대시보드/API가 파이프라인 상태를 즉시 보여줍니다.

## 트레이드오프

1. **파일 기반 동시성 한계**: 다중 세션 동시 수정 시 충돌 관리가 필요합니다.
2. **규칙 의존성**: 에이전트가 스펙을 준수한다는 가정이 강합니다(강제 실행 엔진은 제한적).
3. **도메인 편향**: 현재 설계는 콘텐츠 파이프라인에 최적화되어 범용 업무에는 추가 추상화가 필요합니다.
4. **실시간 외부 데이터 의존**: trend 단계 품질은 외부 검색 가용성 영향이 큽니다(다만 fallback 규칙 존재).

---

## 8. 결론

Polysona는 "잘 대답하는 단일 에이전트"보다, **사용자 정체성 데이터를 중심으로 멀티에이전트 워크플로우를 운영하는 하네스**에 가깝습니다.

특히 다음 두 점이 실전 가치가 큽니다.

- **이식성**: Codex/Claude를 넘나드는 persona 실행
- **검증 가능성**: 결과물과 상태를 파일로 남기는 운영 모델

프로덕션 관점에서는 향후 `content/*`와 `personas/*`의 스키마 진화/마이그레이션 전략, 동시성 제어, SaaS 연동(MCP) 단계가 핵심 확장 지점입니다.

---

## 참고 링크

- [Polysona Repository](https://github.com/LilMGenius/polysona)
- [README](https://github.com/LilMGenius/polysona/blob/main/README.md)
- [README (Korean)](https://github.com/LilMGenius/polysona/blob/main/README.ko.md)
- [AGENTS.md](https://github.com/LilMGenius/polysona/blob/main/AGENTS.md)
- [Codex Agent Map](https://github.com/LilMGenius/polysona/blob/main/agents/openai.yaml)
- [Agents Directory](https://github.com/LilMGenius/polysona/tree/main/agents)
- [Skills Directory](https://github.com/LilMGenius/polysona/tree/main/skills)
- [Hooks Configuration](https://github.com/LilMGenius/polysona/blob/main/hooks/hooks.json)
- [Server Entry](https://github.com/LilMGenius/polysona/blob/main/server/index.ts)
- [API Routes](https://github.com/LilMGenius/polysona/blob/main/server/routes/api.ts)
- [PLOON Parser](https://github.com/LilMGenius/polysona/blob/main/server/lib/ploon.ts)
- [CHANGELOG](https://github.com/LilMGenius/polysona/blob/main/CHANGELOG.md)
