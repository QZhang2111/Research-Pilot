import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_dossier_cli import create_dossier, export_deltas, validate_dossier


class PaperDossierCliTest(unittest.TestCase):
    def test_create_validate_and_export_dossier_delta_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_result = create_dossier(root, "DemoProject", "paper-a", "Paper A", "doi:10.000/demo", overwrite=False)
            dossier = root / create_result["path"]
            validation = validate_dossier(dossier)
            output_dir = root / "deltas"
            export_result = export_deltas(dossier, output_dir)
            exported = json.loads((output_dir / "D1.json").read_text(encoding="utf-8"))

        self.assertTrue(create_result["created"], create_result)
        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["delta_count"], 1)
        self.assertTrue(export_result["valid"], export_result)
        self.assertEqual(exported["source_type"], "paper_dossier")
        self.assertEqual(exported["source_dossier"], "wiki/projects/DemoProject/papers/paper-a/index.md")


if __name__ == "__main__":
    unittest.main()
