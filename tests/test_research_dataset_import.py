import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tools.research_dataset import connect_dataset, initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces"


class ResearchDatasetImportTest(unittest.TestCase):
    def _copy_demo(self, tmp: str) -> Path:
        root = Path(tmp) / "example-workspace"
        shutil.copytree(DEMO_ROOT, root)
        return root

    def test_import_demo_visual_affordance_preserves_core_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)
            initialize_dataset(root)

            result = import_demo_visual_affordance(root, reset=True)

            with closing(connect_dataset(root)) as connection:
                project = connection.execute(
                    "SELECT title FROM projects WHERE project_id = ?",
                    ("DemoVisualAffordance",),
                ).fetchone()
                node_counts = dict(
                    connection.execute(
                        """
                        SELECT node_type, COUNT(*) AS count
                        FROM understanding_nodes
                        WHERE project_id = ? AND scope = 'project'
                        GROUP BY node_type
                        """,
                        ("DemoVisualAffordance",),
                    ).fetchall()
                )
                endpoint_role_counts = dict(
                    connection.execute(
                        """
                        SELECT role, COUNT(*) AS count
                        FROM understanding_link_endpoints
                        JOIN understanding_links
                          ON understanding_links.project_id = understanding_link_endpoints.project_id
                         AND understanding_links.link_id = understanding_link_endpoints.link_id
                        WHERE understanding_link_endpoints.project_id = ?
                          AND understanding_links.scope = 'project'
                        GROUP BY role
                        """,
                        ("DemoVisualAffordance",),
                    ).fetchall()
                )
                rl1_endpoints = [
                    (row["role"], row["node_id"], row["position"])
                    for row in connection.execute(
                        """
                        SELECT role, node_id, position
                        FROM understanding_link_endpoints
                        WHERE project_id = ? AND link_id = ?
                        ORDER BY role, position
                        """,
                        ("DemoVisualAffordance", "project:DemoVisualAffordance:RL1"),
                    )
                ]

        self.assertTrue(result["valid"])
        self.assertEqual("DemoVisualAffordance", result["project_id"])
        self.assertGreaterEqual(result["sources"], 9)
        self.assertGreaterEqual(result["understanding_nodes"], 20)
        self.assertGreaterEqual(result["understanding_links"], 6)
        self.assertEqual(4, result["experiments"])
        self.assertEqual(5, result["experiment_runs"])
        self.assertGreaterEqual(result["literature_lanes"], 4)
        self.assertGreaterEqual(result["literature_items"], 9)
        self.assertEqual("Demo Visual Affordance", project["title"])
        self.assertEqual(3, node_counts.get("question", 0))
        self.assertEqual(4, node_counts.get("claim", 0))
        self.assertEqual(8, node_counts.get("evidence", 0))
        self.assertEqual(4, node_counts.get("warrant", 0))
        self.assertEqual(5, node_counts.get("limitation", 0))
        self.assertEqual(
            {"from": 16, "to": 7, "warrant": 7, "limitation": 13},
            endpoint_role_counts,
        )
        self.assertEqual(
            [
                ("from", "project:DemoVisualAffordance:E1", 0),
                ("from", "project:DemoVisualAffordance:E2", 1),
                ("from", "project:DemoVisualAffordance:E5", 2),
                ("from", "project:DemoVisualAffordance:E8", 3),
                ("limitation", "project:DemoVisualAffordance:L1", 0),
                ("limitation", "project:DemoVisualAffordance:L3", 1),
                ("to", "project:DemoVisualAffordance:C2", 0),
                ("warrant", "project:DemoVisualAffordance:W2", 0),
            ],
            rl1_endpoints,
        )

    def test_import_demo_preserves_experiment_origin_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)
            initialize_dataset(root)

            import_demo_visual_affordance(root, reset=True)

            with closing(connect_dataset(root)) as connection:
                origins = dict(
                    connection.execute(
                        """
                        SELECT origin_type, COUNT(*) AS count
                        FROM experiment_runs
                        WHERE project_id = ?
                        GROUP BY origin_type
                        """,
                        ("DemoVisualAffordance",),
                    ).fetchall()
                )
                metrics = {
                    (row["run_id"], row["name"]): row["value_numeric"]
                    for row in connection.execute(
                        """
                        SELECT run_id, name, value_numeric
                        FROM experiment_metrics
                        WHERE project_id = ?
                        """,
                        ("DemoVisualAffordance",),
                    )
                }
                produced_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM entity_links
                    WHERE project_id = ?
                      AND from_entity_type = 'experiment_run'
                      AND to_entity_type = 'understanding_node'
                      AND relation_type = 'produces'
                    """,
                    ("DemoVisualAffordance",),
                ).fetchone()[0]

        self.assertEqual(5, origins.get("imported_paper"))
        self.assertNotIn("local", origins)
        self.assertEqual(1.825, metrics[("RUN2", "KLD")])
        self.assertEqual(1.493, metrics[("RUN3", "KLD")])
        self.assertEqual(0.326, metrics[("RUN3", "SIM")])
        self.assertEqual(1.090, metrics[("RUN3", "NSS")])
        self.assertEqual(5, produced_count)

    def test_import_is_idempotent_with_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)
            initialize_dataset(root)

            first = import_demo_visual_affordance(root, reset=True)
            second = import_demo_visual_affordance(root, reset=True)

            with closing(connect_dataset(root)) as connection:
                experiment_count = connection.execute(
                    "SELECT COUNT(*) FROM experiments WHERE project_id = ?",
                    ("DemoVisualAffordance",),
                ).fetchone()[0]
                project_count = connection.execute(
                    "SELECT COUNT(*) FROM projects WHERE project_id = ?",
                    ("DemoVisualAffordance",),
                ).fetchone()[0]

        self.assertEqual(first["experiments"], second["experiments"])
        self.assertEqual(4, experiment_count)
        self.assertEqual(1, project_count)

    def test_import_preserves_understanding_update_as_activity_and_safe_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)
            initialize_dataset(root)

            result = import_demo_visual_affordance(root, reset=True)

            with closing(connect_dataset(root)) as connection:
                update = connection.execute(
                    """
                    SELECT update_id, summary, confidence
                    FROM updates
                    WHERE project_id = ? AND update_id = ?
                    """,
                    ("DemoVisualAffordance", "UU-demo-0001"),
                ).fetchone()
                audit = connection.execute(
                    """
                    SELECT operation, entity_type, entity_id
                    FROM audit_events
                    WHERE project_id = ?
                      AND entity_type = 'understanding_update'
                      AND entity_id = ?
                    """,
                    ("DemoVisualAffordance", "UU-demo-0001"),
                ).fetchone()
                source = connection.execute(
                    """
                    SELECT source_id, reading_depth
                    FROM sources
                    WHERE project_id = ? AND source_id = ?
                    """,
                    ("DemoVisualAffordance", "S-demo-luo2022-agd20k"),
                ).fetchone()
                evidence = connection.execute(
                    """
                    SELECT node_id, scope, node_type
                    FROM understanding_nodes
                    WHERE project_id = ? AND node_id = ?
                    """,
                    ("DemoVisualAffordance", "E-demo-agd20k-indirect"),
                ).fetchone()
                run_node = connection.execute(
                    """
                    SELECT node_id, scope, node_type
                    FROM understanding_nodes
                    WHERE project_id = ? AND node_id = ?
                    """,
                    ("DemoVisualAffordance", "run:RUN1:evidence"),
                ).fetchone()
                gap_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM understanding_nodes
                    WHERE project_id = ? AND node_type = 'gap'
                    """,
                    ("DemoVisualAffordance",),
                ).fetchone()[0]

        self.assertGreaterEqual(result["sources"], 10)
        self.assertIsNotNone(update)
        self.assertEqual("agent-inferred", update["confidence"])
        self.assertIsNotNone(audit)
        self.assertEqual("import", audit["operation"])
        self.assertEqual("understanding_update", audit["entity_type"])
        self.assertIsNotNone(source)
        self.assertEqual("lightweight_update", source["reading_depth"])
        self.assertIsNotNone(evidence)
        self.assertEqual("update", evidence["scope"])
        self.assertEqual("evidence", evidence["node_type"])
        self.assertIsNotNone(run_node)
        self.assertEqual("experiment", run_node["scope"])
        self.assertEqual("evidence", run_node["node_type"])
        self.assertEqual(0, gap_count)

    def test_import_preserves_paper_understanding_as_paper_scope_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)
            initialize_dataset(root)

            import_demo_visual_affordance(root, reset=True)

            with closing(connect_dataset(root)) as connection:
                node_counts = dict(
                    connection.execute(
                        """
                        SELECT node_type, COUNT(*) AS count
                        FROM understanding_nodes
                        WHERE project_id = ? AND scope = 'paper' AND source_id = ?
                        GROUP BY node_type
                        """,
                        ("DemoVisualAffordance", "paper:do2017-affordancenet"),
                    ).fetchall()
                )
                paper_links = list(
                    connection.execute(
                        """
                        SELECT link_id, scope, link_type, relation
                        FROM understanding_links
                        WHERE project_id = ? AND scope = 'paper' AND link_id LIKE ?
                        """,
                        ("DemoVisualAffordance", "paper-link:paper:do2017-affordancenet:%"),
                    )
                )

        self.assertEqual(
            {"question": 1, "claim": 1, "evidence": 1, "warrant": 1, "limitation": 1},
            node_counts,
        )
        self.assertEqual(1, len(paper_links))
        self.assertEqual("reasoning", paper_links[0]["link_type"])

    def test_cli_init_import_and_summary_return_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy_demo(tmp)

            init = subprocess.run(
                [
                    sys.executable,
                    "tools/research_dataset_cli.py",
                    "init",
                    "--repo",
                    str(root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            init_result = json.loads(init.stdout)
            self.assertTrue(init_result["valid"])

            imported = subprocess.run(
                [
                    sys.executable,
                    "tools/research_dataset_cli.py",
                    "import-legacy",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoVisualAffordance",
                    "--reset",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            import_result = json.loads(imported.stdout)
            self.assertEqual("DemoVisualAffordance", import_result["project_id"])

            summary = subprocess.run(
                [
                    sys.executable,
                    "tools/research_dataset_cli.py",
                    "summary",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoVisualAffordance",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            summary_result = json.loads(summary.stdout)
            self.assertTrue(summary_result["valid"])
            self.assertEqual("DemoVisualAffordance", summary_result["project_id"])
            self.assertEqual("research-pilot.db", summary_result["source"])


if __name__ == "__main__":
    unittest.main()
