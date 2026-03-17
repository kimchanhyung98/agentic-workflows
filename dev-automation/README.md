# dev-automation (MVP)

`docs/_draft/dev-automation/00-diagram.md`, `01-detail.md` 기준으로 로컬 개발 자동화 워크플로우를 CLI로 실행하는 MVP입니다.

## 포함 기능

- 요구사항 입력 → 리뷰용 기획 문서 생성
- 기획 문서에 대한 최소 멀티 리뷰(확장 가능한 구조)
- 사용자 승인(approve) 전 execute 차단
- 승인 후 구현 백엔드 호출 + 검증 루프 실행
- 실패 리포트 / 성공 요약 생성

## 실행 예시

```bash
cd /home/runner/work/agentic-workflows/agentic-workflows
python3 dev-automation/run.py prepare --requirement "요구사항 텍스트"
python3 dev-automation/run.py show --plan <plan_path>
python3 dev-automation/run.py approve --plan <plan_path> --approver "human"
python3 dev-automation/run.py execute --plan <plan_path> --verify-cmd "make check" --backend echo
```

## 디렉토리 구조

- `dev-automation/dev_automation/`: import 가능한 Python 패키지
- `dev-automation/reviews/`: 리뷰용 기획 문서/리뷰 결과
- `dev-automation/reports/`: 실행 성공/실패 리포트
- `dev-automation/tests/`: 최소 테스트
