# dev-automation

Human-in-the-loop 기반 로컬 개발 자동화 파이프라인입니다.

## 실행

```bash
python3 dev-automation/cli.py \
  --requirement "요구사항 텍스트" \
  --ralph-loop-cmd "ralph-loop"
```

또는:

```bash
REQUIREMENT="요구사항 텍스트" make dev-automation
```

## 동작 요약

1. Prepare: `docs/_draft/dev-automation/*.md` 등 컨텍스트를 포함한 PLAN 문서 생성
2. Human Review: 터미널에서 승인(y) / 수정 재작성(r) / 중단(n) 입력 대기
3. Execute & Gate: 승인 시 Ralph Loop 실행 후 결정론적 gate(`make check` 기본) 검증
4. Escalation: 실패가 `--max-retries`를 초과하면 `dev-automation/failure-report.md` 생성
