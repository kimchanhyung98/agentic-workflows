import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import importlib.util
import sys


def load_cli_module():
    module_path = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("dev_automation_cli", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load cli.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli_module()

    def test_build_plan_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            context = self.cli.collect_context("요구사항 테스트", repo_root)
            plan = self.cli.build_plan_markdown(context)
            self.assertIn("# PLAN: Human-in-the-Loop 로컬 개발 자동화", plan)
            self.assertIn("## 작업 계획", plan)
            self.assertIn("## 테스트 케이스 개요", plan)
            self.assertIn("## 애매한 판단(사람 결정 필요)", plan)

    def test_review_loop_accepts_modify(self):
        with patch("builtins.input", side_effect=["r", "게이트를 make check로 고정"]):
            choice, note = self.cli.review_plan_loop("dummy plan")
        self.assertEqual(choice, "r")
        self.assertEqual(note, "게이트를 make check로 고정")

    def test_execute_runs_gates_after_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            plan_path = repo_root / "PLAN.md"
            plan_path.write_text("plan", encoding="utf-8")
            result = self.cli.run_execute_with_gates(
                repo_root=repo_root,
                plan_path=plan_path,
                ralph_loop_cmd="python -c \"print('ok')\"",
                gates=["python -c \"print('gate')\""],
                max_retries=1,
            )
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
