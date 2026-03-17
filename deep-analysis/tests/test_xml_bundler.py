import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.xml_bundler import build_file_bundle, build_domain_bundle, build_project_bundle


class XmlBundlerTests(unittest.TestCase):
    def test_file_bundle_escapes_xml_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            target = project / "src" / "main.py"
            context = project / "src" / "util.py"
            target.parent.mkdir(parents=True)
            target.write_text('print("<tag>")\n', encoding="utf-8")
            context.write_text("value = 'a & b'\n", encoding="utf-8")

            bundle = build_file_bundle(project, target, [context])

            self.assertIn('target="src/main.py"', bundle)
            self.assertIn('path="src/util.py" role="context"', bundle)
            self.assertIn("&lt;tag&gt;", bundle)
            self.assertIn("a &amp; b", bundle)

    def test_domain_bundle_includes_all_files_as_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "auth").mkdir()
            f1 = project / "auth" / "views.py"
            f2 = project / "auth" / "models.py"
            f1.write_text("def login(): pass\n", encoding="utf-8")
            f2.write_text("class User: pass\n", encoding="utf-8")

            bundle = build_domain_bundle(project, "auth", [f1, f2])

            self.assertIn('domain="auth"', bundle)
            self.assertIn('role="target"', bundle)
            self.assertIn("auth/views.py", bundle)
            self.assertIn("auth/models.py", bundle)
            self.assertIn("</review>", bundle)

    def test_domain_bundle_includes_previous_reviews(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            f1 = project / "app.py"
            f1.write_text("x = 1\n", encoding="utf-8")

            summary = "[높음] issue <with> special & chars"
            bundle = build_domain_bundle(project, "core", [f1], stage1_summary=summary)

            self.assertIn("<previous-reviews>", bundle)
            self.assertIn("<stage1-summary>", bundle)
            self.assertIn("&lt;with&gt;", bundle)
            self.assertIn("special &amp; chars", bundle)

    def test_project_bundle_includes_config_and_summaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            src = project / "app.py"
            cfg = project / "settings.py"
            src.write_text("x = 1\n", encoding="utf-8")
            cfg.write_text("DEBUG = True\n", encoding="utf-8")

            bundle = build_project_bundle(
                "test-proj", project, [src, cfg], [cfg],
                "stage1 summary", "stage2 summary",
            )

            self.assertIn('scope="project"', bundle)
            self.assertIn('name="test-proj"', bundle)
            self.assertIn("<previous-reviews>", bundle)
            self.assertIn("stage1 summary", bundle)
            self.assertIn("stage2 summary", bundle)
            self.assertIn('<config path="settings.py"', bundle)


if __name__ == "__main__":
    unittest.main()
