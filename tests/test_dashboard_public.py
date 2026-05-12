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

    def test_project_card_prefers_overview_display_title_over_query_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Overview\ndisplay_title: Demo Display Title\ntype: project-overview\nmaturity_stage: project_shell\n---\n"
                "# Demo Display Title\n\n## Project Direction\n\nBroad direction.\n\n## Seed Questions\n\n- Setup prompt\n",
                encoding="utf-8",
            )
            (project / "project-query-pack.md").write_text(
                "---\ntitle: Demo Query Pack\ntype: project-query-pack\n---\n# Demo Query Pack\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["title"], "Demo Display Title")
        self.assertEqual(index["projects"][0]["overview"]["seed_questions"], ["Setup prompt"])
        self.assertEqual(index["projects"][0]["overview"]["accepted_questions"], [])
        self.assertNotIn("Setup prompt", index["projects"][0]["overview"]["current_questions"])

    def test_project_card_uses_query_pack_title_when_overview_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "project-query-pack.md").write_text(
                "---\ntitle: Demo Query Pack\ntype: project-query-pack\n---\n# Demo Query Pack\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["title"], "Demo Query Pack")

    def test_dashboard_accepted_questions_come_from_graph_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo\n\n## Search Questions\n\n- Search prompt\n",
                encoding="utf-8",
            )
            (project / "project-understanding-graph.md").write_text(
                "---\ntitle: Demo Graph\ntype: project-understanding-graph\n---\n"
                "# Demo Graph\n\n## Project Questions\n\n"
                "| ID | Question | Role | Status | Confidence | Human Review | Source Refs | Bounds |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q0 | Does the model encode interaction knowledge? | main | active | medium | accepted | human | none |\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(
            index["projects"][0]["overview"]["accepted_questions"],
            ["Does the model encode interaction knowledge?"],
        )
        self.assertEqual(index["projects"][0]["overview"]["search_questions"], ["Search prompt"])

    def test_dashboard_pending_active_graph_questions_are_not_accepted_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo\n",
                encoding="utf-8",
            )
            (project / "project-understanding-graph.md").write_text(
                "---\ntitle: Demo Graph\ntype: project-understanding-graph\n---\n"
                "# Demo Graph\n\n## Project Questions\n\n"
                "| ID | Question | Role | Status | Confidence | Human Review | Source Refs | Bounds |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q0 | Does the model encode interaction knowledge? | main | active | medium | pending | human | none |\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["overview"]["accepted_questions"], [])
        self.assertNotIn(
            "Does the model encode interaction knowledge?",
            index["projects"][0]["overview"]["current_questions"],
        )


if __name__ == "__main__":
    unittest.main()
