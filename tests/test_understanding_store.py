import tempfile
import unittest
from pathlib import Path

from tools.understanding_store import (
    append_understanding_update,
    build_project_understanding,
    project_understanding_path,
    read_understanding_updates,
    understanding_event_path,
    validate_understanding_update,
)


def sample_update(update_id: str = "UU0001") -> dict:
    return {
        "schema_version": "understanding-update-v1",
        "update_id": update_id,
        "project_id": "DemoProject",
        "created_at": "2026-05-23T00:00:00Z",
        "actor": "agent",
        "task": {"kind": "read_source", "summary": "Read S1 and checked claim C1."},
        "source_refs": ["arxiv:1234.56789"],
        "new_sources": [
            {
                "source_id": "S1",
                "type": "arxiv",
                "locator": "https://arxiv.org/abs/1234.56789",
                "title": "Counterfactual Affordance Benchmark",
                "status": "read",
                "relevance": "Tests affordance reasoning indirectly.",
                "related_claims": ["C1"],
                "related_gaps": ["G1"],
            }
        ],
        "changed_claims": [
            {
                "claim_id": "C1",
                "text": "VLMs may encode affordance priors.",
                "change": "weakened",
                "status": "weak",
                "supporting_sources": ["S1"],
                "challenging_sources": [],
                "weakness": "Evidence is indirect.",
            }
        ],
        "new_evidence": [
            {
                "evidence_id": "E1",
                "text": "S1 reports affordance recognition but not causal interaction tests.",
                "source_refs": ["S1"],
                "related_claims": ["C1"],
            }
        ],
        "new_gaps": [
            {
                "gap_id": "G1",
                "text": "Need counterfactual interaction evidence.",
                "type": "missing evidence",
                "related_claims": ["C1"],
                "related_sources": ["S1"],
            }
        ],
        "status_changes": [
            {
                "target_id": "C1",
                "target_type": "claim",
                "status": "weak",
                "reason": "Support is indirect.",
            }
        ],
        "recent_change_summary": "C1 weakened after reading S1; G1 added.",
        "next_moves": [
            {
                "move_id": "N1",
                "type": "search",
                "text": "Find counterfactual VLM affordance benchmarks.",
                "rationale": "C1 lacks direct evidence.",
                "suggested_prompt": "Find papers testing VLM affordance reasoning under counterfactual object interactions.",
            }
        ],
        "confidence": "agent-inferred",
    }


class UnderstandingStoreTest(unittest.TestCase):
    def test_validate_accepts_sample_update(self):
        result = validate_understanding_update(sample_update())
        self.assertEqual([], result["errors"])
        self.assertTrue(result["valid"])

    def test_validate_rejects_missing_required_fields(self):
        update = sample_update()
        update.pop("task")
        result = validate_understanding_update(update)
        self.assertFalse(result["valid"])
        self.assertIn("missing task", result["errors"])

    def test_append_and_read_update_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = append_understanding_update(root, "DemoProject", sample_update())
            updates = read_understanding_updates(root, "DemoProject")

        self.assertTrue(result["appended"])
        self.assertEqual("wiki/understanding/events/DemoProject.jsonl", result["event_path"])
        self.assertEqual(["UU0001"], [item["update_id"] for item in updates])

    def test_append_rejects_duplicate_update_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_understanding_update(root, "DemoProject", sample_update())
            result = append_understanding_update(root, "DemoProject", sample_update())

        self.assertFalse(result["appended"])
        self.assertIn("duplicate update_id: UU0001", result["errors"])

    def test_project_understanding_projection_collects_current_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_understanding_update(root, "DemoProject", sample_update("UU0001"))
            projection = build_project_understanding(root, "DemoProject", generated_at="2026-05-23T00:10:00Z")

        self.assertEqual("project-understanding-v1", projection["schema_version"])
        self.assertEqual("DemoProject", projection["project_id"])
        self.assertEqual("Counterfactual Affordance Benchmark", projection["sources"][0]["title"])
        self.assertEqual("VLMs may encode affordance priors.", projection["claims"][0]["text"])
        self.assertEqual("Need counterfactual interaction evidence.", projection["gaps"][0]["text"])
        self.assertEqual("C1 weakened after reading S1; G1 added.", projection["recent_changes"][0]["summary"])
        self.assertEqual("Find counterfactual VLM affordance benchmarks.", projection["next_moves"][0]["text"])
        self.assertIn("wiki/understanding/events/DemoProject.jsonl", projection["inputs"])

    def test_paths_are_under_understanding_directory(self):
        root = Path("/tmp/research-pilot-test")
        self.assertEqual(root / "wiki" / "understanding" / "events" / "DemoProject.jsonl", understanding_event_path(root, "DemoProject"))
        self.assertEqual(root / "wiki" / "understanding" / "project-understanding" / "DemoProject.json", project_understanding_path(root, "DemoProject"))


if __name__ == "__main__":
    unittest.main()
