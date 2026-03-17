from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev_automation.backend import EchoBackend
from dev_automation.workflow import DevAutomationWorkflow


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name) / "repo"
        self.repo_root.mkdir(parents=True, exist_ok=True)
        (self.repo_root / "docs" / "_draft" / "dev-automation").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "docs" / "_draft" / "dev-automation" / "00-diagram.md").write_text("diagram", encoding="utf-8")
        (self.repo_root / "docs" / "_draft" / "dev-automation" / "01-detail.md").write_text("detail", encoding="utf-8")
        (self.repo_root / "Makefile").write_text("check:\n\t@echo ok\n", encoding="utf-8")

        self.workspace = self.repo_root / "dev-automation"
        self.workflow = DevAutomationWorkflow(self.repo_root, self.workspace)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_prepare_creates_plan_and_review_docs(self) -> None:
        artifacts = self.workflow.prepare("간단 요구사항")

        self.assertTrue(artifacts.plan_path.exists())
        self.assertTrue(artifacts.review_summary_path.exists())
        content = artifacts.plan_path.read_text(encoding="utf-8")
        self.assertIn("## 현재 프로젝트 구조와 사용 언어", content)
        self.assertIn("## 테스트 개요", content)

    def test_execute_requires_approval(self) -> None:
        artifacts = self.workflow.prepare("승인 테스트")

        with self.assertRaises(PermissionError):
            self.workflow.execute(artifacts.plan_path, verify_commands=["echo test"], backend=EchoBackend())

    def test_execute_failure_creates_failure_report(self) -> None:
        artifacts = self.workflow.prepare("실패 테스트")
        self.workflow.approve(artifacts.plan_path, approver="tester")

        result = self.workflow.execute(
            artifacts.plan_path,
            verify_commands=["python3 -c \"import sys; sys.exit(1)\""],
            backend=EchoBackend(),
            max_attempts=2,
        )

        self.assertFalse(result.success)
        self.assertTrue(result.report_path.exists())
        self.assertIn("Failure", result.report_path.read_text(encoding="utf-8"))

    def test_execute_success_creates_success_summary(self) -> None:
        artifacts = self.workflow.prepare("성공 테스트")
        self.workflow.approve(artifacts.plan_path, approver="tester")

        result = self.workflow.execute(
            artifacts.plan_path,
            verify_commands=["echo ok"],
            backend=EchoBackend(),
            max_attempts=2,
        )

        self.assertTrue(result.success)
        self.assertTrue(result.report_path.exists())
        self.assertIn("Success", result.report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
