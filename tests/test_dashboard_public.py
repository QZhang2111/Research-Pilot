import json
import tempfile
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.build_graph_db import main as build_graph_db_main
from tools.build_graph_snapshot import main as build_snapshot_main
from tools.research_browser_server import handle_project_graph_maintenance_request


class DashboardPublicTest(unittest.TestCase):
    def test_build_index_exposes_graph_only_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            event_path.parent.mkdir(parents=True)
            event_path.write_text(Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            build_snapshot_main(["--repo", str(root), "--project", "DemoProject", "--generated-at", "2026-05-11T00:01:00Z"])

            index = build_index(root)

        self.assertEqual(index["projects"][0]["id"], "DemoProject")
        self.assertEqual(index["project_graphs"][0]["project"], "DemoProject")
        self.assertEqual(index["project_graphs"][0]["nodes"][0]["id"], "C0")
        json.dumps(index)

    def test_project_graph_maintenance_api_serves_read_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            event_path.parent.mkdir(parents=True)
            event_path.write_text(Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            build_graph_db_main(["--repo", str(root), "--project", "DemoProject"])

            status, payload = handle_project_graph_maintenance_request(root, "/api/project-graph-maintenance?project=DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["schema_version"], "graph-maintenance-v1")
        self.assertEqual(model["project"], "DemoProject")
        self.assertEqual([delta["id"] for delta in model["open_deltas"]], ["D0"])
        self.assertEqual([delta["id"] for delta in model["review_queue"]["deltas"]], ["D0"])
        self.assertEqual(model["claim_paths"][0]["claim"]["id"], "C0")
        self.assertEqual(model["claim_paths"][0]["supporting_links"][0]["premises"][0]["id"], "E0")


if __name__ == "__main__":
    unittest.main()
