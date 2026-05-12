import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.source_intake_cli import intake_source, source_refs_from_args, zotero_status


class SourceIntakeCliTest(unittest.TestCase):
    SECRET_ENV_LINE = "ZOTERO_API_KEY" + "=secret-value\n"

    def test_source_identity_refs_create_dossier_without_api_key(self):
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
            with patch.dict(os.environ, {}, clear=True):
                result = intake_source(args)
            dossier = Path(tmp) / "wiki" / "projects" / "DemoProject" / "papers" / "paper-a" / "index.md"
            text = dossier.read_text(encoding="utf-8")

        self.assertTrue(result["valid"], result)
        self.assertIn("zotero:item:ABC123", result["source_refs"])
        self.assertIn("doi:10.000/demo", result["source_refs"])
        self.assertIn("zotero:item:ABC123", text)
        self.assertIn("manual-source-identity", result["zotero"]["mode"])

    def test_source_refs_order_prefers_zotero_then_doi_arxiv_url(self):
        args = Namespace(zotero_key="Z", doi="D", arxiv="A", url="U", source_ref=["S"])

        refs = source_refs_from_args(args)

        self.assertEqual(refs, ["zotero:item:Z", "doi:D", "arxiv:A", "U", "S"])

    def test_zotero_status_reports_manual_identity_mode_without_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            status = zotero_status()

        self.assertEqual(status["mode"], "manual-source-identity")

    def test_zotero_status_reads_workspace_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(self.SECRET_ENV_LINE, encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                status = zotero_status(str(root))

        self.assertTrue(status["api_key_present"])
        self.assertNotIn("secret-value", str(status))

    def test_zotero_status_falls_back_to_process_env_with_compatibility_aliases(self):
        env = {
            "ZOTERO_API_KEY": "process-secret",
            "ZOTERO_LIBRARY_ID": "987654",
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, env, clear=True):
                status = zotero_status(tmp)

        self.assertTrue(status["enabled"])
        self.assertTrue(status["library_id_present"])
        self.assertEqual(status["library_type"], "user")
        self.assertEqual(status["mode"], "zotero-env")
        self.assertNotIn("process-secret", str(status))


if __name__ == "__main__":
    unittest.main()
