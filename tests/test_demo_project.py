import json
import subprocess
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.related_work_lineage_cli import validate_lineage_map


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
            "/Users/qing",
            "PersonalResearchWiki",
            "CVPR2026_VisualAffordance",
            "Zotero/storage",
            "AAAI2027",
            "submission_affordance.pdf",
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

    # Expected until Task 3 adds dashboard demo metadata to build_index project records.
    @unittest.expectedFailure
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
