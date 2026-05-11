import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class PluginCommandTests(unittest.TestCase):
    def test_research_init_command_exists(self) -> None:
        command = REPO / "commands" / "research-init.md"
        text = command.read_text()

        self.assertIn("description:", text)
        self.assertIn("# /research-init", text)
        self.assertIn("research_pilot_init.py", text)
        self.assertIn("research-pilot-first-run", text)
        self.assertNotIn("/Users/" + "qing", text)
        self.assertNotIn("Personal" + "ResearchWiki", text)

    def test_readme_uses_agent_command_as_primary_init_path(self) -> None:
        text = (REPO / "README.md").read_text()
        quick_start = text.split("## 🚀 Quick Start", 1)[1].split("## 🧪 What You Can Ask", 1)[0]

        self.assertIn("/research-init ~/Research/MyResearchWiki", quick_start)
        self.assertRegex(quick_start, re.compile(r"Manual fallback:.*research-pilot-init", re.S))
        self.assertNotIn("python3 tools/research_pilot_init.py", quick_start)


if __name__ == "__main__":
    unittest.main()
