# Provider Contract

여러 LLM 공급자(provider)를 교체 가능하게 만들려면 오케스트레이션 레이어(host)와 LLM 호출 레이어(provider) 사이의 경계를 명시해야 합니다.
이 문서는 단일 프로덕션 시스템에서 provider를 교체하려다 발견한 문제와, 이를 해결하기 위해 도출한 계약을 정리한 것입니다. 다른 구현에서는 다른 형태의 경계가 필요할 수 있습니다.

---

## 문제

base 패턴 중 [코디네이터 패턴](/design-pattern/07-coordinator.md)은 "오케스트레이터가 동적으로 서비스를 선택한다"고 설명합니다. 그러나 실제로 LLM 공급자 A에서 B로 교체할 때 다음 질문에 답해야 합니다.

- 공급자마다 다른 기능(네이티브 tool use, 확장 추론, 세션 관리)을 어떻게 표현하는가?
- 어느 Phase가 어느 기능을 필수로 요구하는가? 요구를 만족하지 못하는 공급자는 어떻게 걸러지는가?
- Phase별 최대 실행 시간(timeout)을 공급자에 어떻게 강제하는가?
- 공급자 실패(인증/timeout/rate limit/서비스 중단)를 host가 어떻게 구분해 다음 대응을 결정하는가?

base 패턴 문서는 이들을 다루지 않습니다.

---

## Host와 Provider의 책임 경계

**핵심 원칙**: provider는 "prompt in, text out"의 얇은 어댑터. 워크플로우 의미론은 host에 있습니다.

| 책임 | Host | Provider |
|------|:----:|:--------:|
| Phase별 prompt 생성 | ✅ | ❌ |
| 입력 artifact 로딩, 출력 artifact 저장 | ✅ | ❌ |
| Gate 판정, 상태 전이, 재시도 루프 | ✅ | ❌ |
| Fallback chain 선택 | ✅ | ❌ |
| Prompt 크기 예산 관리, 섹션 절단 | ✅ | ❌ |
| **LLM API 호출 (text in, text out)** | ❌ | ✅ |
| 토큰 사용량 리포트 | ❌ | ✅ |
| Provider 네이티브 tool loop 중계 (지원 시) | optional | ✅ if supported |
| 스트리밍 이벤트 방출 (지원 시) | ❌ | ✅ if supported |
| 인증, API 키 관리 | ❌ | ✅ |

이 경계가 지켜지지 않으면 공급자 교체가 host 코드 변경을 요구하게 됩니다.

---

## Tier 구조

Provider는 세 단계의 인터페이스 중 하나 이상을 구현합니다. 상위 tier는 하위 tier의 전제 조건입니다.

| Tier | 이름 | 최소 계약 |
|:----:|------|-----------|
| 0 | Minimum | prompt in, text out. 동기 함수 하나 |
| 1 | Streaming | 중간 결과를 이벤트로 방출 |
| 2 | Tool Loop | provider 네이티브 tool use/MCP 중계 |

Host는 각 Phase가 요구하는 **최소 tier**만 선언합니다. provider가 그 tier를 만족하는지는 capability로 검증합니다.

### Tier 0 — Minimum (MUST)

모든 provider는 다음을 제공합니다.

```python
class Provider(Protocol):
    name: str
    capabilities: set[ProviderCapability]

    def complete(
        self,
        prompt: str,
        *,
        cwd: str | None = None,
        add_dirs: list[str] | None = None,
        timeout_sec: int | None = None,
    ) -> ProviderResult: ...
```

계약:

- `prompt`는 UTF-8 텍스트. provider는 이를 LLM에 그대로 전달합니다. 공급자 특유의 role 마커(`<thinking>`, `system/user` 분리 등)는 host 프롬프트에 넣지 않습니다.
- `timeout_sec`은 provider 측 wall-clock 상한. 초과 시 예외를 던지지 않고 `returncode != 0`을 반환하며, `stderr`는 `provider_timeout:` prefix로 시작해야 합니다.
- `add_dirs`는 optional input입니다. host는 provider가 `ADD_DIR` capability를 선언한 경우에만 전달해야 하며, 미지원 provider에 비어 있지 않은 `add_dirs`를 전달하면 provider는 `provider_bad_input:` prefix로 거부합니다.
- 함수는 **동기**. 스트리밍/비동기는 Tier 1에서 제공합니다.

`ProviderResult`는 최소한 다음을 포함합니다.

```python
@dataclass
class ProviderResult:
    returncode: int                 # 0 = success
    stdout: str                     # LLM 응답 본문
    stderr: str                     # 진단 메시지
    usage: TokenUsage | None
    provider_name: str              # fallback 추적용
    model: str | None
    elapsed_sec: float
```

**오류 시맨틱**: provider는 예외를 던지지 않습니다. 모든 실행 실패는 `ProviderResult`로 구조화해 반환합니다. host의 재시도/fallback 로직을 단순화하기 위함입니다. 단, **초기화 실패**(API 키 누락, 명령어 없음)는 factory 단계에서 예외를 허용합니다.

### Tier 1 — Streaming (SHOULD)

provider가 중간 결과를 이벤트로 방출할 수 있다면 Tier 1을 지원합니다. 이벤트는 최소한 다음 집합을 포함합니다.

| 이벤트 | 페이로드 | 의미 |
|--------|----------|------|
| `text_delta` | `{chunk}` | 본문 토큰 증분 |
| `thinking_delta` | `{chunk}` | 확장 추론 토큰 (지원 시) |
| `tool_use` | `{tool, args, id}` | tool 호출 요청 (Tier 2) |
| `tool_result` | `{id, output, is_error}` | tool 결과 반영 (Tier 2) |
| `usage` | `{input, output}` | 토큰 리포트 |
| `done` | `{returncode, final_text}` | 정상 종료 |
| `error` | `{message, fatal}` | 오류 |

### Tier 2 — Tool Loop (OPTIONAL)

provider가 LLM tool use를 네이티브로 관리할 수 있으면 Tier 2입니다. host는 tool 스키마와 실행자를 전달하고, provider는 loop 내부에서 tool call과 결과 반영을 처리합니다.

Tier 2를 지원하지 않는 provider에서 tool이 필요한 Phase는 **host가 tool loop를 외부에서 구현**합니다. 더 느리지만 Tier 0만으로도 tool 워크플로우가 가능함을 보장합니다.

---

## Capability Matrix

Tier 외에 provider는 **선택 기능**을 capability로 선언합니다. host는 Phase 요구사항과 교차해 적합한 provider를 선택합니다.

| Capability | 의미 |
|------------|------|
| `COMPLETE` | Tier 0. 모든 provider MUST |
| `EVENT_STREAM` | Tier 1 |
| `TOOL_LOOP` | Tier 2 |
| `THINKING` | 확장 추론 토큰 지원 |
| `CITATIONS` | 응답에 출처 인용 포함 |
| `SESSION` | multi-turn 세션을 네이티브 관리. 미지원 시 host가 대화 이력을 prompt에 포함 |
| `ADD_DIR` | 작업 디렉토리 외 추가 경로 접근 |

**Phase별 최소 요구사항 예시**:

| Phase | 최소 tier | 선호 capability |
|-------|:---------:|----------------|
| 분석 Stage 1 (파일별) | 0 | `ADD_DIR` |
| 설계 (plan) | 0 | `THINKING` |
| 구현 (impl) | 0 | `TOOL_LOOP`, `ADD_DIR` |
| 대화 세션 | 1 | `SESSION` |

`TOOL_LOOP`는 Tier 2 capability이므로, 구현 Phase는 Tier 0 provider로도 시작할 수 있지만 가능하면 Tier 2 provider를 우선 선택합니다.

---

## 오류 분류

stderr는 prefix로 오류 유형을 표현하는 것이 권장됩니다. host는 prefix를 읽어 다음 대응을 결정합니다.

| Prefix | 의미 | host 대응 |
|--------|------|----------|
| `provider_auth:` | 인증 실패 | 재시도 금지, 사용자 설정 안내 |
| `provider_timeout:` | timeout 초과 | fallback chain 이동 |
| `provider_rate_limit:` | rate limit | 지수 백오프 재시도 — 최대 1회 |
| `provider_unavailable:` | 서비스/네트워크 장애 | fallback chain 이동 |
| `provider_bad_input:` | prompt가 너무 크거나 형식 오류 | host가 prompt 재작성/절단 |
| `provider_tool_error:` | tool loop 중 오류 | Tier 2에서 의미 있음 |

**Host 재시도 책임**: provider는 자체 재시도를 하지 않습니다. host는 `provider_rate_limit:`에 한해 최대 1회 지수 백오프 재시도를 허용할 수 있습니다. 그 외 모든 재시도는 host가 결정하며, 재시도 횟수를 [State Schema](/.draft/pattern-composition/02-contracts.md)에 기록해 무한 루프를 방지합니다.

---

## 설계 근거

이 계약은 **공급자 교체가 host 코드 변경을 요구하지 않도록** 경계를 그립니다.

- Phase가 "Claude만 가능"한 것이 아니라 "Tier 0 + `ADD_DIR`이 필요"로 선언되면, 해당 요구를 만족하는 어떤 provider든 사용 가능합니다.
- 공급자별 특수 기능(확장 추론, 세션 관리)은 optional capability로 격리되어 워크플로우 필수 경로에서 배제됩니다.
- timeout과 오류 prefix가 표준화되어 있어 fallback chain 로직이 provider 독립적으로 작동합니다.

단, 이 계약은 도메인 특화 설계입니다:

- Anthropic의 extended thinking, OpenAI의 structured output 같은 최신 기능은 optional capability로 수용하되 1급 지원은 하지 않습니다.
- UX(chat REPL, TUI) 레이어는 이 계약 밖에 있습니다.

---

## 이 계약이 없으면 발생하는 실패

- **Over-provisioning**: capability 선언이 없으면 host가 모든 Phase에 가장 강한 provider를 할당하게 됩니다 ([실패 분류 유형 10](/.draft/pattern-composition/03-failure-taxonomy.md))
- **Vague Error**: 오류 prefix가 표준화되지 않으면 host가 인증 실패와 timeout을 구분하지 못해 부적절한 재시도를 반복합니다 ([실패 분류 유형 12](/.draft/pattern-composition/03-failure-taxonomy.md))
- **공급자 락인**: Phase 로직이 특정 공급자의 네이티브 기능을 전제하면 교체 시 Phase 코드를 수정해야 합니다. 계약은 이 커플링을 방지합니다

---

## 다른 계약과의 관계

| 관계 | 설명 |
|------|------|
| [Agent Card](/.draft/pattern-composition/02-contracts.md) → Provider Contract | Agent Card의 `provider` 필드가 이 계약의 capability 요구를 선언 |
| Provider Contract → [Result Envelope](/.draft/pattern-composition/02-contracts.md) | provider의 `stdout`은 Envelope의 `result` 또는 `escape` 본문으로 host가 파싱 |
| Provider Contract → [State Schema](/.draft/pattern-composition/02-contracts.md) | provider 재시도 횟수와 fallback 경로가 State의 `history`에 기록 |

---

## 참고 자료

- [조합 계약 — Agent Card, Result Envelope, State Schema](/.draft/pattern-composition/02-contracts.md)
- [실패 분류](/.draft/pattern-composition/03-failure-taxonomy.md)
- [코디네이터 패턴](/design-pattern/07-coordinator.md) — base 패턴
