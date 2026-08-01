# Bun Zig→Rust 재작성 사례 분석

## 1. 조사 범위와 판정 기준

이 문서는 Bun의 2026년 Zig→Rust 포트를 다음 질문으로 나눠 조사한다.

1. 왜 언어를 바꿨고, 어디까지 바꿨는가?
2. 약 50개의 AI 워크플로와 최대 약 64개의 동시 작업을 어떻게 충돌 없이 나눴는가?
3. 컴파일러와 테스트 러너의 오류 목록을 어떻게 작업 큐로 사용했는가?
4. 어떤 검증을 거쳐 병합했고, 공개 증거가 보장하지 못하는 부분은 무엇인가?
5. 다른 대규모 마이그레이션을 분석할 때 전이 가능한 원리는 무엇인가?

사실의 기준은 [Bun 공식 회고](https://bun.com/blog/bun-in-rust)다. 수치와 구현 세부는 [PR #30412](https://github.com/oven-sh/bun/pull/30412), 병합 커밋 [`23427dbc`](https://github.com/oven-sh/bun/commit/23427dbc12fdcff30c23a96a3d6a66d62fdc091d), 그 커밋의 워크플로와 스크립트로 교차 확인했다. GeekNews와 WikiDocs는 2차 자료로만 사용한다.

이 분석에서 다음 표현은 서로 다르다.

- **확인:** 공식 글, GitHub 메타데이터, 공개 코드에서 직접 확인
- **공식 집계:** Bun 팀이 회고에서 보고했지만 공개 자료만으로 원장 전체를 재구성할 수 없는 값
- **외부 관찰:** Bun 팀 밖의 사용자가 제한된 조건에서 확인한 결과
- **역설계:** 공개된 실행 흔적을 일관된 오케스트레이션 구조로 설명하기 위해 도출한 모델

이하에서는 workflow를 워크플로, worker를 작업자, fixer를 수정자, worktree를 워크트리, shard를 샤드로 적는다. 코드와 파일 이름은 원문 표기를 유지한다.

Rust 구현은 2026-05-14 `main`에 병합돼 canary에서 사용 중이다. 공식 글은 첫 Rust 안정판으로 v1.4.0을 예고했다. 직전 안정 릴리스는 병합 하루 전인 2026-05-13에 게시된 v1.3.14이고 Zig 구현이다.

즉 2026-05-14 `main` 병합은 안정판 출시와 다른 사건이다. 이 사례를 인용할 때 “Rust로 재작성을 마쳤다”와 “Rust 버전을 출시했다”는 구분해야 한다.

## 2. 왜 Rust였는가

공식 글이 든 직접 원인은 Zig 자체의 결함이 아니라 Bun의 메모리 모델이었다.

- Bun은 JavaScriptCore의 garbage collector와 수동 메모리 관리를 함께 사용한다.
- 이 경계에서 use-after-free, double-free, 해제 누락, 오류 경로의 leak이 반복됐다.
- 안전한 Rust 코드는 소유권 오류를 컴파일 시점에 드러내고, `Drop`으로 조기 반환과 오류 경로의 정리를 일관되게 만든다.
- 공식 글은 GC 값과 수동 수명을 함께 다루는 것이 주요 안정성 문제였고, 메모리 버그가 팀의 개발·디버깅 시간을 막대하게 소모했다고 밝힌다.

따라서 결론을 “Zig는 안전하지 않고 Rust는 모든 메모리 버그를 막는다”로 넓히면 안 된다. Bun의 Rust 코드에는 FFI와 `unsafe`가 남아 있고, JavaScriptCore, uWebSockets/usockets, lshpack/lsquic, BoringSSL, SQLite를 포함한 C·C++ 코드도 전체의 약 20%를 차지한다.

병합 직후에는 안전하다고 선언된 API를 통해 댕글링 참조(dangling reference, 이미 해제된 메모리를 가리키는 참조)에 도달할 수 있는 문제가 [GitHub issue #30719](https://github.com/oven-sh/bun/issues/30719)에서 Miri로 재현됐다. 이 issue는 병합 당일인 2026-05-14에 `PathString::slice`의 댕글링 참조 UB로 열렸고 2026-05-17에 닫혔다. 즉 이미 수정된 사례이며, 열려 있는 결함으로 인용하면 안 된다. Bun의 [unsafe 감사](https://bun.com/bun-unsafe-audit)는 커밋 `3eb0fda021`을 대상으로 2026-05-21에 AI가 만든 스냅샷이다. 이 감사는 13,365개의 `unsafe` 블록을 분류하고 약 9,300개는 안전한 코드로 바꿀 수 있으며 약 4,000개는 `unsafe`로 남는다고 보고했다. 함수 5개는 안전하다고 선언하기 어려운 정도가 아니라 safe Rust에서 정의되지 않은 동작에 도달할 수 있는 unsound 상태로 지목했다. 다만 감사 자신이 상위 네 패턴만 지점별로 측정하고 나머지는 확인된 수치 위의 추정이라고 밝힌다. Rust가 결함의 종류와 탐지 시점을 바꿨지만, FFI와 `unsafe`의 검증 책임까지 없애지는 않았다.

## 3. 무엇을, 어떤 제약으로 바꿨는가

### 3.1 범위

공식 회고의 시작점은 다음과 같다.

| 항목 | 범위 |
|---|---|
| Zig 코드 | 주석 제외 535,496줄 |
| Zig 파일 | 1,448개 |
| 목표 크레이트(crate) 수 | 약 100개 |
| 유지 대상 | 아키텍처, 자료구조, 동작, 성능 특성, 기능 |
| 동작 기준 | 기존 언어 독립적인 TypeScript 테스트 스위트 |

포트의 목표는 Rust다운 재설계가 아니었다. 먼저 기존 Zig 구현을 가능한 한 기계적으로 옮기고, 동작이 같다는 증거를 확보한 뒤 idiomatic Rust로 다듬는 순서를 택했다. 이 제약이 파일 단위 병렬화를 가능하게 했다. 아키텍처와 동작까지 동시에 바꾸면 실패 원인이 언어 변환인지 설계 변경인지 구분하기 어렵다.

### 3.2 왜 점진 전환이 아니라 전체 포트였나

Bun 팀은 일부 모듈만 Rust로 바꾸는 점진 전략보다 일괄 포트를 택했다. 공식 글이 직접 밝힌 맥락은 다음과 같다.

- Zig 코드가 실질적으로 하나의 컴파일 단위처럼 얽혀 있었다.
- GC 객체와 수동 수명이 자료구조 전반에 퍼져 있었다.
- 점진 전환은 단·중기적으로 임시 코드를 만들고 작업을 더 고통스럽게 한다고 판단했다.
- 기존 테스트가 언어와 무관해 전체 동작을 비교할 기준으로 쓸 수 있었다.

두 언어의 경계를 오래 유지하면 FFI와 중복 표현이 늘어날 수 있다는 점도 분석상 예상되는 비용이다. 다만 공식 글이 이를 별도의 선택 이유로 명시한 것은 아니다.

이 선택은 Bun의 결합 구조와 테스트 자산에 맞춘 결정이다. 모듈 경계가 이미 안정적이거나 점진적 이중 실행이 가능한 프로젝트에 그대로 적용할 일반 법칙은 아니다.

## 4. 11일 실행 흐름

### 4.1 포팅 계약과 수명 분류

팀은 약 3시간 동안 [`PORTING.md`](https://github.com/oven-sh/bun/commit/46d3bc29f270fa881dd5730ef1549e88407701a5)를 만들었다. Zig 표현을 Rust의 어떤 타입과 수명 패턴으로 옮길지 정하는 변환 계약이다. 이 커밋은 2026-05-04에 `docs: add Phase-A porting guide`라는 메시지로 `docs/PORTING.md`와 `scripts/port-batch.ts`를 함께 추가했다. 포트 시작 다음 날 변환 계약이 먼저 고정됐다는 뜻이다.

그 다음 workflow가 필드와 참조 관계를 분류해 `LIFETIMES.tsv`를 만들었다. 병합 커밋의 [`lifetime-classify.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/lifetime-classify.workflow.js)에는 `OWNED`, `SHARED`, `BORROW_PARAM`, `BORROW_FIELD`, `STATIC`, `JSC_BORROW`, `BACKREF`, `INTRUSIVE`, `FFI`, `ARENA`, `UNKNOWN` 분류가 남아 있다. 공식 회고에 따르면 이 결과도 두 차례의 적대적 리뷰와 사람의 검토를 거쳤다.

수명 표는 작업자가 파일마다 다시 소유권 설계를 추측하지 않도록 만든 공유 결정 기록이었다. 다만 병합 커밋 `23427dbc`의 트리를 조회하면 `LIFETIMES.tsv`도 `PORTING.md`도 남아 있지 않다. 두 파일이 포트 과정의 입력으로 사용됐다는 사실은 공식 회고와 workflow에서 확인되지만, 언제 어떤 이유로 최종 트리에서 제거됐는지는 공개 자료로 알 수 없다. 병합 트리에는 이름을 참조하는 `lifetime-classify.workflow.js`와 `porting-md-zigleakage.workflow.js`가 남아 있다. 워크플로에는 `/root/bun-5` 같은 절대 경로와 시드를 지정하지 않은 `Math.random()` 샘플링도 남아 있다. 공개 저장소만으로 당시 분류를 결정론적으로 재현할 수는 없다.

### 4.2 3파일 파일럿

전체 포트 전에 파일 3개를 골라 각 파일에 다음 셀을 적용했다.

```text
구현자 1 → 독립 리뷰어 2 → 지적을 반영하는 수정자 1
```

파일럿의 목적은 Rust 코드 3개를 얻는 데 그치지 않았다. 포팅 규칙의 빈칸, 수명 분류의 모호함, reviewer가 잡아야 할 실패 패턴을 찾고 프롬프트와 계약을 고치는 과정이었다.

### 4.3 첫 병렬화 실패와 4개 worktree

초기 에이전트들은 같은 저장소에서 `git stash`, `stash pop`, `reset --hard`를 실행했다. 다른 작업자의 변경을 덮어쓰거나 잃었다. 작업자마다 worktree를 주는 방식은 디스크 사용량이 지나치게 컸고, 변경을 한데 모으기도 어려웠다.

최종적으로 다음 구조를 사용했다.

| 층 | 수 | 역할 |
|---|---:|---|
| 워크플로 샤드 | 4 | 포트 범위와 격리 단위 |
| 워크트리 | 4 | 샤드별 격리된 저장소 상태 |
| Claude 세션 | 워크트리당 최대 16 | 파일 포트, 리뷰, 수정 |
| 최대 동시성 | 약 64 | 네 워크트리의 세션 합계 |

공식 글은 Anthropic이 2025년 12월 Bun을 인수했고, 이 포트에 출시 전 Claude Fable 5를 사용했다고 밝힌다. 모델 제공사와 작성 주체가 이해관계를 공유하며, 외부 사용자가 같은 모델을 선택해 재현할 수도 없다는 점을 결과 해석에 포함해야 한다.

에이전트의 git 명령과 느린 전역 명령도 제한했다. 공식 회고는 약 50개의 동적 워크플로가 11일 동안 계속 실행됐고, 최고 처리량이 분당 약 1,300줄이었다고 집계한다. 이 값은 순간 처리량이며 품질이나 지속 처리량을 뜻하지 않는다.

“약 50개”는 공개 트리로 교차 확인할 수 있는 드문 수치다. 병합 커밋 `23427dbc`의 `.claude/workflows/`에는 `*.workflow.js` 파일이 53개 있고, 이름이 `phase-a`부터 `phase-h`까지의 단계 계열과 `lifetime-classify`, `porting-md-zigleakage`로 나뉜다. 파일 수가 동시 실행 수는 아니지만, 회고의 집계와 공개 산출물이 어긋나지 않는다는 확인은 된다. 반대로 2차 매체는 이 과정을 “4단계”로 요약하기도 한다. 8개 phase를 4개 상위 단계로 묶은 요약일 가능성을 배제할 수 없으나, 공개 workflow 분류는 `phase-a`부터 `phase-h`까지로 더 세분되므로 4를 원래 단계 수로 인용하지 않는다.

### 4.4 기계적 파일 포트

병합 커밋의 [`phase-a-port.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/phase-a-port.workflow.js)는 포트 작업의 입력을 좁힌 방식을 보여준다.

- 같은 Zig 경로에는 항상 같은 Rust 대상 경로를 계산한다.
- 작업자는 `PORTING.md` 전체와 해당 파일의 `LIFETIMES.tsv` 행을 읽는다.
- 다른 Zig 파일, build, Cargo, git을 읽거나 실행하지 못하게 한다.
- 대상 파일만 쓰고, 큰 파일은 800줄 이하 단위로 기록한다.
- 구현 결과에 confidence와 남은 TODO를 구조화해 반환한다.
- 별도의 검증과 수정 단계를 둔다.

이 코드는 공개된 한 시점의 변형이다. 여기에는 검증 에이전트가 하나만 있고, 수정 뒤에 문제가 남아도 상태가 `fixed`로 계산될 여지가 있다. “모든 줄을 두 번 리뷰했다”는 공식 집계와 개별 workflow 파일을 같은 증거로 취급하면 안 된다. 공개 workflow는 최종 리뷰 원장이나 모든 `remaining` 항목의 처리 여부를 증명하지 않는다.

에이전트가 컴파일만 통과시키려고 stub을 넣거나 긴 우회 설명을 주석으로 남기는 실패도 있었다. 팀은 프롬프트와 reviewer 규칙을 바꿨고, 문단 길이의 우회 주석을 구현이 잘못됐다는 신호로 취급했다. 이는 Bun에서 관찰된 실패 패턴과 대응이며, 주석 길이 자체를 일반적인 품질 기준으로 볼 근거는 없다.

### 4.5 crate 경계와 순환 의존

1,448개 파일을 옮긴 뒤에도 바로 컴파일할 수 없었다. 사전 구조화 [PR #30224](https://github.com/oven-sh/bun/pull/30224)는 소스 파일을 주제별 디렉터리로 옮겼지만, Rust crate의 비순환 의존 그래프까지 만들지는 못했다.

팀은 목표한 약 100개 crate 사이의 순환을 분류하고 경계를 다시 잡았다. 그 결과 컴파일러가 실제 작업 목록을 낼 수 있는 상태가 됐고, 첫 본격 단계에 약 16,000개의 오류가 나타났다. 파일 복사가 끝난 시점과 빌드 가능한 시스템이 된 시점을 분리해 봐야 하는 이유다.

### 4.6 컴파일 오류 큐

공식 회고가 설명한 안정된 단위는 crate였다.

1. crate 하나에 `cargo check`를 한 번 실행한다.
2. 출력을 파일별로 묶어 고정한다.
3. 작업자들이 그 크레이트의 오류를 모두 수정한다.
4. 독립 리뷰어 둘이 수정안을 검토한다.
5. 수정자가 지적을 반영한다.
6. 통합 뒤 `cargo check`를 다시 실행해 새 오류 집합을 얻는다.

작업자가 작업 도중 Cargo나 git을 실행하지 않도록 한 이유는 공용 빌드 상태와 저장소 상태가 서로 밟히는 것을 막기 위해서였다. 검증은 batch 시작과 통합 경계에서 오케스트레이터가 담당했다.

공개 workflow에는 이 아이디어의 여러 변형이 남아 있다.

| 자료 | 확인되는 동작 | 주의점 |
|---|---|---|
| [`phase-d-build-queue.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/phase-d-build-queue.workflow.js) | “cargo build가 큐”라고 선언하고 오류를 파일별로 그룹화, 우선 처리 파일 최대 25개 선택 | 공식 회고의 crate별 최종 설명과 명령·git 정책이 일부 다름 |
| [`phase-d-crate-shard.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/phase-d-crate-shard.workflow.js) | `cargo check -p <crate> --keep-going` 1회, 파일별 오류 저장, 정렬 후 `i % N` 분배 | 80개가 넘으면 같은 파일을 약 800줄 구간으로 나누므로 쓰기 충돌 검토 필요 |
| [Cargo `check` 문서](https://doc.rust-lang.org/cargo/commands/cargo-check.html) | `-p`, `--keep-going`, 빠른 타입 검사의 공식 의미 | 최종 코드 생성을 하지 않아 일부 진단은 뒤의 빌드·링크에서만 나타남 |
| [Cargo external tools 문서](https://doc.rust-lang.org/cargo/reference/external-tools.html) | `--message-format=json`의 line-delimited JSON과 `compiler-message` 구조 | 텍스트 grep과 달리 package·target·source span 구조를 보존할 수 있음 |

오류 목록은 지속형 작업 목록이 아니라 특정 커밋에서 만든 일회성 검증 스냅샷이다. 오류 A를 고치면 오류 B가 함께 사라지거나 C가 새로 나타날 수 있다. 따라서 개별 항목의 완료 플래그가 아니라, 통합 후 새 `cargo check`에서 오류가 사라졌는지를 기준 완료 조건으로 삼아야 한다.

### 4.7 링크, 시작, CLI

타입 검사가 끝난 뒤에는 순서대로 더 넓은 실행 경계를 열었다.

1. 코드 생성과 링커 오류
2. 프로세스 시작 panic
3. `bun --version`
4. `bun test <file>`
5. 각 하위 명령의 stacktrace와 실패

이 순서는 검증 범위를 한꺼번에 넓히지 않는다. 타입 검사, 코드 생성·링크, 프로세스 시작, 최소 CLI, 기능 실행을 서로 다른 게이트로 취급한다.

### 4.8 로컬 테스트 실패 큐

약 100개의 임의 테스트 파일을 폴더 기준으로 네 워크트리에 나눴다. 각 실패의 stacktrace와 오류를 파일에 저장하고, 구현자 1명, 리뷰어 2명, 수정자 1명의 셀로 처리했다.

일부 누수·통합 테스트는 1분 넘게 걸렸다. 최대 소켓 수, GB 단위 디스크 I/O, 약 10,000개의 프로세스가 필요한 테스트도 있었다. 팀은 `systemd-run` cgroup으로 CPU와 메모리를 제한하고 PID namespace를 썼다. 그래도 디스크가 꽉 차 workflow가 죽었고, EC2 IOPS 설정 오류 때문에 `grep` 하나가 I/O를 막은 적도 있었다.

병렬 처리량은 모델 호출 수만으로 정해지지 않는다. CPU, 메모리, PID, 파일 descriptor, 디스크 용량과 IOPS를 shard별로 계측하고 상한을 둬야 한다.

### 4.9 CI 실패 큐와 main 추종

첫 CI 실행은 972개 테스트 파일에서 실패했다. 공식 회고에 따르면 이 수는 이틀 만에 23개로 줄었고, 1.5일 뒤 Linux가 green이 됐다. 이후 macOS x64·arm64, Linux x64·arm64, Windows x64·arm64의 여섯 플랫폼을 모두 통과했다.

공개 스크립트는 실패 로그를 task로 바꾸는 방식을 보여준다.

- [`ci-errors-to-tasks.ts`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/scripts/ci-errors-to-tasks.ts): `[new]` 구간을 읽어 `/tmp/tasks/*.md`와 `index.json`을 만든다.
- [`categorize-ci-failures.ts`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/scripts/categorize-ci-failures.ts): panic, ASAN, leak 등 근본 원인 시그니처를 정규화해 같은 원인의 테스트를 묶고 작업 명세를 만든다.
- [`phase-h-ci-tasks.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/phase-h-ci-tasks.workflow.js): 명시적인 task 목록을 구현자→리뷰어 둘→수정자 흐름으로 처리한다.
- [`phase-h-main-parity.workflow.js`](https://github.com/oven-sh/bun/blob/23427dbc12fdcff30c23a96a3d6a66d62fdc091d/.claude/workflows/phase-h-main-parity.workflow.js): 장기 포트 중 기존 `main`에 들어온 변경을 Rust 브랜치에 대응시킨다.

테스트 실패는 파일 수로만 나누는 것보다 원인 시그니처로 묶어야 중복 수정을 줄일 수 있다. 반대로 시그니처가 일반적인 문구뿐이면 관계없는 실패까지 한 task에 들어가므로, 진단의 구체성과 쓰기 대상 집합을 함께 봐야 한다.

### 4.10 병합 게이트

공식 회고가 밝힌 병합 조건은 다음과 같다.

- 여섯 플랫폼의 기존 테스트 스위트 100% 통과
- 테스트 삭제와 skip 0
- 테스트가 실제로 실행됐는지 사람이 확인
- 로컬에서 주요 명령을 수동 실행

마지막 여섯 플랫폼 green 결과로 인용되는 값은 Build #54202다. 이는 별도 병합 조건이라기보다 위 조건을 충족한 최종 CI 증거다. 다만 이 번호는 공식 회고 본문 텍스트가 아니라 페이지의 CI burndown 위젯에서 나오며, 공개 Buildkite URL이나 로그 artifact가 제시되지 않는다. 따라서 외부에서 재검증할 수 있는 CI 증거가 아니라 Bun 팀이 제시한 값으로 다뤄야 한다.

공식 집계의 플랫폼별 규모는 다음과 같다.

| 러너 | 테스트 파일 | 테스트 | expect |
|---|---:|---:|---:|
| Debian 13 x64 | 4,174 | 60,624 | 1,386,826 |
| macOS 14 arm64 | 4,175 | 58,850 | 1,259,953 |
| Windows 2019 x64 | 4,173 | 57,337 | 1,007,544 |

이 표는 여섯 플랫폼 전체가 아니라 회고가 대표로 제시한 러너 셋이다. 세 러너의 테스트 파일 수가 4,173~4,175로 갈리는 것 자체가 플랫폼별 조건부 테스트가 있다는 뜻이고, 따라서 “전 플랫폼 100%”는 모든 러너가 같은 모집단을 돌렸다는 의미가 아니다. 플랫폼별 통과 결과를 각 플랫폼의 실제 실행 모집단과 함께 읽어야 하는 이유다.

`main` 병합 뒤에는 11차례의 보안 리뷰가 이어졌고, Miri의 CI 적용 범위를 넓혔다. 24/7 상시 coverage-guided fuzzing은 parser를 약 1,000억 회 실행했고 약 15개의 PR로 이어졌다는 것이 공식 집계다. 이 후속 단계가 있었다는 사실 자체가 CI green을 메모리 안전성의 증명으로 볼 수 없음을 보여준다.

## 5. 수치 읽기

같은 사건도 도구와 시점에 따라 집계값이 다르다. 하나의 정확한 숫자로 억지로 합치지 않는다.

| 항목 | 값 | 정의·출처 |
|---|---:|---|
| 기간 | 11일, 2026-05-03~05-14 | 공식 회고 |
| 원본 | Zig 535,496 LOC, 1,448 파일 | 주석 제외, 공식 회고 |
| 병합 변경량 | +1,009,272 | 공식 회고 |
| PR diff | +1,009,257 / -4,024, 2,188 파일 | GitHub PR API |
| commit | 6,502 | 공식 회고, merge commit 제외 |
| commit | 6,778 | 공식 회고, merge commit 포함 |
| commit | 6,755 | GitHub PR API의 `commits` 필드 |
| 토큰 | uncached input 59억, output 6.9억, cached read 720억 | 공식 회고 |
| 비용 | 약 165,000달러 | 공식 회고가 당시 API 가격으로 환산한 값. 모델별 단가·호출 혼합·캐시 과금이 공개되지 않아 독립 재계산 불가 |
| 알려진 회귀 | 19개 | 병합 후 발견, 7월 회고 시점 수정 완료 |

세 commit 수치는 서로 모순이 아니라 세는 대상이 다르다. 6,502는 merge commit을 뺀 값, 6,778은 넣은 값이고, PR API의 6,755는 그 사이다. 공식 회고가 두 값을 모두 제시하고 API가 세 번째 값을 내므로, 어떤 수를 인용할 때는 반드시 세는 기준을 붙여야 한다. `+1,009,272`와 `+1,009,257`의 15줄 차이, 6,778과 6,755의 23 commit 차이도 각 출처의 값과 정의는 확인되지만 차이의 정확한 원인은 공개 자료로 확인할 수 없다. 따라서 “집계 도구와 시점의 차이”로 단정하지 않고 값과 출처를 함께 적는다.

`약 100만 줄`은 원본 Zig 코드량이 아니라 추가된 diff다. WikiDocs의 `약 96만 줄 Zig`와 공식 원본 LOC는 같은 측정값이 아니다.

## 6. 결과와 그 한계

### 6.1 공식 결과

공식 글은 다음 결과를 보고한다.

- Linux x64 자체 benchmark에서 대체로 2~5% 빠름
- `Bun.build()` 2,000회 호출 시 메모리 사용량이 v1.3.14의 6,745MB에서 v1.4.0의 609MB로 감소(공식 비교표의 v1.4.0 행은 canary)
- v1.3.14에서 재현 가능한 버그 128개 수정
- 최초 포트에서 플랫폼별 바이너리 크기 3.8~6.8MB 감소
- 7월 기준 약 780,000 Rust LOC 중 `unsafe` 블록 내부 약 27,000줄, 약 4%
- `unsafe` 키워드 약 13,000개, `unsafe` 블록의 78%는 한 줄

benchmark는 Bun 팀이 제한된 조건에서 직접 측정한 값이다. HTTP throughput은 +2.8~+4.8%, build workload는 +2.2~+4.7% 구간이므로 “2~5%”는 이 범위의 요약이다.

바이너리 크기는 같은 사건을 세 방식으로 적는다. 공식 회고는 “Rust 재작성의 최초 변경으로 Windows 3.8MB, macOS 5.5MB, Linux 6.8MB가 줄었다”고 플랫폼별 값을 직접 제시한다. PR #30412 본문은 같은 결과를 `3 MB - 8 MB` 감소로 적는데, 이는 반올림이 아니라 양끝을 바깥으로 느슨하게 잡은 어림값이다. 3.8을 3으로 내리고 6.8을 8로 올렸으므로 산술 변환 관계로 설명할 수 없다. 그래도 두 서술의 대상은 하나이므로 별개 측정으로 세면 안 된다.

세 번째 값인 약 20% 감소는 규모가 다르고 원인도 다르다. 공식 회고는 이 수치를 “Rust 재작성, ICU 변경, identical code folding을 합쳐” 얻은 결과로 명시하고 Windows 94MB→76MB, Linux 88MB→70MB를 제시한다. 최초 포트 이후 linker 최적화와 ICU 미사용 데이터 제거, zstd 사전을 이용한 libicu 지연 압축 해제를 따로 진행했다는 서술도 함께 있다. 따라서 20%를 Rust 전환의 효과로 인용하면 세 원인을 하나로 합치는 오류가 된다. 공식 표의 76MB·70MB는 `Bun v1.4.0 (canary)` 행이므로 안정판 수치로 인용하면 안 된다. 어느 수치도 Rust의 보편적 성능 우위로 일반화할 근거는 아니다.

### 6.2 외부 운영 관찰

[Prisma Compute 보고서](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute)는 Rust canary를 public beta에 적용했다. 보고서의 두 관찰은 조건을 붙여 읽어야 한다.

- 메모리 비교: 안정판 `1.3.14+0d9b296af`는 반복 약 96회에 900MiB를 넘었고, canary `1.3.14-canary.1+172afa532`는 4,096회 실행 동안 sampled RSS 최대 약 118MiB로 평탄했다. 보고서는 이 수치를 [issue #29083](https://github.com/oven-sh/bun/issues/29083) 후속 실행에서 가져왔다고 밝힌다.
- Prisma 자체 운영 관찰: pause/resume 뒤 dead SQL connection pool로 이어진 실패가 Rust 재작성에서는 재현되지 않았다. 이 항목이 Prisma가 직접 측정한 결과다.

Prisma도 이 결과가 모든 workload와 실패 모드를 증명하지 않는다고 한정한다. Bun 팀 밖의 운영 환경에 가까운 관찰이라는 가치는 있지만 전체 정확성이나 메모리 안전성의 독립 증명은 아니다.

### 6.3 공개 자료로 재현할 수 없는 부분

| 빠진 요소 | 영향 |
|---|---|
| dynamic workflow 런타임의 공개 구현 | `agent`, `pipeline`, `parallel`, `phase` 호출을 그대로 실행할 수 없음 |
| 사용한 pre-release Claude Fable 5 | 같은 모델과 출력 특성을 재현할 수 없음 |
| 최종 `LIFETIMES.tsv` | 파일별 수명 결정을 다시 만들거나 검증해야 함 |
| 정확한 prompt·workflow 버전 원장 | 약 50개 workflow가 11일 동안 어떻게 바뀌었는지 완전 재생 불가 |
| 작업 임대·재시작·중복 적용 기록 | crash 뒤 정확히 어디서 재개했는지 검증 불가 |
| 줄별 두 차례 리뷰 원장 | 공식 집계는 있으나 공개 코드만으로 전수 입증 불가 |
| 당시 인프라 이미지와 자원 설정 | 처리량과 장애 조건을 동일하게 재현하기 어려움 |

따라서 공개 자료는 사례 연구와 오케스트레이션 구조의 역설계에는 충분하지만, “Bun의 11일 실행을 그대로 재현한다”는 주장에는 부족하다.

## 7. 2차 자료 교차 검증

| 주장 | GeekNews | WikiDocs | 판정 |
|---|---|---|---|
| 11일 전체 포트, Claude 세션 최대 약 64개 | 공식 글을 요약 | 초기 시점에 6~9일로 기술 | 최종 기간은 공식 11일 사용 |
| Rust 선택 이유 | 메모리 수명 문제 중심 | Zig의 AI 정책과 생태계를 크게 해석 | 직접 동기는 공식 글 기준, 정책은 정황에 근거한 해석 |
| 코드량 | 공식 수치를 요약 | 약 96만 줄 Zig | 공식 원본은 주석 제외 535,496 LOC, 100만은 diff |
| 테스트 | 전 플랫폼 100%, skip/delete 0 | 99.8% | 시점과 분모가 다름, 최종 공식 집계 사용 |
| unsafe | 7월 수치 요약 | 13,044개 | keyword/block/line과 시점이 달라 단순 비교 금지 |
| 메모리 버그 | 안전한 Rust 코드의 이점 | 전면 예방에 가까운 표현 | FFI·`unsafe`·Miri 반례가 있어 조건부로 기술 |

[GeekNews 글](https://news.hada.io/topic?id=31263)은 공식 회고의 한국어 색인으로 유용하지만 독립 검증은 아니다. 위 표에 열거한 GeekNews 수치는 공식 회고와 일치하며, 회고에 없는 값을 새로 만들지 않는다. 다만 위 표의 구분은 한 가지 보정이 필요하다. Zig의 no-AI 정책 언급은 WikiDocs에만 있는 해석이 아니라 GeekNews에도 부가 서술로 들어 있고, GeekNews는 Hacker News·Lobsters 토론 요약과 “마케팅 기사처럼 읽힌다”는 편집 논평도 함께 싣는다. 두 2차 자료의 차이는 정책 해석의 유무가 아니라 그 해석에 실은 비중이다.

위 표의 [WikiDocs](https://wikidocs.net/blog/@jaehong/13487/) 열은 2026-05-15 스냅샷 기준이다. `6~9일`, `99.8%`, `약 96만 줄 Zig`, `unsafe 13,044개`는 집계 시점과 분모, 세는 대상이 공식 최종 집계와 달라 이 문서의 근거로 쓰지 않는다. `99.8%`는 WikiDocs 고유 수치가 아니라 병합 직후 Linux x64 기준으로 돌던 중간 집계이며, 최종 회고의 전 플랫폼 100%와 모집단이 다르다. 2차 자료를 이렇게 다루는 이유는 2차 요약의 집계 시점과 분모 차이가 1차 자료 기반 결론을 흔들지 않게 하기 위해서다.

## 8. 전이 가능한 원리와 Bun에 묶인 선택

### 전이 가능한 원리

- 동작 기준선과 테스트 무결성을 포트 전에 고정한다.
- 기계적 변환과 구조 개선을 다른 단계로 분리한다.
- 수명·FFI·예외 규칙을 작업자 밖의 공유 계약으로 만든다.
- 검증 도구의 실패를 특정 커밋에 묶인 불변 작업 명세로 만든다.
- 파일·크레이트·테스트·원인 시그니처에 맞춰 샤드 키를 바꾼다.
- 구현, 적대적 리뷰, 적용, 전역 검증의 컨텍스트와 권한을 분리한다.
- 작업자의 쓰기 대상 집합을 겹치지 않게 하고 통합은 직렬화한다.
- 완료는 새 기준 검증에서 실패가 사라진 것으로 판정한다.
- 타입 검사, 링크, 프로세스 시작, 기능, 무거운 테스트, 플랫폼, 안전성, 비기능 검증을 단계별로 연다.
- 장기 브랜치에는 기존 main의 변경을 추종하는 별도 큐를 둔다.

### Bun의 조건에 묶인 선택

- 전체를 한 번에 전환한 전략
- 정확히 4개 워크트리와 워크트리당 16개 세션
- 약 100개 크레이트라는 목표
- 문단 길이의 주석을 실패 신호로 삼은 리뷰 규칙
- Claude Fable 5와 비공개 dynamic workflow API
- Bun의 TypeScript 테스트를 동작 기준으로 사용한 방식
- Linux cgroup, PID namespace, 특정 EC2 인스턴스 설정

다른 사례와 비교할 때 유효한 분석 단위는 숫자나 도구 이름보다 작업 경계와 완료 조건이다.

## 9. 종합 판정

공개 증거는 Bun의 작업 분할, 리뷰 분리, 오류 큐, 검증 단계와 그 한계를 분석하기에는 충분하다. 이를 바탕으로 [오케스트레이션 구조](02-implementation-flow.md)를 역설계할 수 있지만, Bun의 비공개 runtime을 복원하거나 같은 방식이 다른 프로젝트에서도 동일한 결과를 낸다고 결론 내릴 수는 없다.

## 참고 자료

### 1차 자료

- [Bun is being rewritten in Rust](https://bun.com/blog/bun-in-rust), 2026-07-08
- [Bun PR #30412: Rewrite Bun in Rust](https://github.com/oven-sh/bun/pull/30412)
- [Bun PR #30224: Reorganize src](https://github.com/oven-sh/bun/pull/30224)
- [`PORTING.md`와 port batch script를 추가한 commit](https://github.com/oven-sh/bun/commit/46d3bc29f270fa881dd5730ef1549e88407701a5)
- [Bun unsafe audit](https://bun.com/bun-unsafe-audit), 2026-05-21
- [Miri로 재현된 issue #30719](https://github.com/oven-sh/bun/issues/30719)
- [Cargo `check` 공식 문서](https://doc.rust-lang.org/cargo/commands/cargo-check.html)
- [Cargo가 외부 도구에 제공하는 JSON 메시지](https://doc.rust-lang.org/cargo/reference/external-tools.html)
- [rustc JSON 진단 형식](https://doc.rust-lang.org/rustc/json.html)

### 외부·2차 자료

- [Prisma Compute: Bun's Rust rewrite in production](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute), 2026-06-11
- [GeekNews: Bun이 Rust로 재작성됩니다](https://news.hada.io/topic?id=31263)
- [WikiDocs: Bun, Zig에서 Rust로 전면 재작성](https://wikidocs.net/blog/@jaehong/13487/)
