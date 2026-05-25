import json
import tempfile
import unittest
from pathlib import Path

from tools.build_graph_db import main as build_db_main
from tools.graph_delta_api import decide_graph_delta, dry_run_graph_delta, load_delta_file, register_graph_delta
from tools.graph_query_cli import query_delta, query_node, query_open


class GraphDeltaLoopTest(unittest.TestCase):
    def make_workspace(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
        event_path.parent.mkdir(parents=True)
        event_path.write_text(Path("examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        build_db_main(["--repo", str(root), "--project", "DemoProject"])
        return temp_dir, root

    def first_graph_delta(self) -> dict:
        return {
            "delta_id": "project:NewProject:D1",
            "local_id": "D1",
            "source_type": "human_discussion",
            "source_refs": ["human_discussion:first-graph"],
            "operation": ["add_node"],
            "operation_type": "add_node",
            "evolution_type": "promote",
            "epistemic_effect": "clarifies",
            "summary": "Create the first project question.",
            "source_paper_nodes": [],
            "affected_nodes": ["project:NewProject:Q0"],
            "affected_links": [],
            "patch_ops": [
                {
                    "op": "add_node",
                    "node": {
                        "node_id": "project:NewProject:Q0",
                        "local_id": "Q0",
                        "node_type": "Question",
                        "text": "What is the first project question?",
                        "scope": "project",
                        "project_id": "NewProject",
                        "paper_id": None,
                        "status": "active",
                        "lifecycle_status": "active",
                        "confidence": "medium",
                        "human_review": "pending",
                        "source_refs": ["human_discussion:first-graph"],
                        "supersedes": [],
                        "superseded_by": [],
                        "derived_from": [],
                        "metadata": {"role": "first project question"},
                    },
                }
            ],
            "rationale": "Bootstrap the project graph through the normal human-gated delta path.",
            "caused_by": ["human_discussion:first-graph"],
            "supersedes": [],
            "confidence": "medium",
            "human_review": "pending",
        }

    def test_first_graph_add_node_dry_run_without_graph_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = self.first_graph_delta()

            dry_run = dry_run_graph_delta(root, "NewProject", delta)

            self.assertTrue(dry_run["valid"], dry_run)
            self.assertEqual(dry_run["preview"]["added_nodes"][0]["id"], "Q0")
            self.assertIn("empty project graph", " ".join(dry_run["warnings"]))

    def test_register_first_graph_delta_creates_read_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = self.first_graph_delta()

            registration = register_graph_delta(root, "NewProject", delta, actor="agent")
            open_deltas = query_open(root, "NewProject")

            self.assertTrue(registration["registered"], registration)
            self.assertTrue((root / "wiki" / "graphs" / "events" / "projects" / "NewProject.jsonl").exists())
            self.assertTrue((root / "wiki" / "graphs" / "graph.db").exists())
            self.assertIn("D1", open_deltas["open_deltas"])

    def test_accept_first_graph_delta_creates_first_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = self.first_graph_delta()

            register_graph_delta(root, "NewProject", delta, actor="agent")
            decision = decide_graph_delta(root, "NewProject", "D1", "accept", actor="human", decision_note="Approve first graph node.")
            node = query_node(root, "NewProject", "Q0")

            self.assertTrue(decision["applied"], decision)
            self.assertEqual(decision["events_appended"], 2)
            self.assertEqual(node["node"]["text"], "What is the first project question?")

    def test_first_graph_delta_can_add_nodes_and_link_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = self.first_graph_delta()
            delta["operation"] = ["add_node", "add_link"]
            delta["operation_type"] = "add_link"
            delta["affected_nodes"].append("project:NewProject:C0")
            delta["affected_links"] = ["project:NewProject:RL0"]
            delta["patch_ops"].append(
                {
                    "op": "add_node",
                    "node": {
                        "node_id": "project:NewProject:C0",
                        "local_id": "C0",
                        "node_type": "Claim",
                        "text": "First bootstrap claim.",
                        "scope": "project",
                        "project_id": "NewProject",
                        "paper_id": None,
                        "status": "active",
                        "lifecycle_status": "active",
                        "confidence": "medium",
                        "human_review": "pending",
                        "source_refs": ["human_discussion:first-graph"],
                        "supersedes": [],
                        "superseded_by": [],
                        "derived_from": [],
                        "metadata": {},
                    },
                }
            )
            delta["patch_ops"].append(
                {
                    "op": "add_link",
                    "link": {
                        "link_id": "project:NewProject:RL0",
                        "local_id": "RL0",
                        "link_type": "ReasoningLink",
                        "relation": "supports",
                        "from_nodes": ["project:NewProject:Q0"],
                        "to_nodes": ["project:NewProject:C0"],
                        "inline_warrant": "Bootstrap link only previews endpoints created in the same delta.",
                        "confidence": "medium",
                        "human_review": "pending",
                        "source_refs": ["human_discussion:first-graph"],
                    },
                }
            )

            dry_run = dry_run_graph_delta(root, "NewProject", delta)

            self.assertTrue(dry_run["valid"], dry_run)
            self.assertEqual(dry_run["preview"]["added_links"][0]["id"], "RL0")

    def test_register_and_accept_delta_updates_graph_state(self):
        temp_dir, root = self.make_workspace()
        self.addCleanup(temp_dir.cleanup)
        delta = load_delta_file(Path("examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json"))

        dry_run = dry_run_graph_delta(root, "DemoProject", delta)
        registration = register_graph_delta(root, "DemoProject", delta, actor="agent")
        open_deltas = query_open(root, "DemoProject")
        decision = decide_graph_delta(root, "DemoProject", "D1", "accept", actor="human", decision_note="Approved demo refinement.")
        node = query_node(root, "DemoProject", "C0")
        accepted_delta = query_delta(root, "DemoProject", "D1")

        self.assertTrue(dry_run["valid"], dry_run)
        self.assertEqual(dry_run["preview"]["updated_nodes"][0]["after"], "Demo claim is supported by demo evidence.")
        self.assertTrue(registration["registered"], registration)
        self.assertIn("D1", open_deltas["open_deltas"])
        self.assertTrue(decision["applied"], decision)
        self.assertEqual(decision["events_appended"], 2)
        self.assertEqual(node["node"]["text"], "Demo claim is supported by demo evidence.")
        self.assertEqual(accepted_delta["delta"]["lifecycle_status"], "accepted")

    def test_reject_delta_records_decision_without_content_update(self):
        temp_dir, root = self.make_workspace()
        self.addCleanup(temp_dir.cleanup)
        delta = json.loads(Path("examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json").read_text(encoding="utf-8"))
        delta["local_id"] = "D2"
        delta["delta_id"] = "project:DemoProject:D2"

        registration = register_graph_delta(root, "DemoProject", delta, actor="agent")
        decision = decide_graph_delta(root, "DemoProject", "D2", "reject", actor="human", decision_note="Rejected for demo.")
        node = query_node(root, "DemoProject", "C0")
        rejected_delta = query_delta(root, "DemoProject", "D2")

        self.assertTrue(registration["registered"], registration)
        self.assertTrue(decision["applied"], decision)
        self.assertEqual(decision["events_appended"], 1)
        self.assertEqual(node["node"]["text"], "Demo claim needs evidence.")
        self.assertEqual(rejected_delta["delta"]["lifecycle_status"], "rejected")


if __name__ == "__main__":
    unittest.main()
