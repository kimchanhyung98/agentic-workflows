# 코드 분석 파이프라인 다이어그램

## 1. 4-Layer 아키텍처

입력 수집에서 산출물 생성까지의 전체 파이프라인 구조입니다.
각 Layer는 명확한 입출력 계약을 가지며, 독립적으로 교체 가능합니다.

```mermaid
graph TB
    subgraph Layer1["Layer 1: Input (탐색)"]
        style Layer1 fill:#e3f2fd,stroke:#1565C0
        L1A["소스코드 수집"] --> L1B["분석 단위 식별"]
        L1B --> L1C["규모 판정"]
        L1C --> L1D["분석 목적 결정"]
    end

    subgraph Layer2["Layer 2: Bundle (관찰 수집)"]
        style Layer2 fill:#e3f2fd,stroke:#1565C0
        L2A["파일별 번들 생성"] --> L2B["관찰 추출 (사실만)"]
        L2B --> L2C["단위별 번들 조립"]
    end

    subgraph Layer3["Layer 3: Analyze (판단)"]
        style Layer3 fill:#fff3e0,stroke:#FF9800
        L3A["Stage 1: 파일별 분석"] --> L3B["Stage 2: 단위 합성"]
        L3B --> L3C["Stage 3: 교차 검증 (조건부)"]
    end

    subgraph Layer4["Layer 4: Output (산출물)"]
        style Layer4 fill:#e3f2fd,stroke:#1565C0
        L4A["결과 병합"] --> L4B["산출물 생성"]
        L4B --> L4C["프로젝트 지식 갱신"]
    end

    Layer1 -->|"파일 목록 + 규모 + 목적"| Layer2
    Layer2 -->|"observation 번들"| Layer3
    Layer3 -->|"종합 판단 결과"| Layer4
```

---

## 2. 분석 상태 머신

실패 시 마지막 완료 Stage 이후부터 재개할 수 있습니다.

```mermaid
stateDiagram-v2
    [*] --> pending: 분석 요청
    pending --> input: Layer 1 시작
    input --> bundle: 파일 수집 완료
    bundle --> stage1: 번들 생성 완료
    stage1 --> stage2: 파일별 분석 완료
    stage2 --> stage3: 단위 합성 완료 (조건부)
    stage2 --> output: 단위 합성 완료
    stage3 --> output: 교차 검증 완료
    output --> completed: 산출물 생성 완료

    input --> failed: 실패
    bundle --> failed: 실패
    stage1 --> failed: 실패
    stage2 --> failed: 실패

    failed --> stage1: 재개 (완료 지점부터)
    failed --> stage2: 재개
```

---

## 3. 규모 기반 Provider 라우팅

분석 대상의 규모(scale)에 따라 Provider 등급과 처리 전략을 결정합니다.

```mermaid
flowchart LR
    Start["파일 수 확인"] --> Check1{"small?"}
    Check1 -->|"예"| Small["저비용 Provider만"]
    Check1 -->|"아니오"| Check2{"standard?"}
    Check2 -->|"예"| Standard["저비용 + 중비용"]
    Check2 -->|"아니오"| Large["저 + 중 + 고비용<br/>(Fanout 병렬 처리)"]

    style Small fill:#e8f5e9,stroke:#2E7D32
    style Standard fill:#fff3e0,stroke:#FF9800
    style Large fill:#fff3e0,stroke:#FF9800
```

---

## 4. Writer/Judge 파이프라인 흐름

Stage 2에서 사용되는 Writer/Judge 패턴의 데이터 흐름입니다.
다중 Writer가 동일한 observation을 독립적으로 분석하고, Analysis Judge가 최종 통합합니다.

```mermaid
flowchart TD
    OBS["Observation 번들<br/>(Layer 2 출력)"] --> W1["Writer A<br/>(관점 1)"]
    OBS --> W2["Writer B<br/>(관점 2)"]
    OBS --> W3["Writer C<br/>(관점 3)"]

    W1 --> CL1["Claim + 산출물 초안"]
    W2 --> CL2["Claim + 산출물 초안"]
    W3 --> CL3["Claim + 산출물 초안"]

    CL1 --> JUDGE["Analysis Judge"]
    CL2 --> JUDGE
    CL3 --> JUDGE

    JUDGE --> DEDUP["중복 Claim 제거"]
    DEDUP --> RESOLVE["모순 해소<br/>(confidence 기준)"]
    RESOLVE --> OUTPUT["최종 산출물"]

    style OBS fill:#e3f2fd,stroke:#1565C0
    style W1 fill:#fff3e0,stroke:#FF9800
    style W2 fill:#fff3e0,stroke:#FF9800
    style W3 fill:#fff3e0,stroke:#FF9800
    style JUDGE fill:#e8f5e9,stroke:#2E7D32
    style DEDUP fill:#e8f5e9,stroke:#2E7D32
    style RESOLVE fill:#e8f5e9,stroke:#2E7D32
    style OUTPUT fill:#e8f5e9,stroke:#2E7D32
```

---

## 참고 자료

- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Google Cloud: Choose a design pattern for an agentic AI system](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
