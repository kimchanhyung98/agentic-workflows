from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

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

            prompts: list[str] = []

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

    def test_reviewer_partial_failure_preserves_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml_path = root / "test.xml"
            xml_path.write_text('<review target="x.py"/>', encoding="utf-8")

            call_count = 0

            def flaky_runner(prompt: str) -> str:
                nonlocal call_count
                call_count += 1
                if "security" in prompt:
                    raise RuntimeError("connection timeout")
                return "[중간] 코드 개선 필요\n- 근거\n- 개선"

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            pipeline = ReviewPipeline(cfg, reviewer_runner=flaky_runner)

            result = pipeline.run_single_stage(
                stage_name="stage1-file-review",
                xml_paths=[xml_path],
                context_text="",
                output_dir=root / "out" / "stage1",
            )

            report = result.report_paths[0].read_text(encoding="utf-8")
            self.assertIn("코드 개선 필요", report)
            self.assertIn("리뷰어 실행 실패", report)

    def test_summary_truncation_on_budget_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xmls = []
            for i in range(20):
                p = root / f"file{i}.xml"
                p.write_text(f'<review target="f{i}.py"/>', encoding="utf-8")
                xmls.append(p)

            def verbose_runner(prompt: str) -> str:
                return "[높음] 이슈 발견 " + ("x" * 500) + "\n- 근거\n- 개선"

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out", max_summary_chars=2000)
            pipeline = ReviewPipeline(cfg, reviewer_runner=verbose_runner)

            result = pipeline.run_single_stage(
                stage_name="stage1-file-review",
                xml_paths=xmls,
                context_text="",
                output_dir=root / "out" / "stage1",
            )

            summary = result.summary_path.read_text(encoding="utf-8")
            self.assertLessEqual(len(summary), 2500)
            self.assertIn("생략", summary)

    def test_context_flows_between_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml1 = root / "s1.xml"
            xml2 = root / "s2.xml"
            xml1.write_text('<review target="a.py"/>', encoding="utf-8")
            xml2.write_text('<review domain="core"/>', encoding="utf-8")

            captured_contexts: list[str] = []

            def capture_runner(prompt: str) -> str:
                if "이전 단계 context:" in prompt:
                    ctx_start = prompt.index("이전 단계 context:") + len("이전 단계 context:\n")
                    ctx_end = prompt.index("\n\n입력 XML:")
                    captured_contexts.append(prompt[ctx_start:ctx_end])
                return "[낮음] OK"

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            pipeline = ReviewPipeline(cfg, reviewer_runner=capture_runner)

            s1 = pipeline.run_single_stage("stage1", [xml1], "", root / "out" / "s1")
            s1_summary = s1.summary_path.read_text(encoding="utf-8")

            pipeline.run_single_stage("stage2", [xml2], s1_summary, root / "out" / "s2")

            stage2_contexts = [c for c in captured_contexts if "stage1 summary" in c]
            self.assertTrue(len(stage2_contexts) > 0, "Stage 2 should receive stage1 summary as context")


if __name__ == "__main__":
    unittest.main()
