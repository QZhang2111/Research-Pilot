import json
import tempfile
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.build_graph_snapshot import main as build_snapshot_main


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


if __name__ == "__main__":
    unittest.main()
