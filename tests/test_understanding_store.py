import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.understanding_store import (
    append_understanding_update,
    build_project_understanding,
    project_understanding_path,
    read_understanding_updates,
    understanding_event_path,
    validate_understanding_update,
    write_project_understanding,
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

    def test_paths_reject_project_ids_with_path_parts(self):
        root = Path("/tmp/research-pilot-test")
        for project_id in ["../x", "a/b", "/tmp/escape", "a/", "a/.", "a\\"]:
            with self.subTest(project_id=project_id):
                with self.assertRaises(ValueError):
                    understanding_event_path(root, project_id)
                with self.assertRaises(ValueError):
                    project_understanding_path(root, project_id)

    def test_paths_accept_valid_project_slug(self):
        root = Path("/tmp/research-pilot-test")
        self.assertEqual(root / "wiki" / "understanding" / "events" / "valid-slug_01.jsonl", understanding_event_path(root, "valid-slug_01"))
        self.assertEqual(root / "wiki" / "understanding" / "events" / "DemoProject.jsonl", understanding_event_path(root, "DemoProject"))
        self.assertEqual(root / "wiki" / "understanding" / "events" / "AAAI2027Affordance.jsonl", understanding_event_path(root, "AAAI2027Affordance"))

    def test_append_rejects_invalid_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = append_understanding_update(Path(tmp), "../x", sample_update())

        self.assertFalse(result["appended"])
        self.assertIn("invalid project_id", result["errors"])

    def test_validate_rejects_projection_fields_that_are_not_arrays(self):
        update = sample_update()
        update["changed_claims"] = {"claim_id": "C1"}
        result = validate_understanding_update(update)

        self.assertFalse(result["valid"])
        self.assertIn("changed_claims must be an array", result["errors"])

    def test_validate_rejects_projection_field_items_without_ids(self):
        update = sample_update()
        update["changed_claims"] = [{"text": "No id."}]
        update["new_evidence"] = [{"text": "No id."}]
        update["new_gaps"] = [{"text": "No id."}]
        update["status_changes"] = [{"status": "weak"}]
        result = validate_understanding_update(update)

        self.assertFalse(result["valid"])
        self.assertIn("changed_claim.claim_id must be non-empty", result["errors"])
        self.assertIn("evidence.evidence_id must be non-empty", result["errors"])
        self.assertIn("gap.gap_id must be non-empty", result["errors"])
        self.assertIn("status_change.target_id must be non-empty", result["errors"])

    def test_validate_rejects_projection_items_without_text(self):
        update = sample_update()
        update["changed_claims"] = [{"claim_id": "C1"}]
        update["new_evidence"] = [{"evidence_id": "E1"}]
        update["new_gaps"] = [{"gap_id": "G1"}]
        result = validate_understanding_update(update)

        self.assertFalse(result["valid"])
        self.assertIn("changed_claim.text must be non-empty", result["errors"])
        self.assertIn("evidence.text must be non-empty", result["errors"])
        self.assertIn("gap.text must be non-empty", result["errors"])

    def test_validate_rejects_status_change_without_status(self):
        update = sample_update()
        update["status_changes"] = [{"target_id": "C1"}]
        result = validate_understanding_update(update)

        self.assertFalse(result["valid"])
        self.assertIn("status_change.status must be non-empty", result["errors"])

    def test_validate_rejects_status_change_with_unsupported_status(self):
        update = sample_update()
        update["status_changes"] = [{"target_id": "C1", "status": "unsupported"}]
        result = validate_understanding_update(update)

        self.assertFalse(result["valid"])
        self.assertIn("unsupported status_change.status: unsupported", result["errors"])

    def test_append_rejects_malformed_projection_fields(self):
        update = sample_update()
        update["new_gaps"] = ["not an object"]

        with tempfile.TemporaryDirectory() as tmp:
            result = append_understanding_update(Path(tmp), "DemoProject", update)

        self.assertFalse(result["appended"])
        self.assertIn("new_gaps items must be objects", result["errors"])

    def test_projection_ignores_malformed_existing_projection_items(self):
        update = sample_update()
        update["changed_claims"] = ["not an object"]
        update["new_evidence"] = [None]
        update["new_gaps"] = [42]
        update["next_moves"] = ["bad"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = understanding_event_path(root, "DemoProject")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(update) + "\n", encoding="utf-8")
            projection = build_project_understanding(root, "DemoProject", generated_at="2026-05-23T00:10:00Z")

        self.assertEqual([], projection["claims"])
        self.assertEqual([], projection["evidence"])
        self.assertEqual([], projection["gaps"])
        self.assertEqual([], projection["next_moves"])

    def test_write_project_understanding_rejects_invalid_project_id_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("tools.understanding_store.Path.open") as path_open:
                with self.assertRaises(ValueError):
                    write_project_understanding(root, "../x")
                path_open.assert_not_called()

    def test_demo_understanding_update_example_is_valid(self):
        import json

        path = Path("examples/demo/understanding/demo-understanding-update.json")
        update = json.loads(path.read_text(encoding="utf-8"))
        result = validate_understanding_update(update)

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual("DemoVisualAffordance", update["project_id"])


if __name__ == "__main__":
    unittest.main()
