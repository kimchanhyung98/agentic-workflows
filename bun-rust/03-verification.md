# 검증 기록

이 문서는 `01-analysis.md`와 `02-implementation-flow.md`가 실제 근거에 맞는지 다시 확인한 기록이다. 검증일은
2026-07-26이고, 방법은 네 가지다. GitHub REST API 조회, 1차 문서 재수집, 저장소 문서 간 기계적 대조, 그리고 여섯
관점의 적대적 교차 검증이다. 앞의 셋은 “있는 것끼리 어긋나는가”를, 마지막 하나는 “있어야 하는데 없는 것”을 찾는다.

## 1. 검증할 수 있는 층과 없는 층

이 저장소의 bun-rust 문서는 두 층으로 나뉘고, 검증 방법이 서로 다르다.

| 층 | 해당 문서 | 검증 방법 | 판정 가능 여부 |
|---|---|---|---|
| 관찰된 사실 | `01-analysis.md`, `00-diagram.md`의 관찰 노드, `README.md` 사실 표 | 1차 자료·API 대조 | 가능 |
| 권장 설계 | `02-implementation-flow.md` 전체, 다이어그램의 권장 노드 | 문서 간 정합성과 완전성 대조 | 외부 대조로는 불가능 |

`02-implementation-flow.md`는 Bun이 실제로 사용한 구현이 아니라 이 저장소가 제안하는 제어 계약이다. 따라서 웹 검색으로
“맞다·틀리다”를 판정할 대상이 아니다. 이 층에 적용할 수 있는 검증은 계약이 서로 모순되지 않는지, 명세한 요구가 검증
절차와 1:1로 연결되는지뿐이다. 아래 2·3절이 첫 번째 층, 4절이 두 번째 층에 해당한다.

## 2. GitHub API 대조

`gh api`로 조회한 값과 문서의 주장을 비교했다.

| 문서의 주장 | API 조회 결과 | 판정 |
|---|---|---|
| 최신 안정 릴리스는 v1.3.14이며 Zig 구현 | `releases/latest` = `bun-v1.3.14`, `prerelease=false`, 게시 2026-05-13 | 일치 |
| v1.4.0은 조사 기준 출시 전 | 안정 릴리스 목록의 최신값이 여전히 v1.3.14 | 일치 |
| PR diff `+1,009,257 / -4,024`, 2,188 파일 | `additions=1009257`, `deletions=4024`, `changed_files=2188` | 일치 |
| PR commit 6,755 | `commits=6755` | 일치 |
| 병합일 2026-05-14 | `merged_at=2026-05-14T08:09:34Z`, `merged=true` | 일치 |
| 병합 커밋 `23427dbc…` | `merge_commit_sha=23427dbc12fdcff30c23a96a3d6a66d62fdc091d` | 일치 |
| 인용한 workflow·script 파일 8개가 병합 트리에 존재 | 트리 조회에서 8개 경로 모두 확인 | 일치 |
| `LIFETIMES.tsv`가 최종 병합 트리에 없음 | 트리에 해당 파일 없음 | 일치 |
| `PORTING.md` 커밋 `46d3bc29` | 2026-05-04, `docs: add Phase-A porting guide`, `docs/PORTING.md`와 `scripts/port-batch.ts` 추가 | 일치 |
| issue #30719에서 Miri로 댕글링 참조 재현 | `PathString::slice dangling reference UB - add Miri to CI`, 2026-05-14 생성 | 일치 |

인용 링크가 살아 있는지 개별 확인하는 대신 병합 커밋의 트리를 한 번 조회해 전수 대조했다. 확인된 경로는
`lifetime-classify`, `phase-a-port`, `phase-d-build-queue`, `phase-d-crate-shard`, `phase-h-ci-tasks`,
`phase-h-main-parity`의 여섯 workflow와 `scripts/ci-errors-to-tasks.ts`, `scripts/categorize-ci-failures.ts`다.

이 조회로 문서에 없던 사실 세 가지가 나왔고, 모두 본문에 반영했다.

- `.claude/workflows/*.workflow.js`가 53개다. 공식 회고의 “약 50개 동적 워크플로”와 어긋나지 않는, 공개 산출물 기반의
  드문 교차 확인 지점이다.
- `PORTING.md`도 `LIFETIMES.tsv`와 마찬가지로 최종 병합 트리에 없다. 기존 문서는 후자만 언급했다.
- issue #30719는 2026-05-17에 닫혔다. 기존 문서는 생성 사실만 적어 열린 결함으로 읽힐 여지가 있었다.

## 3. 1차·외부 자료 대조

### 3.1 공식 회고

[공식 회고](https://bun.com/blog/bun-in-rust)를 다시 수집해 문서가 인용한 수치를 전수 대조했다. 아래 항목이 모두
일치했다.

535,496 Zig LOC, 1,448 `.zig` 파일, 약 100개 crate, 약 16,000개 오류, 실패 테스트 파일 972→23과 그 뒤 1.5일 후 Linux
green, 워크트리 4개 × 세션 16개 = 최대 64개, 약 50개 동적 워크플로, 분당 약 1,300줄, 약 165,000달러, 2026-05-03~05-14의
11일, uncached input 59억·output 6.9억·cached read 720억 토큰, commit 6,502와 6,778, 병합 변경량 `+1,009,272`,
Build #54202, 여섯 플랫폼 100%와 skip·삭제 0과 사람의 실행 확인, `Bun.build()` 2,000회의 6,745MB→609MB, 버그 128개,
`unsafe` 약 13,000 키워드·약 27,000줄·약 780,000줄 중 4%·블록의 78%가 한 줄, 회귀 19개, C++ 약 20%, 출시 전 Claude
Fable 5, 2025년 12월 Anthropic 인수, 보안 리뷰 11회, 파서 1,000억 회 퍼징과 약 15개 PR, `PORTING.md` 약 3시간,
3파일 파일럿의 구현자 1·적대적 리뷰어 2·수정자 1 구조.

대조 과정에서 문서를 더 정확하게 만든 항목은 다음 네 가지다.

| 항목 | 기존 서술 | 확인된 내용 | 처리 |
|---|---|---|---|
| commit 6,778의 정의 | “공식 회고 통계 표” | merge commit을 포함한 값 | 정의를 명시하고 6,502·6,755와의 관계를 설명 |
| 플랫폼별 테스트 표 | `Debian x64` 등 축약 러너명, 테스트·expect 2열 | `Debian 13 x64`·`macOS 14 arm64`·`Windows 2019 x64`, 테스트 파일 4,174·4,175·4,173 | 러너명을 정확히 쓰고 파일 수 열 추가 |
| 바이너리 크기 | 3.8~6.8MB 감소를 공식 회고에 귀속 | 귀속은 정확했다. 공식 회고가 “최초 변경으로 Windows 3.8MB, macOS 5.5MB, Linux 6.8MB”를 직접 제시하고, 약 20% 감소는 “Rust 재작성, ICU 변경, identical code folding을 합쳐”로 명시한다. PR 본문의 `3 MB - 8 MB`는 같은 사건의 어림값 | 세 서술의 관계와 20%의 세 원인을 본문에 분리해 기록 |
| 성능 “2~5%” | 근거 구간 미제시 | HTTP throughput +2.8~+4.8%, build workload +2.2~+4.7% | 요약의 근거 구간을 본문에 기록 |

바이너리 크기 행은 검증 절차 자체에 대한 교훈이라 경위를 남긴다. 첫 재수집에서는 요약이 플랫폼별 문장을 빠뜨려
`3.8/5.5/6.8`의 1차 근거가 보이지 않았고, 그 상태로는 이 수치가 2차 자료에서 흘러든 것처럼 보였다. 해당 절만 좁혀
다시 조회해 공식 회고 원문에 그대로 있음을 확인했다. 넓은 질문 한 번의 요약을 근거로 삼으면 원문에 있는 문장을 없다고
판정할 수 있다. 출처 위계를 다루는 문서에서는 이 방향의 오류가 가장 위험하므로, 귀속이 흔들리는 항목은 해당 절만
좁혀 재확인해야 한다.

### 3.2 unsafe 감사

[unsafe 감사](https://bun.com/bun-unsafe-audit)는 커밋 `3eb0fda021`을 대상으로 2026-05-21에 작성됐고, 페이지 자체가
AI 생성물임을 명시한다. `unsafe` 13,365개를 **블록** 단위로 세며, 약 9,300개는 안전한 코드로 전환 가능하고 약 4,000개는
`unsafe`로 남는다고 분류한다. 상위 네 패턴만 지점별로 측정하고 나머지는 확인된 수치 위의 추정이라고 스스로 밝힌다.

문서가 “안전하다고 선언하기 어려운 함수 5개”로 적었던 부분은 원문보다 약한 표현이었다. 감사는 이 다섯 함수를 safe
Rust에서 정의되지 않은 동작에 도달할 수 있는 unsound 상태로, 즉 실제 버그로 지목한다. 본문을 원문 강도에 맞게 고쳤다.

감사의 13,365 블록(5월)과 회고의 약 13,000 키워드(7월)를 단순 비교하지 말라는 기존 문서의 경고는 이번 확인으로 근거가
분명해졌다. 세는 단위와 시점이 둘 다 다르다.

### 3.3 외부 운영 관찰

[Prisma Compute 보고서](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute)(2026-06-11)의 인용도 일치했다.
안정판은 반복 약 96회에 900MiB 임계를 넘고 이후 컨테이너가 종료될 때까지 증가했으며, Rust canary는 4,096회 실행 동안
sampled RSS 최대 약 118MiB로 평탄했다. scale-to-zero 복귀 뒤 SQL 풀이 교착하던 실패는 같은 조건에서 재현되지 않았다.
보고서는 “가능한 모든 풀 실패가 고쳐졌다고 말하는 것은 아니다”라고 직접 한정하고, 자신의 질문이 Compute workload 한정
이었음을 밝힌다. 문서가 이 결과를 좁은 범위의 외부 관찰로만 쓴 처리가 원문 의도와 맞다.

### 3.4 Cargo 문서

`02-implementation-flow.md` 8.1절의 전제를 [Cargo `check` 문서](https://doc.rust-lang.org/cargo/commands/cargo-check.html)로
확인했다. `-p`/`--package`는 package를 선택하고, `check`는 최종 코드 생성을 생략하므로 “일부 진단과 오류는 코드 생성
중에만 발생하며 따라서 `cargo check`로는 보고되지 않는다”가 문서의 명시적 서술이다. `--keep-going`과
`--message-format=json`도 존재하며 의미가 문서 설명과 같다. compile queue가 비면 `cargo build`와 링크 게이트를 따로
열어야 한다는 설계 근거가 공식 문서로 지지된다.

### 3.5 2차 자료

[GeekNews 글](https://news.hada.io/topic?id=31263)의 수치는 공식 회고와 일치하며 회고에 없는 값을 새로 만들지 않는다.
다만 기존 교차 검증 표는 Zig의 no-AI 정책 해석을 WikiDocs 쪽 특징으로만 배치했는데, GeekNews에도 같은 언급이 부가
서술로 있다. 두 자료의 차이는 해석의 유무가 아니라 비중이므로 본문을 보정했다. GeekNews는 Hacker News·Lobsters 토론
요약과 편집 논평도 함께 싣는다.

[WikiDocs 글](https://wikidocs.net/blog/@jaehong/13487/)은 이번 검증에서 본문을 읽지 못했다. WebFetch와 직접 요청
모두 Cloudflare 챌린지로 HTTP 403이 반환됐고, 대체 경로도 인증 문제로 실패했다. 따라서 교차 검증 표의 WikiDocs 열은
이번에 확인한 값이 아니라 이전 조사 기록이며, `6~9일`·`99.8%`·`약 96만 줄 Zig`·`unsafe 13,044개`를 근거로 재사용하지
않는다는 단서를 본문에 명시했다.

이 과정에서 한 가지가 추가로 드러났다. `99.8%`는 WikiDocs 고유 수치가 아니다. 병합 직후 여러 영문 2차 매체가 같은 값을
인용했고, 같은 매체들이 이 포트를 “4단계 프로세스”로 요약한다. 실제 공개 workflow는 `phase-a`부터 `phase-h`까지의 단계
계열이므로 이 요약은 부정확하다. 2차 자료는 색인으로만 쓰고 수치·구조 서술의 근거로 삼지 않는다는 기존 방침이 옳았다.

## 4. 문서 내부 정합성 대조

`docs/system-prompt.md`는 `02-implementation-flow.md`를 구현 지시로 옮긴 문서다. 두 문서가 어긋나면 구현자가 어느 쪽을
따라야 할지 알 수 없으므로, 계약의 뼈대를 기계적으로 대조했다.

| 대조 축 | 결과 |
|---|---|
| 필수 공개 연산 (`system-prompt` 8절 ↔ `02` 9.5절) | 41개 연산이 양방향 차집합 0으로 일치 |
| task 상태 (9.2절 ↔ 7.1절) | 15개 일치 |
| review job 상태 | 7개 일치 |
| scope job 상태 | 5개 일치 |
| validation request 상태 | 6개 일치 |
| epoch 상태 | 11개 일치 |
| run 상태 | 7개 일치 |
| rollback phase | 6개 일치 |
| Gate 0~9와 9a·9b·9c | 이름과 범위 일치 |
| P0 산출물 (6절 ↔ 4절) | 17개 항목 일치 |
| fault matrix (12.5절 F01~F31 ↔ 16.2절) | **F01·F02 누락** |

상태 머신은 이름 대조에 그치지 않고 그래프로 풀어 기계 검증했다. `02-implementation-flow.md` 7절의 mermaid
`stateDiagram-v2` 블록 5개를 파싱해 도달성을 확인한 결과는 다음과 같다.

| 다이어그램 | 상태 | 전이 | 시작점에서 도달 불가 | 출구 없는 비종료 상태 | 종료에 도달 불가 |
|---|---:|---:|---|---|---|
| task (7.1절) | 15 | 43 | 0 | 0 | 0 |
| review job (7.2절) | 7 | 19 | 0 | 0 | 0 |
| scope decision (7.3절) | 5 | 10 | 0 | 0 | 0 |
| validation request (7.4절) | 6 | 12 | 0 | 0 | 0 |
| epoch (7.5절) | 11 | 26 | 0 | 0 | 0 |

세 열이 모두 0이라는 것은 고아 상태, 진행할 수 없는 막다른 상태, 영구히 종료되지 않는 상태가 없다는 뜻이다. 상태
수도 위 이름 대조 결과와 정확히 같다.

다만 이 검사는 그래프 구조만 본다. 각 전이의 가드가 실제로 만족될 수 있는지, 같은 상태에서 나가는 두 전이의 가드가
겹치지 않는지, 그리고 **산문이 요구하는 전이가 다이어그램에 실제로 있는지**는 계약을 읽어야 판정할 수 있는 별개
문제다. epoch 전이 수가 24가 아니라 26인 것이 그 차이에서 나왔다. 아래 4.1절이 설명한다.

### 4.1 적대적 교차 검증

구조 검사와 이름 대조는 “있는 것끼리 어긋나지 않는가”만 본다. “있어야 하는데 없는 것”은 잡지 못한다. 이를 보완하기
위해 여섯 개 관점으로 문서를 독립 감사하고, 제기된 지적은 각각 별도 검증자가 반박을 시도해 살아남은 것만 채택했다.

| 감사 관점 | 대상 | 제기 | 확정 |
|---|---|---:|---:|
| 사실 정확성 | `01-analysis.md`, `README.md`, `00-diagram.md` | 2 | 0 |
| 상태 머신 | `02` 7절, 15절 | 4 | 2 |
| 동시성·복구 | `02` 6.1·9.3·9.4·9.6·15절 | 7 | 1 |
| 문서 간 정합성 | `system-prompt.md` ↔ `02` | 11 | 1 |
| 검증 기록 자체 | 이 문서 | 4 | 0 |
| 구현 가능성 | 고위험 연산 8개와 파생 산출물 | 7 | 0 |
| 합계 | | 35 | 4 |

이 표의 관점별 확정 수는 감사자별 반환 기록에서 직접 집계했다. 감사자 여섯 개는 각자 어느 파일의 몇 번째 줄을
지적했는지만 반환하고 자기 이름을 붙이지 않으므로, 지적 내용의 범주로 소속을 추측하면 틀린다. 실제로 초안에서는
동시성 관점의 확정 1건을 구현 가능성 관점으로 잘못 배정했고, 반환 기록을 다시 읽어 바로잡았다.

31건은 반박됐다. 기각 사유는 대체로 세 가지였다. 인용한 줄이 실제로 다른 내용을 담고 있거나, 두 서술이 모순이 아니라
서로 다른 scope·owner·epoch kind·run 상태를 말하고 있거나, 요구한 내용이 이미 몇 줄 떨어진 곳에 있었다.

확정 4건은 실질적으로 두 개의 결함이다. 셋은 같은 전이 누락을 7.5절·6.1절·9.3절 세 위치에서 각각 지적한 것이고,
나머지 하나는 파일럿 variant 누락이다. 둘 다 아래 5절 표에 올렸다.

가장 중요한 발견은 상태 머신 감사가 찾은 것이다. 6.1절과 9.3절 `frozen/repair` 행은 artifact 복구 deadline 초과 시
epoch를 `blocked_infrastructure`로 닫으라고 요구하는데, 7.5절 다이어그램에는 `blocked_infrastructure`로 가는 간선이
`validating`과 `validation_retry`에만 있었다. `docs/system-prompt.md`는 “허용 목록에 없는 전이는 application과 DB
양쪽에서 거부하고 상태 변경이 없음을 테스트한다”고 지시하므로, 다이어그램에서 DB 제약을 도출한 구현자는 문서 자신이
요구하는 transaction을 거부하게 된다. 산문을 따르면 맞게 만들고 다이어그램을 따르면 틀리게 만드는 상태였다.

누락된 전이는 두 개였다. task가 `artifact_wait`에 있으면 freeze-ready 조건을 만족할 수 없으므로 epoch는 `draining`에
머물고, 모든 task가 `approved`가 된 뒤 통합 준비 중 읽기 손실이 드러나면 `frozen`에 머문다. 두 상태 모두 출구가
필요하다. 간선 두 개와 이를 설명하는 7.5절 계약 항목을 추가했고, 그 결과 epoch 전이가 24에서 26으로 늘고
`blocked_infrastructure`의 source가 `draining`·`frozen`·`validating`·`validation_retry` 네 개가 됐다.

이 결함을 앞선 두 검사가 모두 놓친 이유는 기록해 둘 만하다. 도달성 검사는 다이어그램 안에서만 보므로 없는 간선을
그리워하지 않고, 이름 대조는 상태 집합이 일치하는지만 보므로 전이 집합의 누락에 반응하지 않는다. 구조 검증과 계약
검증은 서로를 대체하지 못한다.

같은 유형이 한 번 더 나왔다. 확정 지적의 수정 제안에 “범위 밖이지만 확인이 필요하다”는 단서로 `validation_retry`의
run 중지 출구가 딸려 있었고, 후속 검토에서 실제 결함으로 확인됐다. 15절 QUIESCING 표는 request가
`validation_retry_wait`일 때도 cancel 뒤 epoch를 닫으라고 하는데, 7.5절의 `validation_retry` 출구 가드는 “최대 재시도
초과”뿐이었다. `validating`에는 `run 중지 · 검증 취소`가 있는데 `validation_retry`에는 없는 비대칭이다.

이번에는 간선을 추가하지 않고 기존 간선의 가드를 넓히는 것이 맞았다. 목표 상태가 이미 `blocked_infrastructure`로 같기
때문이다. `blocked`로 가는 간선을 새로 만들면 오히려 틀린다. epoch가 `validation_retry`인 동안 request는
`validation_retry_wait`이므로 recorded product result가 존재할 수 없고, backoff가 풀릴 때 epoch가 `validating`으로
함께 돌아오므로 제품 판정은 언제나 `validating`에서만 일어난다. 이 근거를 7.5절 계약에 함께 적었다. 따라서 epoch 전이
수는 26으로 유지된다.

### 4.2 F01·F02 누락

위 정합성 표의 마지막 행은 구조 대조 단계에서 찾은 결함이다. `system-prompt.md`는 F01(bootstrap ref 생성 뒤 baseline DB
commit 전 crash)과 F02(baseline result commit 뒤 `initializeRun` 전후 crash)를 필수 fault 시나리오로 요구하는데,
`02-implementation-flow.md` 16.2절의 fault run 목록(당시 12~31번)에는 대응 단계가 없었다. 계약 자체는 4절의 run
bootstrap 5개 항목에 이미 서술돼 있었으므로, 빠진 것은 계약이 아니라 그 계약을 검증하는 파일럿 단계다.

방치하면 16.3절 합격 기준이 구현자에게 “언제 끝났는지”를 알려주지 못한다. bootstrap은 run 계보의 시작점이라 여기서
생긴 중복 run이나 고아 request는 이후 모든 epoch의 base SHA 계보를 오염시킨다. 다음을 추가해 F01~F31이 전부 파일럿
단계로 이어지게 했다.

- 16.2절 32번: bootstrap-ref-crash run. exact ref 재사용, 다른 tip 미덮어쓰기, orphan 정리, 잘못된 tip 재호출 거부
- 16.2절 33번: baseline-initialize-crash run. baseline result 단일 consume, run·최초 request 원자 생성, 중복 run 0,
  infra 소진 시 bootstrap `BLOCKED`와 run 미생성
- 16.3절: 두 경계의 합격 기준
- 17절: 해당 fault injection 체크 항목

## 5. 발견한 결함과 처리

| 결함 | 발견 경로 | 심각도 | 처리 |
|---|---|---|---|
| `draining`·`frozen` → `blocked_infrastructure` 전이가 7.5절 다이어그램에 없음 | 적대적 검증 | 구현 착수에 영향 | 간선 2개와 7.5절 계약 항목 추가, 전이 24→26 |
| F21의 `validation_leased` variant가 파일럿 24번에 없음 | 적대적 검증 | 완전성 | 네 번째 variant와 leased 특유의 fencing·늦은 result 거부 확인 추가 |
| F01·F02가 파일럿 fault matrix에 없음 | 문서 간 대조 | 구현 착수에 영향 | 16.2절 32·33번, 16.3절, 17절 추가 |
| issue #30719이 닫힌 사실 누락 | API 대조 | 사실 정확성 | 종료일과 “이미 수정됨” 명시 |
| `PORTING.md`의 트리 부재 누락 | API 대조 | 사실 정확성 | 두 파일 모두 실행 중 입력이었음을 서술 |
| unsafe 5개 함수 표현이 원문보다 약함 | 1차 자료 대조 | 사실 정확성 | unsound·safe Rust에서 도달 가능한 UB로 수정 |
| `validation_retry`에서 run 중지 시 출구 가드가 없음 | 후속 검토 | 구현 착수에 영향 | 기존 간선 가드에 `run 중지 · 검증 취소`를 더하고, 이 상태에서 제품 판정이 불가능한 이유를 7.5절에 명시 |
| 바이너리 크기 세 서술의 관계와 “반올림” 표현 | 1차 자료 대조, 적대적 검증 | 사실 정확성 | 플랫폼별 값·PR 어림값·20% 감소를 분리하고, 20%의 세 원인(Rust 포트·ICU·ICF)을 명시. 3.8→3·6.8→8이 반올림이 아님을 밝힘 |
| commit 6,778 정의 불명확 | 1차 자료 대조 | 해석 위험 | merge 포함으로 명시하고 세 수치의 관계 설명 |
| 러너명·테스트 파일 수 누락 | 1차 자료 대조 | 완전성 | 정확한 러너명과 파일 수 열 추가 |
| GeekNews의 no-AI 정책 언급 미반영 | 2차 자료 대조 | 완전성 | 두 2차 자료의 차이를 비중 문제로 보정 |
| WikiDocs 재검증 불가 | 접근 실패 | 근거 신뢰도 | 접근 실패를 명시하고 해당 수치 재사용 금지 |
| README 링크의 경로 표기 불일치 | 형식 검사 | 형식 | 다른 행과 같은 선행 슬래시로 통일 |

`00-diagram.md`는 수정하지 않았다. 릴리스 상태 서술(31행)과 단계·수치 노드가 이번 대조에서 모두 확인됐다.

`docs/CLAUDE.md`는 다른 프로젝트의 자동 생성 컨텍스트가 들어 있으나 저장소 `.gitignore`의 `**/CLAUDE.md` 규칙으로 이미
제외되므로 커밋되지 않는다. 별도 조치가 필요하지 않다.

## 6. 검증하지 못한 항목

| 항목 | 이유 | 결론에 미치는 영향 |
|---|---|---|
| WikiDocs 원문 | Cloudflare 차단(HTTP 403) | 없음. 해당 수치를 근거에서 제외했고 1차 자료로 대체됨 |
| 공식 회고 수치의 원장 | 팀 내부 집계이며 공개 원장이 없음 | 없음. 문서가 이미 “공식 집계”로 등급을 나눠 표기 |
| 비공개 dynamic workflow 런타임 | 미공개 | 없음. 재현 불가 항목으로 이미 명시 |
| 출시 전 Claude Fable 5의 출력 특성 | 재현 불가 | 없음. 이해관계와 재현 불가를 이미 명시 |
| `02-implementation-flow.md` 설계의 실행 증거 | 구현물이 없음 | 있음. 7절의 판정 근거 |

## 7. 구현 착수 판정

`02-implementation-flow.md` 1절의 준비도 기준을 이번 검증 결과에 적용하면 다음과 같다.

| 수준 | 판정 | 근거 |
|---|---|---|
| 연구 준비 | 통과 | 1차 자료·API 대조에서 불일치 0. 수정 항목은 모두 정확성·완전성 보강이며 결론을 바꾼 것은 없음 |
| 흐름 준비 | 통과 | 상태 집합 7축, 연산 41개, Gate, P0 산출물이 두 문서에서 일치. 상태 다이어그램 5개에 고아·막다른·비종료 상태 0. 적대적 검증 35건 중 확정 4건을 모두 수정해 산문이 요구하는 전이와 fault variant가 다이어그램·파일럿에 반영됨 |
| 파일럿 준비 | 미통과 | P0 산출물 17개가 대상 프로젝트에서 만들어지지 않았고, 정상 run 2회와 fault run이 실행되지 않음 |
| 확장 준비 | 미통과 | 파일럿 증거의 후행 조건 |
| 병합 준비 | 미통과 | 파일럿·확장 증거의 후행 조건 |

따라서 “구현을 시작할 수 있는가”와 “구현이 검증됐는가”는 답이 다르다.

**시작할 수 있다.** 구현자가 필요한 것은 갖춰져 있다. 41개 연산의 입력·성공 결과·차단 오류, 7축의 상태 전이와 금지
전이, 저장 제약 40여 개, 락 순서, crash 경계별 복구 절차, Gate 0~9의 통과 조건, F01~F31의 주입 지점과 기대 결과가
모두 명세돼 있고 두 문서가 서로 어긋나지 않는다. `docs/system-prompt.md` 10절의 11단계 구현 순서는 각 단계에 코드,
migration, 테스트, 실행 증거를 함께 요구하므로 첫 수직 경로를 바로 열 수 있다.

**검증된 것은 아니다.** 이 저장소에는 실행 코드가 없고, 따라서 `PROVEN` 증거가 하나도 없다. 17절 체크리스트는 전부
미체크 상태다. 이 상태에서 전체 코드베이스에 작업자를 투입하는 판단은 근거가 없다. 18절의 착수 판정을 적용하면 모든
P0 항목이 `MISSING`이다.

시작점은 문서가 지정한 대로 고정 입력을 쓰는 3파일 파일럿이며, 그 앞에 P0 산출물 17개가 온다. 사례의 규모나 에이전트
수가 아니라 대상 프로젝트에서 이 산출물과 게이트가 실제로 통과한 기록이 전체 포팅을 승인하는 근거다.

## 참고 자료

### 검증에 사용한 조회

- `GET /repos/oven-sh/bun/releases/latest`
- `GET /repos/oven-sh/bun/pulls/30412`
- `GET /repos/oven-sh/bun/git/trees/23427dbc12fdcff30c23a96a3d6a66d62fdc091d?recursive=1`
- `GET /repos/oven-sh/bun/commits/46d3bc29f270fa881dd573`
- `GET /repos/oven-sh/bun/issues/30719`

### 재수집한 문서

- [Bun is being rewritten in Rust](https://bun.com/blog/bun-in-rust)
- [Bun unsafe audit](https://bun.com/bun-unsafe-audit)
- [Prisma Compute: Bun's Rust rewrite in production](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute)
- [Cargo `check` 공식 문서](https://doc.rust-lang.org/cargo/commands/cargo-check.html)
- [GeekNews: Bun이 Rust로 재작성됩니다](https://news.hada.io/topic?id=31263)
- [WikiDocs: Bun, Zig에서 Rust로 전면 재작성](https://wikidocs.net/blog/@jaehong/13487/) — 접근 실패
