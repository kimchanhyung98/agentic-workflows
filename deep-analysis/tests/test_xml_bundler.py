from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import AnalysisConfig
from xml_bundler import XmlBundler


class XmlBundlerTest(unittest.TestCase):
    def test_collect_and_bundle_respects_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("ignored_dir/\n*.log\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("import helper\n", encoding="utf-8")
            (root / "src" / "helper.py").write_text("def x():\n    return 1\n", encoding="utf-8")
            (root / "ignored_dir").mkdir()
            (root / "ignored_dir" / "secret.py").write_text("print('x')", encoding="utf-8")
            (root / "runtime.log").write_text("skip", encoding="utf-8")

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            bundler = XmlBundler(cfg)
            files = bundler.collect_source_files()
            paths = [f.path.as_posix() for f in files]

            self.assertIn("src/app.py", paths)
            self.assertNotIn("ignored_dir/secret.py", paths)
            self.assertNotIn("runtime.log", paths)

            stage1_paths = bundler.bundle_file_stage(files, root / "out" / "stage1")
            xml = stage1_paths[0].read_text(encoding="utf-8")
            self.assertIn('role="target"', xml)
            self.assertIn('encoding="xml-escaped"', xml)

    def test_nested_directory_pattern_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1;", encoding="utf-8")

            (root / "lib" / "vendor" / "node_modules" / "dep").mkdir(parents=True)
            (root / "lib" / "vendor" / "node_modules" / "dep" / "main.js").write_text("export default 1;", encoding="utf-8")

            (root / "src").mkdir()
            (root / "src" / "app.js").write_text("import x from 'pkg';", encoding="utf-8")

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            bundler = XmlBundler(cfg)
            files = bundler.collect_source_files()
            paths = [f.path.as_posix() for f in files]

            self.assertIn("src/app.js", paths)
            self.assertNotIn("node_modules/pkg/index.js", paths)
            self.assertNotIn("lib/vendor/node_modules/dep/main.js", paths)

    def test_output_dir_auto_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "analysis-output"
            out.mkdir()
            (out / "previous-run.xml").write_text("<review/>", encoding="utf-8")

            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hello')", encoding="utf-8")

            cfg = AnalysisConfig(project_root=root, output_dir=out)
            bundler = XmlBundler(cfg)
            files = bundler.collect_source_files()
            paths = [f.path.as_posix() for f in files]

            self.assertIn("src/main.py", paths)
            self.assertNotIn("analysis-output/previous-run.xml", paths)

    def test_domain_grouping_directory_based_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "auth").mkdir(parents=True)
            (root / "src" / "auth" / "views.py").write_text("def login(): pass", encoding="utf-8")
            (root / "src" / "auth" / "models.py").write_text("class User: pass", encoding="utf-8")
            (root / "src" / "order").mkdir(parents=True)
            (root / "src" / "order" / "views.py").write_text("def create(): pass", encoding="utf-8")

            cfg = AnalysisConfig(project_root=root, output_dir=root / "out")
            bundler = XmlBundler(cfg)
            files = bundler.collect_source_files()
            domains = bundler._group_domains(files)

            self.assertIn("auth", domains)
            self.assertIn("order", domains)
            auth_paths = {f.path.as_posix() for f in domains["auth"]}
            self.assertIn("src/auth/views.py", auth_paths)
            self.assertIn("src/auth/models.py", auth_paths)


if __name__ == "__main__":
    unittest.main()
