# Auto Improve Loop Diagram

사람이 목표와 규칙을 정의하고, AI가 자율적으로 실험·측정·판단하여 시스템을 개선하는 Auto Improve Loop의 핵심 구조를 종합한 다이어그램입니다.

---

## 전체 구조

Auto Improve Loop는 **역할 분리**(Human vs AI), **고정 평가 기준**, **안전한 롤백**, **실험 로그 관리** 4가지 설계 원칙 위에서 동작합니다. 사람은 `program.md`로
What과 Constraints를 정의하고, AI Agent는 How를 결정하여 가설 수립 → 코드 수정 → 실험 실행 → 결과 측정 → 유지/폐기 루프를 자율 반복합니다.

```mermaid
flowchart TB
    subgraph Human["👤 사람의 영역"]
        PM["program.md<br/>목표 · 범위 · 평가 기준 · 로그 형식"]
    end

    subgraph AI["🤖 AI Agent의 영역"]
        READ["현재 상태 읽기"]
        HYPO["가설 수립"]
        CODE["코드 수정"]
        COMMIT["Git Commit"]
        RUN["실험 실행"]
        CHECK{"오류 발생?"}
        CRASH["에러 로그 기록"]
        FIX{"수정 가능?"}
        MEASURE["결과 측정"]
        EVAL{"개선되었는가?"}
        KEEP["✅ 유지 (Keep)"]
        DISCARD["❌ 폐기 + Git Reset"]
        LOG["실험 로그 기록"]
    end

    PM -->|" 목표 전달 "| READ
    READ --> HYPO --> CODE --> COMMIT --> RUN --> CHECK
    CHECK -->|" Yes "| CRASH --> FIX
    FIX -->|" Yes "| CODE
    FIX -->|" No "| DISCARD
    CHECK -->|" No "| MEASURE --> EVAL
    EVAL -->|" Yes "| KEEP --> LOG
    EVAL -->|" No "| DISCARD --> LOG
    LOG -->|" 다음 실험 "| READ
    style Human fill: #e3f2fd, stroke: #1565C0
    style AI fill: #fff3e0, stroke: #E65100
    style KEEP fill: #c8e6c9, stroke: #2E7D32
    style DISCARD fill: #ffcdd2, stroke: #C62828
```

## 적용 범위

Auto Improve Loop는 모델 학습 외에도 프롬프트 최적화, 코드 품질, 문서 개선, 설정 최적화 등 측정 가능한 모든 영역에 적용 가능합니다.

```mermaid
graph LR
    LOOP["Auto Improve<br/>Loop"]
    LOOP --> D1["🧠 모델 학습<br/>하이퍼파라미터 → val_bpb"]
    LOOP --> D2["💬 프롬프트 최적화<br/>프롬프트 템플릿 → 품질 점수"]
    LOOP --> D3["💻 코드 품질<br/>소스 코드 → 테스트 통과율"]
    LOOP --> D4["📄 문서 개선<br/>문서 내용 → 가독성 점수"]
    LOOP --> D5["⚙️ 설정 최적화<br/>시스템 설정 → 응답 시간"]
    style LOOP fill: #fff3e0, stroke: #E65100
    classDef domainStyle fill: #e8f5e9, stroke: #388E3C
    class D1,D2,D3,D4,D5 domainStyle
```
