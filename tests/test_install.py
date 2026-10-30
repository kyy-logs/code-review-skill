"""Install both host layouts without overwriting user configuration."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SKILL = ROOT / "skills" / "code-review"
CLAUDE_ADAPTER = ROOT / "adapters" / "claude-code" / "reviewer.md"
CODEX_ADAPTER = ROOT / "adapters" / "codex" / "reviewer.toml"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="code-review-install-")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "consumer project"
        self.project.mkdir()
        self.environment = dict(os.environ, CODE_REVIEW_PYTHON=sys.executable)
        self.environment.pop("CODE_REVIEW_SKILL_DIR", None)

    def install(self, *args, project=None):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(INSTALLER), "--project",
             str(project or self.project), *args],
            cwd=ROOT, env=self.environment, capture_output=True, text=True,
            encoding="utf-8", timeout=30)

    def test_claude_installation_includes_skill_and_adapter(self):
        result = self.install("--agent", "claude-code")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/code-review/SKILL.md").is_file())
        self.assertEqual((self.project / ".claude/agents/reviewer.md").read_bytes(),
                         CLAUDE_ADAPTER.read_bytes())
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".agents").exists())

    def test_codex_installation_includes_skill_and_toml(self):
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".agents/skills/code-review/SKILL.md").is_file())
        adapter = self.project / ".codex/agents/reviewer.toml"
        self.assertEqual(adapter.read_bytes(), CODEX_ADAPTER.read_bytes())
        text = adapter.read_text(encoding="utf-8")
        self.assertIn('name = "reviewer"', text)
        self.assertIn('sandbox_mode = "read-only"', text)
        self.assertIn('developer_instructions = """', text)
        self.assertIn("references/reviewer.md", text)
        self.assertIn("reviewer.json", text)
        self.assertNotIn("tools =", text)
        try:
            import tomli
        except ImportError:
            tomli = None
        if tomli is not None:
            parsed = tomli.loads(text)
            self.assertEqual(parsed["name"], "reviewer")
            self.assertEqual(parsed["sandbox_mode"], "read-only")
            self.assertIn("references/reviewer.md", parsed["developer_instructions"])
        self.assertFalse((self.project / ".claude").exists())

    def test_both_hosts_install_together(self):
        result = self.install("--agent", "both")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/code-review/SKILL.md").is_file())
        self.assertTrue((self.project / ".agents/skills/code-review/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/agents/reviewer.md").is_file())
        self.assertTrue((self.project / ".codex/agents/reviewer.toml").is_file())

    def test_repeat_install_is_a_noop(self):
        self.assertEqual(self.install("--agent", "codex").returncode, 0)
        skill = self.project / ".agents/skills/code-review/SKILL.md"
        adapter = self.project / ".codex/agents/reviewer.toml"
        before = (skill.stat().st_mtime_ns, adapter.stat().st_mtime_ns,
                  skill.read_bytes(), adapter.read_bytes())
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        after = (skill.stat().st_mtime_ns, adapter.stat().st_mtime_ns,
                 skill.read_bytes(), adapter.read_bytes())
        self.assertEqual(before, after)
        self.assertIn("unchanged .agents/skills/code-review", result.stdout)
        self.assertIn("unchanged .codex/agents/reviewer.toml", result.stdout)

    def test_existing_codex_adapter_is_protected_before_any_write(self):
        adapter = self.project / ".codex/agents/reviewer.toml"
        adapter.parent.mkdir(parents=True)
        adapter.write_text('name = "custom"\n', encoding="utf-8")
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 2)
        self.assertIn(".codex/agents/reviewer.toml", result.stderr)
        self.assertEqual(adapter.read_text(encoding="utf-8"), 'name = "custom"\n')
        self.assertFalse((self.project / ".agents/skills/code-review").exists())

    def test_force_backs_up_existing_codex_adapter(self):
        adapter = self.project / ".codex/agents/reviewer.toml"
        adapter.parent.mkdir(parents=True)
        adapter.write_text('name = "custom"\n', encoding="utf-8")
        result = self.install("--agent", "codex", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(adapter.read_bytes(), CODEX_ADAPTER.read_bytes())
        backups = list(adapter.parent.glob("reviewer.toml.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), 'name = "custom"\n')

    def test_existing_skill_directory_is_protected(self):
        skill = self.project / ".claude/skills/code-review"
        skill.mkdir(parents=True)
        (skill / "custom.txt").write_text("user file\n", encoding="utf-8")
        result = self.install("--agent", "claude-code")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".claude/agents/reviewer.md").exists())
        self.assertEqual((skill / "custom.txt").read_text(encoding="utf-8"), "user file\n")

    def test_dry_run_writes_nothing(self):
        result = self.install("--agent", "both", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would create .agents/skills/code-review", result.stdout)
        self.assertIn("would create .codex/agents/reviewer.toml", result.stdout)
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".codex").exists())

    def test_json_output_and_config_toml_untouched(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "keep-me"\n', encoding="utf-8")
        result = self.install("--agent", "codex", "--json", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["actions"]), 2)
        self.assertEqual(config.read_text(encoding="utf-8"), 'model = "keep-me"\n')

    @unittest.skipUnless(os.environ.get("CODE_REVIEW_TEST_BASH"), "Bash is required")
    def test_shell_wrapper_delegates_to_python(self):
        result = subprocess.run(
            [os.environ["CODE_REVIEW_TEST_BASH"], str(ROOT / "scripts/install"),
             "--agent", "codex", "--project", str(self.project)],
            cwd=ROOT, env=self.environment, capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".codex/agents/reviewer.toml").is_file())


if __name__ == "__main__":
    unittest.main()
