# Oh My OpenAgent 설계 및 실행 플로우 분석

## 1. 프로젝트 개요

- 저장소: `code-yeongyu/oh-my-openagent`
- 패키지명: `oh-my-opencode` (`package.json`)
- 런타임: Bun + TypeScript 기반 OpenCode 플러그인
- 목표: 단일 에이전트/단일 모델 호출을 넘어서, **멀티 에이전트 + 멀티 모델 오케스트레이션** 제공

공식 문서에서는 이를 "계획과 실행의 분리(Planning/Execution Separation)"로 설명하며, Prometheus(계획)와 Atlas(실행)를 중심으로 구성합니다.

---

## 2. 핵심 설계 포인트

### 2.1 초기화 파이프라인 분리

`src/index.ts` 기준 플러그인 초기화는 아래 순서로 분리됩니다.

1. `loadPluginConfig` - 유저/프로젝트 설정 로드 및 병합
2. `createManagers` - Background/Tmux/Skill MCP/Config 핸들러 생성
3. `createTools` - 스킬 컨텍스트/카테고리 기반 툴 레지스트리 구성
4. `createHooks` - 코어/연속성/스킬 훅 결합
5. `createPluginInterface` - OpenCode 이벤트 인터페이스에 최종 등록

이 구조는 런타임 문제를 추적할 때 "설정/도구/훅/인터페이스" 경계를 명확히 해줍니다.

### 2.2 카테고리 중심 모델 라우팅

문서(`docs/guide/overview.md`, `docs/guide/orchestration.md`)와 구현(`src/plugin/tool-registry.ts`) 모두 모델 이름 직접 지정보다 **카테고리 기반 위임**을 강조합니다.

- 예: `visual-engineering`, `ultrabrain`, `quick`, `deep`
- 효과: 태스크 성격 기반 자동 모델 매핑, 설정 복잡도 감소

### 2.3 훅 체인 중심 런타임 제어

`chat.message`와 `event` 핸들러에서 다수 훅이 체인으로 동작합니다.

- 입력 전처리: 키워드 감지, auto-slash command, think mode
- 연속 실행: todo continuation, stop guard
- 복원력: runtime/model fallback, session recovery, compaction context

특히 `event` 핸들러는 세션 상태 변화와 모델 오류를 감지해 fallback 재시도까지 연결합니다.

---

## 3. 실행 플로우 (요청 1건 기준)

### 3.1 입력 수신

사용자 메시지는 `chat.message` 핸들러(`src/plugin/chat-message.ts`)로 진입합니다.

- 세션 에이전트/모델 상태 기록
- 키워드 기반 동작(예: `ultrawork`, loop 템플릿) 처리
- 훅 체인 적용 후 최종 메시지/모델 확정

### 3.2 도구/에이전트 실행

`tool-registry`(`src/plugin/tool-registry.ts`)에서 구성된 툴이 사용됩니다.

- 기본 LSP/검색/AST 도구
- `task` 위임 도구(백그라운드 에이전트 연동)
- skill/MCP 관련 도구
- 옵션 기반 hashline edit, task-system 도구

즉, 실행 시점에는 "고정 툴셋"이 아니라 **설정 기반 동적 툴셋**이 제공됩니다.

### 3.3 이벤트 관찰 및 복구

`event` 핸들러(`src/plugin/event.ts`)가 세션/메시지/오류 이벤트를 수신합니다.

- 세션 생성/삭제 상태 추적
- 훅 디스패치(알림/강제 진행/atlas 연동 등)
- 모델 오류 감지 시 fallback chain 계산 및 continue 재시도

이로 인해 장시간 작업(장기 루프, 백그라운드 병렬 실행)에서 복원력이 높아집니다.

---

## 4. 강점과 트레이드오프

### 강점

1. **모듈 경계 명확성**: 초기화 단계 분리로 유지보수/확장 용이
2. **오케스트레이션 친화성**: 계획/실행 분리와 task 위임 체계
3. **운영 복원력**: 세션 이벤트/폴백/연속성 훅이 촘촘함
4. **실무 도구 통합**: LSP, AST-Grep, background session, tmux 결합

### 트레이드오프

1. **학습 비용**: 훅/에이전트/카테고리 개념이 많아 초기 진입 장벽 존재
2. **디버깅 복잡성**: 훅 체인이 길어질수록 원인 추적 난이도 증가
3. **설정 의존성**: 유저 환경/모델 프로바이더 상태에 따라 체감 품질 편차

---

## 5. 우리 레포 관점 적용 인사이트

- 복잡한 코드 변경 작업에서 "계획(질문 기반) → 실행(검증 기반)" 분리는 재현성이 높음
- 카테고리 기반 라우팅은 특정 모델 잠금(lock-in)을 줄이는 전략으로 유효함
- 문서/코드 모두에서 "훅 안전 생성(safe hook creation)"을 기본값으로 두는 설계는 플러그인 안정성에 유리함

---

## 참고 링크

- [Repository](https://github.com/code-yeongyu/oh-my-openagent)
- [README (Korean)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/README.ko.md)
- [Overview Guide](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/overview.md)
- [Orchestration Guide](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/docs/guide/orchestration.md)
- [Entry Point (`src/index.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/index.ts)
- [Chat Message Handler (`src/plugin/chat-message.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/chat-message.ts)
- [Event Handler (`src/plugin/event.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/event.ts)
- [Tool Registry (`src/plugin/tool-registry.ts`)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/d80833896cc61fcb59f8955ddc3533982a6bb830/src/plugin/tool-registry.ts)
