from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


class WorkflowCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name) / "repo"
        self.repo_root.mkdir(parents=True, exist_ok=True)

        (self.repo_root / "docs" / "_draft" / "dev-automation").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "docs" / "_draft" / "dev-automation" / "00-diagram.md").write_text("diagram", encoding="utf-8")
        (self.repo_root / "docs" / "_draft" / "dev-automation" / "01-detail.md").write_text("detail", encoding="utf-8")
        (self.repo_root / "Makefile").write_text("check:\n\t@echo ok\n", encoding="utf-8")

        self.workspace = self.repo_root / "dev-automation"
        self.run_py = (
            Path(__file__).resolve().parents[1] / "run.py"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [
            "python3",
            str(self.run_py),
            "--repo-root",
            str(self.repo_root),
            "--workspace",
            str(self.workspace),
            *args,
        ]
        return subprocess.run(command, check=False, text=True, capture_output=True)

    def test_prepare_creates_plan_and_review_docs(self) -> None:
        completed = self._run_cli("prepare", "--requirement", "간단 요구사항")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        plan_line = next(line for line in completed.stdout.splitlines() if line.startswith("PLAN="))
        review_line = next(line for line in completed.stdout.splitlines() if line.startswith("REVIEW_SUMMARY="))
        plan_path = Path(plan_line.split("=", 1)[1])
        review_path = Path(review_line.split("=", 1)[1])

        self.assertTrue(plan_path.exists())
        self.assertTrue(review_path.exists())
        self.assertIn("## 현재 프로젝트 구조와 사용 언어", plan_path.read_text(encoding="utf-8"))

    def test_execute_requires_approval(self) -> None:
        prepared = self._run_cli("prepare", "--requirement", "승인 테스트")
        plan_line = next(line for line in prepared.stdout.splitlines() if line.startswith("PLAN="))
        plan_path = plan_line.split("=", 1)[1]

        completed = self._run_cli(
            "execute",
            "--plan",
            plan_path,
            "--verify-cmd",
            "echo test",
            "--backend",
            "echo",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Plan is not approved", completed.stderr)

    def test_execute_failure_creates_failure_report(self) -> None:
        prepared = self._run_cli("prepare", "--requirement", "실패 테스트")
        plan_line = next(line for line in prepared.stdout.splitlines() if line.startswith("PLAN="))
        plan_path = plan_line.split("=", 1)[1]

        approved = self._run_cli("approve", "--plan", plan_path, "--approver", "tester")
        self.assertEqual(approved.returncode, 0, approved.stderr)

        completed = self._run_cli(
            "execute",
            "--plan",
            plan_path,
            "--verify-cmd",
            "python3 -c 'import sys; sys.exit(1)'",
            "--backend",
            "echo",
            "--max-attempts",
            "2",
        )

        self.assertNotEqual(completed.returncode, 0)
        report_line = next(line for line in completed.stdout.splitlines() if line.startswith("REPORT="))
        report_path = Path(report_line.split("=", 1)[1])
        self.assertTrue(report_path.exists())
        self.assertIn("Failure", report_path.read_text(encoding="utf-8"))

    def test_execute_success_creates_success_summary(self) -> None:
        prepared = self._run_cli("prepare", "--requirement", "성공 테스트")
        plan_line = next(line for line in prepared.stdout.splitlines() if line.startswith("PLAN="))
        plan_path = plan_line.split("=", 1)[1]

        approved = self._run_cli("approve", "--plan", plan_path, "--approver", "tester")
        self.assertEqual(approved.returncode, 0, approved.stderr)

        completed = self._run_cli(
            "execute",
            "--plan",
            plan_path,
            "--verify-cmd",
            "echo ok",
            "--backend",
            "echo",
            "--max-attempts",
            "2",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report_line = next(line for line in completed.stdout.splitlines() if line.startswith("REPORT="))
        report_path = Path(report_line.split("=", 1)[1])
        self.assertTrue(report_path.exists())
        self.assertIn("Success", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
