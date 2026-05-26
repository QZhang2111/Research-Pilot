import os
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class HiddenInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.remote = self.root / "remote"
        self._make_remote_repo(["alpha-skill"])
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "RP_REPO_URL": str(self.remote),
                "RP_DIR": str(self.home / ".research-pilot" / "repo"),
                "RP_PLUGIN_LINK": str(self.home / ".research-pilot-plugin"),
                "RP_BIN_DIR": str(self.home / ".research-pilot" / "bin"),
                "RP_MARKETPLACE_PATH": str(self.home / ".agents" / "plugins" / "marketplace.json"),
                "RP_CATALOG_LINK": str(self.home / "plugins" / "research-pilot"),
                "RP_CODEX_PROMPTS_DIR": str(self.home / ".codex" / "prompts"),
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _make_remote_repo(self, skills: list[str]) -> None:
        self.remote.mkdir()
        (self.remote / "skills").mkdir()
        (self.remote / ".codex-plugin").mkdir()
        (self.remote / "tools").mkdir()
        (self.remote / "commands").mkdir()
        (self.remote / ".codex-plugin" / "plugin.json").write_text('{"name":"research-pilot","skills":"./skills/"}\n')
        (self.remote / "commands" / "research-init.md").write_text("# /research-init\n")
        (self.remote / "commands" / "research-dashboard.md").write_text("# /research-dashboard\n")
        init = self.remote / "tools" / "research_pilot_init.py"
        init.write_text("#!/usr/bin/env python3\nprint('init')\n")
        init.chmod(init.stat().st_mode | stat.S_IXUSR)
        for skill in skills:
            skill_dir = self.remote / "skills" / skill
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"---\nname: {skill}\n---\n")
        subprocess.run(["git", "init", "-q"], cwd=self.remote, check=True)
        subprocess.run(["git", "add", "."], cwd=self.remote, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "init"],
            cwd=self.remote,
            check=True,
        )

    def _add_remote_skill(self, skill: str) -> None:
        skill_dir = self.remote / "skills" / skill
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\nname: {skill}\n---\n")
        subprocess.run(["git", "add", "."], cwd=self.remote, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", f"add {skill}"],
            cwd=self.remote,
            check=True,
        )

    def _run_install(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(REPO / "install.sh"), *args],
            cwd=REPO,
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_no_arg_install_clones_hidden_repo_and_links_codex_skills(self) -> None:
        legacy_catalog_link = self.home / ".agents" / "plugins" / "research-pilot"
        legacy_catalog_link.parent.mkdir(parents=True)
        legacy_catalog_link.symlink_to(self.home / ".research-pilot" / "repo")
        legacy_prompt_dir = self.home / ".codex" / "prompts"
        legacy_prompt_dir.mkdir(parents=True)
        (legacy_prompt_dir / "research-init.md").symlink_to(self.remote / "commands" / "research-init.md")
        (legacy_prompt_dir / "research-dashboard.md").symlink_to(self.remote / "commands" / "research-dashboard.md")

        result = self._run_install()

        repo_dir = self.home / ".research-pilot" / "repo"
        skill_link = self.home / ".agents" / "skills" / "alpha-skill"
        plugin_link = self.home / ".research-pilot-plugin"
        catalog_link = self.home / "plugins" / "research-pilot"
        init_link = self.home / ".research-pilot" / "bin" / "research-pilot-init"
        prompt_init = self.home / ".codex" / "prompts" / "research-init.md"
        prompt_dashboard = self.home / ".codex" / "prompts" / "research-dashboard.md"

        self.assertTrue((repo_dir / ".git").exists())
        self.assertEqual(Path(os.readlink(skill_link)), repo_dir / "skills" / "alpha-skill")
        self.assertEqual(Path(os.readlink(plugin_link)), repo_dir)
        self.assertEqual(Path(os.readlink(catalog_link)), repo_dir)
        self.assertFalse(legacy_catalog_link.is_symlink())
        self.assertEqual(Path(os.readlink(init_link)), repo_dir / "tools" / "research_pilot_init.py")
        self.assertFalse(prompt_init.exists())
        self.assertFalse(prompt_dashboard.exists())
        self.assert_marketplace_entry_installed()
        self.assertIn("Health check", result.stdout)
        self.assertIn("plugin_health.py", result.stdout)
        normalized = " ".join(result.stdout.split())
        self.assertIn("Next step:", result.stdout)
        self.assertIn("Restart Codex", normalized)
        self.assertIn("Use Research Pilot to track my research project.", normalized)
        self.assertIn("Interface: chat with the agent", normalized)
        self.assertIn("Compatibility helper kept for agents and troubleshooting", normalized)
        self.assertIn(f"{self.home}/.research-pilot/bin/research-pilot-init", normalized)
        self.assertIn("No Research Pilot command memorization is required", normalized)
        self.assertIn("Legacy /research-* prompt links are removed", normalized)
        self.assertIn(f"{self.home}/.codex/prompts", normalized)
        self.assertNotIn("Initialize a private workspace:", result.stdout)

    def test_codex_install_uses_hidden_checkout_not_current_worktree(self) -> None:
        self._run_install("codex")

        skill_link = self.home / ".agents" / "skills" / "alpha-skill"
        self.assertTrue(skill_link.is_symlink())
        self.assertNotIn(str(REPO), os.readlink(skill_link))

    def test_update_pulls_hidden_checkout_and_relinks_skills(self) -> None:
        self._run_install("codex")
        self._add_remote_skill("beta-skill")

        result = self._run_install("--update")

        beta_link = self.home / ".agents" / "skills" / "beta-skill"
        self.assertEqual(Path(os.readlink(beta_link)), self.home / ".research-pilot" / "repo" / "skills" / "beta-skill")
        prompt_dashboard = self.home / ".codex" / "prompts" / "research-dashboard.md"
        self.assertFalse(prompt_dashboard.exists())
        self.assertIn("Health check", result.stdout)
        self.assertIn("plugin_health.py", result.stdout)
        self.assertIn("restart", result.stdout.lower())

    def test_uninstall_removes_links_but_keeps_hidden_checkout(self) -> None:
        self._run_install("codex")

        self._run_install("--uninstall", "codex")

        self.assertFalse((self.home / ".agents" / "skills" / "alpha-skill").exists())
        self.assertFalse((self.home / ".research-pilot-plugin").exists())
        self.assertFalse((self.home / "plugins" / "research-pilot").exists())
        self.assertFalse((self.home / ".research-pilot" / "bin" / "research-pilot-init").exists())
        self.assertFalse((self.home / ".codex" / "prompts" / "research-init.md").exists())
        self.assertFalse((self.home / ".codex" / "prompts" / "research-dashboard.md").exists())
        self.assertTrue((self.home / ".research-pilot" / "repo" / ".git").exists())
        self.assert_marketplace_entry_absent()

    def assert_marketplace_entry_installed(self) -> None:
        path = self.home / ".agents" / "plugins" / "marketplace.json"
        data = json.loads(path.read_text())
        entries = [item for item in data["plugins"] if item["name"] == "research-pilot"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/research-pilot"})
        self.assertEqual(entry["policy"]["installation"], "INSTALLED_BY_DEFAULT")
        self.assertEqual(entry["category"], "Productivity")

    def assert_marketplace_entry_absent(self) -> None:
        path = self.home / ".agents" / "plugins" / "marketplace.json"
        data = json.loads(path.read_text())
        self.assertFalse([item for item in data["plugins"] if item["name"] == "research-pilot"])


if __name__ == "__main__":
    unittest.main()
