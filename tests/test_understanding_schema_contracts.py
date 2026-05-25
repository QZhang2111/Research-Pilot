import json
import unittest
from pathlib import Path


class UnderstandingSchemaContractsTest(unittest.TestCase):
    def test_workspace_templates_include_understanding_contracts(self):
        schema_dir = Path("templates/workspace/wiki/understanding/schema")
        update_schema = json.loads((schema_dir / "understanding-update.schema.json").read_text(encoding="utf-8"))
        projection_schema = json.loads((schema_dir / "project-understanding.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(update_schema["$id"], "https://research-pilot.local/schema/understanding-update-v1")
        self.assertEqual(update_schema["properties"]["schema_version"]["const"], "understanding-update-v1")
        self.assertIn("read_source", update_schema["$defs"]["taskKind"]["enum"])
        self.assertIn("agent-inferred", update_schema["$defs"]["confidenceStatus"]["enum"])
        self.assertIn("skimmed", update_schema["$defs"]["sourceStatus"]["enum"])
        self.assertEqual(projection_schema["$id"], "https://research-pilot.local/schema/project-understanding-v1")
        self.assertEqual(projection_schema["properties"]["schema_version"]["const"], "project-understanding-v1")
        self.assertIn("recent_changes", projection_schema["required"])
        self.assertIn("next_moves", projection_schema["required"])

    def test_workspace_templates_keep_understanding_directories(self):
        root = Path("templates/workspace/wiki/understanding")
        self.assertTrue((root / "events" / ".gitkeep").is_file())
        self.assertTrue((root / "project-understanding" / ".gitkeep").is_file())


if __name__ == "__main__":
    unittest.main()
