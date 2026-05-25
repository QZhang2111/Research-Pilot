import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tools.research_dataset import connect_dataset, dataset_db_path, initialize_dataset
from tools.research_dataset_writer import DatasetValidationError, ProjectDatasetWriter


def _count(connection, table: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class ResearchDatasetWriterTest(unittest.TestCase):
    def test_write_project_source_node_link_and_audit_in_one_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)
            writer = ProjectDatasetWriter(root, actor="agent")

            result = writer.write_project_update(
                {
                    "project_id": "DemoProject",
                    "activity_type": "deep_read",
                    "summary": "Read source and update project graph.",
                    "project": {
                        "slug": "demo-project",
                        "title": "Demo Project",
                        "summary": "Demo summary",
                    },
                    "sources": [
                        {
                            "source_id": "S1",
                            "source_type": "paper",
                            "title": "Source One",
                        }
                    ],
                    "understanding_nodes": [
                        {
                            "node_id": "P-E1",
                            "scope": "paper",
                            "source_id": "S1",
                            "node_type": "evidence",
                            "text": "Paper evidence.",
                        },
                        {
                            "node_id": "C1",
                            "scope": "project",
                            "node_type": "claim",
                            "text": "Project claim.",
                        },
                        {
                            "node_id": "W1",
                            "scope": "project",
                            "node_type": "warrant",
                            "text": "Warrant.",
                        },
                        {
                            "node_id": "L1",
                            "scope": "project",
                            "node_type": "limitation",
                            "text": "Limitation.",
                        },
                    ],
                    "understanding_links": [
                        {
                            "link_id": "RL1",
                            "scope": "project",
                            "link_type": "reasoning",
                            "relation": "supports claim",
                            "endpoints": [
                                {"role": "from", "node_id": "P-E1"},
                                {"role": "to", "node_id": "C1"},
                                {"role": "warrant", "node_id": "W1"},
                                {"role": "limitation", "node_id": "L1"},
                            ],
                        }
                    ],
                }
            )

            with closing(connect_dataset(root)) as connection:
                audit_count = connection.execute(
                    "SELECT COUNT(*) FROM audit_events WHERE update_id = ?",
                    (result["update_id"],),
                ).fetchone()[0]
                counts = {
                    "projects": _count(connection, "projects"),
                    "sources": _count(connection, "sources"),
                    "nodes": _count(connection, "understanding_nodes"),
                    "links": _count(connection, "understanding_links"),
                    "endpoints": _count(connection, "understanding_link_endpoints"),
                    "activity_sessions": _count(connection, "activity_sessions"),
                    "updates": _count(connection, "updates"),
                }

        self.assertTrue(result["valid"])
        self.assertEqual("DemoProject", result["project_id"])
        self.assertGreaterEqual(result["audit_event_count"], 7)
        self.assertEqual(
            {
                "projects": 1,
                "sources": 1,
                "nodes": 4,
                "links": 1,
                "endpoints": 4,
                "activity_sessions": 1,
                "updates": 1,
            },
            counts,
        )
        self.assertEqual(result["audit_event_count"], audit_count)

    def test_invalid_warrant_endpoint_rolls_back_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = ProjectDatasetWriter(root, actor="agent")

            with self.assertRaises(DatasetValidationError):
                writer.write_project_update(
                    {
                        "project_id": "DemoProject",
                        "activity_type": "deep_read",
                        "summary": "Invalid endpoint.",
                        "project": {"slug": "demo-project", "title": "Demo Project"},
                        "understanding_nodes": [
                            {
                                "node_id": "C1",
                                "scope": "project",
                                "node_type": "claim",
                                "text": "Claim.",
                            },
                            {
                                "node_id": "E1",
                                "scope": "project",
                                "node_type": "evidence",
                                "text": "Evidence.",
                            },
                        ],
                        "understanding_links": [
                            {
                                "link_id": "RL1",
                                "scope": "project",
                                "link_type": "reasoning",
                                "relation": "supports",
                                "endpoints": [
                                    {"role": "from", "node_id": "E1"},
                                    {"role": "to", "node_id": "C1"},
                                    {"role": "warrant", "node_id": "C1"},
                                ],
                            }
                        ],
                    }
                )

            self.assertFalse(dataset_db_path(root).exists())
            initialize_dataset(root)
            with closing(connect_dataset(root)) as connection:
                project_count = _count(connection, "projects")
                audit_count = _count(connection, "audit_events")

        self.assertEqual(0, project_count)
        self.assertEqual(0, audit_count)

    def test_imported_paper_run_requires_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = ProjectDatasetWriter(root, actor="agent")

            with self.assertRaises(DatasetValidationError):
                writer.write_project_update(
                    {
                        "project_id": "DemoProject",
                        "activity_type": "experiment_import",
                        "summary": "Import experiment.",
                        "project": {"slug": "demo-project", "title": "Demo Project"},
                        "experiments": [
                            {
                                "experiment_id": "EXP1",
                                "title": "Experiment One",
                            }
                        ],
                        "experiment_runs": [
                            {
                                "run_id": "RUN1",
                                "experiment_id": "EXP1",
                                "origin_type": "imported_paper",
                            }
                        ],
                    }
                )

            self.assertFalse(dataset_db_path(root).exists())

    def test_same_packet_experiment_run_metric_succeeds_without_existing_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = ProjectDatasetWriter(root, actor="agent")

            result = writer.write_project_update(
                {
                    "project_id": "DemoProject",
                    "activity_type": "experiment_write",
                    "summary": "Write experiment run and metric.",
                    "experiments": [{"experiment_id": "EXP1", "title": "Experiment One"}],
                    "experiment_runs": [
                        {
                            "run_id": "RUN1",
                            "experiment_id": "EXP1",
                            "origin_type": "manual",
                        }
                    ],
                    "experiment_metrics": [
                        {
                            "metric_id": "M1",
                            "run_id": "RUN1",
                            "name": "accuracy",
                            "value_text": "0.75",
                        }
                    ],
                }
            )

            with closing(connect_dataset(root)) as connection:
                run_count = _count(connection, "experiment_runs")
                metric_count = _count(connection, "experiment_metrics")

        self.assertTrue(result["valid"])
        self.assertEqual(1, run_count)
        self.assertEqual(1, metric_count)

    def test_missing_from_endpoint_node_does_not_initialize_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = ProjectDatasetWriter(root, actor="agent")

            with self.assertRaises(DatasetValidationError):
                writer.write_project_update(
                    {
                        "project_id": "DemoProject",
                        "activity_type": "deep_read",
                        "summary": "Missing endpoint node.",
                        "understanding_nodes": [
                            {
                                "node_id": "C1",
                                "scope": "project",
                                "node_type": "claim",
                                "text": "Claim.",
                            }
                        ],
                        "understanding_links": [
                            {
                                "link_id": "RL1",
                                "scope": "project",
                                "link_type": "reasoning",
                                "relation": "supports",
                                "endpoints": [
                                    {"role": "from", "node_id": "E1"},
                                    {"role": "to", "node_id": "C1"},
                                ],
                            }
                        ],
                    }
                )

            self.assertFalse(dataset_db_path(root).exists())

    def test_missing_required_fields_do_not_initialize_dataset(self):
        cases = [
            (
                "missing source_id",
                {
                    "project_id": "DemoProject",
                    "activity_type": "write",
                    "summary": "Missing source id.",
                    "sources": [{"title": "No source id"}],
                },
            ),
            (
                "missing experiment_run experiment_id",
                {
                    "project_id": "DemoProject",
                    "activity_type": "write",
                    "summary": "Missing run experiment id.",
                    "experiment_runs": [{"run_id": "RUN1", "origin_type": "manual"}],
                },
            ),
            (
                "missing experiment_artifact run_id",
                {
                    "project_id": "DemoProject",
                    "activity_type": "write",
                    "summary": "Missing artifact run id.",
                    "experiment_artifacts": [
                        {
                            "artifact_id": "A1",
                            "artifact_type": "table",
                            "locator": "artifact.json",
                        }
                    ],
                },
            ),
            (
                "missing literature_relation endpoints",
                {
                    "project_id": "DemoProject",
                    "activity_type": "write",
                    "summary": "Missing relation endpoints.",
                    "literature_relations": [{"relation_id": "R1", "relation_type": "extends"}],
                },
            ),
            (
                "missing entity_link fields",
                {
                    "project_id": "DemoProject",
                    "activity_type": "write",
                    "summary": "Missing entity link fields.",
                    "entity_links": [
                        {
                            "from_entity_type": "source",
                            "from_entity_id": "S1",
                            "relation_type": "mentions",
                        }
                    ],
                },
            ),
        ]
        for name, packet in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    writer = ProjectDatasetWriter(root, actor="agent")

                    with self.assertRaises(DatasetValidationError):
                        writer.write_project_update(packet)

                    self.assertFalse(dataset_db_path(root).exists())


if __name__ == "__main__":
    unittest.main()
