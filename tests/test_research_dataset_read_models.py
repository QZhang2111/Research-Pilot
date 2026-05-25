import shutil
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance
from tools.research_dataset_read_models import (
    build_experiments_model,
    build_literature_model,
    build_paper_graph_model,
    build_project_graph_model,
    build_project_summary_model,
    build_recent_updates_model,
    build_source_detail_model,
    build_sources_model,
    project_exists_in_dataset,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"


class ResearchDatasetReadModelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "example-workspace"
        shutil.copytree(DEMO_ROOT, self.root)
        initialize_dataset(self.root)
        import_demo_visual_affordance(self.root, reset=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_project_summary_model_uses_db(self):
        self.assertTrue(project_exists_in_dataset(self.root, PROJECT_ID))

        model = build_project_summary_model(self.root, PROJECT_ID)

        self.assertEqual(PROJECT_ID, model["project_id"])
        self.assertEqual("Demo Visual Affordance", model["title"])
        self.assertGreaterEqual(model["source_count"], 9)
        self.assertGreaterEqual(model["claim_count"], 4)
        self.assertGreaterEqual(model["evidence_count"], 8)
        self.assertEqual(4, model["experiment_count"])
        self.assertEqual("research-pilot.db", model["source"])

    def test_sources_model_includes_paper_understanding_counts(self):
        model = build_sources_model(self.root, PROJECT_ID)

        self.assertEqual(PROJECT_ID, model["project_id"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertGreaterEqual(len(model["sources"]), 9)
        zhang = next(source for source in model["sources"] if source["source_id"] == "paper:zhang2026-geometry-interaction-vfm")
        self.assertEqual("deep_structured", zhang["reading_depth"])
        self.assertIn("paper_understanding_count", zhang)

        detail = build_source_detail_model(self.root, PROJECT_ID, zhang["source_id"])
        self.assertEqual(zhang["source_id"], detail["source_id"])
        self.assertIn("paper_understanding_nodes", detail)
        self.assertIsInstance(detail["paper_understanding_nodes"], list)

    def test_project_graph_model_preserves_qcewl_and_links(self):
        model = build_project_graph_model(self.root, PROJECT_ID)

        kinds = {node["kind"] for node in model["nodes"]}
        self.assertGreaterEqual(kinds, {"question", "claim", "evidence", "warrant", "limitation"})
        self.assertGreaterEqual(len(model["links"]), 6)
        self.assertGreaterEqual(model["counts"]["reasoning"], 7)
        self.assertEqual(0, model["counts"]["translation"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertTrue(any(link["warrant"] and link["limitations"] for link in model["links"]))
        rl1 = next(link for link in model["links"] if link["id"] == "project:DemoVisualAffordance:RL1")
        self.assertEqual("ReasoningLink", rl1["link_type"])
        self.assertEqual("ReasoningLink", rl1["type"])
        self.assertEqual("RL1", rl1["local_id"])
        self.assertEqual(rl1["premises"], rl1["source"])
        self.assertEqual(
            [
                "project:DemoVisualAffordance:E1",
                "project:DemoVisualAffordance:E2",
                "project:DemoVisualAffordance:E5",
                "project:DemoVisualAffordance:E8",
            ],
            rl1["premises"],
        )
        self.assertEqual(["project:DemoVisualAffordance:C2"], rl1["target"])
        self.assertEqual(
            [
                {"role": "from", "node_id": "project:DemoVisualAffordance:E1", "position": 0},
                {"role": "limitation", "node_id": "project:DemoVisualAffordance:L1", "position": 0},
                {"role": "to", "node_id": "project:DemoVisualAffordance:C2", "position": 0},
                {"role": "warrant", "node_id": "project:DemoVisualAffordance:W2", "position": 0},
                {"role": "from", "node_id": "project:DemoVisualAffordance:E2", "position": 1},
                {"role": "limitation", "node_id": "project:DemoVisualAffordance:L3", "position": 1},
                {"role": "from", "node_id": "project:DemoVisualAffordance:E5", "position": 2},
                {"role": "from", "node_id": "project:DemoVisualAffordance:E8", "position": 3},
            ],
            rl1["endpoints"],
        )
        self.assertFalse(any(node["id"] == "C-demo-affordance-prior" for node in model["nodes"]))
        self.assertFalse(any(node["id"].startswith("run:") for node in model["nodes"]))

    def test_paper_graph_model_uses_paper_scope_understanding(self):
        paper_path = self.root / "wiki" / "projects" / PROJECT_ID / "papers" / "do2017-affordancenet" / "index.md"

        model = build_paper_graph_model(self.root, paper_path)

        self.assertEqual("paper-graph-v1", model["schema_version"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertEqual("paper_understanding_from_research_dataset", model["source_boundary"])
        self.assertEqual("do2017-affordancenet", model["paper"])
        self.assertGreaterEqual(len(model["nodes"]), 5)
        self.assertEqual({"question", "claim", "evidence", "warrant", "limitation"}, {node["kind"] for node in model["nodes"]})
        self.assertTrue(any(node["id"] == "P-C1" for node in model["nodes"]))
        self.assertTrue(any("jointly" in node["label"].lower() or "end-to-end" in node["label"].lower() for node in model["nodes"]))
        self.assertEqual(1, len(model["paper_links"]))
        self.assertEqual(["P-E1"], model["paper_links"][0]["premises"])
        self.assertEqual("P-C1", model["paper_links"][0]["target"])
        self.assertEqual("P-W1", model["paper_links"][0]["warrant"])
        self.assertEqual(["P-L1"], model["paper_links"][0]["limitations"])

    def test_experiments_model_preserves_imported_origin_and_metrics(self):
        model = build_experiments_model(self.root, PROJECT_ID)

        self.assertEqual("experiments-v1", model["schema_version"])
        self.assertEqual(4, model["summary"]["total_experiments"])
        self.assertEqual(5, model["summary"]["total_runs"])
        self.assertEqual(5, model["summary"]["imported_evidence_runs"])
        self.assertEqual(0, model["summary"]["local_result_runs"])
        run3 = next(run for run in model["runs"] if run["id"] == "RUN3")
        metrics = {metric["name"]: metric["value"] for metric in run3["metrics"]}
        self.assertEqual("1.493", metrics["KLD"])
        self.assertEqual("0.326", metrics["SIM"])
        self.assertEqual("1.090", metrics["NSS"])

    def test_literature_model_has_lanes_items_and_relations(self):
        model = build_literature_model(self.root, PROJECT_ID)

        self.assertEqual(PROJECT_ID, model["project"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertGreaterEqual(len(model["routes"]), 4)
        self.assertGreaterEqual(len(model["papers"]), 9)
        self.assertGreaterEqual(len(model["explicit_edges"]), 10)

    def test_recent_updates_model_includes_legacy_import_and_understanding_update(self):
        model = build_recent_updates_model(self.root, PROJECT_ID)

        self.assertEqual(PROJECT_ID, model["project_id"])
        self.assertEqual("research-pilot.db", model["source"])
        activity_types = {update["activity_type"] for update in model["updates"]}
        self.assertIn("legacy_import", activity_types)
        self.assertTrue({"check_claim", "deep_update"} & activity_types)
        self.assertTrue(any(update["id"] == "UU-demo-0001" for update in model["updates"]))
        legacy_import = next(update for update in model["updates"] if update["activity_type"] == "legacy_import")
        self.assertIn("audit_event_count", legacy_import)
        self.assertGreater(legacy_import["audit_event_count"], 0)
        self.assertGreaterEqual(len(model["updates"]), 2)

        limited = build_recent_updates_model(self.root, PROJECT_ID, limit=1)
        self.assertEqual(1, len(limited["updates"]))
        self.assertEqual(model["updates"][0], limited["updates"][0])


if __name__ == "__main__":
    unittest.main()
