# Archon 구조 및 실행 플로우 분석

## 1. 개요

- 저장소: `coleam00/Archon`
- 포지션: 오픈소스 AI 코딩 하네스 빌더
- 구현 스택: TypeScript + Bun 모노레포
- 핵심 목표: AI 코딩 과정을 **재현 가능하고 통제 가능한 워크플로우**로 정착

Archon은 "한 번의 프롬프트로 모든 것을 맡기는" 방식 대신, 계획·구현·검증·리뷰·PR 생성을 YAML DAG로 고정합니다. AI는 각 노드의 추론을 담당하고, 실행 순서/게이트/반복은 워크플로우 엔진이 관리합니다.

---

## 2. 프로젝트 구조 분석

### 2.1 모노레포 패키지 구성

`packages/*` 워크스페이스 중심으로 분리되어 있습니다.

| 패키지 | 역할 |
|---|---|
| `packages/server` | API 서버, 어댑터 브리지, 라우트 |
| `packages/core` | 오케스트레이션, 상태/서비스/DB 연산 |
| `packages/workflows` | YAML 로더/검증기/라우터/실행기(DAG) |
| `packages/providers` | Claude/Codex/Community provider 추상화 |
| `packages/isolation` | 격리 실행(worktree/copy), PR 상태 연계 |
| `packages/adapters` | CLI/Web/채팅/forge 등 입력 채널 통합 |
| `packages/web` | 웹 대시보드 UI |
| `packages/cli` | CLI 엔트리/커맨드 |

### 2.2 워크플로우 자산 구조

- `.archon/workflows/defaults/*.yaml`: 기본 워크플로우 번들
- `.archon/commands/defaults/*.md`: 기본 명령 프롬프트/지침 번들

운영자는 기본 템플릿을 복사·수정해 팀 표준 워크플로우를 코드로 관리할 수 있습니다.

---

## 3. 실행 플로우 분석

## 3.1 요청 진입

1. 사용자 요청이 CLI/Web/Slack/GitHub 등으로 유입  
2. server/core가 세션과 코드베이스 컨텍스트를 구성  
3. router가 적합한 workflow를 선택  

## 3.2 DAG 실행

1. loader/validator가 YAML 구조와 의존성 검증  
2. executor가 노드 그래프를 순서대로 실행  
3. loop 노드는 조건 충족 전까지 반복 수행  
4. 노드별 결과는 event/log로 저장  

## 3.3 실제 작업 수행

- AI 노드: provider(Claude/Codex 등) 호출
- 결정적 노드: bash/script/검증 실행
- isolation 계층: 작업별 분리된 git worktree에서 병렬 안전 실행

## 3.4 완료 및 산출물

- 결과 요약, 상태, 아티팩트, PR 링크 반환
- 동일 세션/워크플로우를 이력으로 추적 가능

---

## 4. 설계 포인트

### 4.1 결정론 + 에이전트 추론의 분리

- **워크플로우 엔진**이 "무엇을 어떤 순서로"를 강제
- **AI 모델**은 각 단계의 "어떻게"를 해결

이 분리가 재현성과 유연성을 동시에 제공합니다.

### 4.2 격리 실행 모델

worktree 기반 격리는 병렬 실행 시 충돌을 줄이고, 실패한 런을 안전하게 폐기/재시도할 수 있게 합니다.

### 4.3 멀티 어댑터 구조

플랫폼별 입력 경로는 다르지만 내부 실행 코어는 동일합니다. 이는 인터페이스 확장 비용을 낮추고 운영 관측 일관성을 높입니다.

### 4.4 기본 워크플로우 제공

`archon-fix-github-issue`, `archon-idea-to-pr`, `archon-smart-pr-review`, `archon-validate-pr` 등 즉시 적용 가능한 시나리오를 내장해 초기 도입 장벽을 낮춥니다.

---

## 5. 장점과 트레이드오프

### 장점

1. **재현성**: 같은 워크플로우로 실행 편차 축소  
2. **거버넌스**: 팀 프로세스를 YAML로 버전 관리  
3. **확장성**: 플랫폼/모델/provider 교체 용이  
4. **운영성**: 이벤트 중심 이력 추적 및 디버깅 용이  

### 트레이드오프

1. **초기 설계 비용**: 워크플로우/게이트 정의 필요  
2. **모델 독립성 한계**: provider별 도구 차이에 따른 결과 편차 가능  
3. **운영 복잡도 증가**: 어댑터·격리·스토리지까지 포함한 시스템 운영 필요  

---

## 6. 적용 인사이트

- 단순 자동화보다 **조직 표준 프로세스의 자동 집행**이 중요한 팀에 적합
- PR 품질 편차/리뷰 부하가 큰 팀에서 검증·리뷰 노드 분리 효과가 큼
- 도입 초기에는 "fix-issue → validate-pr" 같은 짧은 체인부터 시작하는 것이 안전

---

## 참고 링크

- [Archon Repository](https://github.com/coleam00/Archon)
- [README](https://github.com/coleam00/Archon/blob/dev/README.md)
- [Docs: archon.diy](https://archon.diy)
- [Releases](https://github.com/coleam00/Archon/releases)
- [Workflows (defaults)](https://github.com/coleam00/Archon/tree/dev/.archon/workflows/defaults)
- [Commands (defaults)](https://github.com/coleam00/Archon/tree/dev/.archon/commands/defaults)
