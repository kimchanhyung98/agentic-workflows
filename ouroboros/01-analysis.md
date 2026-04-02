# Ouroboros 설계/활용 사례 분석

## 1. 분석 범위

이 문서는 두 축을 함께 다룹니다.

1. **Ouroboros 분석**
   - AI agent 하네스 구조
   - 활용 사례 및 운영 방식
2. **Polysona 분석**
   - 코드/실행 플로우 구조
   - 멀티 에이전트 런타임 연동 방식

참조 저장소는 [LilMGenius/polysona](https://github.com/LilMGenius/polysona)입니다.

---

## 2. Ouroboros: AI Agent Harness 관점 분석

### 2.1 하네스의 핵심 역할

공개 README 기준 Ouroboros는 단일 챗봇이 아니라 다음을 묶은 실행 하네스입니다.

- 입력 채널(Desktop UI, Telegram)
- Supervisor(큐·워커·예산 관리)
- Agent Core(컨텍스트, LLM 호출, 도구 루프)
- Self-modification 파이프라인(코드 수정→리뷰→커밋/재시작)
- 지속 저장소(state/logs/memory/git history)

즉, **“작업 수행기 + 자기개선 런타임”**을 하나의 운영 단위로 통합한 형태입니다.

### 2.2 하네스 내부 레이어

README/아키텍처 설명에서 드러나는 레이어는 다음과 같습니다.

| 레이어 | 주요 책임 |
|---|---|
| Ingress | UI/메신저 입력 수신, 명령 파싱 |
| Supervisor | 작업 큐, 워커 생명주기, 예산/상태 추적 |
| Agent Core | 프롬프트/컨텍스트 구성, 라운드 기반 추론, 도구 선택 |
| Safety | 금지 경로/명령 차단, 안전 검토, 필요 시 되돌리기 |
| Memory | 대화/스크래치패드/반성 로그를 축적·압축 |
| Git Evolution | 변경사항을 커밋 단위로 역사화, 필요 시 원격 동기화 |

### 2.3 활용 사례(운영 시나리오)

공개 문서에서 확인되는 대표 활용은 다음입니다.

1. **자율 개선 루프**
   - `/evolve`, `/review`, `/bg` 같은 명령으로 자기 점검·개선 태스크를 지속 실행
2. **안전한 코드 수정 워크플로우**
   - 도구 실행 전/중/후 검증, 리뷰 게이트, 커밋 히스토리 유지
3. **멀티 모델 검토/폴백**
   - 주 모델 실패나 빈 응답 대응을 위해 폴백 체인·리뷰 모델 활용
4. **장기 운영 관찰**
   - 버전 이력, 이벤트 로그, 비용/예산 추적을 통해 운영지표 관리

### 2.4 강점과 제약

- 강점
  - 실행, 안전, 상태, 진화를 한 런타임으로 결합
  - 자기수정 결과를 git 단위로 추적 가능
  - 운영 명령 체계(`/status`, `/panic`, `/restart`, `/evolve`)가 명확
- 제약
  - 철학/헌법 기반 규칙이 강해 일반 목적 작업에는 과설계가 될 수 있음
  - 장기 루프 운영 시 비용·품질 드리프트 관리가 필수

---

## 3. Polysona: 코드 및 플로우 분석

### 3.1 프로젝트 성격

Polysona는 “에이전트를 하나 더 만드는 프레임워크”라기보다,
**개인 페르소나를 추출·구조화해 여러 에이전트 런타임에서 재사용하는 오케스트레이터**에 가깝습니다.

README/AGENTS.md 기준 핵심은 다음입니다.

- 5개 역할 에이전트(Profiler, Trendsetter, Content-Writer, Virtual-Follower, Admin)
- Setup(인터뷰/구조화) + Loop(트렌드→콘텐츠→QA→발행)
- Codex/Claude Code/OpenCode 등 다중 런타임 호환

### 3.2 코드 구조에서 확인되는 실행 흐름

수집한 파일 기준으로 확인되는 구현 포인트:

| 파일 | 확인 내용 |
|---|---|
| `package.json` | `codex:skills:sync`, `dev`, `build`, `preview` 스크립트 |
| `scripts/sync-codex-skills.mjs` | `skills/`를 `.agents/skills/`로 미러링하여 Codex 자동 발견 지원 |
| `.claude-plugin/marketplace.json` | 로컬 플러그인 마켓으로 `polysona` 설치 정의 |
| `hooks/hooks.json` | SessionStart/PreToolUse/PostToolUse 훅 등록 |
| `hooks/session-start.sh` | 활성 persona 요약 자동 로드 |
| `hooks/pre-tool-use.sh` | persona 파일 Write 전 경고(덮어쓰기 방지) |
| `hooks/post-tool-use.sh` | 장황/슬롭 출력 패턴 경고 |
| `server/index.ts` | Hono 기반 API+정적 UI 서빙, 빌드/개발 모드 분기 |

### 3.3 데이터 모델 특징

Polysona는 `personas/{id}/` 아래 Markdown 파일(`persona.md`, `nuance.md`, `accounts.md`)을 SSOT로 두고, 대화 명령으로 이를 갱신·주입하는
패턴을 사용합니다.

즉, DB 중심이 아니라 **파일 기반 페르소나 레이어**를 중심으로 런타임 간 이식성을 확보합니다.

### 3.4 운영 명령 체계

- 인터뷰/초기화: `$interview`, `$introduce`
- 생성 루프: `$trend`, `$content [platform]`, `$qa`, `$publish`
- 상태/이식: `$status`, `$export`

이 명령 체계는 Codex(`$`)와 Claude(` /`)에서 거의 동일한 의미를 유지하도록 설계되어 있습니다.

---

## 4. Ouroboros × Polysona 비교 시사점

| 관점 | Ouroboros | Polysona |
|---|---|---|
| 주 관심사 | 자기개선형 실행 하네스 | 페르소나 기반 콘텐츠 오케스트레이션 |
| 핵심 자산 | 코드/상태/진화 히스토리 | persona 데이터셋(`persona/nuance/accounts`) |
| 루프 구조 | 작업 처리 + 자기수정 + 리뷰 | 인터뷰 → 트렌드 → 작성 → QA → 발행 |
| 안전 장치 | 하드 규칙 + 안전검토 + 복구 | 훅 기반 가드(덮어쓰기/출력 품질 경고) |
| 이식 전략 | 런타임 자체를 패키징 | 여러 에이전트 런타임에 persona를 주입 |

실무적으로는 다음 조합이 가능합니다.

- **Ouroboros를 실행 하네스로 사용**하고,
- **Polysona를 상위 페르소나/콘텐츠 워크플로우 레이어로 연결**하는 2계층 구성

이 경우 실행 안정성(하네스)과 페르소나 정합성(오케스트레이션)을 분리해 운영할 수 있습니다.

---

## 5. 웹 검색 기반 추가 관찰

수집된 공개 자료 기준으로, `ouroboros` 명칭의 파생 프로젝트가 다수 존재하며(포크/변형 포함), 현재는 원류 Colab/Telegram 계열과 Desktop 계열로
문맥이 분화되어 있습니다. 따라서 분석/도입 시에는 다음을 명시하는 것이 안전합니다.

1. 대상 저장소(예: `joi-lab/ouroboros` vs `joi-lab/ouroboros-desktop`)
2. 실행 환경(Colab/Telegram vs Native Desktop)
3. 안전정책 및 리뷰 게이트의 강제 수준

---

## 6. 결론

- **Ouroboros**는 “자기개선 가능한 AI agent harness” 사례로, 실행/안전/메모리/진화를 일체화한 구조가 강점입니다.
- **Polysona**는 “페르소나를 에이전트 런타임 간 이식”하는 오케스트레이션 계층으로, 명령 체인과 파일 기반 데이터 모델이 강점입니다.
- 두 접근은 경쟁이라기보다 계층 분리가 가능하며, 하네스(운영 안정성) + 페르소나 레이어(콘텐츠 정합성) 조합이 실용적입니다.
