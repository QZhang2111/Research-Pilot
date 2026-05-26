import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def readme_quick_start(text: str) -> str:
    start = "## Quick Start"
    end = "## What You Can Ask"
    if start not in text:
        raise AssertionError(f"README missing expected section heading: {start!r}")
    body = text.split(start, 1)[1]
    if end not in body:
        raise AssertionError(f"README missing expected next section prefix: {end!r}")
    return body.split(end, 1)[0]


class ChatFirstWorkflowSurfaceTests(unittest.TestCase):
    def test_readme_leads_with_chat_first_local_memory(self) -> None:
        text = read("README.md")
        opening = text.split("## Quick Start", 1)[0]

        self.assertIn("local project memory", opening.lower())
        self.assertIn("read-only dashboard", opening.lower())
        self.assertIn("agent", opening.lower())
        self.assertNotIn("Zotero-first", opening)
        self.assertNotIn("Human-gated", opening)
        self.assertNotIn("D* deltas", opening)

    def test_readme_quick_start_does_not_foreground_helper_commands(self) -> None:
        text = read("README.md")
        quick_start = readme_quick_start(text)

        self.assertIn("Use Research Pilot to track this project.", quick_start)
        self.assertIn("Open the Research Pilot dashboard.", quick_start)
        self.assertNotIn("research-pilot-init", quick_start)
        self.assertNotIn("/research-init", quick_start)
        self.assertNotIn("/research-dashboard", quick_start)
        self.assertNotIn("Manual fallback", quick_start)
        self.assertNotIn("human-gated graph update", quick_start)

    def test_primary_agent_skill_is_intent_router_not_command_catalog(self) -> None:
        text = read("skills/research-pilot/SKILL.md")

        self.assertIn("User-facing interface is chat", text)
        self.assertIn("start_or_track_project", text)
        self.assertIn("open_dashboard", text)
        self.assertIn("strict_review", text)
        self.assertNotIn("## Current Capabilities", text)
        self.assertNotIn("Build generated SQLite graph read models", text)
        self.assertNotIn("Register proposed graph deltas", text)

    def test_first_run_defaults_to_db_project_brief_not_delta(self) -> None:
        skill = read("skills/research-pilot-first-run/SKILL.md")
        workflow = read("templates/workspace/wiki/_system/workflows/first-run.md")

        for text in (skill, workflow):
            self.assertIn("research-pilot.db", text)
            self.assertIn("initial project brief", text.lower())
            self.assertIn("UnderstandingUpdate", text)
            self.assertIn("strict review", text.lower())
            self.assertNotIn("first question, claim, evidence pressure, paper synthesis, or experiment result becomes proposed D*", text)
            self.assertNotIn("First graph update", text)

    def test_workspace_template_presents_db_as_primary_memory(self) -> None:
        text = read("templates/workspace/AGENTS.md")

        self.assertIn("research-pilot.db = primary workspace dataset", text)
        self.assertIn("graph events/deltas = advanced strict review", text)
        self.assertIn("Zotero = optional supported adapter", text)
        self.assertNotIn("Zotero = paper metadata, PDFs, collections, tags, reading status mirror", text)

    def test_workspace_workflows_label_advanced_or_adapter_surfaces(self) -> None:
        update = read("templates/workspace/wiki/_system/workflows/project-understanding-update.md")
        synthesis = read("templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md")
        zotero = read("templates/workspace/wiki/_system/workflows/zotero-source-protocol.md")
        source = read("templates/workspace/wiki/_system/workflows/paper-discovery-intake.md")

        self.assertIn("normal path = workspace dataset / UnderstandingUpdate / project memory", update)
        self.assertIn("Strict-review D* proposals are optional advanced outputs", synthesis)
        self.assertIn("optional supported adapter", zotero.lower())
        self.assertIn("source-agnostic", zotero.lower())
        self.assertIn("without forcing a paper-manager workflow", source)

    def test_gap_discovery_surfaces_are_agent_internal_and_source_agnostic(self) -> None:
        template = read("templates/workspace/wiki/_system/workflows/gap-driven-search.md")
        skill = read("skills/project-gap-discovery/SKILL.md")

        self.assertNotIn("Zotero-first", template)
        self.assertNotIn("Normal paper management remains Zotero-first", template)
        self.assertIn("source-agnostic", template.lower())
        self.assertIn("Zotero = optional adapter", template)

        self.assertNotIn("user-facing discovery command", skill)
        self.assertNotIn("This skill owns the user-facing path", skill)
        self.assertRegex(skill, r"agent/internal transition path|agent-internal command")

    def test_no_user_facing_first_run_copy_promotes_dstar_or_zotero_first(self) -> None:
        user_paths = [
            "README.md",
            "docs/guides/install.md",
            "docs/guides/dashboard.md",
            "docs/guides/workspace.md",
            "docs/guides/source-boundaries.md",
        ]
        forbidden = re.compile(
            r"zotero[-\s]+first|d\s*\*\s*[-\s]*deltas?|human[-\s]+gated[-\s]+graph[-\s]+update|graph event log is the source of truth",
            re.IGNORECASE,
        )
        for path in user_paths:
            with self.subTest(path=path):
                self.assertIsNone(forbidden.search(read(path)))


if __name__ == "__main__":
    unittest.main()
