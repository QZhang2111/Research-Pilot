import json
import unittest
from pathlib import Path
from unittest import mock

from tools.workspace_scene_contract import (
    V1_TO_V2_LAYER,
    canonical_source_id,
    normalize_workspace_layer,
    validate_projected_graph,
    validate_workspace_scene,
)
from tools.workspace_scene_builders import build_workspace_scene
from tools.workspace_graph_projection import build_projected_graph


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"


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

    def test_normalize_workspace_layer_rejects_dotted_layer_with_unknown_mode(self):
        with self.assertRaisesRegex(ValueError, "unknown workspace mode"):
            normalize_workspace_layer("madeup", "understanding.project_overview")

    def test_normalize_workspace_layer_rejects_dotted_layer_prefix_mismatch(self):
        with self.assertRaisesRegex(ValueError, "workspace layer mode mismatch"):
            normalize_workspace_layer("literature", "understanding.project_overview")

    def test_normalize_workspace_layer_accepts_valid_dotted_layer(self):
        self.assertEqual(
            "understanding.project_overview",
            normalize_workspace_layer("understanding", "understanding.project_overview"),
        )

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

    def test_projected_validator_rejects_missing_edge_endpoint(self):
        projected = self._minimal_projected_graph()
        projected["edges"].append(
            {
                "projected_id": "edge:R1",
                "relation_type": "supports",
                "source_id": "node:missing",
                "target_id": "node:claim:C1",
                "label": "supports",
                "member_relation_ids": ["R1"],
                "aggregation": None,
                "source": {"kind": "derived", "rule": "test", "inputs": []},
            }
        )

        with self.assertRaisesRegex(ValueError, "projected edge references missing node"):
            validate_projected_graph(projected)

    def test_projected_validator_rejects_missing_frame_member(self):
        projected = self._minimal_projected_graph()
        projected["frames"].append(
            {
                "projected_id": "frame:F1",
                "semantic_id": "frame:F1",
                "frame_kind": "lane",
                "title": "Frame",
                "member_entity_ids": ["claim:C1", "missing"],
                "member_node_ids": ["node:claim:C1", "node:missing"],
                "interaction": {"kind": "none"},
                "source": {"kind": "derived", "rule": "test", "inputs": []},
            }
        )

        with self.assertRaisesRegex(ValueError, "projected frame references missing node"):
            validate_projected_graph(projected)

    def test_projected_validator_rejects_missing_portal_source(self):
        projected = self._minimal_projected_graph()
        projected["portals"].append(
            {
                "projected_id": "portal:P1",
                "from_node_id": "node:missing",
                "label": "Portal",
                "target": {"mode": "understanding", "layer": "understanding.paper_focus"},
                "source": {"kind": "derived", "rule": "test", "inputs": []},
            }
        )

        with self.assertRaisesRegex(ValueError, "projected portal references missing node"):
            validate_projected_graph(projected)

    def _minimal_projected_graph(self):
        return {
            "schema_version": "workspace-projection-v1",
            "project_id": "DemoVisualAffordance",
            "mode": "understanding",
            "layer": "understanding.project_overview",
            "focus_id": "",
            "breadcrumb": [],
            "nodes": [
                {
                    "projected_id": "node:claim:C1",
                    "semantic_id": "claim:C1",
                    "role": "entity",
                    "visual_kind": "claim",
                    "title": "Claim",
                    "display_id": "C1",
                    "interaction": {"kind": "inspect", "inspector_id": "claim:C1"},
                    "source": {"kind": "derived", "rule": "test", "inputs": []},
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

    def test_understanding_project_overview_scene_has_semantic_entities_not_canvas(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
        )

        validate_workspace_scene(scene)
        self.assertEqual("workspace-scene-v2", scene["schema_version"])
        self.assertEqual("understanding.project_overview", scene["layer"])
        self.assertNotIn("canvas", scene)
        self.assertNotIn("breadcrumb", scene)
        entity_types = {entity["entity_type"] for entity in scene["entities"]}
        self.assertEqual({"question", "claim"}, entity_types)
        c2 = next(entity for entity in scene["entities"] if entity["display_id"] == "C2")
        self.assertEqual("understanding:project:DemoVisualAffordance:claim:C2", c2["canonical_id"])
        self.assertEqual({"inspectable", "drillable"}, set(c2["capabilities"]))
        self.assertEqual(
            {"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:C2"},
            c2["source"],
        )

    def test_understanding_claim_focus_scene_keeps_argument_atoms_terminal_by_capability(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        validate_workspace_scene(scene)
        self.assertEqual("understanding.claim_focus", scene["layer"])
        self.assertEqual("understanding:project:DemoVisualAffordance:claim:C2", scene["focus_id"])
        entity_types = {entity["entity_type"] for entity in scene["entities"]}
        self.assertIn("claim", entity_types)
        self.assertIn("evidence", entity_types)
        self.assertIn("warrant", entity_types)
        self.assertIn("limitation", entity_types)
        self.assertIn("source", entity_types)
        atoms = [entity for entity in scene["entities"] if entity["entity_type"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(entity["capabilities"] == ["inspectable"] for entity in atoms))
        self.assertTrue(all("drill" not in entity for entity in atoms))

    def test_understanding_claim_focus_scene_groups_are_derived(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        validate_workspace_scene(scene)
        group_types = {group["group_type"] for group in scene["groups"]}
        self.assertGreaterEqual(group_types, {"lane"})
        titles = {group["title"] for group in scene["groups"]}
        self.assertIn("Evidence / Grounds", titles)
        self.assertIn("Warrants / Bridges", titles)
        self.assertIn("Limitations / Boundaries", titles)
        self.assertTrue(all(group["source"]["kind"] == "derived" for group in scene["groups"]))

    def test_understanding_claim_focus_scene_preserves_warrant_and_limitation_relations(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        relation_keys = {
            (relation["relation_type"], relation["source_id"], relation["target_id"], relation["source"]["primary_key"])
            for relation in scene["relations"]
        }
        c2 = "understanding:project:DemoVisualAffordance:claim:C2"
        self.assertIn(("warrants", "understanding:project:DemoVisualAffordance:warrant:W2", c2, "project:DemoVisualAffordance:RL1"), relation_keys)
        self.assertIn(("limits", "understanding:project:DemoVisualAffordance:limitation:L1", c2, "project:DemoVisualAffordance:RL1"), relation_keys)

    def test_understanding_claim_focus_scene_sources_include_link_refs_and_canonical_source_refs(self):
        graph = {
            "nodes": [
                {
                    "id": "project:Demo:C10",
                    "kind": "claim",
                    "label": "Focused claim",
                    "subtitle": "C10",
                    "status": "active",
                    "confidence": "medium",
                    "source_refs": [],
                    "metadata": {"local_id": "C10"},
                },
                {
                    "id": "project:Demo:E10",
                    "kind": "evidence",
                    "label": "Evidence",
                    "subtitle": "E10",
                    "status": "active",
                    "confidence": "medium",
                    "source_refs": [],
                    "metadata": {"local_id": "E10"},
                },
            ],
            "links": [
                {
                    "id": "project:Demo:RL10",
                    "relation": "supports",
                    "premises": ["project:Demo:E10"],
                    "target": ["project:Demo:C10"],
                    "warrant": [],
                    "limitations": [],
                    "source_refs": ["canonical-paper-only"],
                }
            ],
        }
        sources = {
            "sources": [
                {
                    "source_id": "paper:canonical-paper-only",
                    "title": "Canonical Paper",
                    "locator": "wiki/projects/Demo/papers/canonical-paper-only/index.md",
                    "url": "",
                    "doi": "",
                    "arxiv_id": "",
                    "reading_status": "deep_read",
                    "short_summary": "",
                }
            ]
        }

        with (
            mock.patch("tools.workspace_scene_builders.understanding_scene.build_project_graph_model", return_value=graph),
            mock.patch("tools.workspace_scene_builders.understanding_scene.build_sources_model", return_value=sources),
            mock.patch(
                "tools.workspace_scene_builders.understanding_scene._source_metadata_by_source_id",
                create=True,
                return_value={"paper:canonical-paper-only": {"canonical_source_ref": "canonical-paper-only"}},
            ),
        ):
            scene = build_workspace_scene(WORKSPACE_ROOT, "Demo", mode="understanding", layer="claim_focus", focus_id="claim:C10")

        source_ids = {entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "source"}
        self.assertIn("source:paper:canonical-paper-only", source_ids)

    def test_projected_understanding_overview_has_frames_and_interactions(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="project_overview")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        self.assertEqual("workspace-projection-v1", projected["schema_version"])
        self.assertEqual("understanding.project_overview", projected["layer"])
        self.assertTrue(projected["frames"])
        c2 = next(node for node in projected["nodes"] if node["display_id"] == "C2")
        self.assertEqual("entity", c2["role"])
        self.assertEqual("drill", c2["interaction"]["kind"])
        self.assertEqual("understanding.claim_focus", c2["interaction"]["target"]["layer"])
        q1 = next(node for node in projected["nodes"] if node["display_id"] == "Q1")
        self.assertEqual("inspect", q1["interaction"]["kind"])

    def test_projected_claim_focus_argument_atoms_are_terminal_inspect_only(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        atoms = [node for node in projected["nodes"] if node["visual_kind"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(node["role"] == "terminal" for node in atoms))
        self.assertTrue(all(node["interaction"]["kind"] == "inspect" for node in atoms))
        self.assertFalse(any(node["interaction"]["kind"] == "drill" for node in atoms))

    def test_projected_edges_retain_relation_provenance(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        self.assertTrue(projected["edges"])
        self.assertTrue(all(edge["member_relation_ids"] for edge in projected["edges"]))
        self.assertTrue(all(edge["source"]["kind"] in {"db_row", "derived"} for edge in projected["edges"]))

    def test_projected_claim_focus_source_drill_preserves_claim_focus_id(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)

        source = next(node for node in projected["nodes"] if node["visual_kind"] == "source")
        self.assertEqual("drill", source["interaction"]["kind"])
        self.assertEqual("understanding.paper_focus", source["interaction"]["target"]["layer"])
        self.assertEqual("understanding:project:DemoVisualAffordance:claim:C2", source["interaction"]["target"]["focus_id"])
        self.assertEqual(source["semantic_id"], source["interaction"]["target"]["selected_id"])

    def test_projected_graph_rejects_dangling_relation_endpoint(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        scene["relations"][0]["source_id"] = "understanding:project:DemoVisualAffordance:evidence:missing"

        with self.assertRaisesRegex(ValueError, "projected relation references missing entity"):
            build_projected_graph(scene)

    def test_projected_graph_rejects_dangling_frame_member(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        scene["groups"][0]["member_ids"].append("understanding:project:DemoVisualAffordance:evidence:missing")

        with self.assertRaisesRegex(ValueError, "projected frame references missing entity"):
            build_projected_graph(scene)

    def test_projected_graph_rejects_dangling_portal_from_id(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        scene["portals"].append(
            {
                "canonical_id": "portal:missing-source",
                "from_id": "understanding:project:DemoVisualAffordance:evidence:missing",
                "title": "Missing source portal",
                "target": {"mode": "understanding", "layer": "understanding.paper_focus"},
                "source": {"kind": "derived", "rule": "test portal", "inputs": []},
            }
        )

        with self.assertRaisesRegex(ValueError, "projected portal references missing entity"):
            build_projected_graph(scene)

    def test_scene_v2_rejects_unimplemented_non_understanding_layers_explicitly(self):
        cases = [
            ("literature", "literature_overview"),
            ("literature", "literature_route_focus"),
            ("literature", "literature_paper_focus"),
            ("experiments", "evaluation_overview"),
            ("experiments", "evaluation_setting_focus"),
            ("experiments", "experiment_design_focus"),
        ]
        for mode, layer in cases:
            with self.subTest(mode=mode, layer=layer):
                with self.assertRaisesRegex(ValueError, "workspace-scene-v2 not implemented"):
                    build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode=mode, layer=layer)

    def test_scene_entities_all_have_db_or_derived_sources(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")

        for entity in scene["entities"]:
            self.assertIn(entity["source"]["kind"], {"db_row", "derived"})
            if entity["source"]["kind"] == "db_row":
                self.assertTrue(entity["source"].get("table"))
                self.assertTrue(entity["source"].get("primary_key"))

    def test_projection_does_not_emit_canvas_or_frontend_node_type_fields(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)
        serialized = json.dumps(projected)

        self.assertNotIn('"canvas"', serialized)
        self.assertNotIn('"nodeTypes"', serialized)
        self.assertNotIn('"edgeTypes"', serialized)
        self.assertNotIn('"className"', serialized)


if __name__ == "__main__":
    unittest.main()
