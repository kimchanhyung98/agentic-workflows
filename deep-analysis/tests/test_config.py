import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.config import AnalysisConfig


class AnalysisConfigTests(unittest.TestCase):
    def _make_config(self, temp_dir: str, overrides: dict | None = None) -> Path:
        project = Path(temp_dir) / "project"
        project.mkdir()
        data = {
            "project_path": str(project),
            "output_path": str(Path(temp_dir) / "output"),
            "project_name": "test",
            **(overrides or {}),
        }
        config_path = Path(temp_dir) / "config.json"
        config_path.write_text(json.dumps(data), encoding="utf-8")
        return config_path

    def test_loads_valid_config(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._make_config(td)
            config = AnalysisConfig.from_json_file(path)
            self.assertEqual(config.project_name, "test")
            self.assertEqual(config.reviewers, ["security", "code_quality", "performance"])

    def test_defaults_applied(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._make_config(td)
            config = AnalysisConfig.from_json_file(path)
            self.assertEqual(config.backend, "claude_code_cli")
            self.assertEqual(config.exclude_patterns, [])
            self.assertEqual(config.target_languages, [])
            self.assertEqual(config.domains, {})

    def test_missing_project_path_raises(self):
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(KeyError):
                AnalysisConfig.from_json_file(config_path)

    def test_invalid_json_raises(self):
        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "config.json"
            config_path.write_text("not json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                AnalysisConfig.from_json_file(config_path)

    def test_nonexistent_project_path_raises(self):
        with tempfile.TemporaryDirectory() as td:
            data = {"project_path": "/nonexistent/path/abc123"}
            config_path = Path(td) / "config.json"
            config_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError, msg="project_path가 존재하지 않는"):
                AnalysisConfig.from_json_file(config_path)

    def test_invalid_backend_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._make_config(td, {"backend": "openai"})
            with self.assertRaises(ValueError, msg="알 수 없는 backend"):
                AnalysisConfig.from_json_file(path)

    def test_empty_reviewers_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._make_config(td, {"reviewers": []})
            with self.assertRaises(ValueError, msg="최소 1명의 reviewer"):
                AnalysisConfig.from_json_file(path)


if __name__ == "__main__":
    unittest.main()
