import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.research_dataset import dataset_initialized
from tools.research_dataset_read_models import build_project_summary_model, project_exists_in_dataset
from tools.related_work_lineage_cli import validate_lineage_map
from tools.research_pilot_init import main as research_pilot_init_main


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "workspaces"
PROJECT = DEMO / "wiki" / "projects" / "DemoVisualAffordance"
LINEAGE = PROJECT / "literature-rounds" / "demo-affordance-lineage" / "related-work-lineage.json"
EXPERIMENTS = PROJECT / "experiments" / "experiments.json"


class DemoProjectTest(unittest.TestCase):
    def test_demo_workspace_contains_expected_files(self) -> None:
        expected = [
            DEMO / "AGENTS.md",
            DEMO / "research-pilot.db",
            DEMO / "wiki" / "index.md",
            DEMO / "wiki" / "log.md",
            DEMO / ".research-pilot" / "config.example.toml",
            PROJECT / "overview.md",
            PROJECT / "project-query-pack.md",
            PROJECT / "project-understanding-graph.md",
            PROJECT / "decisions.md",
            LINEAGE,
            LINEAGE.with_suffix(".md"),
            EXPERIMENTS,
            DEMO / "wiki" / "graphs" / "events" / "projects" / "DemoVisualAffordance.jsonl",
            DEMO / "wiki" / "understanding" / "events" / "DemoVisualAffordance.jsonl",
        ]
        for path in expected:
            self.assertTrue(path.exists(), str(path))
        self.assertFalse((DEMO / "demo-visual-affordance").exists())
        self.assertTrue(dataset_initialized(DEMO))
        self.assertTrue(project_exists_in_dataset(DEMO, "DemoVisualAffordance"))
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
            "/tmp/",
            "/private/tmp",
        ]
        forbidden_suffixes = {".pdf", ".sqlite", ".db"}
        allowed_db = (DEMO / "research-pilot.db").resolve()
        for path in DEMO.rglob("*"):
            self.assertNotEqual(path.name, ".dashboard")
            self.assertNotIn("wiki/graphs/snapshots", path.as_posix())
            if path.is_file():
                if path.resolve() != allowed_db:
                    self.assertNotIn(path.suffix.lower(), forbidden_suffixes, str(path))
                else:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden_text:
                    self.assertNotIn(token, text, f"{token} found in {path}")

    def test_demo_lineage_validates(self) -> None:
        payload = json.loads(LINEAGE.read_text(encoding="utf-8"))
        result = validate_lineage_map(payload)
        self.assertTrue(result["valid"], result)
        self.assertEqual(payload["project"], "DemoVisualAffordance")
        self.assertGreaterEqual(result["paper_count"], 6)
        self.assertLessEqual(result["paper_count"], 20)
        self.assertIn(
            "https://arxiv.org/abs/2602.20501",
            payload["route_narrowing"]["selected_anchor_papers"],
        )

    def test_demo_dashboard_index_exposes_project_lineage_and_demo_flag(self) -> None:
        index = build_index(DEMO)
        project = next(item for item in index["projects"] if item["id"] == "DemoVisualAffordance")
        self.assertTrue(project["demo"])
        self.assertEqual(project["title"], "Demo Visual Affordance")
        self.assertEqual(len(index["lineage_maps"]), 1)
        self.assertEqual(index["lineage_maps"][0]["project"], "DemoVisualAffordance")

    def test_demo_experiments_model_contains_design_and_imported_evidence(self) -> None:
        from tools.experiment_store import build_project_experiments

        model = build_project_experiments(DEMO, "DemoVisualAffordance")

        self.assertEqual(model["schema_version"], "experiments-v1")
        self.assertEqual(model["project_id"], "DemoVisualAffordance")
        self.assertGreaterEqual(len(model["experiments"]), 1)
        self.assertGreaterEqual(len(model["runs"]), 1)
        experiment = next(item for item in model["experiments"] if item["id"] == "EXP1")
        self.assertIn("AGD20K", experiment["benchmark"])
        self.assertIn("mIoU", experiment["metrics"])
        self.assertIn("C4", experiment["linked_claims"])
        run = next(item for item in model["runs"] if item["id"] == "RUN1")
        self.assertEqual(run["experiment_id"], "EXP1")
        self.assertEqual(run["evidence_type"], "imported_paper_evidence")
        self.assertIn("not reproduced", " ".join(run["weaknesses"]).lower())
        artifact = run["artifacts"][0]
        artifact_path = DEMO / artifact["path_or_url"]
        self.assertTrue(artifact_path.exists(), str(artifact_path))
        self.assertTrue(artifact_path.resolve().is_relative_to(DEMO.resolve()), str(artifact_path))

    def test_demo_understanding_event_builds_project_understanding(self) -> None:
        from tools.understanding_store import build_project_understanding

        model = build_project_understanding(DEMO, "DemoVisualAffordance", generated_at="2026-05-23T00:00:00Z")

        self.assertEqual(model["schema_version"], "project-understanding-v1")
        self.assertEqual(model["project_id"], "DemoVisualAffordance")
        self.assertGreaterEqual(len(model["sources"]), 1)
        self.assertGreaterEqual(len(model["claims"]), 1)
        self.assertGreaterEqual(len(model["gaps"]), 1)
        self.assertGreaterEqual(len(model["recent_changes"]), 1)
        self.assertGreaterEqual(len(model["next_moves"]), 1)
        self.assertIn("counterfactual", json.dumps(model, ensure_ascii=False).lower())

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
            self.assertIn("Workspace dataset initialized: research-pilot.db", output)
            self.assertIn("Demo project installed and imported: DemoVisualAffordance", output)
            self.assertIn("--no-demo", output)
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
            self.assertTrue((workspace / "research-pilot.db").exists())
            self.assertTrue(dataset_initialized(workspace))
            self.assertTrue(project_exists_in_dataset(workspace, "DemoVisualAffordance"))
            summary = build_project_summary_model(workspace, "DemoVisualAffordance")
            self.assertEqual(summary["source"], "research-pilot.db")
            self.assertEqual(summary["project_id"], "DemoVisualAffordance")
            self.assertEqual(summary["source_count"], 10)
            self.assertEqual(summary["claim_count"], 4)
            self.assertEqual(summary["experiment_count"], 4)

    def test_init_no_demo_skips_demo_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"

            with contextlib.redirect_stdout(io.StringIO()):
                result = research_pilot_init_main(
                    [str(workspace), "--no-git", "--no-demo"]
                )

            self.assertEqual(result, 0)
            self.assertTrue((workspace / "research-pilot.db").exists())
            self.assertTrue(dataset_initialized(workspace))
            self.assertFalse(project_exists_in_dataset(workspace, "DemoVisualAffordance"))
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
