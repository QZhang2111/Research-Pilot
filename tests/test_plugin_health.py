import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.plugin_health import inspect_plugin


class PluginHealthTests(unittest.TestCase):
    def test_inspect_plugin_reports_health_and_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                json.dumps({"name": "research-pilot", "version": "0.1.0"}) + "\n"
            )
            (root / "commands").mkdir()
            (root / "commands" / "research-dashboard.md").write_text("# /research-dashboard\n")
            (root / "tools").mkdir()
            (root / "tools" / "research_browser_server.py").write_text("# server\n")

            health = inspect_plugin(root)

        self.assertEqual(health["version"], "0.1.0")
        self.assertTrue(health["command_files"]["research-dashboard"])
        self.assertTrue(health["dashboard_fallback_available"])
        self.assertEqual(health["commands_visible"], "unknown")
        self.assertIn("install.sh --update", health["update_command"])

    def test_skill_links_accept_installed_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "plugin"
            root.mkdir()
            home = Path(tmp) / "home"
            skills = home / ".agents" / "skills"
            (skills / "research-pilot").mkdir(parents=True)
            (skills / "research-pilot-first-run").mkdir()

            with patch.dict(os.environ, {"HOME": str(home)}):
                health = inspect_plugin(root)

        self.assertTrue(health["skill_links"]["research-pilot"])
        self.assertTrue(health["skill_links"]["research-pilot-first-run"])

    def test_helper_bin_uses_rp_bin_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "plugin"
            root.mkdir()
            home = Path(tmp) / "home"
            bin_dir = Path(tmp) / "custom-bin"
            bin_dir.mkdir()
            (bin_dir / "research-pilot-init").write_text("#!/usr/bin/env python3\n")

            with patch.dict(os.environ, {"HOME": str(home), "RP_BIN_DIR": str(bin_dir)}):
                health = inspect_plugin(root)

        self.assertTrue(health["helper_bins"]["research-pilot-init"])

    def test_prompt_links_report_codex_prompt_command_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "plugin"
            root.mkdir()
            home = Path(tmp) / "home"
            prompts = home / ".codex" / "prompts"
            prompts.mkdir(parents=True)
            (prompts / "research-init.md").write_text("# /research-init\n")
            (prompts / "research-dashboard.md").write_text("# /research-dashboard\n")

            with patch.dict(os.environ, {"HOME": str(home), "RP_CODEX_PROMPTS_DIR": str(prompts)}):
                health = inspect_plugin(root)

        self.assertTrue(health["prompt_links"]["research-init"])
        self.assertTrue(health["prompt_links"]["research-dashboard"])


if __name__ == "__main__":
    unittest.main()
