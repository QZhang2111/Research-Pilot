import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.zotero_setup import prepare_env_files, zotero_status


class ZoteroSetupTest(unittest.TestCase):
    SECRET_ENV_LINE = "ZOTERO_API_KEY" + "=secret-value\n"
    WORKSPACE_SECRET_ENV_LINE = "ZOTERO_API_KEY" + "=workspace-secret\n"

    def test_prepare_env_files_creates_example_and_local_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = prepare_env_files(root)

            env_example = root / ".env.example"
            env = root / ".env"

            self.assertTrue(result["env_example_created"])
            self.assertTrue(result["env_created"])
            self.assertIn("ZOTERO_API_KEY=", env_example.read_text(encoding="utf-8"))
            self.assertIn("ZOTERO_API_KEY=", env.read_text(encoding="utf-8"))

    def test_prepare_env_files_creates_gitignore_for_local_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = prepare_env_files(root)

            gitignore = (root / ".gitignore").read_text(encoding="utf-8")

        self.assertTrue(result["gitignore_updated"])
        self.assertIn(".env\n", gitignore)
        self.assertIn(".env.local\n", gitignore)

    def test_prepare_env_files_updates_existing_gitignore_without_overwriting_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("existing-entry\n", encoding="utf-8")
            (root / ".env").write_text(self.SECRET_ENV_LINE, encoding="utf-8")

            result = prepare_env_files(root)
            gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            env_text = (root / ".env").read_text(encoding="utf-8")

        self.assertFalse(result["env_created"])
        self.assertTrue(result["gitignore_updated"])
        self.assertIn("existing-entry\n", gitignore)
        self.assertIn(".env\n", gitignore)
        self.assertIn(".env.local\n", gitignore)
        self.assertEqual(env_text, self.SECRET_ENV_LINE)
        self.assertNotIn("secret-value", str(result))

    def test_status_reads_workspace_env_without_printing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(self.SECRET_ENV_LINE, encoding="utf-8")

            result = zotero_status(root, validate=False)

        self.assertTrue(result["api_key_present"])
        self.assertEqual(result["mode"], "env-present")
        self.assertNotIn("secret-value", str(result))

    def test_status_uses_configured_library_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[zotero]\nlibrary_type = "users"\nlibrary_id = "123456"\n', encoding="utf-8")
            (root / ".env").write_text(self.SECRET_ENV_LINE, encoding="utf-8")

            result = zotero_status(root, validate=False)

        self.assertEqual(result["library_type"], "users")
        self.assertEqual(result["library_id"], "123456")
        self.assertFalse(result["api_key_valid"])

    def test_status_falls_back_to_process_env_without_printing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {
                "ZOTERO_API_KEY": "process-secret",
                "ZOTERO_LIBRARY_ID": "987654",
                "ZOTERO_LIBRARY_TYPE": "groups",
            }
            with patch.dict("os.environ", env, clear=False):
                result = zotero_status(root, validate=False)

        self.assertTrue(result["api_key_present"])
        self.assertTrue(result["configured"])
        self.assertEqual(result["library_type"], "groups")
        self.assertEqual(result["library_id"], "987654")
        self.assertEqual(result["mode"], "zotero-env")
        self.assertTrue(result["enabled"])
        self.assertTrue(result["library_id_present"])
        self.assertNotIn("process-secret", str(result))

    def test_status_defaults_library_type_to_user_for_process_env_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {
                "ZOTERO_API_KEY": "process-secret",
                "ZOTERO_LIBRARY_ID": "987654",
            }
            with patch.dict("os.environ", env, clear=True):
                result = zotero_status(root, validate=False)

        self.assertEqual(result["library_type"], "user")
        self.assertTrue(result["enabled"])
        self.assertTrue(result["library_id_present"])
        self.assertNotIn("process-secret", str(result))

    def test_status_prefers_workspace_env_and_config_over_process_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[zotero]\nlibrary_type = "users"\nlibrary_id = "123456"\n', encoding="utf-8")
            (root / ".env").write_text(self.WORKSPACE_SECRET_ENV_LINE, encoding="utf-8")
            env = {
                "ZOTERO_API_KEY": "process-secret",
                "ZOTERO_LIBRARY_ID": "987654",
                "ZOTERO_LIBRARY_TYPE": "groups",
            }

            with patch.dict("os.environ", env, clear=False):
                result = zotero_status(root, validate=False)

        self.assertEqual(result["library_type"], "users")
        self.assertEqual(result["library_id"], "123456")
        self.assertEqual(result["mode"], "env-present")
        self.assertNotIn("workspace-secret", str(result))
        self.assertNotIn("process-secret", str(result))


if __name__ == "__main__":
    unittest.main()
