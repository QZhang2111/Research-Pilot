import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.research_browser_server import (
    handle_experiment_proposals_request,
    handle_experiments_request,
    handle_project_graph_request,
)
from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"


class ResearchBrowserDbFallbackTest(unittest.TestCase):
    def _copy_demo(self, tmp: str) -> Path:
        root = Path(tmp) / "example-workspace"
        shutil.copytree(DEMO_ROOT, root, ignore=shutil.ignore_patterns("research-pilot.db"))
        return root

    def _copy_imported_demo(self, tmp: str) -> Path:
        root = self._copy_demo(tmp)
        initialize_dataset(root)
        import_demo_visual_affordance(root, reset=True)
        return root

    def test_experiments_endpoint_prefers_db_when_project_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            status, payload = handle_experiments_request(root, f"/api/experiments?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertEqual("project_experiments_from_research_dataset", model["source_boundary"])
        self.assertEqual(4, model["summary"]["total_experiments"])
        self.assertEqual(5, model["summary"]["imported_evidence_runs"])

    def test_experiments_endpoint_falls_back_to_legacy_without_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)

            status, payload = handle_experiments_request(root, f"/api/experiments?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertEqual("project_experiments_read_model_not_graph_truth", model["source_boundary"])
        self.assertEqual(4, model["summary"]["total_experiments"])

    def test_experiments_endpoint_rejects_invalid_project_id_without_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)

            with mock.patch("tools.research_browser_server.build_project_experiments") as legacy_builder:
                status, payload = handle_experiments_request(root, "/api/experiments?project=../DemoVisualAffordance")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(404, status)
        self.assertEqual("Not Found", model["error"])
        legacy_builder.assert_not_called()

    def test_experiments_endpoint_falls_back_to_legacy_when_db_builder_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            with mock.patch("tools.research_browser_server.build_experiments_model", side_effect=ValueError("bad DB model")):
                status, payload = handle_experiments_request(root, f"/api/experiments?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertEqual("project_experiments_read_model_not_graph_truth", model["source_boundary"])
        self.assertEqual(4, model["summary"]["total_experiments"])

    def test_project_graph_endpoint_prefers_db_when_project_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            status, payload = handle_project_graph_request(root, f"/api/project-graph?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertEqual("research-pilot.db", model["source"])
        self.assertGreaterEqual({node["kind"] for node in model["nodes"]}, {"question", "claim", "evidence", "warrant", "limitation"})

    def test_project_graph_endpoint_falls_back_to_legacy_when_db_builder_returns_non_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            with mock.patch("tools.research_browser_server.build_project_graph_model", return_value=[]):
                status, payload = handle_project_graph_request(root, f"/api/project-graph?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertNotEqual("research-pilot.db", model.get("source"))

    def test_project_graph_endpoint_falls_back_to_legacy_when_db_builder_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            with mock.patch("tools.research_browser_server.build_project_graph_model", side_effect=ValueError("bad DB model")):
                status, payload = handle_project_graph_request(root, f"/api/project-graph?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertNotEqual("research-pilot.db", model.get("source"))

    def test_experiment_proposals_wrapper_uses_db_experiments_model_when_project_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_imported_demo(tmp)

            status, payload = handle_experiment_proposals_request(root, f"/api/experiment-proposals?project={PROJECT_ID}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(200, status)
        self.assertEqual("experiment-proposals-v1", model["schema_version"])
        self.assertEqual("project_experiments_from_research_dataset", model["experiments_model"]["source_boundary"])


if __name__ == "__main__":
    unittest.main()
