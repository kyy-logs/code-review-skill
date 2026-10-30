"""Generate the NEWS Unreleased block from a temporary git history."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "news-update.py"
INITIAL_NEWS = """# News

<!-- UNRELEASED:START -->
## Unreleased

_Old draft._
<!-- UNRELEASED:END -->

## v1.0

### Added

- Initial release.
"""


class NewsUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="news update ")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name) / "repo with spaces"
        self.repo.mkdir()
        self.news = self.repo / "NEWS.md"
        self.news.write_text(INITIAL_NEWS, encoding="utf-8")
        self.git("init", "--quiet")
        self.git("config", "user.name", "News Test")
        self.git("config", "user.email", "news-test@example.invalid")
        self.git("add", "NEWS.md")
        self.git("commit", "--quiet", "-m", "Initial release")
        self.git("tag", "v1.0")

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args], capture_output=True,
            text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def commit(self, message):
        self.git("commit", "--quiet", "--allow-empty", "-m", message)

    def run_update(self, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), "--repo", str(self.repo),
             "--news", str(self.news), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=30)

    def test_conventional_commits_are_grouped_and_non_user_types_are_skipped(self):
        for message in (
            "feat(installer): add codex adapter",
            "fix: preserve existing config",
            "docs: update readme",
            "chore: bump version",
            "refactor(core)!: change output",
        ):
            self.commit(message)
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.news.read_text(encoding="utf-8")
        self.assertIn("### Added\n\n- installer: add codex adapter", text)
        self.assertIn("### Fixed\n\n- preserve existing config", text)
        self.assertIn("### Breaking Changes\n\n- core: change output", text)
        self.assertNotIn("update readme", text)
        self.assertNotIn("bump version", text)
        self.assertIn("## v1.0", text)

    def test_non_conventional_history_uses_keyword_fallback(self):
        for message in (
            "Add remote installer",
            "Fix config conflict",
            "Remove old script",
            "Update documentation",
        ):
            self.commit(message)
        self.assertEqual(self.run_update().returncode, 0)
        text = self.news.read_text(encoding="utf-8")
        self.assertIn("### Added\n\n- Add remote installer", text)
        self.assertIn("### Fixed\n\n- Fix config conflict", text)
        self.assertIn("### Removed\n\n- Remove old script", text)
        self.assertIn("### Changed\n\n- Update documentation", text)

    def test_merge_release_and_news_bot_subjects_are_skipped(self):
        for message in (
            "Merge branch 'feature'",
            "chore(release): v2.0.0",
            "docs: sync latest news into README",
        ):
            self.commit(message)
        self.assertEqual(self.run_update().returncode, 0)
        text = self.news.read_text(encoding="utf-8")
        self.assertIn("_No user-facing changes since the latest release._", text)
        self.assertNotIn("Merge branch", text)
        self.assertNotIn("v2.0.0", text)
        self.assertNotIn("sync latest news", text)

    def test_check_detects_stale_block_without_writing_then_rerun_is_noop(self):
        self.commit("feat: add one command")
        before = self.news.read_bytes()
        stale = self.run_update("--check")
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertEqual(self.news.read_bytes(), before)
        self.assertEqual(self.run_update().returncode, 0)
        rendered = self.news.read_bytes()
        self.assertEqual(self.run_update().returncode, 0)
        self.assertEqual(self.run_update("--check").returncode, 0)
        self.assertEqual(self.news.read_bytes(), rendered)

    def test_explicit_from_revision_is_honored(self):
        self.git("tag", "v1.1")
        self.commit("feat: later change")
        result = self.run_update("--from", "v1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- later change", self.news.read_text(encoding="utf-8"))

    def test_missing_markers_leave_news_untouched(self):
        self.news.write_text("# News\n\n## v1.0\n\n- Old.\n", encoding="utf-8")
        before = self.news.read_bytes()
        result = self.run_update()
        self.assertEqual(result.returncode, 2)
        self.assertIn("UNRELEASED", result.stderr)
        self.assertEqual(self.news.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
