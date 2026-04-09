# 다중 에이전트 오케스트레이션 -- 개념 개요

---

## 1. 5가지 실행 모드

작업의 위험도와 복잡도에 따라 다섯 가지 모드 중 하나를 선택합니다.

### solo -- 단독 실행

Primary 에이전트 하나만 사용합니다. 모든 작업의 기본 모드입니다.

- **흐름**: 프롬프트 → Primary 실행 → 결과 반환
- **Judge**: 불필요
- **적합한 상황**: 저위험 일반 작업, 빠른 프로토타입

### quick -- 읽기 전용

Secondary 에이전트 하나가 read-only로 빠르게 분석합니다. Primary를 사용하지 않아 비용이 가장 낮습니다.

- **흐름**: 프롬프트 → Secondary(읽기 전용) → 분석 결과 반환
- **Judge**: 불필요
- **적합한 상황**: 코드 분석, 빠른 검토, 비용 최소화

### precise -- 순차 검증

Secondary가 먼저 분석하고, Primary가 그 결과를 검증하고 보완합니다.

- **흐름**: 프롬프트 → Secondary 분석 → Primary 검증/보완 → 결과 반환
- **Judge**: 선택적
- **적합한 상황**: 중요 작업의 이중 확인, 분석 후 구현

### cross -- 병렬 교차 검증

두 Secondary 에이전트가 서로 다른 프로토콜로 독립 분석하고, Judge가 결과를 종합합니다.

- **흐름**: 프롬프트 → Agent A + Agent B 병렬 → 결과 수집/정렬 → 중복 제거 → Judge 판정
- **Judge**: 필수
- **적합한 상황**: 보안 검증, 코드 리뷰, 독립적 다중 관점이 필요한 작업

### critical -- 순차 심층 체인

세 에이전트가 순차적으로 실행됩니다. 이전 결과가 다음 입력에 누적됩니다. 가장 높은 신뢰도를 제공합니다.

- **흐름**: 프롬프트 → Agent A → Agent B(+result_A) → Primary(+result_A+result_B) → Judge 판정
- **Judge**: 필수
- **적합한 상황**: 프로덕션 배포, 핵심 인프라 변경, 최고 신뢰도가 필요한 작업

---

## 2. 모드 선택 의사결정 매트릭스

| 판단 기준 | solo | quick | precise | cross | critical |
|----------|------|-------|---------|-------|----------|
| 위험도 | 낮음 | 낮음 | 중간 | 높음 | 매우 높음 |
| 에이전트 수 | 1 | 1 | 2 | 2 + Judge | 3 + Judge |
| 실행 방식 | 단독 | 읽기 전용 | 순차 | 병렬 | 순차 체인 |
| 상대 비용 | 1x | 0.5x | 2x | 2x | 3x |
| 상대 지연 | 1x | 0.5x | 2x | 1x | 3x |
| 신뢰도 | 보통 | 낮음 | 높음 | 높음 | 최고 |

---

## 3. Policy-Based 승격/강등

### 자동 승격 (Auto-Promotion)

프롬프트의 키워드를 분석하여 위험도에 맞는 모드로 자동 승격합니다.

| 키워드 유형 | 예시 | 승격 대상 |
|-----------|------|----------|
| 보안 관련 | `security`, `vulnerability`, `auth`, `encryption` | cross |
| 프로덕션 관련 | `production`, `deploy`, `migration`, `critical` | critical |

### 자동 강등 (Auto-De-escalation)

저위험 키워드가 감지되면 모드를 낮춥니다. 불필요한 비용을 방지합니다.

| 키워드 유형 | 예시 | 강등 대상 |
|-----------|------|----------|
| 읽기 전용 | `read`, `analyze`, `explain`, `describe` | quick |
| 단순 작업 | `format`, `rename`, `comment`, `typo` | solo |

### 실행 중 강등 (Runtime De-escalation)

에이전트 실행 실패 시 하위 모드로 자동 강등합니다. 어떤 상황에서든 작업 완료를 보장합니다.

---

## 4. Provider 추상화

오케스트레이터는 구체적인 AI 제공자를 직접 참조하지 않습니다. Provider Protocol과 Registry 패턴으로 추상화합니다.

### 불변식

- 모든 Provider는 동일한 Protocol(인터페이스)을 구현합니다
- Orchestrator는 Registry를 통해 이름으로 Provider를 조회합니다
- Provider 교체 시 Orchestrator 코드 변경이 불필요합니다

### Protocol 인터페이스

```typescript
interface ProviderProtocol {
  execute(prompt: string, options: ExecuteOptions): Promise<ProviderResult>;
  getCapabilities(): ProviderCapabilities;
  healthCheck(): Promise<boolean>;
}
```

Provider는 Subprocess, SDK, Mock 세 가지 유형으로 구현할 수 있습니다. 테스트 시에는 Mock Provider를 사용합니다.

---

## 5. 역할 기반 프로토콜 (Role-Based Protocols)

각 Secondary 에이전트는 역할(role)에 따라 다른 프로토콜을 할당받습니다. 프로토콜은 외부 파일로 관리되며, 코드 수정 없이 동작을 변경할 수 있습니다.

### 프로토콜 종류

| 프로토콜 | 역할 | 검증 초점 |
|---------|------|----------|
| speed | 빠른 1차 분석 | 명백한 이슈 탐지, 표면 검증 |
| precision | 정밀 분석 | 세부 로직 검증, 엣지 케이스 |
| plan_conformance | 계획 적합성 | 요구사항 충족 여부, 설계 일관성 |
| quality_validation | 품질 검증 | 코드 품질, 테스트 커버리지, 문서화 |

### 프로토콜 원칙

- **역할 정의**: 에이전트의 역할과 관점을 명시합니다
- **검증 기준**: 무엇을 검증해야 하는지 항목화합니다
- **응답 형식**: 구조화된 JSON 스키마를 명시합니다
- **캐싱**: 반복 로드를 방지하기 위해 TTL 기반 캐싱을 적용합니다 (기본 TTL: 5분)

---

## 참고 자료

- [아키텍처 다이어그램](/multi-agent-orchestration/00-diagram.md) -- 모드별 흐름도
- [Judge Rules](/multi-agent-orchestration/02-judge-rules.md) -- 결정론적 판정 로직
- [Provider Routing](/multi-agent-orchestration/03-provider-routing.md) -- Fallback 체인, Synthesis 패턴
- [에이전틱 AI 시스템 설계 패턴](/design-pattern/) -- 단일/멀티 에이전트 패턴 카탈로그
