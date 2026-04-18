# HyperAgents 구조 및 플로우 분석

## 1. 개요

- 저장소: `facebookresearch/HyperAgents`
- 방향성: self-referential self-improving agent
- 구현 스택: Python + Docker + LiteLLM
- 핵심 엔트리: `generate_loop.py`

HyperAgents는 단일 에이전트 성능 향상보다, **에이전트를 개선하는 메커니즘 자체**를 반복적으로 실행하는 구조에 초점을 둡니다.

---

## 2. 코드 구조 요약

### 2.1 에이전트 계층

- `meta_agent.py`: 코드베이스를 수정하는 메타 에이전트
- `task_agent.py`: 주어진 태스크 입력을 풀고 JSON 응답 생성
- `agent/llm.py`: LiteLLM 래퍼 (OpenAI/Claude/Gemini 모델 상수 및 호출)
- `agent/llm_withtools.py`: 툴 호출 JSON 프로토콜 (`tool_name`, `tool_input`)

### 2.2 루프/선택/아카이브 계층

- `generate_loop.py`: 세대 생성/평가/아카이브/부모 재선택 전체 오케스트레이션
- `select_next_parent.py`: 아카이브에서 다음 부모 세대 선택
- `ensemble.py`: 아카이브 중 최고 점수 세대 예측을 앙상블 기준으로 선택
- `utils/gl_utils.py`: 점수 로딩, patch lineage, metadata/아카이브 업데이트 핵심 유틸

### 2.3 평가/도메인 계층

- `domains/harness.py`: 도메인별 TaskAgent 실행 하네스
- `domains/report.py`, `domains/run_eval.py`: 리포트 생성/평가 러너
- `domains/*`: search_arena, paper_review, imo, balrog, genesis, polyglot
- `utils/domain_utils.py`: 도메인별 split/score key/staged eval 샘플 규칙

### 2.4 인프라 계층

- `utils/docker_utils.py`: 컨테이너 빌드/실행/복사/로그/정리
- `utils/git_utils.py`: diff, commit hash, reset 관련 유틸

---

## 3. 실행 플로우 (코드 기준)

1. `generate_loop.py`가 초기 세대(또는 resume) 로딩  
2. archive 기반 부모 세대 선택  
3. Docker 컨테이너에서 lineage patch 적용  
4. `run_meta_agent.py` → `MetaAgent.forward()`로 새 패치 생성  
5. 패치 존재 시 도메인 harness로 staged/full evaluation 수행  
6. `report.json` 점수 기준으로 `metadata.json` 갱신  
7. `archive.jsonl`에 generation 추가 후 다음 세대 반복  

핵심적으로 **생성(메타 에이전트)과 검증(하네스/리포트)**가 분리되어 있습니다.

---

## 4. 설계 포인트

### 4.1 Self-referential 개선

메타 에이전트가 `repo_path` 전체를 수정 대상으로 삼아, 에이전트 코드/루프 코드를 포함한 상위 레벨 로직까지 변경 가능하게 설계됩니다.

### 4.2 Generation lineage 추적

`prev_patch_files`, `curr_patch_files`, `parent_genid`를 메타데이터로 누적해 세대 계보를 보존합니다.

### 4.3 Staged eval 게이트

일부 도메인은 소규모 staged eval을 먼저 수행하고 통과 시 full eval로 확장합니다. 비용/시간 제어를 위한 구조입니다.

### 4.4 컨테이너 격리

생성·평가·리셋 과정을 컨테이너 내부에서 수행 후 정리(`git reset --hard`, `git clean -fd`)하여 실험 상태 오염을 낮춥니다.

---

## 5. 트레이드오프

### 장점

1. **반복 실험 자동화**: 세대 생성-평가-선택 루프 자동화  
2. **재현 가능한 로그**: outputs/metadata/archive 기반 추적 용이  
3. **다중 도메인 확장성**: 도메인별 harness 분리 구조  

### 한계

1. **운영 비용**: Docker + 도메인별 평가 인프라 요구  
2. **평가 의존성**: score key/리포트 품질이 루프 방향을 좌우  
3. **코드 실행 리스크**: README에서도 model-generated code 실행 위험을 명시  

---

## 6. 추가 조사(웹/생태계)

- 공식 저장소는 태그/릴리즈 없이 커밋 중심으로 공개되고 있습니다.
- GitHub 생태계에서 HyperAgents 아이디어를 참조한 파생 구현(예: OpenClaw 연동 DGM-H 루프) 사례가 확인됩니다.
- 공식 README는 실험 로그 다운로드 링크와 함께 arXiv/Meta publication 링크를 제공합니다.

---

## 참고 링크

- [HyperAgents Repository](https://github.com/facebookresearch/HyperAgents)
- [Meta Publication](https://ai.meta.com/research/publications/hyperagents/)
- [arXiv 2603.19461](https://arxiv.org/abs/2603.19461)
- [OpenClaw 기반 파생 구현 예시](https://github.com/GnawClawHQ/dgm-hyperagents-openclaw)
