import json
import tempfile
import unittest
from pathlib import Path

from tools.research_pilot_status import inspect_workspace
from tools.research_pilot_init import main as init_workspace_main


class ResearchPilotStatusTest(unittest.TestCase):
    def test_plugin_repo_stage(self):
        result = inspect_workspace(Path("."))

        self.assertEqual(result["stage"], "plugin_repo")
        self.assertFalse(result["valid_workspace"])
        self.assertEqual(result["next_actions"][0]["id"], "initialize_workspace")

    def test_empty_workspace_stage_after_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])

            result = inspect_workspace(root)

        self.assertTrue(result["valid_workspace"])
        self.assertEqual(result["stage"], "empty_workspace")
        self.assertEqual(result["projects"], [])
        self.assertEqual(result["next_actions"][0]["id"], "create_project_shell")

    def test_project_shell_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\nmaturity_stage: project_shell\nhuman_review: pending\n---\n# Demo Project\n",
                encoding="utf-8",
            )

            result = inspect_workspace(root)

        self.assertEqual(result["stage"], "project_shell")
        self.assertEqual(result["projects"][0]["id"], "DemoProject")
        self.assertEqual(result["projects"][0]["title"], "Demo Project")
        self.assertEqual(result["next_actions"][0]["id"], "configure_zotero_or_add_baselines")

    def test_project_has_graph_stage_when_project_events_exist_without_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\nmaturity_stage: project_shell\nhuman_review: pending\n---\n# Demo Project\n",
                encoding="utf-8",
            )
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text('{"event_id":"E0"}\n', encoding="utf-8")

            result = inspect_workspace(root)

        self.assertEqual(result["stage"], "project_has_graph")
        self.assertTrue(result["projects"][0]["has_graph_events"])

    def test_open_deltas_count_project_event_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text(
                json.dumps(
                    {
                        "event_id": "E0",
                        "event_type": "delta.proposed",
                        "payload": {
                            "delta_id": "project:DemoProject:D1",
                            "local_id": "D1",
                            "status": "proposed",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = inspect_workspace(root)

        self.assertEqual(result["open_deltas"], 1)

    def test_open_deltas_do_not_merge_same_local_id_across_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            events_root = root / "wiki" / "graphs" / "events" / "projects"
            events_root.mkdir(parents=True)
            for project_id in ["ProjectA", "ProjectB"]:
                (events_root / f"{project_id}.jsonl").write_text(
                    json.dumps(
                        {
                            "event_id": f"{project_id}-E0",
                            "event_type": "delta.proposed",
                            "payload": {
                                "delta_id": f"project:{project_id}:D1",
                                "local_id": "D1",
                                "lifecycle_status": "proposed",
                            },
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            result = inspect_workspace(root)

        self.assertEqual(result["open_deltas"], 2)

    def test_read_models_stale_when_events_newer_than_dashboard_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text('{"event_id":"E0"}\n', encoding="utf-8")
            dashboard = root / ".dashboard" / "index.json"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("{}", encoding="utf-8")
            events.touch()

            result = inspect_workspace(root)

        self.assertEqual(result["read_models"]["dashboard_index"], "stale")
        self.assertEqual(result["stage"], "read_models_stale")

    def test_status_json_is_serializable_and_masks_zotero_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            (root / ".env").write_text("ZOTERO_API_KEY=" + "secret-value\n", encoding="utf-8")

            result = inspect_workspace(root)
            encoded = json.dumps(result)

        self.assertIn('"api_key_present": true', encoded)
        self.assertNotIn("secret-value", encoded)


if __name__ == "__main__":
    unittest.main()
