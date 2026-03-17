import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.collector import (
    collect_project_files,
    build_domains,
    resolve_imports,
    language_for_path,
)


class CollectProjectFilesTests(unittest.TestCase):
    def _make_project(self, temp_dir: str) -> Path:
        project = Path(temp_dir) / "project"
        project.mkdir()
        return project

    def test_excludes_binary_files(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")
            (project / "image.png").write_bytes(b"\x89PNG")

            files = collect_project_files(project, [], [])
            names = [f.name for f in files]
            self.assertIn("app.py", names)
            self.assertNotIn("image.png", names)

    def test_excludes_package_lock(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "index.js").write_text("var x = 1;\n", encoding="utf-8")
            (project / "package-lock.json").write_text("{}", encoding="utf-8")

            files = collect_project_files(project, [], [])
            names = [f.name for f in files]
            self.assertNotIn("package-lock.json", names)

    def test_excludes_generated_files(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "api.generated.py").write_text("x = 1\n", encoding="utf-8")
            (project / "api.py").write_text("x = 1\n", encoding="utf-8")

            files = collect_project_files(project, [], [])
            names = [f.name for f in files]
            self.assertNotIn("api.generated.py", names)
            self.assertIn("api.py", names)

    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            vendor = project / "vendor"
            vendor.mkdir()
            (vendor / "lib.py").write_text("x = 1\n", encoding="utf-8")
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")

            files = collect_project_files(project, ["vendor/**"], [])
            names = [f.name for f in files]
            self.assertNotIn("lib.py", names)
            self.assertIn("app.py", names)

    def test_language_filter(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")
            (project / "style.css").write_text("body {}\n", encoding="utf-8")

            files = collect_project_files(project, [], ["python"])
            names = [f.name for f in files]
            self.assertIn("app.py", names)
            self.assertNotIn("style.css", names)

    def test_config_files_bypass_language_filter(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "app.py").write_text("x = 1\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")

            files = collect_project_files(project, [], ["python"])
            names = [f.name for f in files]
            self.assertIn("app.py", names)
            self.assertIn("pyproject.toml", names)

    def test_empty_files_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            (project / "empty.py").write_text("", encoding="utf-8")
            (project / "notempty.py").write_text("x = 1\n", encoding="utf-8")

            files = collect_project_files(project, [], [])
            names = [f.name for f in files]
            self.assertNotIn("empty.py", names)
            self.assertIn("notempty.py", names)

    def test_node_modules_excluded_in_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            project = self._make_project(td)
            nm = project / "node_modules" / "pkg"
            nm.mkdir(parents=True)
            (nm / "index.js").write_text("module.exports = {}\n", encoding="utf-8")
            (project / "app.js").write_text("var x = 1;\n", encoding="utf-8")

            files = collect_project_files(project, [], [])
            names = [f.name for f in files]
            self.assertNotIn("index.js", names)
            self.assertIn("app.js", names)


class BuildDomainsTests(unittest.TestCase):
    def test_auto_infer_from_directory(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            files = [
                project / "src" / "a.py",
                project / "src" / "b.py",
                project / "tests" / "test_a.py",
            ]
            for f in files:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("x = 1\n", encoding="utf-8")

            domains = build_domains(files, project, {})
            self.assertIn("src", domains)
            self.assertIn("tests", domains)
            self.assertEqual(len(domains["src"]), 2)

    def test_configured_domains_with_unmatched(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            files = [
                project / "views" / "auth.py",
                project / "utils" / "helper.py",
            ]
            for f in files:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("x = 1\n", encoding="utf-8")

            configured = {"auth": ["views/auth.py"]}
            domains = build_domains(files, project, configured)
            self.assertIn("auth", domains)
            self.assertIn("unmatched", domains)
            self.assertEqual(len(domains["auth"]), 1)

    def test_root_files_use_stem_as_domain(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            f = project / "settings.py"
            f.write_text("x = 1\n", encoding="utf-8")

            domains = build_domains([f], project, {})
            self.assertIn("settings", domains)


class ResolveImportsTests(unittest.TestCase):
    def test_resolves_python_imports(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            target = project / "views.py"
            model = project / "models.py"
            unrelated = project / "utils.py"
            target.write_text("from models import User\n", encoding="utf-8")
            model.write_text("class User: pass\n", encoding="utf-8")
            unrelated.write_text("def helper(): pass\n", encoding="utf-8")

            result = resolve_imports(target, [target, model, unrelated], max_context=2)
            self.assertIn(model, result)

    def test_falls_back_to_same_directory(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            (project / "src").mkdir()
            target = project / "src" / "a.py"
            sibling = project / "src" / "b.py"
            far = project / "c.py"
            target.write_text("x = 1\n", encoding="utf-8")
            sibling.write_text("y = 2\n", encoding="utf-8")
            far.write_text("z = 3\n", encoding="utf-8")

            result = resolve_imports(target, [target, sibling, far], max_context=1)
            self.assertEqual(result, [sibling])


class LanguageForPathTests(unittest.TestCase):
    def test_known_extensions(self):
        self.assertEqual(language_for_path(Path("app.py")), "python")
        self.assertEqual(language_for_path(Path("index.ts")), "typescript")
        self.assertEqual(language_for_path(Path("config.yaml")), "yaml")

    def test_unknown_extension(self):
        self.assertEqual(language_for_path(Path("data.xyz")), "text")


if __name__ == "__main__":
    unittest.main()
