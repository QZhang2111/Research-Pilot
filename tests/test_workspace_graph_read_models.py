import json
import shutil
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance
from tools.research_browser_server import handle_workspace_graph_request
from tools.workspace_graph_read_models import build_workspace_graph_model


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"


class WorkspaceGraphReadModelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "example-workspace"
        shutil.copytree(DEMO_ROOT, self.root)
        initialize_dataset(self.root)
        import_demo_visual_affordance(self.root, reset=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_understanding_project_overview_contract(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        self.assertEqual("workspace-graph-v1", model["schema_version"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertEqual(PROJECT_ID, model["project_id"])
        self.assertEqual("understanding", model["mode"])
        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertEqual("Questions", model["inspector"]["title"])
        self.assertTrue(any(node["entity_type"] == "question" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "claim" for node in model["canvas"]["nodes"]))
        question_section = next(section for section in model["inspector"]["sections"] if section["kind"] == "question_list")
        self.assertTrue(any(item["local_id"] == "Q1" for item in question_section["items"]))
        c2 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "C2")
        self.assertEqual("claim:C2", c2["id"])
        self.assertEqual("project:DemoVisualAffordance:C2", c2["db_id"])
        self.assertEqual({"mode": "understanding", "layer": "claim_focus", "focus_id": "claim:C2"}, c2["drill"])

    def test_understanding_question_selection_stays_on_project_overview(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
            selected_id="question:Q1",
        )

        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("question_detail", model["inspector"]["kind"])
        self.assertEqual("question:Q1", model["selected_id"])
        self.assertTrue(any(section["kind"] == "linked_claims" for section in model["inspector"]["sections"]))

    def test_understanding_claim_focus_contract(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        self.assertEqual("claim_focus", model["layer"])
        self.assertEqual("claim:C2", model["focus_id"])
        self.assertEqual("claim_detail", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "evidence" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "warrant" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "limitation" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "source" for node in model["canvas"]["nodes"]))

    def test_understanding_claim_focus_canvas_contains_only_focused_claim(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        claim_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "claim"]
        self.assertEqual(["claim:C2"], [node["id"] for node in claim_nodes])

        supporting_claims = next(
            section for section in model["inspector"]["sections"] if section["kind"] == "claim"
        )
        self.assertTrue(any(item["id"] == "claim:C0" for item in supporting_claims["items"]))

    def test_understanding_claim_focus_argument_atoms_are_terminal(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        terminal_nodes = [
            node for node in model["canvas"]["nodes"]
            if node["entity_type"] in {"evidence", "warrant", "limitation"}
        ]
        self.assertTrue(terminal_nodes)
        self.assertTrue(all(not node.get("drill") for node in terminal_nodes))
        self.assertTrue(all(not node.get("inspector") for node in terminal_nodes))

    def test_understanding_paper_focus_contract(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="paper_focus",
            focus_id="claim:C2",
            selected_id="source:paper:do2017-affordancenet",
        )

        self.assertEqual("paper_focus", model["layer"])
        self.assertEqual("claim:C2", model["focus_id"])
        self.assertEqual("source:paper:do2017-affordancenet", model["selected_id"])
        self.assertEqual("paper_layer", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "paper_claim" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "project_claim_anchor" for node in model["canvas"]["nodes"]))

    def test_literature_overview_contract(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")

        self.assertEqual("literature", model["mode"])
        self.assertEqual("literature_overview", model["layer"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "literature_lane" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "source" for node in model["canvas"]["nodes"]))
        self.assertTrue(all(len(node["label"]) <= 120 for node in model["canvas"]["nodes"]))

    def test_experiments_evaluation_overview_uses_settings_not_claims(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("experiments", model["mode"])
        self.assertEqual("evaluation_overview", model["layer"])
        self.assertEqual("Evaluation Settings", model["inspector"]["title"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertEqual({"evaluation_setting"}, entity_types)
        setting_labels = " ".join(node["label"] for node in model["canvas"]["nodes"])
        self.assertIn("AGD20K", setting_labels)
        self.assertIn("UMD", setting_labels)
        self.assertNotIn("C2", setting_labels)

    def test_experiments_setting_focus_excludes_run_nodes(self):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        setting_id = next(node["id"] for node in overview["canvas"]["nodes"] if "AGD20K" in node["label"])

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_setting_focus",
            focus_id=setting_id,
        )

        self.assertEqual("evaluation_setting_focus", model["layer"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertIn("evaluation_setting", entity_types)
        self.assertIn("dataset", entity_types)
        self.assertIn("benchmark", entity_types)
        self.assertIn("metric_family", entity_types)
        self.assertIn("experiment", entity_types)
        self.assertNotIn("run", entity_types)

    def test_experiments_design_focus_and_run_selection(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="experiment_design_focus",
            focus_id="experiment:EXP3",
            selected_id="run:RUN3",
        )

        self.assertEqual("experiment_design_focus", model["layer"])
        self.assertEqual("experiment:EXP3", model["focus_id"])
        self.assertEqual("run:RUN3", model["selected_id"])
        self.assertEqual("run_detail", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "run" for node in model["canvas"]["nodes"]))
        self.assertFalse(any(node["entity_type"] == "evaluation_setting" for node in model["canvas"]["nodes"]))
        impact = next(section for section in model["inspector"]["sections"] if section["kind"] == "project_understanding_impact")
        self.assertTrue(any(item["target_id"] == "claim:C4" for item in impact["items"]))

    def test_invalid_layer_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="run_detail")

    def test_workspace_graph_handler_returns_json(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=evaluation_overview",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-v1", data["schema_version"])
        self.assertEqual("experiments", data["mode"])
        self.assertEqual("evaluation_overview", data["layer"])

    def test_workspace_graph_handler_rejects_invalid_layer(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=run_detail",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("unknown workspace graph layer", data["message"])


if __name__ == "__main__":
    unittest.main()
