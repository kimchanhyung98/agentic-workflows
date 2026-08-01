# 근거와 한계

이 문서는 `bun-rust` 분석에서 사용한 근거의 종류와 각 근거로 말할 수 있는 범위를 정리한다. 목적은 별도의 구현이나 검사 산출물을 검증하는 것이 아니라, 관찰 사실과 역설계 모델의 경계를 분명히 하는 것이다.

## 1. 근거의 층

| 층 | 자료 | 말할 수 있는 것 | 말할 수 없는 것 |
|---|---|---|---|
| 공식 회고 | Bun 팀의 2026-07-08 글 | 기간, 규모, 역할, 처리 흐름, 팀이 보고한 결과 | 내부 집계 원장과 비공개 runtime의 실제 동작 |
| 병합 PR·commit | PR #30412, 병합 commit, GitHub metadata | 병합 시점, diff, commit 수, 최종 tree | 11일 동안의 모든 중간 상태와 workflow 실행 이력 |
| 공개 workflow·script | 병합 tree의 `.claude/workflows`, CI 분류 script | 공개된 시점의 작업 입력, 샤딩, 오류 분류 방식 | 해당 파일이 언제 얼마나 실행됐는지, 비공개 API의 의미 |
| 외부 운영 관찰 | Prisma Compute 보고서 | 특정 build와 workload에서의 관찰 | 전체 Bun workload의 안정성·성능 |
| 역설계 모델 | `00-diagram.md`, `02-implementation-flow.md` | 공개된 동작을 설명하는 일관된 구조 | Bun 내부 구현의 정확한 복제 |

`확인`은 공개 자료에서 직접 읽을 수 있다는 뜻이다. Bun 팀이 자체적으로 집계한 수치는 `공식 집계`, Bun 밖의 제한된 환경에서 나온 결과는 `외부 관찰`, 공개된 동작을 연결해 만든 구조는 `역설계`로 구분한다.

## 2. GitHub 자료가 보여주는 범위

| 주장 | 근거 | 판정 | 한계 |
|---|---|---|---|
| v1.3.14 게시일은 2026-05-13 | release metadata의 게시일과 `prerelease=false` | 확인 | 이 릴리스는 첫 Rust 안정판 예고와 별개 |
| PR diff는 `+1,009,257 / -4,024`, 변경 파일 2,188개 | PR #30412 metadata | 확인 | 공식 회고의 merge 기준 `+1,009,272`와 집계 경계가 다름 |
| PR commit 수는 6,755 | PR #30412의 `commits` 필드 | 확인 | 공식 회고의 6,502·6,778과 세는 경계가 다름 |
| main 병합일은 2026-05-14 | `merged_at=2026-05-14T08:09:34Z` | 확인 | main 병합은 안정판 출시가 아님 |
| 병합 commit은 `23427dbc…` | PR의 merge commit SHA | 확인 | 없음 |
| 인용한 workflow 7개와 script 2개가 병합 tree에 존재 | 완전한 merge tree | 확인 | 파일 존재가 실제 실행을 증명하지 않음 |
| `docs/PORTING.md`와 `LIFETIMES.tsv`는 병합 tree에 없음 | 완전한 merge tree | 확인 | 언제 왜 제거됐는지는 알 수 없음 |
| `PORTING.md` 추가 commit은 `46d3bc29…` | 2026-05-04 commit | 확인 | 문서가 모든 작업에서 그대로 준수됐는지는 알 수 없음 |
| issue #30719에서 Miri로 댕글링 참조를 재현 | issue 생성·종료 기록 | 확인 | issue 종료가 unsafe 전체의 해결을 뜻하지 않음 |
| canary release tag가 존재 | canary metadata의 `prerelease=true`, `immutable=false` | 확인 | 가변 tag만으로 특정 Rust build의 동작을 고정할 수 없음 |

병합 commit `23427dbc12fdcff30c23a96a3d6a66d62fdc091d`의 tree SHA는 `d0c85750ebaae0ebf4c797435b7362ea26c7e7df`다. tree 목록은 `truncated=false`다. 분석에서 인용한 경로는 다음 아홉 개다.

- workflow 7개: `lifetime-classify`, `porting-md-zigleakage`, `phase-a-port`, `phase-d-build-queue`, `phase-d-crate-shard`, `phase-h-ci-tasks`, `phase-h-main-parity`
- script 2개: `scripts/ci-errors-to-tasks.ts`, `scripts/categorize-ci-failures.ts`

같은 tree의 `.claude/workflows/*.workflow.js`는 53개다. 이는 공식 회고의 “약 50개 dynamic workflow”와 규모가 어긋나지 않지만, 파일 수를 동시 실행 수나 실제 호출 횟수로 읽으면 안 된다.

## 3. 공식 회고의 주장

| 주장 | 공식 집계 | 해석 범위 |
|---|---|---|
| 포트 규모 | 주석 제외 Zig 535,496줄, `.zig` 파일 1,448개, 목표 약 100개 crate | 팀이 제시한 시작 범위 |
| 기간과 병렬성 | 2026-05-03~05-14의 11일, worktree 4개 × 세션 16개, 최대 약 64개 | 비공개 runtime 없이 같은 처리량을 재현할 수 없음 |
| 컴파일 단계 | 순환 의존 정리 뒤 약 16,000개 오류, crate·파일별 queue | 공개 workflow에는 명령과 분배 방식이 다른 변형이 있음 |
| 처리량과 비용 | 최고 분당 약 1,300줄, 약 165,000달러 | 순간 처리량이며 비용 원장은 공개되지 않음 |
| token | uncached input 59억, output 6.9억, cached read 720억 | 모델·호출 혼합과 과금 세부는 공개되지 않음 |
| 테스트 수렴 | 실패 파일 972→23, 여섯 플랫폼 100%, skip·삭제 0 | 공개 CI log와 artifact로 독립 재실행할 수 없음 |
| 메모리 비교 | `Bun.build()` 2,000회에서 6,745MB→609MB | 해당 재현 조건에 한정 |
| 결함과 회귀 | v1.3.14에서 재현되는 버그 128개 수정, 병합 뒤 알려진 회귀 19개 | 공식 글 작성 시점의 집계 |
| 성능 | HTTP throughput +2.8~+4.8%, build workload +2.2~+4.7% | 공식 글의 Linux x64 workload에 한정 |
| 후속 안전성 작업 | 보안 리뷰 11회, parser 약 1,000억 회 fuzzing, 약 15개 PR | CI green 이후에도 안전성 작업이 계속됐음을 보여줌 |
| 첫 Rust 안정판 | 공식 글이 v1.4.0을 예고 | 2026-05-14 main 병합과 구분해야 함 |

이 수치는 공식 글과 일치한다는 의미에서 확인할 수 있지만, Bun 내부에서 수치를 생성한 원장까지 독립적으로 검증한 것은 아니다. 공식 회고는 Bun 작성자의 자기 보고이며, Bun이 Anthropic에 인수된 뒤 출시 전 Claude Fable 5를 사용한 사례를 설명한다는 이해관계도 함께 고려해야 한다.

## 4. unsafe 감사

[Bun unsafe audit](https://bun.com/bun-unsafe-audit)는 commit `3eb0fda021`을 대상으로 2026-05-21에 작성됐고, 페이지 자체가 AI 생성물임을 명시한다. 이 감사는 `unsafe` 13,365개를 block 단위로 세고 약 9,300개는 safe code로 바꿀 수 있으며 약 4,000개는 남는다고 분류한다.

감사는 safe Rust에서 undefined behavior에 도달할 수 있는 unsound 함수 다섯 개도 별도로 지목한다. 다만 상위 네 패턴만 지점별로 측정하고 나머지는 확인된 수치 위의 추정이라고 밝힌다. 공식 회고의 약 13,000개 `unsafe` 키워드와 감사의 13,365 block은 단위와 commit이 달라 직접 비교할 수 없다.

## 5. 외부 운영 관찰

[Prisma Compute 보고서](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute)는 메모리 비교와 Prisma 자체 운영 관찰을 구분해 읽어야 한다.

- 메모리 비교는 issue #29083의 후속 실행을 인용한다. 안정판 `1.3.14+0d9b296af`는 약 96회에 900MiB를 넘었고, canary `1.3.14-canary.1+172afa532`는 4,096회 실행 동안 sampled RSS 최대 약 118MiB였다.
- Prisma가 직접 관찰한 결과는 scale-to-zero 복귀 뒤 dead idle connection 때문에 SQL pool이 멈추던 문제가 Rust canary에서는 나타나지 않았다는 것이다.

보고서도 모든 pool 실패가 해결됐다고 주장하지 않는다. 이 결과는 Prisma Compute의 당시 workload와 명시된 build에만 적용한다.

## 6. 2차 자료

[GeekNews 글](https://news.hada.io/topic?id=31263)은 공식 회고의 한국어 색인과 요약으로 유용하지만 독립 검증 자료는 아니다. Hacker News·Lobsters 토론과 Zig의 no-AI 정책에 대한 편집 서술도 포함한다.

[WikiDocs 글](https://wikidocs.net/blog/@jaehong/13487/)의 `6~9일`, `99.8%`, `약 96만 줄 Zig`, `unsafe 13,044개`는 2026-05-15 무렵의 중간 스냅샷이다. 공식 최종 회고와 집계 시점·분모·단위가 달라 이 문서의 사실 기준으로 사용하지 않는다.

## 7. 역설계 모델의 한계

`02-implementation-flow.md`는 공개 workflow를 queue, 작업 셀, 통합 장벽, 재검증 라운드로 설명한다. 다음 요소는 공개 자료에서 직접 확인되지 않는다.

- 중앙 DB나 durable queue의 사용 여부
- lease, fencing token, idempotency key 같은 중복 실행 방지 방식
- 정확한 재시작과 충돌 해결 규칙
- 모든 작업과 리뷰의 상태 계보
- canary와 release rollback 절차

따라서 역설계 모델은 공개된 동작 사이의 관계를 설명하는 도구다. 그 모델이 논리적으로 자연스럽다는 사실과 Bun이 실제로 같은 내부 구현을 사용했다는 주장은 서로 다르다.

## 8. 남은 한계

| 항목 | 남은 한계 | 분석에 미치는 영향 |
|---|---|---|
| 공식 수치의 원장 | 팀 내부 자료가 공개되지 않음 | 공식 집계로만 인용 |
| dynamic workflow runtime | 공개되지 않음 | workflow 파일과 실제 오케스트레이션을 구분 |
| Claude Fable 5 | 출시 전 모델이라 재현할 수 없음 | 모델별 성과를 일반화하지 않음 |
| 최종 `LIFETIMES.tsv` | 병합 tree에 없음 | 수명 분류 결과를 재구성할 수 없음 |
| prompt·task 계보 | 실행 중 버전과 원장이 없음 | 11일 실행을 완전 재생할 수 없음 |
| 줄별 리뷰 원장 | 공식 집계만 존재 | 모든 줄의 두 차례 리뷰를 전수 입증할 수 없음 |
| Build #54202 | 공개 Buildkite log·artifact가 없음 | 전 플랫폼 green은 공식 회고의 주장으로 취급 |
| canary tag | 가변 tag | 성능·안정성 수치는 고정 build가 있을 때만 인용 |

## 참고 자료

### GitHub 자료

- `GET /repos/oven-sh/bun/releases/tags/bun-v1.3.14`
- `GET /repos/oven-sh/bun/releases/tags/canary`
- `GET /repos/oven-sh/bun/pulls/30412`
- `GET /repos/oven-sh/bun/commits/23427dbc12fdcff30c23a96a3d6a66d62fdc091d`
- `GET /repos/oven-sh/bun/git/trees/d0c85750ebaae0ebf4c797435b7362ea26c7e7df?recursive=1`
- `GET /repos/oven-sh/bun/commits/46d3bc29f270fa881dd5730ef1549e88407701a5`
- `GET /repos/oven-sh/bun/issues/30719`
- `GET /repos/oven-sh/bun/issues/29083`

### 문서 자료

- [Bun is being rewritten in Rust](https://bun.com/blog/bun-in-rust)
- [Bun unsafe audit](https://bun.com/bun-unsafe-audit)
- [Prisma Compute: Bun's Rust rewrite in production](https://www.prisma.io/blog/bun-rust-rewrite-prisma-compute)
- [Cargo `check` 공식 문서](https://doc.rust-lang.org/cargo/commands/cargo-check.html)
- [Cargo external tools 문서](https://doc.rust-lang.org/cargo/reference/external-tools.html)
- [rustc JSON 진단 형식](https://doc.rust-lang.org/rustc/json.html)
- [GeekNews: Bun이 Rust로 재작성됩니다](https://news.hada.io/topic?id=31263)
- [WikiDocs: Bun, Zig에서 Rust로 전면 재작성](https://wikidocs.net/blog/@jaehong/13487/)
