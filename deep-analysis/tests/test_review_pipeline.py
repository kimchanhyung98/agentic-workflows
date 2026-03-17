import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.config import AnalysisConfig
from deep_analysis.pipeline import DeepAnalysisPipeline, _truncate_to_line, _extract_severity_lines


class ReviewPipelineTests(unittest.TestCase):
    def test_pipeline_writes_stage_documents_and_final_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            project.mkdir()

            (project / "src").mkdir()
            (project / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")
            (project / "settings.py").write_text("DEBUG = False\n", encoding="utf-8")

            output = root / "output"
            config = AnalysisConfig(
                project_path=project,
                output_path=output,
                backend="stub",
                project_name="sample",
                reviewers=["security", "code_quality", "performance"],
            )

            result = DeepAnalysisPipeline(config).run()

            self.assertTrue(result.stage1_path.exists())
            self.assertTrue(result.stage2_path.exists())
            self.assertTrue(result.stage3_path.exists())
            self.assertTrue(result.final_report_path.exists())

            final_report = result.final_report_path.read_text(encoding="utf-8")
            self.assertIn("## 요약", final_report)
            self.assertIn("### 높음", final_report)
            self.assertIn("Assumption / TODO", final_report)

            stage1 = result.stage1_path.read_text(encoding="utf-8")
            self.assertIn("# 1단계 파일 리뷰", stage1)
            self.assertIn("[security]", stage1)
            self.assertIn("[code_quality]", stage1)

            stage2 = result.stage2_path.read_text(encoding="utf-8")
            self.assertIn("# 2단계 도메인 리뷰", stage2)

            stage3 = result.stage3_path.read_text(encoding="utf-8")
            self.assertIn("# 3단계 프로젝트 리뷰", stage3)

    def test_final_report_severity_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            project.mkdir()
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")

            output = root / "output"
            config = AnalysisConfig(
                project_path=project,
                output_path=output,
                backend="stub",
                project_name="count-test",
                reviewers=["security", "code_quality"],
            )

            result = DeepAnalysisPipeline(config).run()
            final = result.final_report_path.read_text(encoding="utf-8")

            self.assertIn("총 이슈 수:", final)
            self.assertIn("높음:", final)
            self.assertIn("중간:", final)

    def test_empty_project_produces_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "empty-project"
            project.mkdir()

            output = root / "output"
            config = AnalysisConfig(
                project_path=project,
                output_path=output,
                backend="stub",
                project_name="empty",
                reviewers=["security"],
            )

            result = DeepAnalysisPipeline(config).run()
            self.assertTrue(result.final_report_path.exists())
            final = result.final_report_path.read_text(encoding="utf-8")
            self.assertIn("총 이슈 수:", final)
            self.assertIn("## 요약", final)


class TruncationTests(unittest.TestCase):
    def test_truncate_to_line_preserves_last_complete_line(self):
        text = "line1\nline2\nline3\nline4"
        result = _truncate_to_line(text, 15)
        self.assertIn("line1", result)
        self.assertFalse(result.endswith("lin"))

    def test_truncate_to_line_returns_short_text_unchanged(self):
        text = "short"
        self.assertEqual(_truncate_to_line(text, 100), text)

    def test_extract_severity_lines_filters_tagged_lines(self):
        text = "some intro\n[높음] issue A\nunrelated\n[중간] issue B\nmore text"
        result = _extract_severity_lines(text, 500)
        self.assertIn("[높음] issue A", result)
        self.assertIn("[중간] issue B", result)
        self.assertNotIn("some intro", result)
        self.assertNotIn("unrelated", result)


if __name__ == "__main__":
    unittest.main()
