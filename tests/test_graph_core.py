import json
import tempfile
import unittest
from pathlib import Path

from tools.graph_store import build_graph_db_from_event_files, build_snapshot_from_event_files, validate_event_files
from tools.graph_query_cli import query_link, query_node, query_open, query_summary


def demo_events() -> list[dict]:
    return [
        json.loads(line)
        for line in Path("examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class GraphCoreTest(unittest.TestCase):
    def test_validate_demo_events(self):
        result = validate_event_files([Path("examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl")])

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["event_count"], 4)

    def test_build_snapshot_from_demo_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "demo.jsonl"
            event_path.write_text("\n".join(json.dumps(event) for event in demo_events()) + "\n", encoding="utf-8")

            snapshot = build_snapshot_from_event_files([event_path], generated_at="2026-05-11T00:01:00Z")

        self.assertEqual(snapshot["schema_version"], "graph-snapshot-v1")
        self.assertEqual(snapshot["graph_id"], "project:DemoProject")
        self.assertEqual(len(snapshot["nodes"]), 2)
        self.assertEqual(len(snapshot["links"]), 1)
        self.assertEqual(len(snapshot["deltas"]), 1)
        self.assertEqual(snapshot["deltas"][0]["lifecycle_status"], "proposed")

    def test_build_db_and_query_demo_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            event_path.parent.mkdir(parents=True)
            event_path.write_text("\n".join(json.dumps(event) for event in demo_events()) + "\n", encoding="utf-8")
            stats = build_graph_db_from_event_files([event_path], root / "wiki" / "graphs" / "graph.db")

            node = query_node(root, "DemoProject", "C0")
            link = query_link(root, "DemoProject", "RL0")
            open_deltas = query_open(root, "DemoProject")
            summary = query_summary(root, "DemoProject")

        self.assertEqual(stats["events"], 4)
        self.assertEqual(stats["nodes"], 2)
        self.assertEqual(stats["links"], 1)
        self.assertEqual(stats["deltas"], 1)
        self.assertEqual(node["node"]["text"], "Demo claim needs evidence.")
        self.assertEqual(link["link"]["from_nodes"], ["E0"])
        self.assertEqual(open_deltas["open_deltas"], ["D0"])
        self.assertEqual(summary["node_counts"], {"Claim": 1, "Evidence": 1})


if __name__ == "__main__":
    unittest.main()
