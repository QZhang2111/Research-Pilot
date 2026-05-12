import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class PluginCommandTests(unittest.TestCase):
    def test_research_init_command_exists(self) -> None:
        command = REPO / "commands" / "research-init.md"
        text = command.read_text()

        self.assertIn("description:", text)
        self.assertIn("# Research Pilot Init Workflow", text)
        self.assertIn("research_pilot_init.py", text)
        self.assertIn("Slash command visibility is not required", text)
        self.assertIn("research-pilot-first-run", text)
        self.assertNotIn("/Users/" + "qing", text)
        self.assertNotIn("Personal" + "ResearchWiki", text)

    def test_readme_uses_chat_first_as_primary_init_path(self) -> None:
        text = (REPO / "README.md").read_text()
        quick_start = text.split("## 🚀 Quick Start", 1)[1].split("## 🧪 What You Can Ask", 1)[0]

        self.assertIn("Use Research Pilot to initialize ~/Research/MyResearchWiki.", quick_start)
        self.assertIn("chat-first", quick_start)
        self.assertIn("do not register new top-level slash commands", quick_start)
        self.assertRegex(quick_start, re.compile(r"Manual fallback:.*research-pilot-init", re.S))
        self.assertNotIn("python3 tools/research_pilot_init.py", quick_start)

    def test_research_dashboard_command_exists(self) -> None:
        command = REPO / "commands" / "research-dashboard.md"
        text = command.read_text()

        self.assertIn("description:", text)
        self.assertIn("# Research Pilot Dashboard Workflow", text)
        self.assertIn("Chat-First Operation", text)
        self.assertIn("research_browser_server.py", text)
        self.assertIn("plugin_health.py", text)
        self.assertIn("http://127.0.0.1:", text)
        self.assertIn("open \"$URL\"", text)
        self.assertNotIn("/Users/" + "qing", text)
        self.assertNotIn("Personal" + "ResearchWiki", text)

    def test_readme_uses_chat_first_as_primary_dashboard_path(self) -> None:
        text = (REPO / "README.md").read_text()
        quick_start = text.split("## 🚀 Quick Start", 1)[1].split("## 🧪 What You Can Ask", 1)[0]

        self.assertIn("Use Research Pilot to open the dashboard for ~/Research/MyResearchWiki.", quick_start)
        self.assertIn("Slash command visibility is not required", quick_start)
        self.assertNotIn("python3 ~/.research-pilot/repo/tools/build_dashboard_index.py", quick_start)


if __name__ == "__main__":
    unittest.main()
