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
        self.assertIn("project shell", skill.read_text(encoding="utf-8"))
        self.assertIn("project shell", workflow.read_text(encoding="utf-8"))
        self.assertIn("defer", workflow.read_text(encoding="utf-8").lower())

    def test_workspace_init_installs_first_run_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            init_workspace_main([str(root), "--no-git"])

            workflow = root / "wiki" / "_system" / "workflows" / "first-run.md"
            self.assertTrue(workflow.exists())
            self.assertIn("Research Pilot First-Run Protocol", workflow.read_text(encoding="utf-8"))

    def test_workspace_init_installs_program_context_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            init_workspace_main([str(root), "--no-git"])

            overview = root / "wiki" / "program" / "overview.md"
            text = overview.read_text(encoding="utf-8")
            self.assertTrue(overview.exists())
            self.assertIn("agent context layer", text)
            self.assertIn("not graph truth", text)
            self.assertIn("not evidence", text)
            self.assertIn("must not make decisions for the user", text)


if __name__ == "__main__":
    unittest.main()
