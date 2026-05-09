# 조합 계약 (Composition Contracts)

패턴을 조합할 때, base 패턴 문서에 명시되지 않은 인터페이스가 필요합니다.
이 문서의 계약은 단일 시스템 구현에서 도출한 것입니다. 다른 구현에서는 다른 형태의 계약이 필요할 수 있습니다.

---

## Agent Card — Phase 간 런타임 계약

> **용어 주의**: 이 문서의 "Agent Card"는 Phase별 런타임 계약(입출력/Gate/재시도)을 의미하며, [A2A Protocol](https://a2a-protocol.org/latest/specification/)의 Agent Card(에이전트 발견용 메타데이터)와는 다른 개념입니다. 업계에서는 이 개념을 CrewAI의 "Task contract", LangGraph의 "Node schema(input_schema/output_schema)", 또는 일반적으로 "Step definition"으로 부릅니다.

### 문제

[순차 패턴](/design-pattern/02-sequential.md)은 "에이전트 출력이 다음 에이전트의 입력"이라고 설명합니다. 그러나 실제 조합에서는 다음 질문에 답해야 합니다.

- 이 Phase에 어떤 파일이 필요한가?
- Gate 통과 조건은 무엇인가?
- 실패하면 몇 번까지 재시도하는가?
- 재시도 소진 후 어느 Phase로 돌아가는가?

### 최소 스키마

```json
{
  "phase": "review",
  "description": "설계 문서와 코드의 정합성을 검토합니다",
  "input": {
    "required_artifacts": [
      {"key": "spec", "path": "artifacts/spec.md"}
    ]
  },
  "output": {
    "artifacts": [
      {"key": "review_report", "path": "artifacts/review-report.md", "format": "markdown"}
    ],
    "structured_result": {
      "conclusion": "PASS|FAIL",
      "findings": [],
      "coverage": {"percentage": 0}
    }
  },
  "gate": {
    "id": "G2",
    "pass_conditions": [
      "findings.count(severity=CRITICAL) == 0",
      "coverage.percentage >= 80"
    ],
    "retry": {"max": 3},
    "on_pass": {"next_phase": "approve"},
    "on_fail": {
      "critical_found": "plan",
      "default": "prompt_user"
    }
  }
}
```

### 설계 근거

Phase를 독립적으로 교체할 수 있게 만듭니다. Agent Card만 교체하면 Gate 조건, 재시도 정책, 라우팅이 함께 바뀝니다. Phase 구현 코드를 수정할 필요가 없습니다.

### 이 계약이 없으면 발생하는 실패

- **Infinite/Unbounded**: 재시도 예산이 정의되지 않아 무한 반복 ([실패 분류 유형 4](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Ghost Decision**: Gate 실패 후 라우팅이 없어 단계가 정체 ([실패 분류 유형 3](/.draft/pattern-composition/03-failure-taxonomy.md))

---

## Result Envelope — Worker 결과 전달 표준

### 문제

[검토-비평 패턴](/design-pattern/05-review-critique.md)은 "비평 에이전트가 검증"한다고 설명합니다. 그러나 Worker가 정상 완료하지 못한 경우를 다루지 않습니다.

- 의존성이 없어서 작업을 완료할 수 없다면?
- 요구사항이 모호해서 범위를 벗어났다면?
- 시간 초과로 부분 결과만 있다면?

### 최소 스키마

```jsonc
{
  "status": "completed|escaped|failed",     // 필수. 세 값 중 하나
  "phase": "review",                         // 필수
  "provider": "provider-name",               // 필수
  "result": {                                // status=completed일 때 필수, escaped/failed일 때 선택
    "conclusion": "PASS",
    "findings": [],
    "coverage": {"percentage": 85}
  },
  "escape": {                                // status=escaped일 때 필수, 그 외 null
    "severity": "blocking|degraded|advisory",
    "reason": "scope_divergence|missing_dependency|contract_conflict|unknown",
    "summary": "요구사항 범위가 설계 문서와 불일치합니다",
    "recommended_action": "replan|user_decision|abort|continue|escalate"
  },
  "meta": {                                  // 선택
    "format_version": 1
  }
}
```

**상태별 필드 조건**:

| status | result | escape |
|--------|--------|--------|
| completed | 필수 (structured output) | null |
| escaped | 선택 (부분 결과) | 필수 (severity + reason) |
| failed | 선택 | null |

### 설계 근거

정상 경로(`completed`)와 비정상 경로(`escaped`, `failed`)를 하나의 스키마로 통합합니다. `escape` 필드의 `severity`와 `reason` 조합으로 자동 판정(continue/replan/abort/escalate/user_decision)이 가능해집니다.

### 이 계약이 없으면 발생하는 실패

- **Silent Data Loss**: Worker가 이탈했지만 reason/evidence가 무시됨 ([실패 분류 유형 2](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Ghost Decision**: 이탈이 발생했으나 기록되지 않아 후속 Phase가 잘못된 전제로 진행

---

## State Schema — 파이프라인 진행 상태

### 문제

[반복 개선 패턴](/design-pattern/06-iterative-refinement.md)은 "다중 사이클에 걸친 개선"을 설명합니다. 그러나 상태를 어디에 저장하는지 정의하지 않습니다.

- LLM 컨텍스트에 저장하면 Provider 교체 시 상태를 잃습니다.
- 세션이 끊기면 어디서부터 재개해야 하는지 알 수 없습니다.
- 두 프로세스가 동시에 같은 워크플로우를 실행하면 상태가 손상됩니다.

### 최소 스키마

```json
{
  "id": "2026-04-09-feature-x",
  "currentPhase": "impl",
  "totalExecutions": 12,
  "phases": {
    "plan": {"status": "completed", "retries": 0},
    "review": {"status": "completed", "retries": 1},
    "impl": {"status": "in_progress", "retries": 0}
  },
  "gates": {
    "G1": {"passed": true},
    "G2": {"passed": true, "checkedAt": "2026-04-09T10:30:00+09:00"}
  },
  "loop": {
    "replanCount": 1,
    "maxReplans": 3
  },
  "history": []
}
```

### 설계 근거

모든 상태를 파일 시스템에 JSON으로 외부화합니다. LLM 컨텍스트에 의존하지 않으므로 Provider 교체, 세션 재개, 감사 추적이 가능합니다. 원자적 쓰기(tmp → rename)는 부분 쓰기/찢어진 파일을 방지하는 수준이며, writer 간 직렬화가 필요하면 별도 파일락(`fcntl.flock`, `filelock` 등)을 병행해야 합니다.

### 이 계약이 없으면 발생하는 실패

- **State Corruption**: 동시 쓰기로 JSON 손상 ([실패 분류 유형 5](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Stale State Reuse**: 파일 변경 후 이전 상태로 재개 ([실패 분류 유형 1](/.draft/pattern-composition/03-failure-taxonomy.md))

---

## Readiness Gate — 실행 전 자동화 판정 계약

### 문제

에이전트용 CLI나 skill은 "먼저 상태를 확인하라"는 자연어 지침만으로는 충분히 안전하지 않습니다. 실제 조합에서는 다음 질문에 답해야 합니다.

- 이 repo에서 지금 provider-backed 분석을 실행해도 되는가?
- workflow를 새로 만들거나 다음 phase로 진행해도 되는가?
- operations wiki 같은 장기 기억 surface를 갱신해도 되는가?
- Claude/Codex entrypoint가 preflight를 했더라도, 사용자가 직접 CLI 명령을 실행하면 같은 stop condition이 적용되는가?

### 최소 스키마

```jsonc
{
  "gate": "analysis",                     // inspect|analysis|workflow-init|workflow-run|operations
  "decision": "allow",                    // allow|dry_run_only|block
  "automation_level": "L2_analysis",
  "reasons": [
    {
      "code": "workflow_state_missing",
      "severity": "block",
      "message": ".workflow/state.json is missing"
    }
  ],
  "recommended_commands": [
    "awf ready --repo-root .",
    "awf wf init <concept> --repo-root ."
  ]
}
```

### 설계 근거

Readiness Gate는 repo-level 상태를 먼저 구조화한 뒤 intent별 실행 가능성을 판정합니다. `allow`는 그대로 진행, `dry_run_only`는 조회/시뮬레이션만 허용, `block`은 상태 전이를 중단합니다.

계약은 두 겹으로 적용됩니다.

- **External preflight**: Claude Code skill, Codex runner, `AGENTS.md` snippet 같은 entrypoint가 실행 전에 `ready --gate`를 호출하고 exit code를 따릅니다.
- **Command-internal enforcement**: 실제로 상태를 바꾸거나 provider를 호출하는 CLI 명령이 같은 gate를 내부에서 다시 확인합니다.

두 겹을 분리하는 이유는 UX와 안전 경계가 다르기 때문입니다. External preflight는 사용자에게 다음 안전 명령을 빨리 보여주고, command-internal enforcement는 사용자가 wrapper를 우회해도 같은 invariant를 보존합니다. 조회성 명령(`status`, `log`, `lint`, `--dry-run`, `--check`)은 gate로 막지 않아야 첫 5분 탐색이 가능해집니다.

### 이 계약이 없으면 발생하는 실패

- **Ghost Decision**: readiness report를 읽었지만 자연어 판단으로 provider 실행이 계속됨 ([실패 분류 유형 3](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Contract Drift**: wrapper는 gate를 적용하지만 직접 CLI 명령은 gate 없이 상태를 변경함
- **Stale State Reuse**: workflow state나 operations profile이 없는 repo에서 이전 세션 전제를 재사용해 진행

### 관찰된 사례

`ai-workflow-tools`는 PR #37~#39에서 같은 계약을 단계적으로 적용했습니다.

- PR #37: `awf ready`를 read-only repo readiness report로 추가. config/provider/skill/scan/workflow/operations 상태와 추천 명령을 한 보고서로 묶음.
- PR #38: `awf ready --gate inspect|analysis|workflow-init|workflow-run|operations --json`을 deterministic preflight로 추가. Claude/Codex entrypoint가 `allow|dry_run_only|block`과 exit code를 따름.
- PR #39: `awf analyze`, `awf wf init`, `awf wf next`, `awf wiki decision`, `awf wiki regenerate-index`, non-dry-run `awf wiki compile`이 내부에서 같은 gate를 기본 실행. read-only/dry-run 경로는 유지하고 `--no-ready-gate`를 명시적 escape hatch로 둠.

이 사례는 "처음 쓰는 사용자가 설명서를 읽고 순서를 맞춘다"는 가정을 제거하고, 구조화된 readiness model과 결정론적 gate가 실행 순서를 강제하는 방식입니다.

---

## Prior Threading — Step 간 결과 전달 방식

### 문제

[순차 패턴](/design-pattern/02-sequential.md)은 "에이전트 출력이 다음 에이전트의 입력"이라고 설명합니다. 그러나 Step N의 결과가 Step N+1로 *어떻게* 전달되는지는 미정입니다.

- 같은 role이 같은 산출물을 여러 step에 걸쳐 정제한다면, prior 결과는 함수 인자로 받아야 하는가, 아니면 외부 store에서 다시 읽어야 하는가?
- 다른 role들이 결과를 공유한다면, 누가 어디에 쓰고 누가 어디서 읽는지를 어떤 형태로 선언하는가?
- 재시도/재개 시 prior 결과를 다시 만들지, 아니면 보존된 것을 재사용할지 결정 가능한가?

### 최소 스키마 — 두 형태

**Form A — Direct Factory Threading**: chain 안에서 prior 결과를 다음 step의 spec 빌더로 직접 전달합니다. 같은 role이 한 산출물을 점진적으로 정제하는 chain에 자연스럽습니다.

```python
class StepFactory(Protocol):
    """prior_results를 받아 다음 Step의 spec을 빌드하는 순수 함수."""
    def __call__(self, prior_results: list[ResultEnvelope]) -> StepSpec: ...

@dataclass
class ChainedStep:
    role: str
    factory: StepFactory

# Caller (chain runner)는 prior 결과를 누적해 다음 factory에 주입
results: list[ResultEnvelope] = []
for step in steps:
    spec = step.factory(prior_results=results)
    results.append(run_one(spec))
```

- prior 결과는 in-memory `list[ResultEnvelope]` (즉 Result Envelope 계약과 직결).
- factory는 부수효과 없는 pure builder. 외부 store 쓰기/읽기 없음.
- 같은 role이 여러 step에 등장하면 동일 worker를 재사용해 단말 컨텍스트가 누적되도록 구현 가능.

**Form B — Blackboard Threading**: step들이 공유 artifact store(파일/DB/메모리)에서 prior 결과를 읽고 자기 결과를 씁니다. 다른 role들이 DAG로 협업할 때 자연스럽습니다.

```jsonc
// Step 1
{
  "step": {"role": "review", "n": 1},
  "reads":  ["artifacts/spec.md"],
  "writes": ["artifacts/review-1.md"]
}
// Step 2 — review-1을 보고 verify를 수행
{
  "step": {"role": "verify", "n": 2},
  "reads":  ["artifacts/spec.md", "artifacts/review-1.md"],
  "writes": ["artifacts/verify-1.md"]
}
```

- prior 결과는 store의 path로 참조. step은 path 계약만 알면 동작.
- writer/reader가 다른 role이어도 path로 분리되므로 loose coupling.
- 재시도/재개 시 store에 남은 partial state 재사용 가능 (Form A는 in-memory 누적이라 재실행 필요).

### 설계 근거

선택은 chain의 형상이 결정합니다.

- **Linear chain of same-role refinement** — Form A. prior 결과가 데이터로 주입되므로 결정론적이고 외부 store 불필요. Worker 재사용 최적화 (단말 컨텍스트 누적)가 가능합니다.
- **DAG with multiple roles** — Form B. role 간 결합이 path 계약 한 겹뿐이라 한쪽 role을 갈아끼워도 다른 step들이 영향받지 않습니다. Audit/recovery에 유리합니다.

한 시스템에서 두 형태가 공존할 수 있고, 자주 그렇습니다. 핵심은 **하나의 step이 어느 form을 가정하는지가 spec에 명시되어야** 한다는 것입니다 — 그래야 caller(chain runner / pipeline)가 적절한 threading 경로를 선택할 수 있습니다.

### 이 계약이 없으면 발생하는 실패

- **Silent Data Loss**: Form A 의도였는데 caller가 prior 결과를 factory에 안 넘기면, step은 "처음 실행"처럼 동작 ([실패 분류 유형 2](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Stale State Reuse**: Form B 의도였는데 step이 store path를 잘못 읽으면, 이전 사이클의 산출물로 진행 ([실패 분류 유형 1](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Contract Drift**: 같은 step의 caller마다 form을 다르게 가정하면, 한 caller에서는 동작하던 step이 다른 caller에서는 prior 결과를 못 받습니다.

### 관찰된 사례

이 두 form은 단일 시스템에서 공존하는 사례가 있습니다 (`ai-workflow-tools`, dispatch series).

- **Form A — `MultiAgentDispatch.run_chained(steps)`** (PR #27, [ADR](https://github.com/coldplay126/ai-workflow-tools/blob/main/.awf-operations/wiki/decisions/2026-05-09-run-chained-option-a.md)): critical mode (codex precision → sonnet impact → primary judgment)는 같은 산출물을 단계적으로 정제. `ChainedStep(role, factory)`의 factory가 `prior_results`를 받아 다음 spec을 lazy build. cmux backend는 같은 role의 worker를 chain 전체에 pin해 단말 컨텍스트가 자연스럽게 누적되도록 구현.
- **Form B — `team_runner` + 공유 blackboard** (PR #31, [ADR](https://github.com/coldplay126/ai-workflow-tools/blob/main/.awf-operations/wiki/decisions/2026-05-09-team-runner-dispatch-not-run-chained.md)): team mode는 각기 다른 role(`happy_path` / `adversarial` 등)이 공유 blackboard에 결과를 누적. 각 worker의 prompt builder가 blackboard에서 prior 결과를 읽음. **`run_chained`를 쓰지 않는 이유**가 ADR로 기록됨 — distinct roles라 cmux pinning 이득이 없고, blackboard 부수효과를 factory에 넣는 것은 "pure builder" 가정 위반.

같은 시스템이 두 form을 상황에 따라 선택한다는 점이 핵심 evidence입니다.

---

## 계약 간 관계

5가지 계약은 독립적이 아니라 상호 참조합니다.

| 관계 | 설명 |
|------|------|
| Agent Card → State Schema | Gate 평가 결과를 State에 기록 |
| Result Envelope → State Schema | Worker 상태(completed/escaped/failed)를 State에 반영 |
| Agent Card → Result Envelope | `output.structured_result`가 Envelope의 `result` 스키마를 정의 |
| State Schema → Agent Card | `phases[phase].retries`가 `gate.retry.max`와 비교됨 |
| Readiness Gate → Agent Card | intent별 실행 가능성이 phase/gate 실행 전에 평가됨 |
| Readiness Gate → State Schema | workflow state 존재 여부와 operations profile 상태가 gate decision 입력이 됨 |
| Prior Threading (A) → Result Envelope | factory가 받는 `prior_results` 항목이 Envelope 스키마를 따름 |
| Prior Threading (B) → State Schema | blackboard `reads`/`writes` path가 State에 기록됨 (recovery에서 재사용) |
| Prior Threading → Agent Card | step의 input/output 정의가 어느 form을 가정하는지 spec에 명시되어야 함 |

---

## 관련 계약

이 문서가 다루는 5가지 계약 외에, host와 LLM 공급자 사이의 경계를 정의하는 [Provider Contract](/.draft/pattern-composition/04-provider-contract.md)도 조합의 핵심 계약입니다. Agent Card의 `provider` 필드가 Provider Contract의 capability 요구를 선언하고, Result Envelope의 `provider` 필드가 실행한 공급자를 기록합니다.

---

## 참고 자료

- [순차 패턴](/design-pattern/02-sequential.md) — Phase 연결의 base 패턴
- [검토-비평 패턴](/design-pattern/05-review-critique.md) — Gate 평가의 base 패턴
- [반복 개선 패턴](/design-pattern/06-iterative-refinement.md) — 재시도/재계획의 base 패턴
- [실패 분류](/.draft/pattern-composition/03-failure-taxonomy.md) — 계약 부재로 발생하는 실패
