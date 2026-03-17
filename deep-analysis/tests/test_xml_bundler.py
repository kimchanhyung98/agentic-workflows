import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deep_analysis.xml_bundler import build_file_bundle


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


if __name__ == "__main__":
    unittest.main()
