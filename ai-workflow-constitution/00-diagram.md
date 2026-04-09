# AI 워크플로우 설계 원칙 다이어그램

---

## 1. 시스템 전체 구조

3개 파이프라인과 공유 인프라 계층의 관계입니다.

```mermaid
graph TB
    subgraph pipelines["파이프라인"]
        AP["Analysis Pipeline\n코드 분석 → 문서 생성"]
        WP["Workflow Pipeline\n기능 구현 자동화"]
        MA["Multi-Agent Pipeline\n교차 검증"]
    end

    subgraph infra["공유 인프라"]
        PL["Provider Layer"]
        CFG["Config"]
        ST["State"]
        EV["Event System"]
        SK["Skill System"]
        PM["Permission Model"]
    end

    AP --> PL & CFG & ST & EV & SK
    WP --> PL & CFG & ST & EV & SK
    MA --> PL & CFG & EV & SK
    PL --> PM

    style pipelines fill:#e8f4f8,stroke:#2196F3
    style infra fill:#fff3e0,stroke:#FF9800
```

### 파이프라인 역할

| 파이프라인 | 목적 | 핵심 패턴 |
|-----------|------|----------|
| Analysis | 코드 분석 → 구조화된 문서 생성 | N-Layer, M-Stage, Writer/Judge |
| Workflow | 기능 구현의 구조화된 자동화 | N-Phase, Gate, Closed-Loop |
| Multi-Agent | 다중 에이전트 교차 검증 | N-Mode, Judge Rules, Synthesis |

---

## 2. 역할 분리

시스템의 5가지 역할과 책임 경계입니다.

```mermaid
flowchart LR
    subgraph roles["역할 흐름"]
        ORC["Orchestrator\n상태 관리\nPhase 전환\nProvider 라우팅"]
        EXE["Executor\n코드 실행\n파일 수정"]
        REV["Reviewer\n분석/검증\n관찰 추출"]
        JDG["Judge\n결과 종합\n판정"]
        GAT["Gate\n통과 조건 평가\n라우팅 결정"]
    end

    ORC --> EXE
    EXE --> REV
    REV --> JDG
    JDG --> GAT
    GAT -->|pass| ORC
    GAT -->|fail| EXE

    style roles fill:#e8f5e9,stroke:#2E7D32
```

### 역할별 권한

| 역할 | 할 수 있는 것 | 할 수 없는 것 |
|------|-------------|-------------|
| Orchestrator | 상태 관리, 라우팅, Phase 전환 | 코드 수정, AI 호출 |
| Executor | allowed_files 내 코드 수정 | forbidden_paths 접근, plan 변경 |
| Reviewer | 관점별 분석, claim 생성 | 코드 수정, 최종 판정 |
| Judge | claim 선별/병합, 일관성 검증 | evidence 수정, 새 claim 생성 |
| Gate | 도구 실행, pass/fail 판정 | AI 판단, 예외 허용 |

---

## 3. 원칙 계층 구조

C1-C11 원칙의 우선순위와 상호 관계입니다.

```mermaid
graph TB
    subgraph tier1["Tier 1: 기반 원칙"]
        C9["C9 재현 전에 확정하지 않는다"]
        C1["C1 관찰과 판단을 분리한다"]
    end

    subgraph tier2["Tier 2: 범위·검증 원칙"]
        C2["C2 계약으로 범위를 고정한다"]
        C3["C3 기계가 잡을 수 있는 것은\n기계가 잡는다"]
        C7["C7 역할을 분리하고\n권한을 제한한다"]
    end

    subgraph tier3["Tier 3: 품질·효율 원칙"]
        C4["C4 한 곳만 보면 틀린다"]
        C8["C8 피드백은 구조화하고\n재시도는 예산 내에서"]
        C5["C5 위험도에 비례하여 투자한다"]
    end

    subgraph tier4["Tier 4: 인프라·확장 원칙"]
        C6["C6 상태는 파일에 둔다"]
        C11["C11 세션은 작업 단위에 맞게 분리"]
        C10["C10 산출물은 목적에 따라 교체"]
    end

    C9 --> C2 & C3
    C1 --> C4 & C7
    C2 --> C5
    C3 --> C8
    C7 --> C11
    C5 --> C6
    C6 --> C10

    style tier1 fill:#e8f4f8,stroke:#2196F3
    style tier2 fill:#fff3e0,stroke:#FF9800
    style tier3 fill:#e8f5e9,stroke:#2E7D32
    style tier4 fill:#fff3e0,stroke:#FF9800
```

### 충돌 시 우선순위

| 순위 | 원칙 | 분류 |
|------|------|------|
| 1 | C9 재현 전에 확정하지 않는다 | 기반 |
| 2 | C1 관찰과 판단을 분리한다 | 기반 |
| 3 | C2 계약으로 범위를 고정한다 | 범위 |
| 4 | C3 기계가 잡을 수 있는 것은 기계가 잡는다 | 검증 |
| 5 | C7 역할을 분리하고 권한을 제한한다 | 검증 |
| 6 | C4 한 곳만 보면 틀린다 | 품질 |
| 7 | C8 피드백은 구조화하고 재시도는 예산 내에서 | 효율 |
| 8 | C5 위험도에 비례하여 투자한다 | 효율 |
| 9 | C6 상태는 파일에 둔다 | 인프라 |
| 10 | C11 세션은 작업 단위에 맞게 분리한다 | 운영 |
| 11 | C10 산출물은 목적에 따라 교체한다 | 확장 |

---

## 참고 자료

- [01-principles.md](01-principles.md) — 각 원칙의 정의, 근거, 위반 신호
- [02-architecture.md](02-architecture.md) — 공유 인프라 아키텍처 상세
- [에이전틱 AI 시스템 설계 패턴](/design-pattern/00-diagram.md)
