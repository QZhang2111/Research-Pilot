import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.source_intake_cli import intake_source, source_refs_from_args, zotero_status


class SourceIntakeCliTest(unittest.TestCase):
    def test_manual_and_zotero_identity_refs_create_dossier_without_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = Namespace(
                repo=tmp,
                project="DemoProject",
                paper="paper-a",
                title="Paper A",
                zotero_key="ABC123",
                doi="10.000/demo",
                arxiv="2605.00001",
                url="https://example.org/paper",
                source_ref=[],
                overwrite=False,
            )
            result = intake_source(args)
            dossier = Path(tmp) / "wiki" / "projects" / "DemoProject" / "papers" / "paper-a" / "index.md"
            text = dossier.read_text(encoding="utf-8")

        self.assertTrue(result["valid"], result)
        self.assertIn("zotero:item:ABC123", result["source_refs"])
        self.assertIn("doi:10.000/demo", result["source_refs"])
        self.assertIn("zotero:item:ABC123", text)
        self.assertIn("manual-fallback", result["zotero"]["mode"])

    def test_source_refs_order_prefers_zotero_then_doi_arxiv_url(self):
        args = Namespace(zotero_key="Z", doi="D", arxiv="A", url="U", source_ref=["S"])

        refs = source_refs_from_args(args)

        self.assertEqual(refs, ["zotero:item:Z", "doi:D", "arxiv:A", "U", "S"])

    def test_zotero_status_has_no_key_fallback(self):
        status = zotero_status()

        self.assertIn(status["mode"], {"manual-fallback", "zotero-env"})


if __name__ == "__main__":
    unittest.main()
