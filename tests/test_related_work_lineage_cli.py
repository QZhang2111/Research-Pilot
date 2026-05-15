import json
import tempfile
import unittest
from pathlib import Path

from tools.related_work_lineage_cli import (
    artifact_paths,
    create_template,
    main,
    render_markdown_summary,
    validate_lineage_map,
)


VALID_MAP = {
    "schema_version": "related-work-lineage-v1",
    "project": "DemoProject",
    "round": "vision-world-model-baselines",
    "title": "Vision World Model Related Work Lineage",
    "status": "candidate",
    "source_boundary": "related_work_lineage_only_not_graph_truth",
    "max_papers": 20,
    "route_narrowing": {
        "input_mode": "baseline_papers",
        "user_direction": "vision world models",
        "selected_anchor_papers": ["paper:dreamerv3"],
        "candidate_routes": [],
    },
    "axis_candidates": [
        {
            "axis": "state abstraction",
            "lanes": ["object-centric-modeling", "monolithic-latent-modeling"],
            "source": ["baseline related work", "comparison methods"],
            "why_field_native": "World-model papers are commonly grouped by how state is represented, independent of the baseline method.",
            "risk": "Some systems mix object-centric and monolithic latent structure.",
            "tests": {
                "baseline_removal": "Still organizes neighboring world-model papers without DreamerV3.",
                "neighbor_paper": "Neighbor papers describe object-centric or monolithic state representations.",
                "project_intent": "Matches project interest in state abstraction.",
                "non_component": "Not a module, loss, backbone, or fusion component.",
            },
            "decision": "selected",
            "reason": "Best field-native axis for this project.",
        },
        {
            "axis": "encoder architecture",
            "lanes": ["cnn", "transformer"],
            "source": ["baseline method details"],
            "why_field_native": "Architecture alone does not define the world-model field.",
            "risk": "Restates implementation choices instead of task ontology.",
            "tests": {
                "baseline_removal": "Weak; many papers would not use this as the primary field split.",
                "neighbor_paper": "Weak; neighboring papers often frame by task or state abstraction.",
                "project_intent": "Weak; does not answer project interest.",
                "non_component": "Fails; architecture is method-component-like.",
            },
            "decision": "rejected",
            "reason": "Too close to method implementation.",
        },
    ],
    "baseline_paper_field_scope": {
        "primary_problem": "latent world-model reinforcement learning",
        "input_output": "observations and actions to latent dynamics and policy learning",
        "benchmarks_or_datasets": ["Atari", "DMControl"],
        "evaluation_setting": "cross-domain reinforcement-learning benchmarks",
        "survey_boundary": "field-structure baseline-conditioned survey; do not use model internals as route lanes",
        "exclusion_rules": ["exclude generic transformer papers unless they define a field problem setting"],
        "field_structure": {
            "lane_axis": {
                "name": "state abstraction",
                "why_this_axis_defines_field_structure": "The baseline paper and comparison methods split the field by how world state is represented.",
                "selected_lanes": ["object-centric-modeling"],
            },
            "non_lane_axes": [
                {
                    "name": "deployment setting",
                    "encode_as": "tooltip",
                    "reason_not_lane": "It describes evaluation conditions, not the broad field structure.",
                }
            ],
        },
        "derived_taxonomy": [
            {
                "axis": "state abstraction",
                "values": ["monolithic latent state", "object-centric latent state"],
                "source": "baseline related work and comparison methods",
            },
            {
                "axis": "deployment setting",
                "values": ["single-domain", "cross-domain"],
                "source": "baseline benchmark framing",
            },
        ],
    },
    "search_log": [
        {
            "query_type": "task definition and benchmark",
            "query": "latent world model reinforcement learning benchmark Atari DMControl",
            "source": "web",
            "result_count": 2,
            "derived_from": "baseline_paper_field_scope.primary_problem",
        },
        {
            "query_type": "derived axis: state abstraction",
            "query": "object centric latent world model reinforcement learning",
            "source": "web",
            "result_count": 2,
            "derived_from": "baseline_paper_field_scope.derived_taxonomy[0]",
        }
    ],
    "routes": [
        {
            "id": "object-centric-modeling",
            "label": "Object-centric Modeling",
            "description": "Papers that model world state through objects, slots, or entities.",
            "review_status": "candidate",
        }
    ],
    "papers": [
        {
            "id": "paper:dreamerv3",
            "kind": "paper",
            "title": "DreamerV3",
            "year": 2023,
            "month": "01",
            "route": "object-centric-modeling",
            "roles": ["method", "milestone", "baseline"],
            "venue": "arXiv",
            "source_url": "https://arxiv.org/abs/2301.04104",
            "identity": {"arxiv": "2301.04104"},
            "summary": "Scales latent world model reinforcement learning across domains.",
            "source_evidence": "arXiv page and abstract.",
            "field_position": "object-centric-modeling",
            "method_setting": "reinforcement-learning",
            "artifact_type": "method",
            "key_paper": True,
            "context_precursor": False,
            "review_status": "candidate",
        },
        {
            "id": "paper:focus",
            "kind": "paper",
            "title": "FOCUS",
            "year": 2023,
            "month": "07",
            "route": "object-centric-modeling",
            "roles": ["method"],
            "venue": "arXiv",
            "source_url": "https://example.org/focus",
            "identity": {"official": "https://example.org/focus"},
            "summary": "Object-centric world modeling paper.",
            "source_evidence": "Official project page.",
            "field_position": "object-centric-modeling",
            "method_setting": "reinforcement-learning",
            "artifact_type": "method",
            "key_paper": False,
            "context_precursor": False,
            "review_status": "candidate",
        },
    ],
    "survey_catalog": [
        {
            "period": "2023 Q1",
            "paper": "paper:dreamerv3",
            "contribution": "Scales latent world-model RL across domains.",
            "field_relevance": "Baseline anchor for the field scope.",
        }
    ],
    "timeline_tracks": [
        {
            "id": "object-centric-modeling",
            "label": "Object-centric Modeling",
            "description": "Task route lane for the timeline diagram.",
            "color": "purple",
        }
    ],
    "major_trends": [
        {
            "name": "World models become generalist benchmark learners",
            "evidence_papers": ["paper:dreamerv3", "paper:focus"],
            "summary": "Multiple papers pursue cross-domain latent modeling instead of one-domain policies.",
        }
    ],
    "notable_forks": [
        {
            "name": "Object-centric state versus monolithic latent state",
            "sides": ["object-centric", "monolithic"],
            "summary": "The task splits between entity-based state abstractions and broad latent dynamics.",
        }
    ],
    "explicit_edges": [
        {
            "source": "paper:dreamerv3",
            "target": "paper:focus",
            "relation": "influences",
            "rationale": "FOCUS follows the object-centric world model route.",
            "confidence": "medium",
            "source_evidence": "FOCUS introduction positions itself against prior world model work.",
            "review_status": "candidate",
        }
    ],
    "positioning_note": "The project appears closest to object-centric modeling.",
}


class RelatedWorkLineageCliTest(unittest.TestCase):
    def test_artifact_paths_follow_literature_round_convention(self):
        root = Path("/tmp/workspace")
        paths = artifact_paths(root, "DemoProject", "vision-world-model-baselines")

        self.assertEqual(
            paths["json"],
            root / "wiki" / "projects" / "DemoProject" / "literature-rounds" / "vision-world-model-baselines" / "related-work-lineage.json",
        )
        self.assertEqual(paths["markdown"].name, "related-work-lineage.md")

    def test_artifact_paths_reject_unsafe_segments(self):
        root = Path("/tmp/workspace")

        with self.assertRaises(ValueError):
            artifact_paths(root, "../escape", "vision-world-model-baselines")
        with self.assertRaises(ValueError):
            artifact_paths(root, "DemoProject", "round/escape")
        with self.assertRaises(ValueError):
            artifact_paths(root, ".", "vision-world-model-baselines")

    def test_validates_paper_only_map(self):
        result = validate_lineage_map(VALID_MAP)

        self.assertTrue(result["valid"], result)
        self.assertEqual(result["paper_count"], 2)

    def test_baseline_mode_requires_field_scope(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["baseline_paper_field_scope"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("baseline_paper_field_scope is required for baseline_papers input_mode", result["errors"])

    def test_baseline_field_scope_requires_primary_problem(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["baseline_paper_field_scope"]["primary_problem"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("baseline_paper_field_scope.primary_problem is required", result["errors"])

    def test_baseline_field_scope_requires_derived_taxonomy(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["baseline_paper_field_scope"]["derived_taxonomy"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("baseline_paper_field_scope.derived_taxonomy must be a non-empty list", result["errors"])

    def test_baseline_field_scope_requires_field_structure(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["baseline_paper_field_scope"]["field_structure"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("baseline_paper_field_scope.field_structure is required", result["errors"])

    def test_baseline_mode_requires_axis_candidates(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["axis_candidates"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("axis_candidates must be a non-empty list for baseline_papers input_mode", result["errors"])

    def test_baseline_mode_requires_selected_axis_candidate_matching_lane_axis(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["axis_candidates"][0]["decision"] = "rejected"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn(
            "axis_candidates must include one selected candidate matching baseline_paper_field_scope.field_structure.lane_axis.name",
            result["errors"],
        )

    def test_rejects_static_supervision_template_query_types(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["search_log"] = [
            {
                "query_type": "weakly supervised",
                "query": "latent world model reinforcement learning weakly supervised",
            }
        ]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn(
            "search_log[0].query_type looks like a fixed domain template; baseline searches must be derived from extracted taxonomy",
            result["errors"],
        )

    def test_rejects_paper_missing_field_position(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["papers"][0]["field_position"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].field_position is required", result["errors"])

    def test_rejects_paper_missing_method_setting(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["papers"][0]["method_setting"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].method_setting is required", result["errors"])

    def test_rejects_method_component_lane_in_baseline_task_mode(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["routes"][0]["id"] = "internal-attention-analysis"
        payload["routes"][0]["label"] = "Internal Attention Analysis"
        payload["papers"][0]["route"] = "internal-attention-analysis"
        payload["papers"][1]["route"] = "internal-attention-analysis"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn(
            "routes[0].id looks like a method-component lane; baseline_papers mode must use field-structure routes",
            result["errors"],
        )

    def test_rejects_route_not_in_selected_field_lanes(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["routes"][0]["id"] = "unselected-lane"
        payload["papers"][0]["route"] = "unselected-lane"
        payload["papers"][1]["route"] = "unselected-lane"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn(
            "routes[0].id is not in baseline_paper_field_scope.field_structure.lane_axis.selected_lanes",
            result["errors"],
        )

    def test_markdown_summary_includes_field_scope_and_catalog(self):
        summary = render_markdown_summary(VALID_MAP)

        self.assertIn("## Baseline Paper Field Scope", summary)
        self.assertIn("latent world-model reinforcement learning", summary)
        self.assertIn("## Chronological Catalog", summary)
        self.assertIn("Scales latent world-model RL across domains.", summary)
        self.assertIn("## Major Trends", summary)
        self.assertIn("## Axis Candidates", summary)
        self.assertIn("selected: state abstraction", summary)

    def test_rejects_non_object_payload(self):
        result = validate_lineage_map([])

        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"], ["payload must be an object"])
        self.assertEqual(result["paper_count"], 0)
        self.assertEqual(result["route_count"], 0)
        self.assertEqual(result["edge_count"], 0)

    def test_rejects_non_paper_nodes(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["papers"][0]["kind"] = "dataset"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].kind must be paper", result["errors"])

    def test_rejects_paper_without_identity(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["papers"][0]["identity"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].identity must be a non-empty object", result["errors"])

    def test_rejects_more_than_twenty_papers(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["papers"] = [
            {
                **payload["papers"][0],
                "id": f"paper:item-{index}",
                "title": f"Paper {index}",
                "source_url": f"https://example.org/{index}",
            }
            for index in range(21)
        ]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("paper count must be <= 20", result["errors"])

    def test_rejects_edges_to_unknown_papers(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["explicit_edges"][0]["target"] = "paper:missing"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("explicit_edges[0].target unknown paper: paper:missing", result["errors"])

    def test_rejects_missing_explicit_edges(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["explicit_edges"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("explicit_edges must be a list", result["errors"])

    def test_rejects_explicit_edge_without_confidence(self):
        payload = json.loads(json.dumps(VALID_MAP))
        del payload["explicit_edges"][0]["confidence"]

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("explicit_edges[0].confidence is required", result["errors"])

    def test_template_and_markdown_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = create_template(
                root=root,
                project="DemoProject",
                round_id="vision-world-model-baselines",
                title="Vision World Model Related Work Lineage",
                user_direction="vision world models",
                baseline_papers=["DreamerV3"],
                overwrite=False,
            )
            payload = json.loads(Path(created["json_path"]).read_text(encoding="utf-8"))
            summary = render_markdown_summary(VALID_MAP)

        self.assertTrue(created["created"], created)
        self.assertEqual(payload["project"], "DemoProject")
        self.assertEqual(payload["route_narrowing"]["selected_anchor_papers"], ["DreamerV3"])
        self.assertIn("# Vision World Model Related Work Lineage", summary)
        self.assertIn("## Technical Routes", summary)
        self.assertIn("DreamerV3", summary)

    def test_markdown_frontmatter_escapes_yaml_scalars(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["title"] = "Lineage \"Quoted\"\ninjected: value"

        summary = render_markdown_summary(payload)
        frontmatter = summary.split("---", 2)[1].strip().splitlines()
        title_lines = [line for line in frontmatter if line.startswith("title: ")]

        self.assertEqual(len(title_lines), 1)
        self.assertEqual(title_lines[0], 'title: "Lineage \\"Quoted\\"\\ninjected: value"')
        self.assertNotIn("injected: value", frontmatter)

    def test_cli_create_rejects_unsafe_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = main(
                [
                    "create",
                    "--repo",
                    tmp,
                    "--project",
                    "../escape",
                    "--round",
                    "vision-world-model-baselines",
                    "--title",
                    "Unsafe",
                    "--json",
                ]
            )

            self.assertEqual(result, 1)
            self.assertFalse((Path(tmp).parent / "escape").exists())

    def test_cli_validate_missing_file_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"

            result = main(["validate", "--path", str(missing), "--json"])

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
