"""Exercise the remote entry against a local Git repository, without a network."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/install-remote.py"
RUNNER = """
from pathlib import Path
import sys
namespace = {'__name__': 'remote_installer'}
exec(Path(sys.argv[1]).read_bytes(), namespace)
main = namespace['main']
main.__globals__['REPOSITORY'] = sys.argv[2]
sys.exit(main(sys.argv[3:]))
"""


class RemoteInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="review-remote-source-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name) / "source repository"
        cls.source.mkdir()
        for relative in ("skills/code-review", "adapters"):
            shutil.copytree(ROOT / relative, cls.source / relative,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (cls.source / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/install.py", cls.source / "scripts/install.py")
        marker = cls.source / "skills/code-review/fixture-version"
        marker.write_text("selected release", encoding="utf-8")
        cls.git("init", "--initial-branch", "install-test")
        cls.git("add", ".")
        cls.git("-c", "user.name=Installer Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "fixture release")
        cls.git("tag", "fixture-release")
        marker.write_text("latest branch", encoding="utf-8")
        cls.git("add", ".")
        cls.git("-c", "user.name=Installer Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "fixture update")

    @classmethod
    def git(cls, *args):
        subprocess.run(["git", *args], cwd=cls.source, check=True,
                       capture_output=True, timeout=30)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="review-remote-consumer-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.project = self.directory / "consumer project"
        self.project.mkdir()
        self.cache = self.directory / "downloads"
        self.cache.mkdir()
        self.environment = dict(os.environ, TMP=str(self.cache), TEMP=str(self.cache),
                                TMPDIR=str(self.cache), PYTHONDONTWRITEBYTECODE="1")

    def install(self, *args, repository=None):
        self.assertTrue(BOOTSTRAP.is_file(), "remote installation entry is missing")
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", RUNNER, str(BOOTSTRAP),
             str(repository or self.source), "--ref", "fixture-release", *args],
            cwd=self.project, env=self.environment, capture_output=True,
            text=True, encoding="utf-8", timeout=60)
        self.assertEqual(list(self.cache.iterdir()), [], "download must be temporary")
        return result

    def test_codex_installs_selected_ref_in_current_project(self):
        result = self.install("--agent", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        skill = self.project / ".agents/skills/code-review"
        self.assertEqual((skill / "fixture-version").read_text(), "selected release")
        self.assertEqual((self.project / ".codex/agents/reviewer.toml").read_bytes(),
                         (ROOT / "adapters/codex/reviewer.toml").read_bytes())
        self.assertFalse((self.project / "code-review-skill").exists())

    def test_both_hosts_and_explicit_project_path(self):
        destination = self.directory / "another project"
        destination.mkdir()
        result = self.install("--agent", "both", "--project", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((destination / ".claude/skills/code-review/SKILL.md").is_file())
        self.assertTrue((destination / ".claude/agents/reviewer.md").is_file())
        self.assertTrue((destination / ".agents/skills/code-review/SKILL.md").is_file())
        self.assertTrue((destination / ".codex/agents/reviewer.toml").is_file())
        self.assertEqual(list(self.project.iterdir()), [])

    def test_dry_run_does_not_install(self):
        result = self.install("--agent", "codex", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["dry_run"])
        self.assertEqual(list(self.project.iterdir()), [])

    def test_conflict_exit_and_force_backup_survive_remote_entry(self):
        adapter = self.project / ".codex/agents/reviewer.toml"
        adapter.parent.mkdir(parents=True)
        adapter.write_text("custom reviewer", encoding="utf-8")
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(adapter.read_text(), "custom reviewer")
        self.assertFalse((self.project / ".agents").exists())
        result = self.install("--agent", "codex", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list(adapter.parent.glob("reviewer.toml.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "custom reviewer")

    def test_failed_download_leaves_project_untouched(self):
        result = self.install("--agent", "codex", repository=self.directory / "missing.git")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_missing_ref_does_not_install_another_version(self):
        result = self.install("--agent", "codex", "--ref", "missing-ref")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.project.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
