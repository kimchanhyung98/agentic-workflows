# Open SWE 아키텍처 및 워크플로우 상세 분석

## 1. 개요

- 저장소: `langchain-ai/open-swe`
- 성격: 조직 내부 코딩 에이전트를 빠르게 구축하기 위한 오픈소스 프레임워크
- 핵심 기반: **LangGraph 런타임 + Deep Agents harness**
- 주요 목표:
  - Slack/Linear/GitHub 등 기존 협업 표면에서 호출
  - 격리 샌드박스에서 안전하게 코드 작업
  - 자동 커밋/PR 생성까지 파이프라인화

Open SWE의 핵심은 "에이전트 자체를 처음부터 만드는 것"보다, Deep Agents 위에 조직별 실행 규칙과 통합 포인트를 얹는 구조입니다.

---

## 2. 아키텍처 레이어

## 2.1 Trigger & Ingestion Layer

요청 진입점은 3가지입니다.

1. **Slack**: 스레드에서 멘션으로 작업 요청
2. **Linear**: 이슈 코멘트 멘션으로 요청
3. **GitHub**: 이슈/PR 코멘트 멘션으로 요청

이 레이어의 역할은 "메시지 수신"이 아니라, 실행에 필요한 맥락(스레드/이슈/사용자/대상 레포)을 결정적으로 정규화하는 것입니다.

## 2.2 Agent Harness Layer (Deep Agents)

Open SWE는 `create_deep_agent(...)`로 에이전트를 조립합니다. 이때 Deep Agents가 제공하는 기본 역량이 핵심 실행 엔진이 됩니다.

- **Planning**: `write_todos`
- **Filesystem**: `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`
- **Shell**: `execute`
- **Sub-agent Delegation**: `task`
- **Context Management**: 긴 대화/대출력 자동 요약 및 컨텍스트 유지

즉, Open SWE는 Deep Agents의 일반 목적 코딩 루프를 재사용하고, 외부 시스템 연결과 안전장치를 강화합니다.

## 2.3 Tool Layer (Curated Tooling)

Open SWE는 "도구 개수"보다 "도구 큐레이션"을 우선합니다.

- `commit_and_open_pr`: 커밋 + Draft PR 생성
- `fetch_url`: 웹 문서 수집
- `http_request`: 외부 API 호출
- `linear_comment`: Linear 업데이트
- `slack_thread_reply`: Slack 스레드 응답

여기에 Deep Agents 내장 도구가 합쳐져 실제 작업 루프를 구성합니다.

## 2.4 Sandbox Layer

각 작업은 독립 샌드박스에서 실행됩니다.

- 기본: LangSmith cloud sandbox
- 대체 가능: Daytona / Runloop / Modal / Local
- 설계 원칙: **경계 밖 권한 최소화, 경계 안 실행 자유도 최대화**

스레드 단위로 샌드박스를 재사용해 후속 지시를 같은 실행 문맥에서 처리할 수 있습니다.

## 2.5 Middleware Layer

미들웨어는 비결정적 LLM 루프 주위에 결정적 제어를 추가합니다.

- `ToolErrorMiddleware`: 도구 오류 처리
- `check_message_queue_before_model`: 실행 중 들어온 후속 메시지 반영
- `ensure_no_empty_msg`: 빈 메시지 보호
- `open_pr_if_needed`: PR 미생성 시 안전망 동작

이 구조는 "모델이 잘하면 좋고, 못해도 망가지지 않게" 만드는 실무형 설계입니다.

---

## 3. End-to-End 워크플로우

1. **요청 수신**: Slack/Linear/GitHub 이벤트 발생
2. **컨텍스트 조립**: 이슈 본문, 코멘트, 스레드 히스토리, 사용자 정보, 대상 레포 추출
3. **프롬프트 구성**: 시스템 프롬프트 + 소스 컨텍스트 + `AGENTS.md` 주입
4. **Deep Agent 루프 시작**:
   - `write_todos`로 계획 수립
   - 파일/셸 도구로 구현
   - 필요 시 `task`로 서브에이전트 병렬 위임
5. **검증 단계**: 린트/테스트/포맷 확인 (프롬프트 유도 + 팀 규칙)
6. **PR 단계**: `commit_and_open_pr` 수행, 실패 시 `open_pr_if_needed`가 후처리
7. **회신 단계**: Slack/Linear/GitHub에 결과 링크/상태 전달

핵심은 단발성 답변이 아니라, "협업 도구 안에서 지속되는 작업 세션"이라는 점입니다.

---

## 4. Deep Agents 관점에서 본 Open SWE

문제 요구사항의 핵심인 deep-agent(Deep Agents) 기반성은 다음 3가지에서 명확합니다.

### 4.1 에이전트 조립 방식

Open SWE는 독자 에이전트 루프를 새로 구현하지 않고, Deep Agents의 `create_deep_agent`에 모델/도구/미들웨어/백엔드를 주입하는 방식입니다.

### 4.2 실행 능력 재사용

코드 작업에 필요한 기본 실행 능력(파일, 셸, 계획, 서브에이전트, 컨텍스트 관리)을 Deep Agents에서 그대로 가져옵니다.

### 4.3 확장성 보장

Deep Agents가 LangGraph 기반이므로, Open SWE도 스트리밍/체크포인트/스튜디오 연계 같은 LangGraph 런타임 장점을 계승합니다.

요약하면 Open SWE는 "Deep Agents를 조직용 내부 코딩 에이전트로 제품화하는 참조 구현"에 가깝습니다.

---

## 5. 장점과 트레이드오프

## 장점

1. **빠른 내부 도입**: 트리거-샌드박스-PR 루프가 이미 연결되어 있음
2. **안전한 실행 경계**: 샌드박스 격리로 blast radius 축소
3. **실행 중 상호작용**: 작업 도중 follow-up 메시지 주입 가능
4. **구성 가능한 기반**: 샌드박스/모델/도구/트리거/미들웨어를 선택 교체

## 트레이드오프

1. **운영 복잡도**: GitHub App, OAuth, Webhook, Sandbox 인프라 설정 필요
2. **도구 품질 의존성**: 조직별 내부 API/도구 품질이 전체 성능에 영향
3. **검증 자동화 한계**: 강한 결정론 검증(CI 게이트)을 추가하지 않으면 품질 편차 가능

---

## 6. 실무 적용 인사이트

- **규칙은 코드보다 AGENTS.md로 먼저 고정**: 레포별 코딩 규칙/검증 기준을 컨텍스트로 강제
- **트리거별 모델/도구 차등화**: Slack(경량) vs Linear/GitHub(코드수정 중심)로 비용 최적화
- **미들웨어에 품질 게이트 추가**: 조직 CI 상태 확인, 보안 스캔, 배포 정책을 after-agent에 결합
- **샌드박스 이미지 표준화**: 언어/빌드 도구를 미리 포함한 템플릿으로 초기 실행 시간 단축

---

## 7. 참고 링크

- [Open SWE 저장소](https://github.com/langchain-ai/open-swe)
- [Open SWE Announcement](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/)
- [Open SWE README](https://raw.githubusercontent.com/langchain-ai/open-swe/main/README.md)
- [Open SWE Customization Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/CUSTOMIZATION.md)
- [Open SWE Installation Guide](https://raw.githubusercontent.com/langchain-ai/open-swe/main/INSTALLATION.md)
- [Deep Agents 저장소](https://github.com/langchain-ai/deepagents)
- [Deep Agents 문서](https://docs.langchain.com/oss/python/deepagents/overview)
- [뉴스 하다: open-swe 소개](https://news.hada.io/topic?id=27604)
