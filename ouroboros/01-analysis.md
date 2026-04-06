# Ouroboros 설계 및 실행 플로우 분석

## 1. 개요

- 저장소: `Q00/ouroboros`
- 패키지: `ouroboros-ai` (PyPI)
- 런타임 요구사항: Python >= 3.12
- 핵심 방향: **Specification-first AI workflow harness**

Ouroboros는 "프롬프트를 바로 코드로 변환"하는 접근 대신, 인터뷰를 통해 요구를 명세화하고 고정된 Seed를 기준으로 실행/평가/진화를 반복하는 하네스입니다. Claude Code와 Codex CLI를 동일 인터페이스로 감싸 실행하는 런타임 추상화가 특징입니다.

---

## 2. AI 에이전트 하네스 관점 분석

### 2.1 하네스 목적

하네스의 목표는 모델 성능 자체를 올리는 것이 아니라, **입력 명확도와 실행 검증성**을 제어하는 것입니다.

| 문제 | 일반 에이전트 워크플로우 | Ouroboros 하네스 |
|---|---|---|
| 요구가 모호함 | 모델이 추정하여 구현 | Socratic 인터뷰로 가정/누락 노출 |
| 스펙 부재 | 중간에 방향 드리프트 | Seed immutable 정책으로 의도 고정 |
| 품질 게이트 약함 | 수동 리뷰 의존 | Mechanical→Semantic→Consensus 자동 게이트 |
| 장기 실행 복원력 | 세션 유실 시 재시작 부담 | EventStore + checkpoint로 재개/추적 |

### 2.2 하네스 핵심 구성

- **Phase 0 (Big Bang)**: 인터뷰 + ambiguity score + Seed 생성
- **Phase 1 (PAL Router)**: 비용/난이도 기반 모델 티어 선택
- **Phase 2 (Double Diamond)**: Discover→Define→Design→Deliver 실행 구조
- **Phase 3 (Resilience)**: stagnation 패턴 감지 + lateral persona 전환
- **Phase 4 (Evaluation)**: 3-stage 품질 게이트
- **Phase 5 (Secondary Loop)**: 비핵심 TODO 후처리

### 2.3 활용 사례

1. **신규 기능 개발**: vague idea를 인터뷰로 구조화 후 명세 기반 구현
2. **브라운필드 개선**: 기존 코드 제약/환경을 반영해 명세 우선 실행
3. **장시간 자율 실행**: `ralph` 루프로 세대별 진화와 수렴 판단
4. **멀티 런타임 운영**: 팀마다 Claude/Codex를 선택해도 동일 워크플로우 유지
5. **PM 워크플로우**: `pm` 모드로 PRD 산출까지 하네스 확장

---

## 3. 코드 구조 및 모듈 분석

아키텍처 문서 기준 주요 모듈:

```text
src/ouroboros/
├─ core/            # types, errors, seed, context, AC tree
├─ bigbang/         # interview, ambiguity scoring, seed generation
├─ routing/         # PAL router
├─ execution/       # Double Diamond execution
├─ resilience/      # stagnation detection, lateral personas
├─ evaluation/      # mechanical/semantic/consensus pipeline
├─ secondary/       # TODO registry/scheduler
├─ orchestrator/    # runtime adapter abstraction + runner/session/events
├─ mcp/             # MCP client/server/tools/resources
├─ providers/       # LLM provider adapter (LiteLLM)
├─ persistence/     # event store, checkpoint, schema
└─ observability/   # logging, drift, retrospective
```

### 3.1 orchestrator 계층

- `runtime_factory.py`가 backend 이름으로 어댑터를 생성
- `adapter.py`의 `AgentRuntime` 프로토콜을 공통 계약으로 사용
- 구현체:
  - `ClaudeAgentAdapter` (Claude Code 세션 기반)
  - `CodexCliRuntime` (Codex CLI 세션/NDJSON 기반)

핵심은 런타임 차이를 어댑터 경계에서 흡수하고, 상위 오케스트레이터는 동일한 `AgentMessage`/`RuntimeHandle` 추상으로 다루는 점입니다.

### 3.2 persistence/observability 계층

- EventStore append-only 이벤트 저장
- checkpoint 기반 복구/재개
- drift 측정(목표/제약/온톨로지 축)
- retrospective 자동 생성

이 설계는 장기/반복 실행에서 디버깅 가능성과 감사 추적성을 강화합니다.

### 3.3 MCP 계층

Ouroboros는 MCP를 양방향으로 사용합니다.

- **Server mode**: Ouroboros 기능을 MCP 툴로 외부 클라이언트에 노출
- **Client mode**: 외부 MCP 서버 도구를 실행에 병합해 활용

즉, 단순한 "도구 소비자"가 아니라 도구 플랫폼/허브 역할도 수행합니다.

---

## 4. 실행 플로우 상세

### 4.1 Interview → Seed

1. 사용자 아이디어 입력
2. Socratic 질문 반복
3. ambiguity score 계산 (`<= 0.2` 통과 시 Seed 생성)
4. Seed immutable 고정

Seed에는 goal, constraints, acceptance criteria, ontology schema, exit conditions가 포함되며, 이후 실행의 기준점(헌법) 역할을 합니다.

### 4.2 Seed → Execution

1. PAL Router가 난이도/비용에 맞는 모델 티어 선택
2. Double Diamond로 AC 트리 실행
3. stagnation 시 Resilience 계층에서 시각 전환
4. 필요 시 세션 재개/체크포인트 복구

### 4.3 Execution → Evaluation

**Stage 1 Mechanical**
- lint/build/test/static/coverage 자동 실행(프로젝트 언어 자동 감지)
- 실패 즉시 중단

**Stage 2 Semantic**
- AC 정합성, goal alignment, drift, uncertainty 점수화
- 충분 점수면 consensus 생략 가능

**Stage 3 Consensus**
- 트리거 발생 시에만 고비용 합의 수행
- simple voting 또는 deliberative(advocate/devil/judge) 모드

### 4.4 Evolution loop

평가 결과를 다음 세대 입력으로 반영하며 ontology similarity가 기준(예: 0.95 이상)에 도달하면 수렴으로 종료합니다. `ralph`는 이 과정을 세션 경계를 넘어 지속 실행하도록 설계되었습니다.

---

## 5. 웹 조사 기반 추가 정보

### 5.1 배포/설치 채널

- PyPI 패키지: `ouroboros-ai`
- one-liner 설치 스크립트 제공
- Claude plugin 경로와 pip/uv/pipx 경로를 함께 제공

### 5.2 명령/스킬 체계

- 에이전트 세션: `ooo <skill>` 중심
- 터미널: `ouroboros <command>` 중심
- setup/init/run/status/cancel/tui/mcp 등 CLI 명령 제공

### 5.3 런타임 가이드

- Claude runtime: Max Plan 기반, 별도 API 키 없이 실행 가능
- Codex runtime: Codex CLI + OpenAI API 키 기반, 모델 권장값 제시
- 동일 Seed를 공유하지만, 런타임 도구/권한/샌드박스 차이로 실행 경로는 달라질 수 있음

---

## 6. 장점과 트레이드오프

### 장점

1. **요구 명확화 강제**: 인터뷰+모호성 게이트로 초기 품질 향상
2. **검증 자동화**: 3-stage 평가로 "보이는 성공"을 줄임
3. **운영 복원력**: 이벤트 소싱+체크포인트로 장기 실행 안정성 확보
4. **런타임 이식성**: Claude/Codex 전환 비용 감소
5. **MCP 허브화**: 외부 도구 생태계 연동 유연성

### 트레이드오프

1. **초기 진입 비용**: 하네스 개념(Seed, 단계 게이트, 드리프트 등) 학습 필요
2. **실행 오버헤드**: 명세/평가 단계 추가로 단발 작업 체감 속도 저하 가능
3. **구성 복잡도**: 런타임/모델/도구/MCP 설정 조합이 많음
4. **결과 편차**: 런타임별 도구 차이로 결과/경로의 재현성이 완전 동일하지 않음

---

## 7. 적용 인사이트

- **팀 표준화 관점**: "좋은 프롬프트 작성 능력" 의존도를 낮추고, 인터뷰/Seed를 통해 요구 정의를 팀 자산화할 수 있습니다.
- **거버넌스 관점**: event sourcing과 단계 게이트를 결합해 품질/감사 추적 요구가 있는 환경에 적합합니다.
- **실무 적용 순서**: 인터뷰-Seed-Mechanical gate까지 우선 도입하고, 이후 consensus/evolution을 점진 확장하는 방식이 리스크가 낮습니다.

---

## 참고 링크

- [Repository](https://github.com/Q00/ouroboros)
- [README](https://github.com/Q00/ouroboros/blob/main/README.md)
- [Architecture](https://github.com/Q00/ouroboros/blob/main/docs/architecture.md)
- [CLI Reference](https://github.com/Q00/ouroboros/blob/main/docs/cli-reference.md)
- [Runtime Guide - Claude Code](https://github.com/Q00/ouroboros/blob/main/docs/runtime-guides/claude-code.md)
- [Runtime Guide - Codex CLI](https://github.com/Q00/ouroboros/blob/main/docs/runtime-guides/codex.md)
- [pyproject.toml](https://github.com/Q00/ouroboros/blob/main/pyproject.toml)
- [PyPI - ouroboros-ai](https://pypi.org/project/ouroboros-ai/)
