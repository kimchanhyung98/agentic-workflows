# Operations Wiki Pattern

운영 이벤트, PR, 결정 기록을 에이전트가 다시 읽을 수 있는 wiki로 누적하는 패턴입니다.
Karpathy의 LLM Wiki 아이디어를 개인 지식베이스가 아니라 에이전틱 시스템의 운영 기억(operational memory)에 적용합니다.

이 문서는 특정 구현을 표준으로 선언하지 않습니다. 패턴 조합 문서와 같은 성격의 초안이며, `awf wiki compile` 사례를 부록으로 사용해 경계를 설명합니다.

---

## 핵심 아이디어

일반적인 운영 분석은 매번 raw 로그, PR 본문, 실행 결과를 다시 검색하고 요약합니다. 이 방식은 RAG와 비슷하게 동작합니다. 질문할 때마다 근거 조각을 다시 찾고, 같은 판단을 반복하며, 이전 세션에서 만든 synthesis가 누적되지 않습니다.

Operations Wiki는 이 흐름을 바꿉니다.

1. raw source는 수정하지 않고 보존합니다.
2. 에이전트나 deterministic compiler가 raw source를 읽어 markdown wiki page로 컴파일합니다.
3. wiki page는 provenance, confidence, 관련 page 링크를 frontmatter에 기록합니다.
4. 이후 에이전트는 raw source 전체가 아니라 컴파일된 wiki를 먼저 읽고 판단합니다.
5. 새 운영 이벤트나 새 질문이 생기면 wiki를 갱신해 지식이 세션 밖에 남습니다.

핵심은 "검색"이 아니라 "컴파일"입니다. 운영 지식은 매번 재생성되는 답변이 아니라, git에 남는 누적 artifact가 됩니다.

---

## 3-Layer 구조

Karpathy의 LLM Wiki는 raw sources, wiki, schema의 3개 layer로 설명할 수 있습니다. Operations Wiki도 같은 구조를 따르지만, raw source의 성격이 운영 데이터로 바뀝니다.

| Layer | Operations Wiki에서의 형태 | 소유자 | 변경 규칙 |
|-------|----------------------------|--------|-----------|
| Raw sources | JSONL 이벤트, PR 본문, 커밋, CI 결과, ADR, 실행 로그 | 시스템/사람 | append-only 또는 외부 시스템의 원본 그대로 보존 |
| Wiki | `operations/`, `decisions/`, `concepts/` 아래 markdown page | compiler 또는 LLM | source를 근거로 갱신. 사람이 직접 사실을 invent하지 않음 |
| Schema | AGENTS/CLAUDE 지침, frontmatter 규칙, topic registry, lint rule | 사람 + 에이전트 | wiki가 커지며 진화. 변경 시 migration 또는 `metric_method` 기록 |

이 구조에서 wiki는 raw source의 복사본이 아닙니다. raw source를 읽고 얻은 운영 의미를 축약, 연결, 비교한 working layer입니다.

---

## 운영 루프

### Ingest

새 운영 source를 받아 wiki에 반영합니다.

- 이벤트 스트림을 topic별로 묶습니다.
- PR/commit/ADR에서 결정 맥락을 추출합니다.
- 관련 page의 frontmatter와 본문을 갱신합니다.
- `index.md` 또는 catalog를 재생성합니다.

### Query

사용자나 에이전트가 운영 질문을 던지면 raw source 전체를 먼저 뒤지지 않습니다.

- `index.md`로 관련 page를 찾습니다.
- compiled page의 provenance와 confidence를 확인합니다.
- 답변 중 새 insight가 생기면 새 page나 결정 기록으로 되돌려 저장합니다.

### Lint

wiki가 커질수록 health check가 필요합니다.

- stale page: `last_compiled_at` 또는 `event_window`가 오래됨
- orphan page: inbound/outbound link가 없음
- provenance gap: source event, PR, commit, ADR 연결이 없음
- schema drift: 같은 topic이 다른 metric 의미로 덮어써짐
- low-confidence overreach: 표본이 적은데 결론이 단정적으로 쓰임

Lint는 wiki를 "예쁘게" 만들기 위한 단계가 아니라, 에이전트가 오래된 운영 지식을 사실처럼 재사용하지 못하게 하는 안전장치입니다.

---

## Deterministic Evidence와 LLM Narrative의 경계

Operations Wiki에서 가장 중요한 설계 경계는 evidence layer와 narrative layer를 분리하는 것입니다.

| Layer | 역할 | 권장 구현 |
|-------|------|-----------|
| Deterministic evidence | 이벤트 집계, 카운트, 기간, provenance, confidence 계산 | stdlib/SQL/CLI 같은 결정론적 코드 |
| LLM narrative | 경향 해석, 원인 후보, follow-up 질문, 운영 개선 제안 | opt-in LLM pass |

처음부터 LLM이 raw event를 읽고 운영 page를 쓰게 만들면 빠르게 그럴듯한 문서가 생기지만, 작은 표본이나 누락된 이벤트를 과도하게 일반화할 위험이 큽니다. 반대로 deterministic compiler가 먼저 evidence page를 만들면, LLM은 그 위에서 해석만 담당할 수 있습니다.

권장 순서:

1. raw source와 schema를 먼저 안정화합니다.
2. deterministic compiler로 재현 가능한 operations page를 만듭니다.
3. 충분한 이벤트 수와 시간 범위가 생긴 뒤 LLM narrative를 opt-in으로 추가합니다.
4. LLM이 쓴 해석은 evidence page와 분리하거나 frontmatter에 `confidence`와 source를 명시합니다.

---

## 최소 계약

Operations Wiki가 재사용 가능하려면 다음 계약이 필요합니다.

### Raw Source Contract

- 원본 이벤트와 로그는 append-only로 유지합니다.
- compiled page가 source를 대체하지 않습니다.
- source identifier(event id, timestamp, PR number, commit SHA)를 page frontmatter나 본문에 남깁니다.

### Page Contract

모든 wiki page는 최소 frontmatter를 갖습니다.

```yaml
---
title: Stage 1 import-graph invalidation
last_compiled_at: 2026-05-09T00:00:00+00:00
confidence: low
source_commits: [344da98]
context_prs: ["#32"]
related: []
---
```

이벤트 집계 page는 추가 provenance를 갖는 것이 좋습니다.

```yaml
event_window: [2026-05-01, 2026-05-09]
event_count: 42
event_types: [stage1_invalidation]
metric_method: deterministic_v1
```

### Schema Contract

- page type별 필수 섹션을 정의합니다.
- topic registry가 어떤 event type을 어떤 page로 컴파일하는지 선언합니다.
- `metric_method`를 기록해 aggregator 의미가 바뀌었을 때 silent overwrite를 막습니다.
- confidence 산정 규칙을 문서화합니다.

### Index/Log Contract

- `index.md`는 현재 wiki page catalog입니다. 에이전트가 query 시작점으로 읽습니다.
- `log.md`는 append-only chronology입니다. 최근 ingest/query/lint 흐름을 복원합니다.
- index는 재생성 가능해야 하고, log는 원본 chronology로 남겨야 합니다.

---

## 실패 모드

| 실패 | 증상 | 완화 |
|------|------|------|
| Re-derived Every Query | 에이전트가 매번 raw 로그와 PR을 다시 요약 | compiled wiki page를 우선 읽고, raw source는 drill-down으로 사용 |
| Narrative Without Evidence | 그럴듯한 운영 결론이 있지만 source/event 연결이 없음 | frontmatter provenance, source table, confidence 필수화 |
| Stale Compiled Page | 새 이벤트가 있는데 오래된 집계가 재사용됨 | `last_compiled_at`, `event_window`, lint stale rule |
| Low-Confidence Overgeneralization | 1-2건 표본으로 정책을 단정 | 표본 수/기간 기반 confidence, low confidence page의 language 제한 |
| Schema Drift | 같은 page가 다른 metric 의미로 덮어써짐 | `metric_method`와 schema changelog |
| Source Mutation | LLM이 raw log나 PR 복사본을 수정 | raw source read-only/append-only 원칙 |
| Wiki Bloat | page가 너무 커져 query 시작점으로 부적합 | topic registry, page split rule, index regeneration |

---

## 기존 패턴과의 관계

Operations Wiki는 단일 base pattern이 아니라 조합 패턴입니다.

| base 패턴 | Operations Wiki에서의 역할 |
|-----------|----------------------------|
| [순차 패턴](/design-pattern/02-sequential.md) | ingest → compile → index → lint 순서 |
| [루프 패턴](/design-pattern/04-loop.md) | 새 이벤트가 쌓일 때 반복 compile |
| [맞춤 로직 패턴](/design-pattern/12-custom-logic.md) | metric 집계, confidence 계산, schema lint |
| [인간 참여형 패턴](/design-pattern/11-human-in-the-loop.md) | contested decision, low-confidence 해석, schema 변경 승인 |

base pattern 문서는 "운영 지식이 어디에 누적되는가"를 다루지 않습니다. Operations Wiki는 이 누적 계층을 별도 artifact로 둡니다.

---

## 부록: awf `wiki compile` 사례

`ai-workflow-tools` PR #32는 Operations Wiki의 evidence-first 변형입니다.

### 입력

- raw source: `.awf-operations/events/*.jsonl`
- 보조 source: `log.md`, PR 본문, 운영 ADR
- profile: `self_improvement`

### 컴파일 대상

PR #32는 deterministic compiler로 4개 operations page를 생성합니다.

| Topic page | Source event |
|------------|--------------|
| `stage1-invalidation.md` | `stage1_invalidation` |
| `scope-check.md` | `scope_check` |
| `dispatch-performance.md` | `dispatch_complete` |
| `dual-strategy-promotions.md` | `dual_strategy_engaged` |

`analysis_complete`는 PR #36 이후 `source_file_count`, `bundle_line_count`, `bundle_token_estimate`, `output_file_count`를 추가로 갖지만, 여전히 단일 실행 telemetry입니다. 충분한 event volume과 threshold가 정해지기 전까지는 compile topic으로 승격하지 않았습니다. 이 결정은 topic registry가 모든 event를 무조건 page로 만들 필요는 없다는 예시입니다.

### Schema

PR #32는 operations page frontmatter를 확장했습니다.

```yaml
event_window: [start, end]
event_count: 0
event_types: [dispatch_complete]
metric_method: deterministic_v1
confidence: low
```

`metric_method: deterministic_v1`은 aggregator 의미를 고정합니다. 나중에 percentile 계산, bucket 구분, confidence threshold가 바뀌면 새 method로 올려야 합니다.

### 설계 판단

이 사례의 핵심 판단은 LLM을 compiler 안에 넣지 않은 것입니다.

- output은 이벤트 로그만으로 재현 가능합니다.
- 0-event 상태에서도 실패하지 않고 skip note를 남깁니다.
- compile 후 index를 재생성해 query 시작점을 갱신합니다.
- LLM narrative는 이벤트가 충분히 누적된 뒤 `--with-llm` 같은 opt-in으로 붙일 수 있습니다.

이 구조는 Karpathy LLM Wiki의 "지식 누적" 목적과 맞지만, 초기 layer는 LLM이 아니라 deterministic compiler가 소유합니다. 운영 데이터에서는 이 보수적 경계가 중요합니다. evidence가 약한 상태에서 LLM이 먼저 narrative를 만들면, wiki가 기억 장치가 아니라 hallucination을 보존하는 장소가 될 수 있습니다.

### 남은 확장 지점

- 100개 이상 operations page가 쌓인 뒤 cross-topic synthesis page 생성
- low-confidence page를 LLM이 단정적으로 인용하지 못하게 query prompt 보강
- lint가 `event_window`, `event_count`, `metric_method` 누락을 검사
- schema migration 기록을 ADR과 연결

### 후속 확장: ready-gated operations writes

PR #37~#39는 Operations Wiki를 단순한 compile artifact가 아니라 repo automation surface의 일부로 다루기 시작한 사례입니다.

첫 단계는 `awf ready`입니다. 이 명령은 config, provider, skill, heuristic scan, workflow, operations 상태를 read-only로 모아 repo가 지금 어떤 자동화 수준에 있는지 보고합니다. 사용자는 `doctor`, `scan`, `skills list`, `wf status`, `wiki init`을 따로 조합하지 않고 한 번의 check로 다음 안전 명령을 확인합니다.

두 번째 단계는 `awf ready --gate`입니다. gate는 `inspect`, `analysis`, `workflow-init`, `workflow-run`, `operations` 같은 intent별로 `allow`, `dry_run_only`, `block` 결정을 JSON에 담고, `allow`가 아니면 non-zero exit로 Claude/Codex entrypoint를 멈춥니다. 자연어 지침에 "먼저 확인하세요"라고 쓰는 대신, host runner와 skill이 같은 결정론적 contract를 호출합니다.

세 번째 단계는 command-internal enforcement입니다. `awf wiki decision`, `awf wiki regenerate-index`, non-dry-run `awf wiki compile`은 기본적으로 operations gate를 내부에서 다시 확인합니다. 반대로 `wiki init`, `log`, `events`, `lint`, `compile --dry-run` 같은 조회/검사 경로는 막지 않습니다. `--no-ready-gate`는 상위 wrapper가 같은 gate를 이미 수행했을 때만 쓰는 명시적 escape hatch입니다.

이 후속 확장은 Operations Wiki 패턴의 중요한 경계를 보여줍니다. wiki write는 지식 축적 surface이므로, "에이전트가 읽는 memory"를 갱신하기 전에 repo가 operations write를 받아도 되는지 결정론적으로 판정해야 합니다. 첫 사용자의 5분 경험도 같은 원칙을 따릅니다. 설명서를 읽게 하기보다 read-only readiness report와 machine-enforced gate가 다음 행동을 결정합니다.

---

## 적용 체크리스트

1. raw source가 append-only 또는 외부 원본으로 보존되는가?
2. wiki page가 source identifier를 남기는가?
3. compiler output이 같은 input에서 재현 가능한가?
4. confidence가 표본 수와 시간 범위를 반영하는가?
5. schema 변경이 `metric_method`나 ADR로 추적되는가?
6. 에이전트가 query할 때 `index.md`를 시작점으로 삼는가?
7. low-confidence page를 정책 결정 근거로 쓸 때 사람 검토가 들어가는가?

---

## 참고 자료

- [Karpathy: LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LLM Wiki reference app](https://llmwiki.app/)
- [ai-workflow-tools PR #32: `awf wiki compile`](https://github.com/coldplay126/ai-workflow-tools/pull/32)
- [ai-workflow-tools PR #36: `analysis_complete` metrics](https://github.com/coldplay126/ai-workflow-tools/pull/36)
- [ai-workflow-tools PR #37: `awf ready`](https://github.com/coldplay126/ai-workflow-tools/pull/37)
- [ai-workflow-tools PR #38: deterministic ready gates](https://github.com/coldplay126/ai-workflow-tools/pull/38)
- [ai-workflow-tools PR #39: command-internal ready gates](https://github.com/coldplay126/ai-workflow-tools/pull/39)
- [패턴 조합](/.draft/pattern-composition/README.md)
