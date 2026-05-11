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
        event_path.write_text(Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        build_db_main(["--repo", str(root), "--project", "DemoProject"])
        return temp_dir, root

    def test_register_and_accept_delta_updates_graph_state(self):
        temp_dir, root = self.make_workspace()
        self.addCleanup(temp_dir.cleanup)
        delta = load_delta_file(Path("examples/demo/deltas/refine-demo-claim.json"))

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
        delta = json.loads(Path("examples/demo/deltas/refine-demo-claim.json").read_text(encoding="utf-8"))
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
