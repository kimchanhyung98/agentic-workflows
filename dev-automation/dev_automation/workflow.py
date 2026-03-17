from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .analysis import ProjectAnalyzer
from .backend import EchoBackend, ExecutionBackend
from .models import ExecutionResult, PlanArtifacts
from .review import ChecklistReviewer, MultiReviewer


class DevAutomationWorkflow:
    def __init__(self, repo_root: Path, workspace_dir: Path):
        self.repo_root = repo_root
        self.workspace_dir = workspace_dir
        self.reviews_dir = workspace_dir / "reviews"
        self.reports_dir = workspace_dir / "reports"
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def prepare(self, requirement: str) -> PlanArtifacts:
        analyzer = ProjectAnalyzer(self.repo_root)
        structure_summary = analyzer.summarize_structure()
        integration_points = analyzer.find_integration_points()
        integration_text = "\n".join(f"- {item}" for item in integration_points) or "- 확인된 통합 지점 없음"

        timestamp = _timestamp()
        plan_path = self.reviews_dir / f"{timestamp}.plan.md"
        plan_text = "\n".join(
            [
                "# Dev Automation Review Plan",
                "",
                "## 입력 요구사항",
                requirement.strip(),
                "",
                "## 현재 프로젝트 구조와 사용 언어",
                structure_summary,
                "",
                "## 기존 CLI / 설정 / 문서 구조와의 통합 지점",
                integration_text,
                "",
                "## dev-automation 기능 권장 구조",
                "- 작업 디렉토리: `dev-automation/`",
                "- Python 패키지: `dev_automation` (import 가능한 모듈)",
                "- 리뷰 산출물 저장: `dev-automation/reviews/`",
                "- 실행 결과 저장: `dev-automation/reports/`",
                "",
                "## MVP 범위",
                "- CLI 직접 실행 경로 우선 구현",
                "- 리뷰 문서 생성 + 승인 게이트 + 실행/검증 루프",
                "- 멀티 AI 리뷰는 확장 가능한 추상화 + 최소 리뷰어 구현",
                "",
                "## 작업 계획",
                "- 관련 파일 생성/수정",
                "  - `dev-automation/dev_automation/*.py`",
                "  - `dev-automation/tests/*.py`",
                "  - `dev-automation/README.md`",
                "- 승인 전 실행 차단 로직 구현",
                "- 실패 리포트/성공 요약 산출 로직 구현",
                "",
                "## 테스트 개요",
                "- 리뷰 문서 생성 경로 테스트",
                "- 승인 전 execute 차단 테스트",
                "- 승인 후 실행 성공/실패 리포트 테스트",
                "",
                "## Assumption / TODO",
                "- 기본 실행 백엔드는 Claude Code를 가정하되 인터페이스로 추상화",
                "- 멀티 AI 리뷰어 실제 API 연동은 후속 작업으로 남김",
                "- 프로젝트별 검증 명령은 CLI 인자로 주입",
                "",
                "## 사용자 리뷰 요청",
                "- 이 문서를 확인 후 승인(approve) 또는 수정 요청을 전달하세요.",
                "- 승인 전에는 execute 단계가 동작하지 않습니다.",
            ]
        )
        plan_path.write_text(plan_text, encoding="utf-8")

        reviewer = MultiReviewer([ChecklistReviewer()])
        review_results = reviewer.run(plan_text)
        summary_path, detail_paths = reviewer.write_results(review_results, self.reviews_dir, plan_path.stem)
        return PlanArtifacts(plan_path=plan_path, review_summary_path=summary_path, review_detail_paths=detail_paths)

    def approve(self, plan_path: Path, approver: str, note: str = "") -> Path:
        approval_path = self._approval_path(plan_path)
        payload = {
            "plan": str(plan_path),
            "approved_by": approver,
            "note": note,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        approval_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return approval_path

    def execute(
        self,
        plan_path: Path,
        verify_commands: Sequence[str],
        backend: ExecutionBackend | None = None,
        max_attempts: int = 2,
    ) -> ExecutionResult:
        if not self._approval_path(plan_path).exists():
            raise PermissionError("Plan is not approved. Run approve step before execute.")

        backend = backend or EchoBackend()
        plan_text = plan_path.read_text(encoding="utf-8")
        previous_error = ""

        for attempt in range(1, max_attempts + 1):
            backend_output = backend.execute(plan_text, attempt, previous_error)
            success, output = self._run_verification(verify_commands)
            if success:
                report_path = self.reports_dir / f"{plan_path.stem}.success.md"
                report_path.write_text(
                    "\n".join(
                        [
                            "# Execution Success Summary",
                            "",
                            f"- Plan: {plan_path}",
                            f"- Attempts: {attempt}",
                            f"- Backend output: {backend_output}",
                            "",
                            "## Verification Output",
                            "```",
                            output,
                            "```",
                        ]
                    ),
                    encoding="utf-8",
                )
                return ExecutionResult(success=True, report_path=report_path, attempts=attempt)

            previous_error = output

        report_path = self.reports_dir / f"{plan_path.stem}.failure.md"
        report_path.write_text(
            "\n".join(
                [
                    "# Execution Failure Report",
                    "",
                    f"- Plan: {plan_path}",
                    f"- Max attempts reached: {max_attempts}",
                    "",
                    "## 마지막 검증 실패 로그",
                    "```",
                    previous_error,
                    "```",
                    "",
                    "## 다음 조치",
                    "- 사용자에게 실패 원인을 공유하고 기획 문서 수정 여부를 확인하세요.",
                ]
            ),
            encoding="utf-8",
        )
        return ExecutionResult(success=False, report_path=report_path, attempts=max_attempts)

    def _approval_path(self, plan_path: Path) -> Path:
        return plan_path.with_suffix(".approval.json")

    def _run_verification(self, commands: Iterable[str]) -> tuple[bool, str]:
        output_lines: list[str] = []
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                shell=True,
                text=True,
                capture_output=True,
            )
            output_lines.append(f"$ {command}")
            if completed.stdout:
                output_lines.append(completed.stdout.strip())
            if completed.stderr:
                output_lines.append(completed.stderr.strip())
            if completed.returncode != 0:
                return False, "\n".join(output_lines)
        return True, "\n".join(output_lines)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
