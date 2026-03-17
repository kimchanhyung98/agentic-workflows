from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import AnalysisConfig
from review_pipeline import ReviewPipeline


class ReviewPipelineTest(unittest.TestCase):
    def test_progressive_stages_create_final_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage1_xml = root / "stage1.xml"
            stage2_xml = root / "stage2.xml"
            stage3_xml = root / "stage3.xml"
            stage1_xml.write_text('<review target="a.py"/>', encoding="utf-8")
            stage2_xml.write_text('<review domain="core"/>', encoding="utf-8")
            stage3_xml.write_text('<review scope="project"/>', encoding="utf-8")

            prompts = []

            def fake_runner(prompt: str) -> str:
                prompts.append(prompt)
                if "security" in prompt:
                    return "[높음] 인증 점검 필요\n- 근거\n- 개선"
                return "[중간] 품질 개선\n- 근거\n- 개선"

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            pipeline = ReviewPipeline(cfg, reviewer_runner=fake_runner)

            results = pipeline.run([stage1_xml], [stage2_xml], stage3_xml, root / "out")
            final_report = results["final"].summary_path.read_text(encoding="utf-8")

            self.assertIn("Deep Analysis Final Report", final_report)
            self.assertIn("Severity Summary", final_report)
            self.assertIn("stage1-file-review summary", final_report)
            self.assertTrue(len(prompts) >= 3)


if __name__ == "__main__":
    unittest.main()
