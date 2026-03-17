# Deep Analysis

프로젝트 전체 코드를 XML로 번들링하고, 3단계 점진적 리뷰(파일 → 도메인 → 프로젝트)를 수행하는 파이프라인입니다.

## 실행

```bash
python /home/runner/work/agentic-workflows/agentic-workflows/deep-analysis/main.py \
  --project-root /home/runner/work/agentic-workflows/agentic-workflows \
  --output-dir /home/runner/work/agentic-workflows/agentic-workflows/deep-analysis/output \
  --print-design
```

## Ralph Loop 스타일 진입점

```bash
python /home/runner/work/agentic-workflows/agentic-workflows/deep-analysis/entrypoint.py \
  --project-root /home/runner/work/agentic-workflows/agentic-workflows \
  --output-dir /home/runner/work/agentic-workflows/agentic-workflows/deep-analysis/output \
  --loop --interval-seconds 3600
```

## 설정 파일 (JSON)

```json
{
  "project_name": "agentic-workflows",
  "claude_command": "claude",
  "excludes": ["docs/**"],
  "include_extensions": [".py", ".ts", ".js"],
  "domain_map": {
    "auth": ["**/*auth*.py", "**/*auth*.ts"],
    "order": ["**/*order*.py", "**/*order*.ts"]
  },
  "config_files": ["pyproject.toml", "package.json", "Makefile"],
  "max_context_files": 6,
  "reviewers": [
    {"name": "security", "focus": "인증/인가, 입력 검증, 시크릿 노출"},
    {"name": "quality", "focus": "코드 품질, 설계, 유지보수성"},
    {"name": "performance", "focus": "성능, 리소스, 동시성"}
  ]
}
```
