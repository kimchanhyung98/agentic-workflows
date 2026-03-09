# Codex Review: `docs/effective-agents`

검토 일시: 2026-03-09

## 검토 범위

- 대상 디렉토리: `docs/effective-agents`
- 로컬 문서:
  - `docs/effective-agents/README.md`
  - `docs/effective-agents/01-prompt-chaining.md`
  - `docs/effective-agents/02-routing.md`
  - `docs/effective-agents/03-parallelization.md`
  - `docs/effective-agents/04-orchestrator-workers.md`
  - `docs/effective-agents/05-evaluator-optimizer.md`
  - `docs/effective-agents/06-autonomous-agent.md`
- 외부 근거:
  - Anthropic: `Building effective agents`
  - Google Cloud: `Choose a design pattern for an agentic AI system`
  - Google DeepMind: `AlphaFold`

## 최종 판정

`docs/effective-agents`는 Google Cloud 문서 기반 정리라고 보기 어렵습니다.

현재 문서 세트는 실제로는 Anthropic의 `Building effective agents` 글을 바탕으로 한 6개 패턴 요약에 가깝습니다. 따라서 "Anthropic 패턴 정리"로는 대체로 읽을 만하지만, `README.md`의 출처 표기처럼 "Google Cloud 기반 문서"로 배치하면 사실관계가 어긋납니다.

추가로 다음 이슈가 확인되었습니다.

1. Google Cloud 기반이라는 출처 표기가 잘못됨
2. 선택 가이드와 비교 차트가 Google Cloud 원문과 맞지 않음
3. 참고 링크 1건이 `404`
4. AlphaFold 예시가 자율 에이전트 사례로는 부정확함
5. Markdown lint 기준 미통과

---

## 핵심 근거

### 1. 로컬 문서의 패턴 구성은 Anthropic의 6개 패턴 체계와 일치함

로컬 `README.md`는 다음 6개 패턴만 다룹니다.

- 프롬프트 체이닝
- 라우팅
- 병렬화
- 오케스트레이터-워커
- 평가자-최적화자
- 자율 에이전트

근거:

- `docs/effective-agents/README.md:12`
- `docs/effective-agents/README.md:13`
- `docs/effective-agents/README.md:14`
- `docs/effective-agents/README.md:15`
- `docs/effective-agents/README.md:16`
- `docs/effective-agents/README.md:17`

Anthropic 원문은 에이전틱 시스템을 `workflows`와 `agents`로 구분하고, 본문에서 다음 패턴을 순서대로 설명합니다.

- Prompt chaining
- Routing
- Parallelization
- Orchestrator-workers
- Evaluator-optimizer
- Agents

또한 Anthropic 글의 핵심 메시지는 "가장 단순한 해결책부터 시작하고 필요할 때만 복잡도를 올리라"는 점입니다.

### 2. Google Cloud 원문은 12개 패턴 체계를 사용함

Google Cloud 원문은 확인 시점 기준 `최종 업데이트: 2025-10-08(UTC)`이며, 다음 패턴을 직접 다룹니다.

- 단일 에이전트 패턴
- 순차 패턴
- 병렬 패턴
- 루프 패턴
- 검토 및 비평 패턴
- 반복적 개선 패턴
- 코디네이터 패턴
- 계층적 작업 분해 패턴
- 스웜 패턴
- ReAct 패턴
- 인간 참여형(Human-In-The-Loop) 패턴
- 맞춤 로직 패턴

즉, Google Cloud의 패턴 분류와 Anthropic의 6개 패턴 체계는 동일하지 않습니다.

---

## 주요 발견 사항

### 발견 1. `Google Cloud 기반` 표기는 사실과 다름

영향 파일:

- `docs/effective-agents/README.md:4`

로컬 근거:

- `README.md:4`
  - `Google Cloud - Choose a design pattern for an agentic AI system 을 기반으로 작성되었습니다.`

외부 근거:

- Anthropic 글은 `Published Dec 19, 2024`이며, 본문에서 `Prompt chaining`, `Routing`, `Parallelization`, `Orchestrator-workers`, `Evaluator-optimizer`, `Agents`를 설명합니다.
- Google Cloud 문서는 12개 패턴 체계로 구성되며 `Prompt chaining`, `Routing`, `Orchestrator-workers`, `Evaluator-optimizer`, `Autonomous agent`를 독립 패턴명으로 사용하지 않습니다.

판단:

- 현재 문서는 Google Cloud 요약본이 아니라 Anthropic 패턴 요약본입니다.
- 따라서 출처 표기가 잘못되었고, 문서 독자가 참고 기준을 잘못 이해할 수 있습니다.

권장 수정:

- `README.md`의 기준 문서를 Anthropic으로 수정
- 또는 문서를 Google Cloud 12개 체계에 맞게 전면 재구성

---

### 발견 2. 선택 가이드와 비교 차트가 Google Cloud 원문과 맞지 않음

영향 파일:

- `docs/effective-agents/README.md:21`
- `docs/effective-agents/README.md:54`

로컬 근거:

- `README.md:21` 이하 선택 가이드는 6개 패턴만 전제로 분기합니다.
- `README.md:54` 이하 비교 차트도 6개 패턴만 비교합니다.

외부 근거:

- Google Cloud 원문은 `single-agent`, `sequential`, `parallel`, `loop`, `review and critique`, `iterative refinement`, `coordinator`, `hierarchical task decomposition`, `swarm`, `ReAct`, `human-in-the-loop`, `custom logic`를 모두 비교 대상으로 둡니다.
- Google Cloud 문서는 특히 `human-in-the-loop`와 `custom logic`를 별도 패턴으로 강조합니다.

판단:

- 현재 선택 가이드는 "Google Cloud 방식의 패턴 선택표"로 읽히지만, 실제로는 Anthropic식 6패턴만 대상으로 한 작성자 재구성입니다.
- 이 상태로 두면 `single-agent`, `loop`, `review and critique`, `custom logic` 같은 Google 핵심 패턴이 존재하지 않는 것처럼 보입니다.

권장 수정:

- README를 Anthropic 기준으로 명시하고 6패턴 선택 가이드로 유지
- 또는 Google Cloud 12패턴 기준으로 다시 작성

---

### 발견 3. LlamaIndex 참고 링크 1건이 깨져 있음

영향 파일:

- `docs/effective-agents/01-prompt-chaining.md:105`

로컬 근거:

- `01-prompt-chaining.md:105`
  - `https://docs.llamaindex.ai/en/stable/module_guides/querying/pipeline/`

확인 결과:

- HTTP 상태 코드: `404`

판단:

- 외부 참고 자료 중 실제로 열리지 않는 링크가 포함되어 있습니다.
- 문서 신뢰도와 유지보수 상태를 떨어뜨리는 요소입니다.

권장 수정:

- 현행 LlamaIndex 문서의 유효한 경로로 교체
- 또는 링크를 제거

---

### 발견 4. AlphaFold는 자율 에이전트 사례로 쓰기 부정확함

영향 파일:

- `docs/effective-agents/06-autonomous-agent.md:200`

로컬 근거:

- `06-autonomous-agent.md:200`
  - `실제 사례: AlphaFold (DeepMind), 자율 실험 플랫폼`

외부 근거:

- Google DeepMind의 AlphaFold 페이지는 AlphaFold를 단백질 구조 예측 시스템, 서버, 데이터베이스로 설명합니다.
- 해당 페이지의 설명은 `Predict protein structures with high accuracy`, `Protein Structure Database`, `AlphaFold Server predicts how proteins will interact...`와 같이 생물학 구조 예측 모델/서비스에 초점이 있습니다.

판단:

- AlphaFold는 범용 자율 에이전트의 대표 사례라기보다, 단백질 구조 예측 모델 및 관련 연구 인프라에 가깝습니다.
- 자율 연구 에이전트 예시로 들면 개념 범주가 흐려집니다.

권장 수정:

- AlphaFold 언급 삭제
- 대신 실제 자율 연구/코딩/조사 에이전트 사례로 교체

---

### 발견 5. Markdown lint 기준으로는 미통과

영향 범위:

- `docs/effective-agents/**/*.md`

재현 명령:

```bash
npx --yes markdownlint-cli2 "docs/effective-agents/**/*.md"
```

확인 결과:

- `Summary: 107 error(s)`

반복된 오류 유형:

- `MD013` 긴 줄
- `MD022` heading 주변 공백
- `MD032` list 주변 공백
- `MD060` 표 스타일

판단:

- 내용 문제와 별개로 문서 품질 게이트를 둔다면 현재 상태는 미통과입니다.

권장 수정:

- 일괄 포맷 정리
- 또는 프로젝트용 markdownlint 설정 파일 추가

---

## 정상적으로 작성된 부분

다음 항목은 긍정적으로 확인했습니다.

### 1. Anthropic 6패턴 체계로 보면 문서 구조는 일관적임

각 파일이 공통적으로 다음 구조를 따릅니다.

- 정의 및 핵심 요약
- 작동 원리 및 흐름
- 실제 사용 예시
- 장단점
- 추가 학습 자료

### 2. 대부분의 외부 링크는 정상 응답함

확인 시점 기준 대부분의 링크는 `200` 응답이었습니다.

확인된 예외:

- `https://docs.llamaindex.ai/en/stable/module_guides/querying/pipeline/` → `404`

### 3. Anthropic 원문과의 개념 대응은 전반적으로 맞음

특히 다음은 Anthropic 글과 높은 정합성을 보였습니다.

- `01-prompt-chaining.md`
- `02-routing.md`
- `03-parallelization.md`
- `04-orchestrator-workers.md`
- `05-evaluator-optimizer.md`
- `06-autonomous-agent.md`

즉, 문제는 "내용 자체가 전부 틀렸다"가 아니라 "출처와 기준 프레이밍이 잘못됐다"는 데 있습니다.

---

## 원문 기준 요약

Anthropic 기준으로 이 디렉토리를 해석하면 다음 설명이 가장 정확합니다.

1. `docs/effective-agents`는 Anthropic의 `Building effective agents`를 바탕으로 한 6패턴 요약 문서다.
2. Google Cloud는 보조 참고 자료로 넣을 수는 있지만, 현재 문서의 주된 구조적 기준은 아니다.
3. 따라서 README 첫 문장과 선택 가이드의 기준 출처를 수정해야 문서 설명과 실제 내용이 일치한다.

---

## 재현에 사용한 명령

```bash
rg --files docs/effective-agents
```

```bash
for f in docs/effective-agents/*.md; do
  nl -ba "$f" | sed -n '1,220p'
done
```

```bash
rg -o -N -I 'https?://[^)]+' docs/effective-agents/*.md | sort -u | while IFS= read -r u; do
  code=$(curl -L -s -o /dev/null -w '%{http_code}' "$u")
  printf '%s %s\n' "$code" "$u"
done
```

```bash
npx --yes markdownlint-cli2 "docs/effective-agents/**/*.md"
```

```bash
curl -L -s 'https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system?hl=ko' | rg -n '단일 에이전트 패턴|순차 패턴|병렬 패턴|루프 패턴|검토 및 비평 패턴|반복적 개선 패턴|코디네이터 패턴|계층적 작업 분해 패턴|스웜 패턴|ReAct 패턴|인간 참여형|맞춤 로직 패턴|최종 업데이트'
```

---

## 참고 자료

- Anthropic: https://www.anthropic.com/engineering/building-effective-agents
- Google Cloud: https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system?hl=ko
- Google DeepMind AlphaFold: https://deepmind.google/technologies/alphafold/
- OpenAI guide: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
