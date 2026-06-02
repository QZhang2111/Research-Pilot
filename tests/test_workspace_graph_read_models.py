import json
import shutil
import tempfile
import unittest
from contextlib import closing
from http import HTTPStatus
from pathlib import Path

from tools.research_dataset import connect_dataset, initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance
from tools.research_browser_server import handle_workspace_graph_request
from tools.workspace_graph_read_models import _paper_dossier_brief, build_workspace_graph_model


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

    def assert_workspace_node_contract(self, node):
        self.assertIn("id", node)
        self.assertIn("entity_type", node)
        self.assertIn("label", node)
        self.assertIn("metadata", node)
        self.assertIn("display", node)
        self.assertIsInstance(node["metadata"], dict)
        self.assertIsInstance(node["display"], dict)
        self.assertIn("tone", node["display"])
        self.assertIn("badges", node["display"])
        self.assertIn("warnings", node["display"])
        self.assertIsInstance(node["display"]["badges"], list)
        self.assertIsInstance(node["display"]["warnings"], list)

    def _arena_id_by_label(self, label):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        matches = [node for node in overview["canvas"]["nodes"] if node["label"] == label]
        self.assertEqual(
            1,
            len(matches),
            f"Expected exactly one evaluation arena node labeled {label!r}; got {[node['label'] for node in overview['canvas']['nodes']]}",
        )
        return matches[0]["id"]

    def _node_id_by_label(self, model, label):
        matches = [node for node in model["canvas"]["nodes"] if node["label"] == label]
        self.assertEqual(
            1,
            len(matches),
            f"Expected exactly one node labeled {label!r}; got {[node['label'] for node in model['canvas']['nodes']]}",
        )
        return matches[0]["id"]

    def _node_by_id(self, model, node_id):
        matches = [node for node in model["canvas"]["nodes"] if node["id"] == node_id]
        self.assertEqual(
            1,
            len(matches),
            f"Expected exactly one canvas node with id {node_id!r}; got {[node['id'] for node in model['canvas']['nodes']]}",
        )
        return matches[0]

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

    def test_workspace_payload_has_no_dashboard_owned_storage_fields(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        self.assertEqual("research-pilot.db", model["source"])
        self.assertNotIn("dashboard_db", model)
        self.assertNotIn("dashboard_state", model)
        self.assertNotIn("mutation", model)

    def test_understanding_question_nodes_do_not_create_question_layer(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
            selected_id="question:Q2",
        )

        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("question_detail", model["inspector"]["kind"])
        self.assertTrue(all(node.get("drill", {}).get("layer") != "question_focus" for node in model["canvas"]["nodes"] if node["entity_type"] == "question"))

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
        self.assertTrue(all(node.get("inspector") == {"selected_id": node["id"]} for node in terminal_nodes))

    def test_understanding_claim_focus_terminal_selection_updates_inspector(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
            selected_id="evidence:E1",
        )

        self.assertEqual("argument_atom_detail", model["inspector"]["kind"])
        self.assertEqual("E1", model["inspector"]["title"])
        self.assertIn("geometric awareness", model["inspector"]["summary"])
        self.assertTrue(any(section["kind"] == "source_refs" for section in model["inspector"]["sections"]))

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
        self.assertEqual("paper_focus", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "paper_claim" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "paper_question" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "paper_evidence" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "project_claim_anchor" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(edge["relation"] == "translation" for edge in model["canvas"]["edges"]))
        self.assertEqual(
            [
                {"label": "Workspace", "mode": "understanding", "layer": "project_overview", "focus_id": ""},
                {"label": "C2", "mode": "understanding", "layer": "claim_focus", "focus_id": "claim:C2", "selected_id": ""},
            ],
            model["breadcrumb"],
        )

    def test_literature_overview_contract(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")

        self.assertEqual("literature", model["mode"])
        self.assertEqual("literature_overview", model["layer"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "literature_lane" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "source" for node in model["canvas"]["nodes"]))
        self.assertTrue(all(len(node["label"]) <= 120 for node in model["canvas"]["nodes"]))
        route_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "literature_lane"]
        paper_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "source"]
        self.assertTrue(all(node["display"]["tone"].startswith("route-") for node in route_nodes))
        self.assertTrue(all(node["metadata"].get("route_key") for node in paper_nodes))
        self.assertTrue(all("sort_year" in node["metadata"] for node in paper_nodes))

    def test_literature_paper_focus_reuses_deep_read_paper_graph(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="literature",
            layer="literature_paper_focus",
            focus_id="source:paper:do2017-affordancenet",
        )

        self.assertEqual("paper_focus", model["inspector"]["kind"])
        self.assertEqual("literature_paper_focus", model["layer"])
        self.assertTrue(any(node["entity_type"] == "paper_question" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "paper_claim" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "paper_evidence" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(edge["relation"] == "supports" for edge in model["canvas"]["edges"]))
        self.assertTrue(any(section["kind"] == "translation_bridge" for section in model["inspector"]["sections"]))

    def test_shared_paper_focus_uses_deep_read_brief_before_raw_nodes(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="literature",
            layer="literature_paper_focus",
            focus_id="source:paper:li2024-ooal",
        )

        self.assertEqual("paper_focus", model["inspector"]["kind"])
        self.assertEqual("One-Shot Open Affordance Learning with Foundation Models", model["inspector"]["title"])
        section_titles = [section["title"] for section in model["inspector"]["sections"]]
        self.assertEqual("Paper Brief", section_titles[0])
        self.assertIn("Paper Argument Nodes", section_titles)
        brief = model["inspector"]["sections"][0]
        brief_labels = [item["label"] for item in brief["items"]]
        self.assertIn("Core Contribution", brief_labels)
        self.assertIn("Evidence Boundary", brief_labels)
        self.assertIn("What Not To Overlearn", brief_labels)
        self.assertTrue(any("not training-free VFM probing" in item["text"] for item in brief["items"]))

    def test_paper_dossier_brief_rejects_locator_escape(self):
        outside = self.root.parent / "outside.md"
        outside.write_text("### Core Contribution\nLeaked brief.\n", encoding="utf-8")

        self.assertEqual([], _paper_dossier_brief(self.root, {"locator": "../outside.md"}))

    def test_literature_paper_focus_without_deep_read_stays_in_literature_mode(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="literature",
            layer="literature_paper_focus",
            focus_id="source:hassanin2018-visual-affordance-survey",
        )

        self.assertEqual("paper_detail", model["inspector"]["kind"])
        self.assertEqual("source:hassanin2018-visual-affordance-survey", model["selected_id"])
        self.assertEqual(
            [
                {"label": "Workspace", "mode": "literature", "layer": "literature_overview", "focus_id": ""},
                {"label": "Literature", "mode": "literature", "layer": "literature_overview", "focus_id": ""},
            ],
            model["breadcrumb"],
        )

    def test_experiments_evaluation_overview_uses_arenas_not_settings(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("experiments", model["mode"])
        self.assertEqual("evaluation_overview", model["layer"])
        self.assertEqual("Evaluation Arenas", model["inspector"]["title"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertEqual({"evaluation_arena"}, entity_types)
        labels = {node["label"] for node in model["canvas"]["nodes"]}
        self.assertEqual(
            {
                "AGD20K Affordance Localization",
                "UMD Geometry / Segmentation Probe",
                "Semantic Assimilation Control",
            },
            labels,
        )
        agd20k = next(node for node in model["canvas"]["nodes"] if node["label"] == "AGD20K Affordance Localization")
        self.assertEqual("2 experiments / 3 runs", agd20k["subtitle"])
        self.assertEqual(
            {"mode": "experiments", "layer": "evaluation_arena_focus", "focus_id": agd20k["id"]},
            agd20k["drill"],
        )
        self.assertTrue(all(not node["id"].startswith("evaluation_setting:") for node in model["canvas"]["nodes"]))
        self.assertTrue(all(node["entity_type"] != "evaluation_setting" for node in model["canvas"]["nodes"]))

    def test_experiments_overview_inspector_surfaces_summary_and_next_moves(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertIn("AGD20K evidence", model["inspector"]["summary"])
        section_kinds = [section["kind"] for section in model["inspector"]["sections"]]
        self.assertIn("evaluation_arena_list", section_kinds)
        self.assertIn("next_move_list", section_kinds)
        next_moves = next(section for section in model["inspector"]["sections"] if section["kind"] == "next_move_list")
        self.assertTrue(any(item.get("linked_experiment") == "EXP3" for item in next_moves["items"]))

    def test_experiments_arena_focus_shows_context_designs_and_runs(self):
        arena_id = self._arena_id_by_label("AGD20K Affordance Localization")

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_arena_focus",
            focus_id=arena_id,
        )

        self.assertEqual("evaluation_arena_focus", model["layer"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertGreaterEqual(entity_types, {"evaluation_arena", "dataset", "benchmark", "metric_family", "experiment", "run"})
        self.assertEqual("arena_detail", model["inspector"]["kind"])
        self.assertEqual("AGD20K Affordance Localization", model["inspector"]["title"])
        run_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "run"]
        self.assertEqual({"run:RUN2", "run:RUN3", "run:RUN4"}, {node["id"] for node in run_nodes})
        self.assertTrue(all(node["metadata"].get("origin_type") == "imported_paper" for node in run_nodes))
        self.assertEqual("Workspace", model["breadcrumb"][0]["label"])
        self.assertEqual("Experiments", model["breadcrumb"][1]["label"])
        self.assertEqual("evaluation_overview", model["breadcrumb"][1]["layer"])

    def test_experiments_old_setting_focus_aliases_to_arena_focus(self):
        arena_id = self._arena_id_by_label("AGD20K Affordance Localization")

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_setting_focus",
            focus_id=arena_id,
        )

        self.assertEqual("evaluation_arena_focus", model["layer"])
        self.assertEqual(arena_id, model["focus_id"])

    def test_experiments_old_setting_focus_id_aliases_to_matching_arena(self):
        legacy_setting_id = "evaluation_setting:agd20k-quantitative-evaluation-umd-qualitative-validation:agd20k-unseen-egocentric-objects-for-kld-sim-nss-umd-categorical-masks-for-qualitative-part-alig:saliency-heatmap-alignment"

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_setting_focus",
            focus_id=legacy_setting_id,
        )

        arena_id = self._arena_id_by_label("AGD20K Affordance Localization")
        self.assertEqual("evaluation_arena_focus", model["layer"])
        self.assertEqual(arena_id, model["focus_id"])
        self.assertEqual("AGD20K Affordance Localization", model["inspector"]["title"])

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
        run3 = self._node_by_id(model, "run:RUN3")
        self.assertEqual("imported_paper", run3["metadata"]["origin_type"])
        metric_values = {metric["name"]: metric["value"] for metric in run3["metadata"]["metrics"]}
        self.assertEqual("1.493", metric_values["KLD"])
        self.assertEqual("0.326", metric_values["SIM"])
        self.assertEqual("1.090", metric_values["NSS"])

    def test_experiment_run_is_terminal_inspector_selection(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="experiment_design_focus",
            focus_id="experiment:EXP3",
            selected_id="run:RUN3",
        )

        run = next(node for node in model["canvas"]["nodes"] if node["id"] == "run:RUN3")
        self.assertIsNone(run.get("drill"))
        self.assertEqual({"selected_id": "run:RUN3"}, run["inspector"])
        self.assertEqual("run_detail", model["inspector"]["kind"])

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

    def test_workspace_graph_api_default_schema_remains_v1(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-v1", data["schema_version"])
        self.assertIn("canvas", data)

    def test_workspace_graph_api_scene_v2_schema(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview&schema=scene-v2",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-scene-v2", data["schema_version"])
        self.assertNotIn("canvas", data)
        self.assertEqual("understanding.project_overview", data["layer"])
        self.assertIn("entities", data)
        self.assertTrue(data["entities"])
        serialized = json.dumps(data)
        self.assertNotIn('"drill"', serialized)

    def test_workspace_graph_api_scene_v2_rejects_dotted_layer_prefix_mismatch(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=literature&layer=understanding.project_overview&schema=scene-v2",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("workspace layer mode mismatch", data["message"])

    def test_workspace_graph_api_projection_v1_schema(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=claim_focus&focus_id=claim:C2&schema=projection-v1",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-projection-v1", data["schema_version"])
        self.assertEqual("understanding.claim_focus", data["layer"])
        self.assertIn("frames", data)
        self.assertIn("nodes", data)
        self.assertNotIn("canvas", data)
        atoms = [node for node in data["nodes"] if node["visual_kind"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(node["role"] == "terminal" for node in atoms))
        self.assertTrue(all(node["interaction"]["kind"] == "inspect" for node in atoms))

    def test_workspace_graph_handler_rejects_invalid_layer(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=run_detail",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("unknown workspace graph layer", data["message"])

    def test_workspace_graph_handler_defaults_to_understanding(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("understanding", data["mode"])
        self.assertEqual("project_overview", data["layer"])

    def test_workspace_graph_handler_rejects_invalid_mode(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=madeup",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("unknown workspace graph mode", data["message"])

    def test_literature_empty_data_returns_payload_not_crash(self):
        with closing(connect_dataset(self.root)) as connection:
            with connection:
                connection.execute("DELETE FROM literature_relations WHERE project_id = ?", (PROJECT_ID,))
                connection.execute("DELETE FROM literature_items WHERE project_id = ?", (PROJECT_ID,))
                connection.execute("DELETE FROM literature_lanes WHERE project_id = ?", (PROJECT_ID,))

        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")

        self.assertEqual("literature_overview", model["layer"])
        self.assertEqual([], model["canvas"]["nodes"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertIsNotNone(model["empty_state"])
        self.assertIn("No literature structure", model["empty_state"]["message"])

    def test_literature_empty_route_focus_still_rejects_unknown_route(self):
        with closing(connect_dataset(self.root)) as connection:
            with connection:
                connection.execute("DELETE FROM literature_relations WHERE project_id = ?", (PROJECT_ID,))
                connection.execute("DELETE FROM literature_items WHERE project_id = ?", (PROJECT_ID,))
                connection.execute("DELETE FROM literature_lanes WHERE project_id = ?", (PROJECT_ID,))

        with self.assertRaises(ValueError):
            build_workspace_graph_model(
                self.root,
                PROJECT_ID,
                mode="literature",
                layer="literature_route_focus",
                focus_id="literature_lane:missing",
            )

    def test_all_workspace_canvas_nodes_have_display_contract(self):
        arena_id = self._arena_id_by_label("AGD20K Affordance Localization")
        literature_overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")
        literature_route_id = self._node_id_by_label(literature_overview, "Text-Conditioned Affordance Grounding")
        literature_paper_id = self._node_id_by_label(
            literature_overview,
            "AffordanceNet: An End-to-End Deep Learning Approach for Object Affordance Detection",
        )
        cases = [
            ("understanding", "project_overview", "", ""),
            ("understanding", "claim_focus", "claim:C2", ""),
            ("understanding", "paper_focus", "claim:C2", "source:paper:do2017-affordancenet"),
            ("literature", "literature_overview", "", ""),
            ("literature", "literature_route_focus", literature_route_id, ""),
            ("literature", "literature_paper_focus", literature_paper_id, ""),
            ("experiments", "evaluation_overview", "", ""),
            ("experiments", "evaluation_arena_focus", arena_id, ""),
            ("experiments", "experiment_design_focus", "experiment:EXP3", "run:RUN3"),
        ]

        for mode, layer, focus_id, selected_id in cases:
            with self.subTest(mode=mode, layer=layer):
                model = build_workspace_graph_model(
                    self.root,
                    PROJECT_ID,
                    mode=mode,
                    layer=layer,
                    focus_id=focus_id,
                    selected_id=selected_id,
                )
                self.assertTrue(model["canvas"]["nodes"])
                for node in model["canvas"]["nodes"]:
                    self.assert_workspace_node_contract(node)

    def test_display_contract_maps_allowed_demo_roles(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        q1 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "Q1")
        c2 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "C2")
        q1_badges = {(badge["key"], badge["label"]) for badge in q1["display"]["badges"]}
        c2_badges = {(badge["key"], badge["label"]) for badge in c2["display"]["badges"]}

        self.assertIn(("question_role", "Framing"), q1_badges)
        self.assertIn(("claim_role", "Geometry Primitive"), c2_badges)
        self.assertEqual([], q1["display"]["warnings"])

    def test_display_contract_blocks_unknown_metadata_role(self):
        with closing(connect_dataset(self.root)) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE understanding_nodes
                    SET metadata_json = ?
                    WHERE project_id = ? AND node_id = ?
                    """,
                    (
                        json.dumps({"demo": True, "local_id": "Q1", "role": "agent invented role"}),
                        PROJECT_ID,
                        "project:DemoVisualAffordance:Q1",
                    ),
                )

        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")
        q1 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "Q1")
        badge_labels = [badge["label"] for badge in q1["display"]["badges"]]

        self.assertEqual("agent invented role", q1["metadata"]["role"])
        self.assertNotIn("Agent Invented Role", badge_labels)
        self.assertIn("Unsupported metadata.role was not rendered.", q1["display"]["warnings"])
        self.assertTrue(any(item["node_id"] == "question:Q1" for item in model["warnings"]))


if __name__ == "__main__":
    unittest.main()
