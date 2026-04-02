# OpenSpace 아키텍처/워크플로우 분석

## 1. 개요

- 대상: `HKUDS/OpenSpace`
- 목적: 코딩 에이전트의 실행 경험을 **재사용 가능한 skill**로 축적하고 자동 진화
- 인터페이스: CLI + MCP 서버(`openspace-mcp`) + Python API
- 실행 백엔드: `shell`, `gui`, `mcp`, `web`, `system`

OpenSpace의 핵심은 "에이전트가 작업을 수행한 뒤, 그 실행 경험 자체를 다음 작업에 반영하도록 구조화"한 점입니다.

---

## 2. 문제 정의와 접근

OpenSpace가 겨냥하는 문제는 크게 3가지입니다.

1. 반복 작업에서 동일한 시행착오가 재발
2. 성공 패턴이 다음 작업으로 충분히 전이되지 않음
3. 도구/환경 변화로 기존 프롬프트·스킬이 쉽게 노후화

이를 해결하기 위해 OpenSpace는 다음 전략을 결합합니다.

- **Skill 중심 재사용**: 성공/실패 패턴을 SKILL 단위로 축적
- **지속 진화**: FIX/DERIVED/CAPTURED로 스킬 라이프사이클 자동화
- **품질 계측 기반 트리거**: 실행 결과뿐 아니라 도구/스킬 지표 변화를 감시

---

## 3. 구조 분해

### 3.1 Agent/Runtime 계층

- `openspace/agents/grounding_agent.py`
- `openspace/grounding/*`

역할:

- 질의를 반복 루프로 분해해 tool 호출
- backend scope 내에서 필요한 실행 수단 선택
- 실행 기록/결과를 skill engine으로 전달

### 3.2 Skill Engine 계층

- `registry.py`, `skill_ranker.py`: 스킬 검색/선택
- `analyzer.py`: 실행 후 개선 지점 분석
- `evolver.py`: FIX/DERIVED/CAPTURED 생성
- `store.py`: SQLite 기반 버전 DAG/메트릭 저장

핵심은 "스킬을 정적 문서가 아니라 버전과 품질 지표를 가진 객체"로 취급하는 점입니다.

### 3.3 Cloud Community 계층 (선택)

- `openspace/cloud/*`
- CLI: `openspace-download-skill`, `openspace-upload-skill`

로컬 스킬만으로도 동작하지만, cloud를 연결하면 팀/공개 단위로 스킬 공유 및 재사용이 가능합니다.

---

## 4. 진화 엔진 동작

### 4.1 진화 모드

- **FIX**: 기존 skill의 결함 수정(동일 스킬 버전 업)
- **DERIVED**: 부모 skill 기반 파생 스킬 생성
- **CAPTURED**: 실행 성공 패턴을 신규 skill로 추출

### 4.2 트리거

- **Post-Execution Analysis**: 각 작업 후 분석
- **Tool Degradation**: 도구 성공률/품질 하락 감지
- **Metric Monitor**: skill 적용률·완료율·fallback률 악화 감시

### 4.3 안전장치

- 확인 게이트(오탐/과진화 방지)
- anti-loop guard(무한 진화 루프 방지)
- 위험 패턴 점검(프롬프트 인젝션, 민감정보 유출 등)
- 진화 결과 검증 후 반영

---

## 5. 사용 경로

### Path A: 기존 에이전트 확장

- OpenSpace를 MCP 서버로 등록
- `delegate-task`, `skill-discovery` host skill을 기존 에이전트 skill 디렉토리에 추가
- 기존 에이전트 실행 맥락에서 OpenSpace 기능 호출

### Path B: OpenSpace 단독 실행

- `openspace` CLI로 직접 실행
- 동일한 skill 진화/백엔드 기능을 단독으로 사용

운영 관점에서는 Path A가 "현재 팀 워크플로우를 크게 바꾸지 않고" 도입하기 쉬운 형태입니다.

---

## 6. GDPVal 결과 해석

공개 README의 핵심 지표(자체 보고 기준):

- 50개 GDPVal task에서 **4.2× Higher Income**
- **72.8% Value Capture**
- **70.8% Average Quality**
- Phase 2에서 Phase 1 대비 **약 45.9% 토큰 절감**

해석 포인트:

1. OpenSpace의 주장은 "더 좋은 모델 사용"보다 "동일 모델에서의 skill 진화 효과"를 강조
2. 2단계(Cold→Warm) 비교는 누적 학습 효과를 관찰하기 적합
3. 다만 결과는 프로젝트 자체 벤치마크이므로, 조직 도입 전에는 내부 태스크셋으로 재현 검증이 필요

---

## 7. 도입 시 체크 포인트

- skill 저장소(SQLite + 파일) 백업/보존 정책
- 진화 허용 범위(FIX만 허용 vs DERIVED/CAPTURED 포함)
- 민감 데이터 포함 로그/recording 처리 정책
- cloud 공유 시 공개 범위(공개/그룹/비공개) 관리
- 품질 KPI(완료율, 재시도율, 토큰/비용)를 사전 정의

---

## 8. 종합 평가

OpenSpace는 "도구를 잘 쓰는 에이전트"를 넘어 "실행 경험을 누적 자산으로 전환하는 에이전트"를 만들기 위한 프레임워크입니다.

특히 **진화 트리거를 단일 이벤트가 아니라 다중 품질 신호로 구성**한 점과, **기존 에이전트에 MCP/Skill 형태로 부착 가능한 설계**가 실무 도입에서 가장 큰 장점입니다.
