import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tools.research_dataset import (
    SCHEMA_VERSION,
    connect_dataset,
    dataset_initialized,
    dataset_db_path,
    initialize_dataset,
    valid_project_id,
)


EXPECTED_TABLES = {
    "workspace",
    "schema_migrations",
    "projects",
    "sources",
    "understanding_nodes",
    "understanding_links",
    "understanding_link_endpoints",
    "experiments",
    "experiment_runs",
    "experiment_metrics",
    "experiment_artifacts",
    "literature_lanes",
    "literature_items",
    "literature_relations",
    "project_positionings",
    "activity_sessions",
    "updates",
    "audit_events",
    "entity_links",
}


class ResearchDatasetSchemaTest(unittest.TestCase):
    def test_initialize_creates_expected_tables_workspace_and_migration_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = initialize_dataset(root, workspace_id="test-workspace")
            with closing(connect_dataset(root)) as connection:
                tables = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                workspace = connection.execute("SELECT * FROM workspace").fetchall()
                migrations = connection.execute("SELECT * FROM schema_migrations").fetchall()

            self.assertEqual(dataset_db_path(root), path)
            self.assertTrue(dataset_initialized(root))
        self.assertEqual(EXPECTED_TABLES, tables)
        self.assertEqual(1, len(workspace))
        self.assertEqual("test-workspace", workspace[0]["workspace_id"])
        self.assertEqual(SCHEMA_VERSION, workspace[0]["schema_version"])
        self.assertTrue(workspace[0]["created_at"].endswith("Z"))
        self.assertTrue(workspace[0]["updated_at"].endswith("Z"))
        self.assertEqual("{}", workspace[0]["metadata_json"])
        self.assertEqual(1, len(migrations))
        self.assertEqual(SCHEMA_VERSION, migrations[0]["version"])
        self.assertTrue(migrations[0]["applied_at"].endswith("Z"))
        self.assertTrue(migrations[0]["description"])

    def test_initialize_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            first = initialize_dataset(root)
            second = initialize_dataset(root)
            with closing(connect_dataset(root)) as connection:
                workspace_count = connection.execute("SELECT COUNT(*) FROM workspace").fetchone()[0]
                migration_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

        self.assertEqual(first, second)
        self.assertEqual(1, workspace_count)
        self.assertEqual(1, migration_count)

    def test_valid_project_id_accepts_simple_id_and_rejects_path_like_or_empty_ids(self):
        self.assertTrue(valid_project_id("DemoVisualAffordance"))
        self.assertFalse(valid_project_id("../DemoVisualAffordance"))
        self.assertFalse(valid_project_id("nested/project"))
        self.assertFalse(valid_project_id(""))

    def test_connect_dataset_enables_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_dataset(root)

            with closing(connect_dataset(root)) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO sources (
                            source_id, project_id, source_type, title, created_at, updated_at
                        )
                        VALUES (
                            'source-1', 'missing-project', 'paper', 'Missing project source',
                            '2026-05-25T00:00:00Z', '2026-05-25T00:00:00Z'
                        )
                        """
                    )


if __name__ == "__main__":
    unittest.main()
