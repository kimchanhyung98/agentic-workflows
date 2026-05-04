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

## 계약 간 관계

3가지 계약은 독립적이 아니라 상호 참조합니다.

| 관계 | 설명 |
|------|------|
| Agent Card → State Schema | Gate 평가 결과를 State에 기록 |
| Result Envelope → State Schema | Worker 상태(completed/escaped/failed)를 State에 반영 |
| Agent Card → Result Envelope | `output.structured_result`가 Envelope의 `result` 스키마를 정의 |
| State Schema → Agent Card | `phases[phase].retries`가 `gate.retry.max`와 비교됨 |

---

## 관련 계약

이 문서가 다루는 3가지 계약 외에, host와 LLM 공급자 사이의 경계를 정의하는 [Provider Contract](/.draft/pattern-composition/04-provider-contract.md)도 조합의 핵심 계약입니다. Agent Card의 `provider` 필드가 Provider Contract의 capability 요구를 선언하고, Result Envelope의 `provider` 필드가 실행한 공급자를 기록합니다.

---

## 참고 자료

- [순차 패턴](/design-pattern/02-sequential.md) — Phase 연결의 base 패턴
- [검토-비평 패턴](/design-pattern/05-review-critique.md) — Gate 평가의 base 패턴
- [반복 개선 패턴](/design-pattern/06-iterative-refinement.md) — 재시도/재계획의 base 패턴
- [실패 분류](/.draft/pattern-composition/03-failure-taxonomy.md) — 계약 부재로 발생하는 실패
