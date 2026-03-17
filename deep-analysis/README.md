# Deep Analysis

프로젝트 전체 소스코드를 수집/구조화(XML Bundling)하고, 파일 → 기능 도메인 → 프로젝트의 3단계 리뷰 문서와 최종 리포트를 생성한다.

## 실행 방법

```bash
cd /path/to/repo
PYTHONPATH=/path/to/repo/deep-analysis python3 -m deep_analysis --config /absolute/path/to/config.json
# 또는
python3 /path/to/repo/deep-analysis/run.py --config /absolute/path/to/config.json
```

> `backend`를 `claude_code_cli`로 두면 Claude Code CLI를 호출한다.
> 로컬/테스트 환경에서는 `backend: stub`으로 실행 가능하다.

## 설정 파일

`deep-analysis/config.example.json`를 복사해 프로젝트에 맞게 수정한다.

필수 필드:
- `project_path`: 분석할 프로젝트 경로
- `output_path`: 단계별 산출물 저장 경로
- `project_name`: 프로젝트 식별자

선택 필드:
- `exclude_patterns`: 추가 제외 패턴
- `target_languages`: 대상 언어 필터
- `domains`: 기능 도메인 수동 그룹핑

## 산출물

실행 완료 시 아래 파일이 생성된다.

- `stage1-file-review.md`
- `stage2-domain-review.md`
- `stage3-project-review.md`
- `final-review-report.md`

샘플 형식은 `deep-analysis/examples/sample-final-report.md` 참고.

## Assumption / TODO

- 기능 도메인 자동 그룹핑은 기본적으로 디렉토리 기반이며, `domains` 설정으로 오버라이드한다.
- Claude Code CLI 실행 명령은 `claude --print`를 기본 가정으로 두었다.
- Ralph loop는 런타임 필수 의존성으로 추가하지 않았다. 반복 실행 전략이 필요하면 별도 옵션으로 확장한다.
