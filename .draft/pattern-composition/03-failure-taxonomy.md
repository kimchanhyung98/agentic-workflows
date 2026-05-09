# 실패 분류 (Failure Taxonomy)

패턴을 조합한 시스템에서 발견된 실패 유형을 분류합니다.

---

## 방법론

| 항목 | 내용 |
|------|------|
| 출처 | 단일 프로덕션 시스템 (4개 파이프라인: 분석, 워크플로우, 멀티에이전트, Blackboard) |
| 구현 | Python CLI, 26개 소스 파일, 약 5,700줄 |
| 방법 | spec ↔ 구현 대조 감사, 상태 머신 전이 분석, 동시성 경합 검토 |
| 원시 관찰 | 86건 (코드 경로별 개별 이슈) |
| 중복 제거 규칙 | 동일 유형 + 동일 근본 원인 → 1건. 예: "Gate G2 결과 미기록"과 "Gate G5 결과 미기록"은 같은 유형(Silent Data Loss) + 같은 원인(PHASE_GATE 매핑 불완전)이므로 1건 |
| **결과** | **26건, 12개 고유 실패 유형** |
| 한계 | 단일 시스템, 단일 언어(Python)에서 도출. 다른 언어, 아키텍처, 규모에서는 다른 유형이 발생할 수 있음 |

---

## 실패 유형 요약

| 유형 | 건수 | 비율 |
|------|------|------|
| Stale State Reuse | 6 | 23% |
| Silent Data Loss | 6 | 23% |
| Ghost Decision | 4 | 15% |
| Infinite/Unbounded | 2 | 8% |
| 기타 8개 유형 | 각 1건 | 각 4% |

상위 3개 유형이 전체의 62%를 차지합니다.

---

## 유형 1: Stale State Reuse (6건)

오래된 상태나 캐시를 새 실행에서 그대로 사용하는 실패입니다.

### 발생 시점

파이프라인을 재개하거나, 입력 파일이 변경된 후 다시 실행할 때 발생합니다.

### 촉발하는 패턴 조합

[순차 패턴](/design-pattern/02-sequential.md) + 점진적 재개, 또는 캐시 + 다단계 의존성.

### 증상

- 변경된 파일이 반영되지 않은 결과가 출력됩니다
- Stage 1이 미완료인데 Stage 2 결과가 재사용됩니다
- 설정 변경 후에도 이전 번들이 사용됩니다

### 근본 원인

상태 무효화 로직이 누락되었습니다. 입력이 변경되면 의존하는 모든 하위 상태를 초기화해야 하지만, 일부 경로에서 이 초기화가 빠져 있었습니다.

### 완화

- 해시 기반 의존성 검증: 입력 해시 변경 시 하위 Layer 상태를 `pending`으로 초기화
- Stage 의존성 검증: Stage N 결과 재사용 전 Stage N-1 완료 여부 확인
- 캐시 키에 content hash 포함: 경로만이 아닌 내용 해시로 캐시 유효성 판단

---

## 유형 2: Silent Data Loss (6건)

데이터가 존재하지만 처리 경로에서 무시되는 실패입니다.

### 발생 시점

Worker가 비정상 종료하거나, 이벤트 핸들러가 특정 상태를 처리하지 않을 때 발생합니다.

### 촉발하는 패턴 조합

[순차 패턴](/design-pattern/02-sequential.md) + 결과 전달, 또는 이벤트 기반 처리 + 핸들러 누락.

### 증상

- Worker가 `escaped` 상태로 종료했지만, escape 이유와 증거가 보고서에 포함되지 않습니다
- Phase Gate 결과가 일부 Phase에서만 기록됩니다
- 멀티에이전트 모드에서 solo 실행의 이벤트가 누락됩니다

### 근본 원인

비정상 경로(escaped, failed)에 대한 처리 코드가 없었습니다. 정상 경로(completed)만 구현하고, 나머지는 예외 처리로 넘겼습니다.

### 완화

- Result Envelope의 모든 status 값(completed, escaped, failed)에 대해 명시적 핸들러 구현
- 전체 Phase에 대해 Gate 결과 기록 (일부가 아닌 전체)
- 이벤트 발행 조건에서 모드별 필터링 제거

---

## 유형 3: Ghost Decision (4건)

의사결정이 발생했으나 기록되지 않거나 실행되지 않는 실패입니다.

### 발생 시점

Gate 실패 후 라우팅, 모드 선택, 또는 Worker 결론 해석 과정에서 발생합니다.

### 촉발하는 패턴 조합

[검토-비평 패턴](/design-pattern/05-review-critique.md) + 라우팅, 또는 [코디네이터 패턴](/design-pattern/07-coordinator.md) + 모드 검증.

### 증상

- Gate 실패했지만 on_fail 핸들러가 없어 Phase가 정체합니다
- 잘못된 모드 문자열이 silent fallback으로 처리됩니다
- Worker가 FAIL을 결론지었지만 오케스트레이터가 PASS로 보고합니다

### 근본 원인

- 실패 경로에 라우팅 로직을 구현하지 않았습니다
- 입력 검증 없이 기본값으로 대체했습니다
- Worker의 structured output을 무시하고 프로세스 exit code만 확인했습니다

### 완화

- Agent Card의 on_fail 라우팅을 Gate 평가 코드에서 읽고 실행
- 유효하지 않은 모드는 silent fallback 대신 명시적 오류 발생
- Worker 결론(parsed JSON)을 프로세스 exit code보다 우선하여 판정

---

## 유형 4: Infinite/Unbounded (2건)

종료 조건 없이 같은 동작을 무한 반복하는 실패입니다.

### 발생 시점

Gate가 반복적으로 실패하거나, 재시도 예산이 정의되지 않았을 때 발생합니다.

### 촉발하는 패턴 조합

[반복 개선 패턴](/design-pattern/06-iterative-refinement.md) + Gate 평가.

### 증상

- 워크플로우가 종료되지 않고 같은 Phase를 반복합니다
- 토큰 비용이 예상의 수십 배로 증가합니다

### 근본 원인

- 전역 실행 횟수 제한이 없었습니다
- Phase별 재시도 예산이 Agent Card에 정의되어 있었지만, 코드에서 확인하지 않았습니다

### 완화

- 전역 실행 카운터: 전체 Phase 실행 횟수를 추적하고 상한(예: 30회) 초과 시 중단
- Phase별 재시도 예산: Agent Card의 `gate.retry.max`를 읽고 초과 시 Phase를 abort

---

## 유형 5-12: 기타 실패 유형

각 1건씩 발견된 실패 유형입니다. 유형별 대표 사례를 포함합니다.

### 유형 5: State Corruption (1건)

[병렬 패턴](/design-pattern/03-parallel.md) + 공유 상태 파일. 두 프로세스가 동시에 같은 상태 파일을 쓰면 JSON이 중간에 잘리거나 섞입니다. 대표 사례: 분석 재개와 이벤트 핸들러가 동시에 `.analysis-state.json`을 갱신하여 파일이 손상되었습니다. 완화: 원자적 쓰기(임시 파일 작성 후 rename) + 경로별 파일락(`fcntl.flock`, `filelock`, `portalocker` 등). 단일 프로세스 내 스레드만 다룬다면 `threading.Lock`으로 충분하지만, 멀티프로세스 환경에서는 파일락이 필요합니다.

### 유형 6: Invalid Transition (1건)

[반복 개선 패턴](/design-pattern/06-iterative-refinement.md) + Phase(단계) 순서. 재계획 시 현재 단계보다 뒤(순방향)로 이동하면 이미 완료된 단계를 건너뛰게 됩니다. 대표 사례: review 단계에서 실패 후 test 단계로 재계획이 허용되어 impl/verify를 건너뛰었습니다. 완화: 재계획 대상이 현재 단계 이전(역방향)인지 검증.

### 유형 7: Incomplete Recovery (1건)

[코디네이터 패턴](/design-pattern/07-coordinator.md) + 모드 강등. 고급 모드 실패 시 항상 최저 모드(solo)로 떨어지면, 중간 수준의 검증(precise)이 가능했음에도 건너뛰게 됩니다. 대표 사례: critical 모드에서 timeout 발생 시 cross나 precise를 시도하지 않고 바로 solo로 강등되었습니다. 완화: 에스컬레이션 체인(critical → cross → precise → solo).

### 유형 8: Timeout Starvation (1건)

[순차 패턴](/design-pattern/02-sequential.md) + 독립 timeout. 순차 체인의 각 단계에 독립 timeout을 주면, 앞 단계가 예산 대부분을 소비한 뒤 뒷 단계에 시간이 부족해집니다. 대표 사례: precise 모드에서 1단계(codex)가 85초를 사용하고, 2단계(primary)에도 120초가 주어져 총 205초가 소요되었습니다. 완화: 누적 경과 시간을 추적하고 잔여 budget을 다음 단계에 전달.

### 유형 9: Non-Deterministic (1건)

[병렬 패턴](/design-pattern/03-parallel.md) + 판정 규칙(Judge). 병렬 에이전트의 완료 순서가 실행마다 달라지면, 판정 규칙의 입력 순서도 달라져 같은 입력에 다른 결과가 나옵니다. 대표 사례: cross 모드에서 codex가 먼저 완료되는 경우와 sonnet이 먼저 완료되는 경우에 `agents[0]` 선택이 달라졌습니다. 완화: 판정 전에 결과를 provider 이름순으로 정렬.

### 유형 10: Over-provisioning (1건)

[코디네이터 패턴](/design-pattern/07-coordinator.md) + 자동 승격. 위험 키워드 감지로 모드를 승격하지만, 저위험 작업에서 강등하는 경로가 없으면 불필요한 고비용 모드가 실행됩니다. 대표 사례: 사용자가 명시적으로 critical 모드를 설정했지만 작업은 README 오타 수정이었습니다. 완화: 저위험 키워드(readme, typo, doc 등) 감지 시 자동 강등.

### 유형 11: Resource Leak (1건)

다단계 파이프라인 + 임시 파일. 각 단계가 중간 결과를 임시 파일로 저장하지만, 실패 후 재시도 시 이전 임시 파일이 정리되지 않으면 디스크가 누적됩니다. 대표 사례: Stage 2 실패 후 재시도했지만 이전 prompt/result 파일이 .tmp/에 남아 있었습니다. 완화: 상태 파일에서 참조하지 않는 임시 파일을 정리.

### 유형 12: Vague Error (1건)

Provider fallback + 에러 메시지. Provider가 사용 불가능할 때 에러 메시지가 "unavailable"만 표시하면, 사용자가 다음 조치를 알 수 없습니다. 대표 사례: quick 모드에서 codex가 설치되지 않았을 때 "codex unavailable"만 출력되었습니다. 완화: Provider 이름 + 구체적 조치 방법("install codex or use a different mode")을 포함한 메시지.

---

## 실패 유형 × 계약 관계

계약 부재가 실패를 유발하는 관계입니다.

| 계약 | 부재 시 발생 유형 | 건수 |
|------|-----------------|------|
| Agent Card | Infinite/Unbounded, Ghost Decision | 6 |
| Result Envelope | Silent Data Loss | 6 |
| State Schema | Stale State Reuse, State Corruption | 7 |

State Schema 관련 실패가 가장 많습니다(7건, 27%). 파이프라인 진행 상태를 외부화하지 않으면 재개, 동시성, 변경 감지에서 다양한 실패가 발생합니다.

---

## 부록: 보조 관측 — 외부 시스템 운영 데이터 (4건)

위 26건은 단일 시스템에서 도출되었습니다. 동일 패턴 조합이 다른 시스템에서 어떻게 다른 실패로 나타나는지 확인하기 위해, 별도 시스템(`ai-workflow-tools`, awf-cli + cmux-agent 모노레포, 2026-04~05 dispatch 시리즈 PR #25–#31)에서 관찰된 4건을 부록으로 정리합니다. 본 corpus(26건)에는 포함하지 않습니다.

### 유형 13: Async Warmup Race (1건, 보조)

[코디네이터 패턴](/design-pattern/07-coordinator.md) + 외부 워커 인프라. 워커 인프라(예: 별도 터미널 + AI CLI)가 처음 활성화될 때 부팅 비용(약 10–30초)을 지불하지만, per-call timeout 만 정의되어 있으면 첫 호출이 일관되게 시간 부족으로 실패합니다. 대표 사례: 첫 cmux dispatch 호출이 30초 워밍업으로 끝나고 두 번째부터는 정상 동작했습니다. 완화: 첫 호출에 warmup grace 가산(awf 의 `_CMUX_WARMUP_GRACE_SEC = 30`), 또는 워커 라이프사이클을 reusable 로 두어 같은 run 안에서 워밍업 비용을 1회만 지불. 출처: ai-workflow-tools PR #26, ADR `2026-05-09-cmux-dispatch-lifecycle-reusable-default`.

### 유형 14: Contract Drift Within Factory (1건, 보조)

[순차 패턴](/design-pattern/02-sequential.md) + lazy spec building. factory-pattern dispatch 에서 factory 가 호출 시점에 자유롭게 spec 을 만들 수 있다면, factory 가 선언한 role 과 반환 spec 의 role 이 일치한다는 보장이 없습니다. 대표 사례: `ChainedStep(role="x")` 의 factory 가 실수로 `role="y"` 인 spec 을 반환해 dispatch 의 결과 라우팅이 어긋났고, 디버그 trace 가 LLM 응답까지 갔다 돌아오는 시간을 낭비했습니다. 완화: dispatch 측에서 step.role 과 spec.role 의 일치를 검증하고 불일치 시 즉시 actionable error 발생. 출처: ai-workflow-tools `MultiAgentDispatch.run_chained` (PR #27).

### 유형 15: Phantom Sidecar (1건, 보조)

[코디네이터 패턴](/design-pattern/07-coordinator.md) + 명시적 사이드카 의존. 외부 broker/watcher daemon 이 필요하지만 사용자가 띄우지 않은 상태에서 dispatch 가 실행되면, 메시지 artifact 는 정상 작성되지만 라우팅이 발생하지 않아 timeout 으로만 실패합니다. 사용자는 dispatch 호출 자체만 보고 broker 미구동을 의심하기 어렵습니다. 대표 사례: cmux-agent watch 가 백그라운드에 없는데 awf cross 가 cmux 백엔드를 선택해 outbox 에 dispatch artifact 만 누적시켰습니다. 완화: pre-dispatch readiness check (사이드카 heartbeat / active run 존재 검증 / doctor 출력에서 broker 상태 노출). 출처: ai-workflow-tools `cmux_dispatch_available(cwd)`, `awf doctor` 의 dispatch 섹션.

### 유형 16: Boundary Drift (1건, 보조)

다중 패키지 모노레포 + 직접 import. 두 패키지가 서로 다른 floor (예: Python 버전 또는 라이브러리 의존성) 를 선언하는데 한쪽이 다른 쪽을 직접 import 하면, 한 패키지가 다른 패키지의 floor 를 silently 강제 상승시켜 사용자 환경 호환성을 깹니다. CI 가 양쪽 floor 의 max 위에서 돌면 통과하므로 감지가 늦어집니다. 대표 사례: awf-cli `requires-python = ">=3.9"` 가 cmux-agent `>=3.11` 을 직접 import 하면 awf-cli 의 floor 가 사실상 3.11 로 상승했지만 명시는 3.9 로 남았습니다. 완화: 통합 경계를 import 가 아닌 외부 surface (CLI subprocess, on-disk format, 명시적 API endpoint) 로 잡기. 출처: ai-workflow-tools `_cmux_bridge.py` (stdlib `sqlite3` + filesystem + `cmux-agent` CLI subprocess), ADR `2026-05-09-stdlib-only-cmux-bridge`.

### 부록의 시사점

- 13~16번은 모두 **외부 인프라/사이드카에 의존하는 코디네이터 조합**에서 나타났습니다. 단일 프로세스 내 패턴 조합과는 다른 실패 모드 군이 존재함을 시사합니다.
- 본 corpus 26건은 단일 프로세스 내 조합에 치우쳐 있어, 외부 인프라가 개입하는 시스템에서 추가 관측이 필요합니다.

---

## 참고 자료

- [에이전틱 AI 시스템 설계 패턴](/design-pattern/README.md) — base 패턴 정의
- [조합 계약](/.draft/pattern-composition/02-contracts.md) — 실패 완화에 사용된 계약
- [패턴 조합 사례](/.draft/pattern-composition/01-composition.md) — 실패가 발생한 조합 구조
