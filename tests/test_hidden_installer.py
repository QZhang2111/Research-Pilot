import os
import shutil
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
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _make_remote_repo(self, skills: list[str]) -> None:
        self.remote.mkdir()
        (self.remote / "skills").mkdir()
        (self.remote / ".codex-plugin").mkdir()
        (self.remote / "tools").mkdir()
        (self.remote / ".codex-plugin" / "plugin.json").write_text('{"name":"research-pilot","skills":"./skills/"}\n')
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
        self._run_install()

        repo_dir = self.home / ".research-pilot" / "repo"
        skill_link = self.home / ".agents" / "skills" / "alpha-skill"
        plugin_link = self.home / ".research-pilot-plugin"
        init_link = self.home / ".research-pilot" / "bin" / "research-pilot-init"

        self.assertTrue((repo_dir / ".git").exists())
        self.assertEqual(Path(os.readlink(skill_link)), repo_dir / "skills" / "alpha-skill")
        self.assertEqual(Path(os.readlink(plugin_link)), repo_dir)
        self.assertEqual(Path(os.readlink(init_link)), repo_dir / "tools" / "research_pilot_init.py")

    def test_codex_install_uses_hidden_checkout_not_current_worktree(self) -> None:
        self._run_install("codex")

        skill_link = self.home / ".agents" / "skills" / "alpha-skill"
        self.assertTrue(skill_link.is_symlink())
        self.assertNotIn(str(REPO), os.readlink(skill_link))

    def test_update_pulls_hidden_checkout_and_relinks_skills(self) -> None:
        self._run_install("codex")
        self._add_remote_skill("beta-skill")

        self._run_install("--update")

        beta_link = self.home / ".agents" / "skills" / "beta-skill"
        self.assertEqual(Path(os.readlink(beta_link)), self.home / ".research-pilot" / "repo" / "skills" / "beta-skill")

    def test_uninstall_removes_links_but_keeps_hidden_checkout(self) -> None:
        self._run_install("codex")

        self._run_install("--uninstall", "codex")

        self.assertFalse((self.home / ".agents" / "skills" / "alpha-skill").exists())
        self.assertFalse((self.home / ".research-pilot-plugin").exists())
        self.assertFalse((self.home / ".research-pilot" / "bin" / "research-pilot-init").exists())
        self.assertTrue((self.home / ".research-pilot" / "repo" / ".git").exists())


if __name__ == "__main__":
    unittest.main()
