"""Exercise the release-note synchronizer without touching repository documents."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync-news.py"
README = """# Project

Keep this introduction.

<!-- NEWS:START -->
Old preview.
<!-- NEWS:END -->

Keep this footer.
"""
NEWS = """# News

Newest release first.

## v2.0 (2026-10-30)

### Added

- Support paths with spaces and 中文.

## v1.0 (2026-10-01)

- Old change.
"""
EXPECTED = """# Project

Keep this introduction.

<!-- NEWS:START -->
### v2.0 (2026-10-30)

#### Added

- Support paths with spaces and 中文.

[Full update history](NEWS.md)
<!-- NEWS:END -->

Keep this footer.
"""


class NewsSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="news sync ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.news = self.root / "NEWS.md"
        self.readme = self.root / "README.md"
        self.news.write_text(NEWS, encoding="utf-8")
        self.readme.write_text(README, encoding="utf-8")

    def run_sync(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--news", str(self.news),
             "--readme", str(self.readme), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_renders_only_latest_release_and_preserves_surrounding_content(self):
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), EXPECTED)
        self.assertEqual(self.news.read_text(encoding="utf-8"), NEWS)

    def test_check_detects_stale_preview_without_writing_and_rerun_is_noop(self):
        before = self.readme.read_bytes()
        stale = self.run_sync("--check")
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertEqual(self.readme.read_bytes(), before)
        self.assertEqual(self.run_sync().returncode, 0)
        rendered = self.readme.read_bytes()
        modified = self.readme.stat().st_mtime_ns
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.run_sync("--check").returncode, 0)
        self.assertEqual(self.readme.read_bytes(), rendered)
        self.assertEqual(self.readme.stat().st_mtime_ns, modified)

    def test_invalid_markers_or_news_leave_readme_untouched(self):
        fixtures = [
            ("# No preview markers\n", NEWS),
            (README + "<!-- NEWS:START -->\n", NEWS),
            ("<!-- NEWS:END -->\n<!-- NEWS:START -->\n", NEWS),
            (README, "# News\n\nNo release yet.\n"),
            (README, "# News\n\n## v2.0\n\n## v1.0\n\n- Older.\n"),
        ]
        for readme, news in fixtures:
            with self.subTest(readme=readme, news=news):
                self.readme.write_text(readme, encoding="utf-8")
                self.news.write_text(news, encoding="utf-8")
                before = self.readme.read_bytes()
                result = self.run_sync()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("sync-news:", result.stderr)
                self.assertEqual(self.readme.read_bytes(), before)

    def test_crlf_and_markdown_in_code_blocks_are_preserved(self):
        news = "# News\n\n## v2.0\n\n```sh\n## shell comment\n### unchanged\n```\n\n## v1.0\n\n- Older.\n"
        self.news.write_bytes(news.replace("\n", "\r\n").encode("utf-8"))
        self.readme.write_bytes(README.replace("\n", "\r\n").encode("utf-8"))
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = README.replace("Old preview.", "### v2.0\n\n```sh\n## shell comment\n### unchanged\n```\n\n[Full update history](NEWS.md)")
        self.assertEqual(self.readme.read_bytes(), expected.replace("\n", "\r\n").encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
