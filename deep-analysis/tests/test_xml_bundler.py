from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

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


if __name__ == "__main__":
    unittest.main()
