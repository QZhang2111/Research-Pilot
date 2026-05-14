import json
import tempfile
import unittest
from pathlib import Path

from tools.related_work_lineage_cli import (
    artifact_paths,
    create_template,
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
            "review_status": "candidate",
        },
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

    def test_validates_paper_only_map(self):
        result = validate_lineage_map(VALID_MAP)

        self.assertTrue(result["valid"], result)
        self.assertEqual(result["paper_count"], 2)

    def test_rejects_non_paper_nodes(self):
        payload = json.loads(json.dumps(VALID_MAP))
        payload["papers"][0]["kind"] = "dataset"

        result = validate_lineage_map(payload)

        self.assertFalse(result["valid"])
        self.assertIn("papers[0].kind must be paper", result["errors"])

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


if __name__ == "__main__":
    unittest.main()
