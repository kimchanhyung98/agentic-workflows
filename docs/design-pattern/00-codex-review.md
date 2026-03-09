# Codex Review: `docs/design-pattern`

검토 일시: 2026-03-09 11:10:43 KST

## 검토 범위

- 대상 디렉토리: `docs/design-pattern`
- 기준 문서:
  - Google Cloud: `Choose a design pattern for an agentic AI system`
  - Google Cloud: `Choose your agentic AI architecture components`
  - Google Cloud: `Multi-agent AI system in Google Cloud`
  - Google ADK 문서

## 최종 판정

현재 `docs/design-pattern` 문서 세트는 이전 버전과 달리 Google Cloud의 12개 패턴 체계를 대부분 정확하게 반영하고 있습니다.

다만 다음 4가지는 수정이 필요합니다.

1. 일부 비용/호출 수 설명이 원문보다 과도하게 단순화되어 있습니다.
2. ADK 참고 자료 라벨은 구체적이지만 실제 링크는 대부분 루트 페이지입니다.
3. `README.md`의 비교표는 유용하지만 작성자 해석임을 명시하는 편이 안전합니다.
4. Markdown lint 기준으로는 아직 문서가 정리되지 않았습니다.

즉, 내용 구조는 대체로 정상이나, 엄격한 기준에서는 아직 "최종 마감 상태"는 아닙니다.

---

## 핵심 근거

### 1. Google Cloud 원문과의 구조 정합성은 대체로 맞음

Google Cloud 원문은 다음 패턴들을 직접 설명합니다.

- 단일 에이전트 시스템
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

로컬 디렉토리도 동일한 12개 파일로 구성되어 있습니다.

- `docs/design-pattern/01-single-agent.md`
- `docs/design-pattern/02-sequential.md`
- `docs/design-pattern/03-parallel.md`
- `docs/design-pattern/04-loop.md`
- `docs/design-pattern/05-review-critique.md`
- `docs/design-pattern/06-iterative-refinement.md`
- `docs/design-pattern/07-coordinator.md`
- `docs/design-pattern/08-hierarchical.md`
- `docs/design-pattern/09-swarm.md`
- `docs/design-pattern/10-react.md`
- `docs/design-pattern/11-human-in-the-loop.md`
- `docs/design-pattern/12-custom-logic.md`

근거:

- Google Cloud 원문 HTML 확인 결과 해당 섹션 제목이 모두 존재함
- 확인 시점 기준 원문 최종 업데이트: `2025-10-08(UTC)`

---

## 주요 발견 사항

### 발견 1. `단일 모델 호출` 및 `추가 모델 호출 없음` 표현은 부정확함

영향 파일:

- `docs/design-pattern/01-single-agent.md:93`
- `docs/design-pattern/02-sequential.md:84`

로컬 근거:

- `01-single-agent.md:93`
  - `단일 모델 호출로 비용 효율적`
- `02-sequential.md:84`
  - `운영 비용 절감 (추가 모델 호출 없음)`

외부 근거:

- Google Cloud 원문은 에이전트가 필요한 경우를 다음처럼 설명합니다.
  - 예측 가능하거나 고도로 구조화되었거나 AI 모델에 대한 단일 호출로 처리 가능하면 에이전트 없는 솔루션이 더 비용 효율적일 수 있음
  - 단일 에이전트 시스템은 여러 단계와 외부 데이터 접근이 필요한 작업에 적합함
- 같은 문서에서 순차 패턴은
  - 하위 에이전트 오케스트레이션을 위해 AI 모델을 참조하지 않는 사전 정의 로직
  - 으로 설명됩니다.

판단:

- 단일 에이전트는 "단일 프롬프트"와 같은 개념이 아닙니다.
- 순차 패턴도 "오케스트레이션용 모델 호출이 없다"는 뜻이지, 하위 에이전트나 모델 호출 비용이 없다는 뜻은 아닙니다.

권장 수정:

- `단일 모델 호출로 비용 효율적`
  - `상대적으로 단순한 구조로 시작하기 쉬우며, 복잡한 멀티 에이전트 대비 비용을 통제하기 쉽다`
- `추가 모델 호출 없음`
  - `오케스트레이션용 별도 모델 호출이 없어 구조가 단순하다`

---

### 발견 2. ADK 참고 링크는 살아 있지만 라벨 대비 정밀도가 낮음

영향 파일 예시:

- `docs/design-pattern/01-single-agent.md:104`
- `docs/design-pattern/02-sequential.md:96`
- `docs/design-pattern/03-parallel.md:111`
- `docs/design-pattern/04-loop.md:111`
- `docs/design-pattern/07-coordinator.md:125`

로컬 근거:

- 위 파일들은 각각 `Google ADK: Single Agent`, `Sequential Agents`, `Parallel Agents`, `Loop Agents`, `Multi-Agent Patterns`라고 표기하지만 실제 URL은 대부분 `https://google.github.io/adk-docs/` 루트입니다.

외부 근거:

Google Cloud 원문 내부 링크와 ADK 문서에서 확인 가능한 더 구체적인 경로:

- `https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/`
- `https://google.github.io/adk-docs/agents/workflow-agents/parallel-agents/`
- `https://google.github.io/adk-docs/agents/workflow-agents/loop-agents`
- `https://google.github.io/adk-docs/agents/multi-agents/`
- `https://google.github.io/adk-docs/agents/custom-agents/`

판단:

- 링크는 `200` 응답이므로 깨진 링크는 아닙니다.
- 다만 "구체 문서 제목"을 달아놓고 루트 페이지로 보내는 방식은 참고 자료 품질이 낮습니다.

권장 수정:

- 라벨이 구체적이면 URL도 구체 문서로 연결
- 루트 링크만 쓸 경우 라벨을 `Google ADK Documentation`으로 통일

---

### 발견 3. `README.md` 비교표는 해석값이므로 출처 성격을 분리하는 편이 안전함

영향 파일:

- `docs/design-pattern/README.md:95`

로컬 근거:

- `복잡도 | 비용 | 지연 시간 | 자율성` 비교표가 단정형으로 제시되어 있음

외부 근거:

- Google Cloud 원문은 패턴별 절충을 서술형으로 설명하지만, 현재 로컬 문서와 동일한 종합 비교표를 제공하지는 않습니다.
- 예를 들어 원문은
  - 병렬 패턴: 지연 시간 감소 가능, 비용과 복잡성 증가
  - 코디네이터 패턴: 단일 에이전트보다 더 많은 모델 호출과 더 높은 비용/지연
  - 스웜 패턴: 가장 복잡하고 비용이 많이 듦
  - 처럼 패턴별로 설명합니다.

판단:

- 표 자체는 요약 도구로 유용합니다.
- 다만 독자가 이를 Google 공식 비교표로 오인할 수 있습니다.

권장 수정:

- 표 제목 또는 바로 위 문장에 다음 중 하나를 명시
  - `아래 표는 Google Cloud 원문 설명을 바탕으로 재구성한 요약입니다.`
  - `아래 평가는 작성자 해석입니다.`

---

### 발견 4. Markdown lint 기준으로는 아직 정리되지 않음

영향 범위:

- `docs/design-pattern/**/*.md` 전체

재현 명령:

```bash
npx --yes markdownlint-cli2 "docs/design-pattern/**/*.md"
```

확인 결과:

- `Summary: 208 error(s)`

반복된 오류 유형:

- `MD013` 긴 줄
- `MD022` heading 주변 공백
- `MD032` list 주변 공백
- `MD060` 표 스타일

판단:

- 내용 정확성과 별개로, 문서 품질 게이트를 둔다면 현재 상태는 미통과입니다.
- 특히 표와 리스트가 많아 후속 자동 정리 필요성이 큽니다.

권장 수정:

- lint 규칙을 맞출 생각이면 일괄 정리
- 현재 스타일을 유지할 생각이면 `.markdownlint-cli2.*` 또는 `.markdownlint.*`로 프로젝트 기준을 명시

---

## 정상적으로 작성된 부분

다음 항목은 긍정적으로 확인했습니다.

### 1. Google Cloud의 12개 패턴 체계를 모두 반영함

이전 버전의 6개 패턴 정리와 달리, 현재는 Google Cloud 문서의 패턴 분류 체계를 직접 따라가고 있습니다.

### 2. 핵심 예시가 원문과 대체로 일치함

특히 다음은 원문과 높은 정합성을 보였습니다.

- `03-parallel.md`
  - 고객 의견을 감정, 키워드, 분류, 긴급도로 동시에 분석
- `07-coordinator.md`
  - 고객 서비스 요청을 주문/반품/환불 전문 에이전트로 라우팅
- `10-react.md`
  - 로봇 에이전트의 경로 계획 예시
- `11-human-in-the-loop.md`
  - 환자 데이터 익명화 후 인간 규정 준수 담당자 승인
- `12-custom-logic.md`
  - 환불 프로세스에서 병렬 검사 후 조건 분기

### 3. 외부 링크는 현재 기준으로 모두 응답함

검사한 참고 링크들은 확인 시점 기준 모두 `200` 응답이었습니다.

재현 명령:

```bash
rg -o -N -I 'https?://[^)]+' docs/design-pattern/*.md | sort -u | while IFS= read -r u; do
  code=$(curl -L -s -o /dev/null -w '%{http_code}' "$u")
  printf '%s %s\n' "$code" "$u"
done
```

주의:

- 링크가 살아 있다는 사실과 "가장 적절한 목적지"라는 사실은 다릅니다.
- ADK 링크는 응답은 정상이나, 일부는 더 구체적인 페이지로 바꾸는 편이 낫습니다.

---

## 원문 핵심 요약

Google Cloud 문서의 핵심 메시지는 다음과 같습니다.

1. 먼저 에이전트가 정말 필요한지 판단합니다.
2. 가능하면 가장 단순한 패턴부터 시작합니다.
3. 필요할 때만 동적 오케스트레이션, 반복 구조, 인간 개입, 맞춤 로직으로 복잡도를 올립니다.

원문에서 직접 확인한 중요한 기준:

- 예측 가능하거나 구조화되어 있거나 단일 모델 호출로 처리 가능한 작업은 에이전트 없는 솔루션이 더 비용 효율적일 수 있음
- 단일 에이전트는 여러 단계와 외부 데이터 접근이 필요한 작업에 적합함
- 순차/병렬/루프는 사전 정의된 로직 기반 워크플로 에이전트 계열임
- 코디네이터는 AI 모델을 사용해 동적으로 라우팅하고 오케스트레이션함
- 계층적 작업 분해는 코디네이터 패턴의 구현으로 설명됨
- 스웜은 all-to-all 협업이며 일반적으로 중앙 감독자가 없음
- Human-in-the-loop는 체크포인트에서 실행을 일시중지하고 외부 시스템을 통해 사람의 결정을 기다림
- 맞춤 로직은 여러 패턴이 혼합된 복잡한 분기 워크플로에 적합함

---

## 재현에 사용한 명령

```bash
rg --files docs/design-pattern
```

```bash
for f in docs/design-pattern/*.md; do
  nl -ba "$f" | sed -n '1,220p'
done
```

```bash
curl -L -s 'https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system?hl=ko' | rg -n '단일 에이전트 패턴|순차 패턴|병렬 패턴|루프 패턴|검토 및 비평 패턴|반복적 개선 패턴|코디네이터 패턴|계층적 작업 분해 패턴|스웜 패턴|ReAct 패턴|인간 참여형|맞춤 로직 패턴|최종 업데이트'
```

```bash
curl -L -s 'https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system?hl=ko' | rg -n '에이전트가 없는 솔루션|단일 호출|단일 에이전트 시스템은 여러 단계|병렬 패턴|코디네이터 패턴|Human-In-The-Loop|맞춤 로직 패턴'
```

```bash
npx --yes markdownlint-cli2 "docs/design-pattern/**/*.md"
```

---

## 참고 자료

- Google Cloud: https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system?hl=ko
- Google Cloud: https://docs.cloud.google.com/architecture/choose-agentic-ai-architecture-components
- Google Cloud: https://docs.cloud.google.com/architecture/multiagent-ai-system
- Google ADK: https://google.github.io/adk-docs/
- Google ADK Workflow Agents: https://google.github.io/adk-docs/agents/workflow-agents/
- Google ADK Multi-Agents: https://google.github.io/adk-docs/agents/multi-agents/
- Google ADK Custom Agents: https://google.github.io/adk-docs/agents/custom-agents/
- Google Developers Blog: https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- ReAct 논문: https://arxiv.org/abs/2210.03629
