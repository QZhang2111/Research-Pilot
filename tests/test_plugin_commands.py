import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path

from tools.research_pilot_init import main as research_pilot_init_main


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
        self.assertIn("examples/workspaces", text)
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

    def test_related_work_lineage_skill_and_workflow_exist(self) -> None:
        skill = REPO / "skills" / "related-work-lineage" / "SKILL.md"
        workflow = REPO / "templates" / "workspace" / "wiki" / "_system" / "workflows" / "related-work-lineage.md"
        router = REPO / "skills" / "research-pilot" / "SKILL.md"
        self.assertTrue(skill.exists())
        self.assertTrue(workflow.exists())
        skill_text = skill.read_text(encoding="utf-8")
        workflow_text = workflow.read_text(encoding="utf-8")
        router_text = router.read_text(encoding="utf-8")
        self.assertIn("paper-only", skill_text)
        self.assertIn('--direction "$DIRECTION"', skill_text)
        self.assertIn('--baseline-paper "$BASELINE"', skill_text)
        self.assertIn("ask the user to narrow or split maps", skill_text)
        self.assertIn("exclude low-signal follow-ups", skill_text)
        self.assertIn("must not append graph events", workflow_text)
        self.assertIn("ask the user to narrow or split maps", workflow_text)
        self.assertIn("exclude low-signal follow-ups", workflow_text)
        self.assertRegex(
            router_text,
            re.compile(r"related-work route map.*related-work-lineage", re.S),
        )
        self.assertIn("Do not use `project-evidence-synthesis` for this intent", router_text)
        self.assertIn("broad direction", router_text)
        self.assertIn("candidate technical routes", router_text)

    def test_related_work_lineage_workflow_copies_into_initialized_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            with contextlib.redirect_stdout(io.StringIO()):
                result = research_pilot_init_main([str(workspace), "--no-git"])

            workflow = workspace / "wiki" / "_system" / "workflows" / "related-work-lineage.md"
            self.assertEqual(result, 0)
            self.assertTrue(workflow.exists())
            self.assertIn("must not append graph events", workflow.read_text(encoding="utf-8"))

    def test_docs_explain_default_demo_project_and_no_demo_option(self) -> None:
        install = (REPO / "docs" / "guides" / "install.md").read_text(encoding="utf-8")
        dashboard = (REPO / "docs" / "guides" / "dashboard.md").read_text(encoding="utf-8")
        workspace = (REPO / "docs" / "guides" / "workspace.md").read_text(encoding="utf-8")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for text in [install, dashboard, workspace, readme]:
            self.assertIn("DemoVisualAffordance", text)
        self.assertIn("--no-demo", install)
        self.assertIn("--no-demo", workspace)
        self.assertIn("research-pilot.db", workspace)
        self.assertIn("project_id", workspace)


if __name__ == "__main__":
    unittest.main()
