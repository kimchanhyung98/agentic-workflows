# HyperAgents 분석

`facebookresearch/HyperAgents`의 공개 코드와 문서를 기준으로, 핵심 구조와 실행 플로우를 정리한 문서입니다.

HyperAgents는 에이전트가 자신의 코드베이스를 다시 수정하고 평가하는 **self-referential self-improving** 루프를 구현합니다.

---

## 분석 범위

- Meta 공개 자료 확인
  - GitHub: `facebookresearch/HyperAgents`
  - Meta Research 소개 페이지
  - arXiv 논문(2603.19461)
- 코드 구조 분석
  - `generate_loop.py`
  - `meta_agent.py`
  - `task_agent.py`
  - `domains/harness.py`, `domains/report.py`
- 실행 플로우 정리
  - 세대 생성 → 패치 적용 → 평가 → 부모 선택 → 반복

---

## 아키텍처 개요

```text
MetaAgent (코드 수정 제안/생성)
   ↓
패치(model_patch.diff) 생성
   ↓
Docker 격리 환경에서 lineage patch 적용
   ↓
TaskAgent 평가 (domain harness/report)
   ↓
아카이브 업데이트 (generation metadata, score)
   ↓
부모 선택(select_parent / select_next_parent)
   ↓
다음 세대 반복(generate_loop)
```

### 핵심 컴포넌트

- **MetaAgent (`meta_agent.py`)**
  - 리포지토리 수정을 목표로 LLM 에이전트를 호출
  - tool 사용이 가능한 채팅 루프(`chat_with_agent`) 기반
- **TaskAgent (`task_agent.py`)**
  - 도메인 태스크를 입력받아 JSON 스키마 응답 생성
  - `domains/harness.py`에서 병렬 실행되어 성능 측정에 사용
- **Generate Loop (`generate_loop.py`)**
  - 세대별 컨테이너 실행, 패치 적용, 평가, 아카이브/시각화 갱신
  - 옵션에 따라 staged eval, full eval, ensemble 평가 수행

---

## 코드 기반 실행 플로우

1. **초기 세대 준비**
   - 출력 디렉토리/아카이브 초기화
   - 필요 시 meta patch 선적용
2. **부모 선택**
   - 기본 점수 기반/랜덤/최신 선택 또는 편집된 선택 로직 실행
3. **세대 생성**
   - 컨테이너에서 부모 계보 patch 적용 후 MetaAgent 실행
   - 생성된 `model_patch.diff`를 다음 평가의 후보로 등록
4. **평가**
   - 도메인 harness 실행(`domains.harness`)
   - 리포트 생성(`domains.report`)
   - staged eval 통과 시 full eval로 확장
5. **아카이브 업데이트 및 반복**
   - metadata/score 저장
   - 다음 부모를 선택하고 최대 세대까지 반복

---

## 구현 관찰 포인트

- **격리 실행 중심 설계**: 세대 생성/평가를 컨테이너로 분리해 재현성 관리
- **아카이브 기반 탐색**: 단일 최신 버전이 아니라 계보 전체를 부모 후보로 유지
- **도메인 확장 구조**: `domains/*` 유틸 동적 로딩으로 평가 도메인 확장 가능
- **자기개선 루프 실험 친화성**: baseline 옵션, staged/full eval, ensemble 비교를 한 루프에서 제어

---

## 참고 자료

- https://github.com/facebookresearch/hyperagents
- https://ai.meta.com/research/publications/hyperagents/
- https://arxiv.org/abs/2603.19461
