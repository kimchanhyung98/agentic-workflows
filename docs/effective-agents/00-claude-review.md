# 문서 리뷰 결과

`docs/effective-agents/` 디렉토리의 문서를 [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 원문과 대조하여 검토한 결과입니다.

---

## Critical Issues

### 1. 오케스트레이터 다이어그램의 Synthesizer 별도 노드

- **위치**: `04-orchestrator-workers.md` 기본 다이어그램 (26-36행)
- **현재**: `Synth[종합기 Synthesizer]`가 오케스트레이터와 별도 노드로 분리
- **문제**: 원문 다이어그램에서는 오케스트레이터 자체가 워커에게 위임하고 결과를 종합하는 역할을 수행하며, 별도의 Synthesizer 컴포넌트가 존재하지 않음. 같은 파일의 상세 아키텍처 다이어그램(42-71행)에서는 오케스트레이터 내부에 종합 기능을 포함시키고 있어 두 다이어그램 간 불일치도 존재.
- **원문 근거**: 원문 다이어그램은 `Input → Orchestrator → (dashed) LLM Call 1/2/3 → (dashed) Synthesizer → Output` 구조이나, 여기서 Synthesizer는 오케스트레이터의 최종 종합 단계를 나타내는 것이지 독립 컴포넌트가 아님. 원문 설명: "A central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results."
- **수정 제안**: 오케스트레이터가 직접 종합하는 구조로 변경하거나, Synthesizer가 오케스트레이터의 최종 단계임을 명시

### 2. 병렬화 패턴의 Guardrails 사용 사례 누락

- **위치**: `03-parallelization.md` 실제 사용 예시 (113-146행)
- **현재**: 법률 계약서, 코드 보안 감사, 콘텐츠 모더레이션, 금융 리스크, 번역 검증 등 독자적 예시만 존재
- **문제**: 원문의 핵심 Sectioning 예시인 **Guardrails 패턴**이 완전 누락됨. 이 패턴은 하나의 LLM이 사용자 쿼리를 처리하는 동시에 다른 LLM이 부적절한 콘텐츠를 스크리닝하는 구조로, 병렬화의 가장 실용적인 활용 사례 중 하나.
- **원문 근거**: "Implementing guardrails where one model instance processes the user query while another screens it for inappropriate content or requests. This tends to be more effective than having the same LLM call handle both guardrails and the core response."
- **수정 제안**: 원문의 Guardrails 예시를 Sectioning 사용 사례에 추가

### 3. 프롬프트 체이닝의 Gate 사용 사례 미반영

- **위치**: `01-prompt-chaining.md` 실제 사용 예시 (58-83행)
- **현재**: 문서 생성 파이프라인, 코드 리뷰 자동화, 번역 및 현지화, 금융 보고서 분석
- **문제**: 원문이 강조하는 Gate(관문) 개념의 구체적 활용 사례가 부족. 원문에서는 Gate를 "programmatic checks"로 설명하며, 이전 단계의 출력을 평가하여 계속 진행할지 종료할지 결정하는 것이 프롬프트 체이닝의 핵심 차별점.
- **원문 근거**: "Generating a marketing copy, then translating it into a different language." / "Writing a document outline, checking that the outline meets certain criteria, then writing the document based on the outline."
- **수정 제안**: 원문의 Gate 활용 예시(아웃라인 → 기준 검증 → 문서 작성)를 추가하거나, 기존 예시에 Gate 단계를 명시적으로 포함

### 4. 라우팅의 모델별 비용 최적화 사례 누락

- **위치**: `02-routing.md` 실제 사용 예시 (65-98행)
- **현재**: 고객 서비스, 코드 어시스턴트, 의료 정보, 금융 서비스 예시 제공. 금융 서비스에서 "경량 모델"과 "강력한 모델"을 간접적으로 언급하나 핵심 메시지가 희석됨.
- **문제**: 원문의 핵심 라우팅 사용 사례인 **모델 크기별 비용 최적화**(간단한 쿼리 → 소형 모델, 복잡한 쿼리 → 대형 모델)가 명시적으로 다루어지지 않음.
- **원문 근거**: "Directing simple/common questions to smaller models like Claude 3.5 Haiku and hard/unusual questions to more capable models like Claude 3.5 Sonnet to optimize cost and speed."
- **수정 제안**: 모델 크기별 라우팅을 통한 비용 최적화 사례를 별도 예시로 추가하고, 구체적인 모델명(Haiku/Sonnet 등) 언급

---

## Important Issues

### 5. 전체 문서 - 원문의 핵심 프레이밍 누락

- **위치**: 6개 문서 전체
- **현재**: 각 패턴을 독립적으로 설명하며, 원문의 상위 분류 체계가 반영되지 않음
- **문제**: 원문의 가장 중요한 메타 메시지 3가지가 어디에도 없음:
  1. **Workflows vs Agents 구분**: 패턴 1-5는 "workflows"(사전 정의된 코드 경로로 LLM과 도구를 오케스트레이션), 패턴 6만 "agents"(LLM이 동적으로 자신의 프로세스와 도구 사용을 결정). 현재 문서에서는 이 구분 없이 모두 동일한 레벨로 나열.
  2. **Augmented LLM 빌딩 블록**: 모든 패턴의 기본 구성 요소인 retrieval + tools + memory로 강화된 LLM 개념이 누락.
  3. **복잡성 최소화 원칙**: 원문의 핵심 메시지가 반영되지 않음.
- **원문 근거**:
  - "We think it's helpful to distinguish between workflows and agents. 'Workflows' are systems where LLMs and tools are orchestrated through predefined code paths. 'Agents,' on the other hand, are systems where LLMs dynamically direct their own processes and tool usage."
  - "The basic building block of agentic systems is an LLM enhanced with augmentations such as retrieval, tools, and memory."
  - "You should consider adding complexity only when it demonstrably improves outcomes. That means not building agentic systems at all if simpler approaches suffice."
- **수정 제안**: 개요 문서(`00-overview.md` 등)를 추가하거나, 각 문서 서두에 해당 패턴이 workflow/agent 중 어디에 속하는지 명시

### 6. 자율 에이전트의 ACI 원칙 및 도구 설계 누락

- **위치**: `06-autonomous-agent.md` 전체
- **현재**: ReAct 패턴, 상태 관리, 위험 관리 전략은 다루지만, 원문이 강조하는 도구 설계 원칙이 없음
- **문제**: 원문의 에이전트 구현 3대 원칙 중 **Agent-Computer Interface (ACI)**가 완전 누락. 원문은 SWE-bench 구현에서 전체 프롬프트보다 도구 최적화에 더 많은 시간을 투자했다고 밝히며, 이를 에이전트 성공의 핵심 요소로 제시.
- **원문 근거**:
  - "We spent more time optimizing our tools and their descriptions than the overall prompt."
  - "Just as you might give a human a task along with a well-designed UI, you should design your ACI to make tools easy to use."
  - 3대 원칙: "(1) Design toolsets and their documentation to be clear and unambiguous, (2) Reduce the number of tools so the LLM can maintain focus, (3) Build in explicit signals of success or failure"
- **수정 제안**: "도구 설계 원칙" 또는 "ACI (Agent-Computer Interface)" 섹션 추가

### 7. 평가자-최적화자의 용어 혼용

- **위치**: `05-evaluator-optimizer.md` 8-9행
- **현재**: "최적화자(Generator/Optimizer)"로 Generator와 Optimizer를 혼용
- **문제**: 원문에서 이 패턴의 두 구성 요소는 **"LLM call that generates a response"**(생성)와 **"LLM call that provides evaluation and feedback"**(평가)로 설명됨. 패턴 이름이 Evaluator-Optimizer이므로 Generator라는 별도 용어 추가는 불필요한 혼란을 줄 수 있음.
- **원문 근거**: "One LLM call generates a response while another provides evaluation and feedback in a loop."
- **수정 제안**: "최적화자(Optimizer)" 또는 "생성자(Generator)"로 일관되게 사용. 원문의 패턴명을 따르면 "최적화자(Optimizer)"가 적합

### 8. 오케스트레이터-워커와 병렬화의 차이점 설명 부족

- **위치**: `04-orchestrator-workers.md` 13-15행
- **현재**: 프롬프트 체이닝과의 차이만 설명
- **문제**: 원문은 오케스트레이터-워커와 **병렬화(Parallelization)**의 핵심 차별점을 명확히 함. 두 패턴 모두 여러 LLM을 동시에 사용하지만, 병렬화는 하위 작업이 사전 정의되고 오케스트레이터-워커는 런타임에 동적으로 결정됨.
- **원문 근거**: "A key difference from parallelization is its flexibility—subtasks aren't pre-defined, but determined by the orchestrator based on the specific input."
- **수정 제안**: 병렬화와의 차이점 비교 추가 (고정 하위 작업 vs 동적 하위 작업)

### 9. 평가자-최적화자의 원문 사용 사례 누락

- **위치**: `05-evaluator-optimizer.md` 92-128행
- **현재**: 코드 품질, 학술 논문, 마케팅 카피, 법률 문서, 번역 품질 등 5개 독자적 예시
- **문제**: 원문의 핵심 사용 사례인 **"복잡한 검색(complex search)"**이 누락됨.
- **원문 근거**: "Complex search tasks that require multiple rounds of searching and analysis to gather comprehensive information, where the evaluator decides whether further searches are warranted."
- **수정 제안**: "복잡한 정보 검색" 사용 사례 추가 (다수 라운드의 검색과 분석을 통한 종합 정보 수집, 평가자가 추가 검색 필요 여부 결정)

---

## Suggestions

### 10. 개요 문서 추가 권장

- **위치**: `docs/effective-agents/` 디렉토리
- **현재**: 6개 패턴 문서만 존재
- **제안**: 원문의 핵심 프레이밍을 담는 개요 문서 추가. 포함 내용:
  - Workflows vs Agents 분류 체계
  - Augmented LLM (retrieval + tools + memory) 빌딩 블록 설명
  - 복잡성 최소화 원칙 ("When and how to use frameworks")
  - 6개 패턴의 복잡도 순서와 선택 가이드
  - 원문의 Augmented LLM 다이어그램: `Input → LLM → Output; LLM ↔ Retrieval, LLM ↔ Tools, LLM ↔ Memory`

### 11. 원문 사용 사례 병기

- **위치**: 6개 문서 전체
- **현재**: 모든 문서에서 원문의 사용 사례가 독자적 예시로 완전 대체됨
- **제안**: 각 문서에 "원문 예시"와 "확장 예시"를 구분하여 제시하면, 원본 아티클과의 추적성을 확보하면서도 추가 가치를 제공할 수 있음

### 12. 자율 에이전트에 3대 구현 원칙 추가

- **위치**: `06-autonomous-agent.md`
- **제안**: 원문의 에이전트 구현 3대 원칙을 별도 섹션으로 추가
  1. **환경의 단순화**: 에이전트가 작업하는 환경을 최대한 단순하게 설계
  2. **투명성 확보**: 명시적 계획 단계를 포함하여 에이전트의 의사결정 과정을 가시화
  3. **ACI 설계**: 도구 문서화, 도구 수 최소화, 성공/실패 신호 명시

### 13. Mermaid 구문 경미한 문제 수정

- `03-parallelization.md:97` - gantt 차트의 `axisFormat %s초`에서 `%s`는 d3-time-format에서 Unix epoch 초를 반환하므로, 축 레이블이 의도와 다른 큰 숫자로 표시될 수 있음
- `05-evaluator-optimizer.md:57` - 엣지 라벨의 `≥` 유니코드 특수문자가 일부 렌더러에서 호환성 문제 가능 (경미)

---

## Positive Findings

- **풍부한 다이어그램 구성**: 16개 Mermaid 다이어그램을 5가지 유형(flowchart, sequenceDiagram, stateDiagram-v2, gantt, quadrantChart)으로 활용. 원문보다 훨씬 다양한 시각 자료로 학습 효과 극대화. 특히 `03-parallelization.md`의 간트 차트(순차/병렬 시간 비교), `06-autonomous-agent.md`의 상태 다이어그램과 코딩 에이전트 시퀀스가 우수
- **원문 스타일 기본 + 상세 확장 이중 구조**: 각 문서의 첫 번째 다이어그램이 원문의 간결한 스타일을 따르고, 이후 상세 아키텍처/시퀀스 다이어그램으로 확장하는 구조가 효과적
- **한국어 품질**: 전문 용어 영문 병기(예: "집계기 Aggregator", "게이트 gate")로 원문 추적성 유지. 문체가 자연스럽고 문법 오류 없음
- **장단점 분석의 실용성**: 원문의 간결한 설명을 실무 의사결정에 도움되는 수준으로 확장
- **다양한 추가 학습 자료**: Anthropic 원문 외 Google Cloud, LangChain, LlamaIndex, 관련 논문(ReAct, Constitutional AI, Reflexion) 등 폭넓은 참고 자료 제공
- **Mermaid 구문 품질**: 16개 다이어그램 중 14개 완전 정상, 2개 경미한 호환성 이슈만 존재. 참조 URL도 모두 올바른 경로(`/engineering/`)로 수정 완료
