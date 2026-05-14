import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.related_work_lineage_cli import validate_lineage_map
from tools.research_pilot_init import main as research_pilot_init_main


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "workspaces" / "demo-visual-affordance"
PROJECT = DEMO / "wiki" / "projects" / "DemoVisualAffordance"
LINEAGE = PROJECT / "literature-rounds" / "demo-affordance-lineage" / "related-work-lineage.json"


class DemoProjectTest(unittest.TestCase):
    def test_demo_workspace_contains_expected_files(self) -> None:
        expected = [
            DEMO / "AGENTS.md",
            DEMO / "wiki" / "index.md",
            DEMO / "wiki" / "log.md",
            DEMO / ".research-pilot" / "config.example.toml",
            PROJECT / "overview.md",
            PROJECT / "project-query-pack.md",
            PROJECT / "project-understanding-graph.md",
            PROJECT / "decisions.md",
            LINEAGE,
            LINEAGE.with_suffix(".md"),
            DEMO / "wiki" / "graphs" / "events" / "projects" / "DemoVisualAffordance.jsonl",
        ]
        for path in expected:
            self.assertTrue(path.exists(), str(path))
        paper_dossiers = sorted((PROJECT / "papers").glob("*/index.md"))
        self.assertGreaterEqual(len(paper_dossiers), 6)
        self.assertLessEqual(len(paper_dossiers), 10)

    def test_demo_tree_has_no_private_or_generated_artifacts(self) -> None:
        forbidden_text = [
            "/Users/" + "qing",
            "Personal" + "ResearchWiki",
            "CVPR" + "2026_VisualAffordance",
            "Zotero/storage",
            "AAAI2027",
            "submission_" + "affordance.pdf",
        ]
        forbidden_suffixes = {".pdf", ".sqlite", ".db"}
        for path in DEMO.rglob("*"):
            self.assertNotEqual(path.name, ".dashboard")
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), forbidden_suffixes, str(path))
                text = path.read_text(encoding="utf-8")
                for token in forbidden_text:
                    self.assertNotIn(token, text, f"{token} found in {path}")

    def test_demo_lineage_validates(self) -> None:
        payload = json.loads(LINEAGE.read_text(encoding="utf-8"))
        result = validate_lineage_map(payload)
        self.assertTrue(result["valid"], result)
        self.assertEqual(payload["project"], "DemoVisualAffordance")
        self.assertGreaterEqual(result["paper_count"], 6)
        self.assertLessEqual(result["paper_count"], 10)

    def test_demo_dashboard_index_exposes_project_lineage_and_demo_flag(self) -> None:
        index = build_index(DEMO)
        project = next(item for item in index["projects"] if item["id"] == "DemoVisualAffordance")
        self.assertTrue(project["demo"])
        self.assertEqual(project["title"], "Demo Visual Affordance")
        self.assertEqual(len(index["lineage_maps"]), 1)
        self.assertEqual(index["lineage_maps"][0]["project"], "DemoVisualAffordance")

    def test_demo_graph_events_validate(self) -> None:
        completed = subprocess.run(
            [
                "python3",
                "tools/graph_validate.py",
                "--repo",
                str(DEMO),
                "--project",
                "DemoVisualAffordance",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_init_copies_demo_visual_affordance_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = research_pilot_init_main([str(workspace), "--no-git"])

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("Demo project installed: DemoVisualAffordance", output)
            self.assertIn(
                "Delete it by removing wiki/projects/DemoVisualAffordance and "
                "wiki/graphs/events/projects/DemoVisualAffordance.jsonl.",
                output,
            )
            self.assertTrue(
                (
                    workspace
                    / "wiki"
                    / "projects"
                    / "DemoVisualAffordance"
                    / "overview.md"
                ).exists()
            )
            self.assertTrue(
                (
                    workspace
                    / "wiki"
                    / "graphs"
                    / "events"
                    / "projects"
                    / "DemoVisualAffordance.jsonl"
                ).exists()
            )

    def test_init_no_demo_skips_demo_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            with contextlib.redirect_stdout(io.StringIO()):
                result = research_pilot_init_main(
                    [str(workspace), "--no-git", "--no-demo"]
                )

            self.assertEqual(result, 0)
            self.assertFalse(
                (workspace / "wiki" / "projects" / "DemoVisualAffordance").exists()
            )
            self.assertFalse(
                (
                    workspace
                    / "wiki"
                    / "graphs"
                    / "events"
                    / "projects"
                    / "DemoVisualAffordance.jsonl"
                ).exists()
            )

    def test_init_preserves_demo_edits_unless_overwrite_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            overview = (
                workspace
                / "wiki"
                / "projects"
                / "DemoVisualAffordance"
                / "overview.md"
            )

            with contextlib.redirect_stdout(io.StringIO()):
                research_pilot_init_main([str(workspace), "--no-git"])
            overview.write_text("local edit\n", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                research_pilot_init_main([str(workspace), "--no-git"])
            self.assertEqual(overview.read_text(encoding="utf-8"), "local edit\n")

            with contextlib.redirect_stdout(io.StringIO()):
                research_pilot_init_main([str(workspace), "--no-git", "--overwrite"])
            self.assertEqual(
                overview.read_text(encoding="utf-8"),
                (PROJECT / "overview.md").read_text(encoding="utf-8"),
            )
