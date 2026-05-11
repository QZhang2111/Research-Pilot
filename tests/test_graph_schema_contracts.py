import json
import unittest
from pathlib import Path


class GraphSchemaContractsTest(unittest.TestCase):
    def test_workspace_templates_include_full_graph_contracts(self):
        schema_dir = Path("templates/workspace/wiki/graphs/schema")
        event_schema = json.loads((schema_dir / "graph-event.schema.json").read_text(encoding="utf-8"))
        snapshot_schema = json.loads((schema_dir / "graph-snapshot.schema.json").read_text(encoding="utf-8"))
        maintenance_schema = json.loads((schema_dir / "graph-maintenance.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(event_schema["$id"], "https://research-pilot.local/schema/graph-event-v1")
        self.assertIn("nodePayload", event_schema["$defs"])
        self.assertIn("linkPayload", event_schema["$defs"])
        self.assertIn("deltaPayload", event_schema["$defs"])
        self.assertEqual(snapshot_schema["$id"], "https://research-pilot.local/schema/graph-snapshot-v1")
        self.assertEqual(maintenance_schema["$id"], "https://research-pilot.local/schema/graph-maintenance-v1")
        self.assertIn("claimPath", maintenance_schema["$defs"])


if __name__ == "__main__":
    unittest.main()
