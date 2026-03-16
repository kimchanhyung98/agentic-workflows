# 프로젝트 Deep Analysis 워크플로우 — 상세 문서

## 개요

대규모 프로젝트의 전체 소스코드를 AI로 분석하는 워크플로우이다.
소스코드를 **XML Bundling**으로 구조화하고, **3단계 점진적 리뷰**로 파일 수준부터 프로젝트 수준까지 검증한다.

```text
XML Bundling (소스코드 구조화) + 3단계 점진적 리뷰 (파일 → 기능 도메인 → 프로젝트) = 프로젝트 Deep Analysis
```

> 참고: [LLM이 Django에서 보안 취약점을 찾은 방법](https://new-blog.ch4n3.kr/llm-found-security-issues-from-django-ko/)

---

## 아키텍처

[다이어그램 참조](00-diagram.md)

4계층으로 구성된다.

| 레이어             | 역할                              |
|-----------------|---------------------------------|
| Layer 1: Input  | 프로젝트 소스코드, 리뷰 설정                |
| Layer 2: Bundle | 파일 수집 · 필터링, 단계별 XML Bundling   |
| Layer 3: Review | 3단계 점진적 리뷰 — 파일 → 기능 도메인 → 프로젝트 |
| Layer 4: Output | 단계별 리뷰 문서 (3개) + 최종 리뷰 리포트      |

### Layer 1: Input

분석 대상 프로젝트와 리뷰 설정을 입력한다.

**프로젝트 소스코드** — 분석 대상이 되는 프로젝트 디렉토리 전체. Git 저장소를 기준으로, 추적 대상 파일이 수집 범위가 된다.

**리뷰 설정** — 분석의 범위와 관점을 정의한다.

- **리뷰 관점**: 보안, 코드 품질, 성능, 설계 패턴 등 중점적으로 검토할 영역
- **제외 패턴**: 분석에서 제외할 파일/디렉토리 (예: `vendor/`, `*.min.js`, 테스트 픽스처)
- **기능 도메인 정의**: 관련 파일을 묶는 기준 (기능, 디렉토리, 수동 지정)
- **대상 언어**: 분석할 프로그래밍 언어 필터 (선택)

### Layer 4: Output

3단계 리뷰에서 생성된 리뷰 문서를 최종 리포트로 종합한다.

| 산출물           | 생성 시점    | 내용                            |
|---------------|----------|-------------------------------|
| 파일 리뷰 문서      | 1단계 완료 후 | 파일별 이슈 목록 — 로직, 보안, 문법 오류     |
| 도메인 리뷰 문서     | 2단계 완료 후 | 기능 도메인별 이슈 목록 — 일관성, 흐름, 커버리지 |
| 프로젝트 리뷰 문서    | 3단계 완료 후 | 프로젝트 수준 이슈 — 아키텍처, 전체 패턴      |
| **최종 리뷰 리포트** | 전체 완료 후  | 3개 리뷰 문서의 종합 — 중복 제거, 심각도 재판정 |

**최종 리뷰 리포트 구성**:

- **요약**: 전체 리뷰 결과 개요 — 단계별 이슈 수, 심각도 분포
- **이슈 목록**: 전 단계의 이슈를 심각도순으로 통합 — 위치, 심각도, 설명, 개선 제안
- **주요 발견**: 프로젝트 전반에 걸친 패턴 이슈 또는 구조적 문제
- **긍정적 측면**: 잘 작성된 코드, 좋은 패턴 활용 사례

**심각도 분류**:

| 심각도 | 설명                           | 예시                 |
|-----|------------------------------|--------------------|
| 심각  | 즉시 수정 필요 — 보안 취약점, 데이터 손실 위험 | SQL 인젝션, 하드코딩된 비밀키 |
| 높음  | 빠른 수정 권장 — 버그, 심각한 설계 결함     | 인증 우회 가능성, 메모리 누수  |
| 중간  | 개선 권장 — 코드 품질, 유지보수성 이슈      | 코드 중복, 부적절한 에러 처리  |
| 낮음  | 참고 사항 — 스타일, 사소한 개선 가능 사항    | 네이밍 컨벤션, 주석 부족     |

---

## 3단계 점진적 리뷰

범위를 점진적으로 넓히며, 이전 단계에서 감지하지 못한 이슈를 보완한다.
각 단계마다 독립적인 **리뷰 문서**를 산출한다.

```text
1단계 (파일별 리뷰) → 📄 파일 리뷰 문서
    → 2단계 (기능 도메인 리뷰) → 📄 도메인 리뷰 문서
        → 3단계 (프로젝트 리뷰) → 📄 프로젝트 리뷰 문서
```

### 1단계: 파일 리뷰

개별 파일의 로직, 보안, 문법 오류를 검증한다.

**입력**: 파일 단위 XML 번들 (대상 파일 + import/참조 관련 파일)

**검증 관점**:

- 문법 오류, 타입 불일치
- 보안 취약점 (SQL 인젝션, XSS, 하드코딩된 시크릿)
- 로직 버그, 엣지케이스 누락
- 에러 처리 누락, 리소스 미해제
- 코딩 컨벤션 위반

**산출물 — 파일 리뷰 문서**:

```text
# 1단계 파일 리뷰 — src/views/auth.py

[심각] :42 SQL 인젝션 취약점
  - f-string으로 사용자 입력을 직접 쿼리에 삽입
  - 개선: ORM 또는 파라미터화된 쿼리 사용

[높음] :15 (context: src/utils/crypto.py) 약한 해시 알고리즘
  - 비밀번호 해싱에 MD5 사용
  - 개선: bcrypt 또는 argon2 사용

[중간] :28 에러 처리 누락
  - 데이터베이스 조회 실패 시 예외 처리 없음
```

### 2단계: 기능 도메인 리뷰

하나의 기능을 구성하는 파일 묶음의 일관성과 상호작용을 검증한다.

**입력**:

- 기능 도메인 XML 번들 (관련 파일 묶음)
- 1단계 리뷰 문서 (이미 지적된 사항은 제외하고 이 단계의 관점에서만 리뷰)

**검증 관점**:

- 파일 간 인터페이스 불일치 (model 필드와 serializer 필드 불일치 등)
- 도메인 내 코드 중복
- 입력 검증 흐름 (view → serializer → model 흐름의 정합성)
- 테스트 커버리지 (해당 기능의 핵심 경로가 테스트되고 있는가)
- 도메인 내 책임 분리 (비즈니스 로직이 적절한 레이어에 위치하는가)

**산출물 — 도메인 리뷰 문서**:

```text
# 2단계 도메인 리뷰 — auth

[높음] 입력 검증 흐름 불일치
  - views/auth.py:42에서 사용자 입력을 직접 사용
  - serializers/user.py의 검증 로직을 거치지 않음
  - 관련 파일: views/auth.py, serializers/user.py

[중간] 테스트 커버리지 부족
  - login 실패 케이스(잘못된 비밀번호, 미등록 이메일)에 대한 테스트 없음
  - 관련 파일: tests/test_auth.py

[중간] 책임 분리 위반
  - views/auth.py에 비밀번호 비교 로직이 직접 구현됨
  - models/user.py 또는 별도 서비스 레이어로 이동 권장
```

### 3단계: 프로젝트 리뷰

프로젝트 전체의 아키텍처, 일관성, 전체 패턴을 검증한다.

**입력**: 프로젝트 XML 번들 (1~2단계 리뷰 결과 + 프로젝트 구조 + 설정 파일)

**검증 관점**:

- 아키텍처 일관성 (레이어 위반, 의존성 방향)
- 도메인 간 중복 구현
- 전체 보안 패턴 (인증 미적용 엔드포인트, CSRF 보호 범위)
- 에러 응답 형식 일관성
- 설정 관련 이슈 (미들웨어 순서, 환경별 설정)
- 1~2단계에서 반복적으로 나타난 패턴 이슈의 프로젝트 수준 진단

**산출물 — 프로젝트 리뷰 문서**:

```text
# 3단계 프로젝트 리뷰 — my-project

[높음] 인증 미적용 엔드포인트 존재
  - views/public.py의 3개 엔드포인트에 @login_required 누락
  - 1단계에서 개별 파일로는 정상 판정되었으나, 프로젝트 정책상 인증 필수

[중간] 에러 응답 형식 불일치
  - auth 도메인: {"error": "message"} 형식
  - order 도메인: {"detail": "message"} 형식
  - 2단계에서 각 도메인 내부는 일관적이나, 도메인 간 불일치 확인

[중간] 1~2단계 반복 패턴
  - 5개 파일에서 동일한 "에러 처리 누락" 패턴 발견
  - 프로젝트 수준의 공통 에러 처리 미들웨어 도입 권장

[낮음] 레이어 위반 2건
  - models/order.py가 views/cart.py를 import (역방향 의존성)
  - utils/email.py가 models/user.py를 import (유틸리티가 도메인 모델에 의존)
```

---

## XML Bundling

소스코드를 LLM이 이해할 수 있는 구조화된 형식으로 변환한다.
리뷰 단계에 따라 번들 범위가 달라진다.

### 파일 수집

```text
디렉토리 순회 → 필터링 → 단계별 XML Bundling (파일 / 기능 도메인 / 프로젝트)
```

프로젝트 디렉토리를 순회하여 분석 대상 파일을 수집한다.

- `.gitignore` 규칙을 기본 제외 패턴으로 적용
- 리뷰 설정의 제외 패턴을 추가 적용
- 바이너리 파일, 미디어 파일 자동 제외
- 빈 파일, 자동 생성 파일(`package-lock.json`, `*.generated.*`) 제외

### 단계별 번들 범위

| 리뷰 단계        | 번들 범위                   | 예시                                         |
|--------------|-------------------------|--------------------------------------------|
| 1단계 (파일)     | 대상 파일 + import/참조 관련 파일 | `auth.py` + User 모델 + crypto 유틸            |
| 2단계 (기능 도메인) | 하나의 기능을 구성하는 파일 묶음      | auth view + user model + serializer + test |
| 3단계 (프로젝트)   | 이전 단계 리뷰 결과 + 프로젝트 구조   | 1~2단계 리뷰 문서 + 디렉토리 트리 + 설정 파일              |

### XML 구조

`<content>` 내부의 원문 코드는 반드시 XML-escaped 텍스트로 저장한다.
`<`, `>`, `&` 같은 문자는 엔티티로 변환하여, HTML/XML/JSX나 문자열 리터럴이 포함되어도 문서 전체가 항상 유효한 XML이 되도록 한다.

#### 태그 설명

| 태그                   | 속성                                   | 설명                                          |
|----------------------|--------------------------------------|---------------------------------------------|
| `<review>`           | `target`, `domain`, `scope`, `name` | 리뷰 단위를 정의합니다. `target`(파일 경로), `domain`(기능 도메인), `scope='project'`(프로젝트)로 범위를 지정하고, `name`으로 프로젝트 식별자를 지정합니다. |
| `<structure>`        | —                                    | 프로젝트 디렉토리 구조                              |
| `<file>`             | `path`, `role`, `language`           | 개별 파일 — 경로, 역할, 언어 정보 포함                  |
| `<content>`          | `encoding`                           | XML-escaped 형태로 저장된 실제 소스코드 내용          |
| `<config>`           | `path`, `language`                   | 프로젝트 설정 파일 (3단계에서 사용)                   |
| `<previous-reviews>` | —                                    | 이전 단계 리뷰 결과 (3단계에서 사용)                  |

### 1단계 번들: 파일 단위

각 소스 파일마다 개별 XML을 생성한다.
대상 파일(`role="target"`)과 해당 파일이 import/참조하는 관련 파일(`role="context"`)을 함께 포함한다.

```xml
<review target="src/views/auth.py">
  <structure>
src/
├── models/
│   └── user.py
├── views/
│   └── auth.py        ← 리뷰 대상
└── utils/
    └── crypto.py
  </structure>

  <file path="src/views/auth.py" role="target" language="python">
    <content encoding="xml-escaped">
from src.models.user import User
from src.utils.crypto import hash_password

def login(request):
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = User.objects.filter(email=email).first()
    if user and hash_password(password) == user.password:
        return create_session(user)
    return HttpResponse("Invalid credentials", status=401)
    </content>
  </file>

  <file path="src/models/user.py" role="context" language="python">
    <content encoding="xml-escaped">
class User(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    </content>
  </file>

  <file path="src/utils/crypto.py" role="context" language="python">
    <content encoding="xml-escaped">
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
    </content>
  </file>
</review>
```

### 2단계 번들: 기능 도메인 단위

하나의 기능을 구성하는 관련 파일을 모두 묶어 하나의 XML을 생성한다.
해당 기능의 모든 파일이 리뷰 대상(`role="target"`)이다.

```xml
<review domain="auth">
  <structure>
src/
├── models/
│   └── user.py
├── views/
│   └── auth.py
├── serializers/
│   └── user.py
└── tests/
    └── test_auth.py
  </structure>

  <file path="src/views/auth.py" role="target" language="python">
    <content encoding="xml-escaped">...</content>
  </file>

  <file path="src/models/user.py" role="target" language="python">
    <content encoding="xml-escaped">...</content>
  </file>

  <file path="src/serializers/user.py" role="target" language="python">
    <content encoding="xml-escaped">...</content>
  </file>

  <file path="src/tests/test_auth.py" role="target" language="python">
    <content encoding="xml-escaped">...</content>
  </file>
</review>
```

기능 도메인 그룹핑의 기준:

- 같은 기능을 구성하는 view, model, serializer, test 등을 하나로 묶는다
- 디렉토리 구조가 아닌 **기능/도메인** 단위로 그룹핑한다
- 예: `auth` 도메인 = `views/auth.py` + `models/user.py` + `serializers/user.py` + `tests/test_auth.py`

### 3단계 번들: 프로젝트 단위

원본 코드 대신, 이전 단계의 리뷰 결과와 프로젝트 메타데이터를 입력으로 구성한다.

```xml
<review scope="project" name="my-project">
  <structure>
src/
├── models/
├── views/
├── serializers/
├── utils/
└── tests/
  </structure>

  <config path="settings.py" language="python">
    <content encoding="xml-escaped">...</content>
  </config>

  <config path="urls.py" language="python">
    <content encoding="xml-escaped">...</content>
  </config>

  <previous-reviews>
    <stage1-summary>
      1단계 파일별 리뷰 결과 요약 (이슈 목록, 심각도 분포)
    </stage1-summary>
    <stage2-summary>
      2단계 기능 도메인별 리뷰 결과 요약 (도메인 간 이슈, 일관성 문제)
    </stage2-summary>
  </previous-reviews>
</review>
```

### XML Bundling의 장점

| 장점         | 설명                                              |
|------------|-------------------------------------------------|
| 구조 보존      | 파일 경로가 XML 속성으로 포함되어 프로젝트 구조를 유지                |
| 파일 간 관계 파악 | 관련 파일끼리 묶인 번들 안에서 import/참조 관계를 LLM이 직접 추적 가능   |
| 메타데이터 포함   | 파일 경로, 언어, 역할(target/context) 등의 메타데이터를 속성으로 포함 |
| 단계별 확장     | 동일한 XML 구조로 파일 → 도메인 → 프로젝트까지 일관되게 표현           |
| LLM 친화적    | XML은 LLM이 잘 이해하는 구조화 형식 — 파일 경계와 내용을 명확히 구분     |

일반 텍스트 방식(`=== file.py ===`)은 파일 경계 구분이 모호하고 메타데이터를 표현하기 어렵다.
XML은 태그로 경계를 명확히 하고, 속성으로 메타데이터를 자연스럽게 포함한다.

---

## 멀티 AI 리뷰

각 단계에서 복수의 AI 모델이 서로 다른 관점으로 병렬 검증한다.
[개발 워크플로우의 멀티 AI 리뷰](../dev-automation/01-detail.md#멀티-ai-리뷰-구조)와 동일한 구조를 적용한다.

### 리뷰어 구성

| 역할    | 검증 관점                                                |
|-------|------------------------------------------------------|
| 리뷰어 1 | **보안**: 인증/인가, 입력 검증, SQL 인젝션, XSS, 민감정보 노출, 암호화     |
| 리뷰어 2 | **코드 품질**: 설계 패턴, 코드 중복, 네이밍, 에러 처리, 유지보수성, SOLID 원칙 |
| 리뷰어 3 | **성능**: N+1 쿼리, 메모리 누수, 불필요한 연산, 캐싱, 리소스 관리, 동시성 이슈  |

리뷰어 구성은 프로젝트 특성에 따라 조정한다.
예: 프론트엔드 프로젝트는 접근성·UX 관점을 추가하고, 데이터 파이프라인은 데이터 정합성 관점을 추가한다.

### 개발 워크플로우와의 비교

| 요소     | 개발 워크플로우           | Deep Analysis 워크플로우              |
|--------|--------------------|----------------------------------|
| 리뷰 대상  | 기획 문서 또는 코드 diff   | 프로젝트 전체 소스코드                     |
| 입력 형식  | 기획 문서 또는 diff      | 단계별 XML Bundle (파일 / 도메인 / 프로젝트) |
| 병렬 리뷰  | 복수 AI 모델이 독립적으로 검증 | 동일                               |
| 결과 종합  | 오케스트레이션 AI가 판정     | 단계별 리뷰 문서 → 최종 리포트 종합            |
| 피드백 루프 | 실패 시 수정 → 재리뷰      | 없음 (일회성 분석)                      |

- 개발 워크플로우는 **코드 변경(diff) 기준**으로 리뷰하지만, Deep Analysis는 **프로젝트 전체**를 분석한다
- 개발 워크플로우는 기획 문서 대조가 핵심이지만, Deep Analysis는 **일반적인 코드 품질 관점**으로 분석한다
- Deep Analysis는 **3단계 점진적 리뷰**로 파일 수준부터 프로젝트 수준까지 범위를 확장한다
- Deep Analysis에는 자동 수정 루프가 없다 — 리포트를 산출물로 제공한다

---

## 설계 원칙

| 원칙           | 설명                                   |
|--------------|--------------------------------------|
| XML Bundling | 소스코드를 구조화된 XML로 변환 — 파일 경로 · 역할을 보존  |
| 3단계 점진적 리뷰   | 파일 → 기능 도메인 → 프로젝트 — 이전 단계 결과가 다음 입력 |
| 멀티 AI 리뷰     | 복수 모델의 병렬 검증 — 각 단계에서 독립적으로 적용       |
| 단계별 산출물      | 3개 리뷰 문서 + 최종 리포트 — 심각도 분류 · 개선 제안   |

### 적용된 설계 패턴

| 패턴              | 적용 위치           | 설명                              |
|-----------------|-----------------|---------------------------------|
| Parallel        | 각 단계의 멀티 AI 리뷰  | 복수 모델이 병렬로 검증, 결과 집계            |
| MapReduce       | 1단계 파일별 리뷰 → 종합 | 개별 파일을 독립 리뷰한 뒤 결과를 합산          |
| Sectioning      | 기능 도메인 그룹핑      | 프로젝트를 기능 도메인 단위로 분할하여 단계적 리뷰    |
| Review-Critique | 멀티 AI 리뷰        | 각 리뷰어가 서로 다른 관점에서 비평            |
| Pipeline        | 3단계 점진적 리뷰      | 이전 단계 결과가 다음 단계의 입력으로 흐르는 연쇄 구조 |

---

## 검토 사항

- XML Bundling 도구는 CLI 스크립트로 제공할 것인가, 에이전트가 직접 수행할 것인가?
- 기능 도메인 그룹핑은 자동 감지할 것인가, 수동 설정할 것인가?
- 리뷰어 모델 구성은 고정인가, 프로젝트별 설정인가?
- 리뷰 결과의 출력 형식은? (마크다운, JSON, GitHub Issue)
- 정기적 분석(cron)과 수동 실행을 모두 지원할 것인가?
- 분석 결과를 개발 워크플로우의 기획 단계에 피드백으로 활용할 수 있는가?

---

## 참고 자료

- [LLM이 Django에서 보안 취약점을 찾은 방법](https://new-blog.ch4n3.kr/llm-found-security-issues-from-django-ko/)
- [로컬 개발 에이전트 워크플로우](../dev-automation/01-detail.md)
- [멀티 AI 리뷰 구조](../dev-automation/01-detail.md#멀티-ai-리뷰-구조)
- [병렬 패턴](/docs/effective-agents/03-parallelization.md)
- [병렬 패턴 (Google Cloud)](/docs/design-pattern/03-parallel.md)
- [Review-Critique 패턴](/docs/design-pattern/05-review-critique.md)
