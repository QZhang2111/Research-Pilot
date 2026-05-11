import tempfile
import unittest
from pathlib import Path

from tools.research_pilot_init import main as init_workspace_main


class FirstRunProtocolTest(unittest.TestCase):
    def test_public_repo_contains_first_run_skill_and_workspace_workflow(self):
        skill = Path("skills/research-pilot-first-run/SKILL.md")
        workflow = Path("templates/workspace/wiki/_system/workflows/first-run.md")

        self.assertTrue(skill.exists())
        self.assertTrue(workflow.exists())
        self.assertIn("first project graph update", skill.read_text(encoding="utf-8"))
        self.assertIn("human gate", workflow.read_text(encoding="utf-8"))

    def test_workspace_init_installs_first_run_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            init_workspace_main([str(root), "--no-git"])

            workflow = root / "wiki" / "_system" / "workflows" / "first-run.md"
            self.assertTrue(workflow.exists())
            self.assertIn("Research Pilot First-Run Protocol", workflow.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
