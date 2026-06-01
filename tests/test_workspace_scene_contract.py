import unittest

from tools.workspace_scene_contract import (
    V1_TO_V2_LAYER,
    canonical_source_id,
    normalize_workspace_layer,
    validate_projected_graph,
    validate_workspace_scene,
)


class WorkspaceSceneContractTest(unittest.TestCase):
    def test_normalize_workspace_layer_maps_current_v1_names(self):
        self.assertEqual("understanding.project_overview", normalize_workspace_layer("understanding", "project_overview"))
        self.assertEqual("understanding.claim_focus", normalize_workspace_layer("understanding", "claim_focus"))
        self.assertEqual("understanding.paper_focus", normalize_workspace_layer("understanding", "paper_focus"))
        self.assertEqual("literature.overview", normalize_workspace_layer("literature", "literature_overview"))
        self.assertEqual("literature.route_focus", normalize_workspace_layer("literature", "literature_route_focus"))
        self.assertEqual("literature.paper_focus", normalize_workspace_layer("literature", "literature_paper_focus"))
        self.assertEqual("experiments.evaluation_overview", normalize_workspace_layer("experiments", "evaluation_overview"))
        self.assertEqual("experiments.evaluation_setting_focus", normalize_workspace_layer("experiments", "evaluation_setting_focus"))
        self.assertEqual("experiments.experiment_design_focus", normalize_workspace_layer("experiments", "experiment_design_focus"))

    def test_v1_to_v2_mapping_covers_current_workspace_layers(self):
        self.assertEqual(
            {
                ("understanding", "project_overview"),
                ("understanding", "claim_focus"),
                ("understanding", "paper_focus"),
                ("literature", "literature_overview"),
                ("literature", "literature_route_focus"),
                ("literature", "literature_paper_focus"),
                ("experiments", "evaluation_overview"),
                ("experiments", "evaluation_setting_focus"),
                ("experiments", "experiment_design_focus"),
            },
            set(V1_TO_V2_LAYER),
        )

    def test_canonical_source_id_wraps_db_source_id_without_losing_prefixes(self):
        self.assertEqual("source:paper:do2017-affordancenet", canonical_source_id("paper:do2017-affordancenet"))
        self.assertEqual("source:S-demo-luo2022-agd20k", canonical_source_id("S-demo-luo2022-agd20k"))

    def test_scene_validator_rejects_ui_payload_fields(self):
        scene = {
            "schema_version": "workspace-scene-v2",
            "project_id": "DemoVisualAffordance",
            "mode": "understanding",
            "layer": "understanding.project_overview",
            "focus_id": "",
            "source": "research-pilot.db",
            "entities": [
                {
                    "canonical_id": "understanding:project:DemoVisualAffordance:claim:C2",
                    "display_id": "C2",
                    "entity_type": "claim",
                    "title": "Claim text",
                    "summary": "",
                    "status": "active",
                    "confidence": "medium",
                    "capabilities": ["inspectable", "drillable"],
                    "source": {"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:C2"},
                    "metadata": {},
                    "drill": {"mode": "understanding", "layer": "claim_focus"},
                }
            ],
            "relations": [],
            "groups": [],
            "portals": [],
            "inspector": {},
            "warnings": [],
            "canvas": {"nodes": []},
        }

        with self.assertRaisesRegex(ValueError, "WorkspaceScene must not contain UI field"):
            validate_workspace_scene(scene)

    def test_projection_validator_rejects_terminal_drill(self):
        projected = {
            "schema_version": "workspace-projection-v1",
            "project_id": "DemoVisualAffordance",
            "mode": "understanding",
            "layer": "understanding.claim_focus",
            "focus_id": "understanding:project:DemoVisualAffordance:claim:C2",
            "breadcrumb": [],
            "nodes": [
                {
                    "projected_id": "node:evidence:E1",
                    "semantic_id": "understanding:project:DemoVisualAffordance:evidence:E1",
                    "role": "terminal",
                    "visual_kind": "evidence",
                    "title": "Evidence text",
                    "display_id": "E1",
                    "interaction": {"kind": "drill", "target": {"mode": "understanding", "layer": "claim_focus"}},
                    "source": {"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:E1"},
                    "layout_hints": {},
                }
            ],
            "edges": [],
            "frames": [],
            "portals": [],
            "inspector_default_id": "",
            "layout": {"kind": "layered"},
            "warnings": [],
        }

        with self.assertRaisesRegex(ValueError, "terminal projected nodes must not drill"):
            validate_projected_graph(projected)


if __name__ == "__main__":
    unittest.main()
