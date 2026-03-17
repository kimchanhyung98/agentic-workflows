import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.config import AnalysisConfig
from deep_analysis.pipeline import DeepAnalysisPipeline


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


if __name__ == "__main__":
    unittest.main()
