import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.research_pilot_init import main as research_pilot_init_main


REPO = Path(__file__).resolve().parents[1]


def readme_quick_start(text: str) -> str:
    start = "## Quick Start"
    end = "## What You Can Ask"
    if start not in text:
        raise AssertionError(f"README missing expected section heading: {start!r}")
    body = text.split(start, 1)[1]
    if end not in body:
        raise AssertionError(f"README missing expected next section prefix: {end!r}")
    return body.split(end, 1)[0]


class PluginCommandTests(unittest.TestCase):
    def test_research_init_command_exists(self) -> None:
        command = REPO / "commands" / "research-init.md"
        text = command.read_text()

        self.assertIn("description:", text)
        self.assertIn("# Research Pilot Init Workflow", text)
        self.assertIn("research_pilot_init.py", text)
        self.assertIn("agent-internal compatibility runbook", text)
        self.assertIn("natural-language intent", text)
        self.assertIn("research-pilot-first-run", text)
        self.assertNotIn("/Users/" + "qing", text)
        self.assertNotIn("Personal" + "ResearchWiki", text)

    def test_readme_uses_chat_first_as_primary_init_path(self) -> None:
        text = (REPO / "README.md").read_text()
        quick_start = readme_quick_start(text)

        self.assertIn("Use Research Pilot to track this project.", quick_start)
        self.assertIn("local workspace", quick_start.lower())
        self.assertIn("research-pilot.db", quick_start)
        self.assertNotIn("Use Research Pilot to initialize", quick_start)
        self.assertNotIn("Manual fallback", quick_start)
        self.assertNotIn("research-pilot-init", quick_start)
        self.assertNotIn("human-gated graph update", quick_start)
        self.assertNotIn("do not register new top-level slash commands", quick_start)

    def test_research_dashboard_command_exists(self) -> None:
        command = REPO / "commands" / "research-dashboard.md"
        text = command.read_text()

        self.assertIn("description:", text)
        self.assertIn("# Research Pilot Dashboard Workflow", text)
        self.assertIn("agent-internal compatibility runbook", text)
        self.assertIn("natural-language intent", text)
        self.assertIn("research_browser_server.py", text)
        self.assertIn("examples/workspaces", text)
        self.assertIn("plugin_health.py", text)
        self.assertIn("http://127.0.0.1:", text)
        self.assertIn("open \"$URL\"", text)
        self.assertNotIn("/Users/" + "qing", text)
        self.assertNotIn("Personal" + "ResearchWiki", text)

    def test_readme_uses_chat_first_as_primary_dashboard_path(self) -> None:
        text = (REPO / "README.md").read_text()
        quick_start = readme_quick_start(text)

        self.assertIn("Open the Research Pilot dashboard.", quick_start)
        self.assertIn("agent starts or reuses the local dashboard server", quick_start)
        self.assertNotIn("Slash command visibility is not required", quick_start)
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
        self.assertIn("map_literature", router_text)
        self.assertIn("related-work-lineage", router_text)
        self.assertIn("paper-only", router_text)
        self.assertIn("Do not append graph events", router_text)

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
