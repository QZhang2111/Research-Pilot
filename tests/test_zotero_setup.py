import contextlib
import io
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.zotero_setup import ensure_collection_tree, main, prepare_env_files, write_zotero_config, zotero_status


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

    def test_ensure_collections_uses_configured_group_target_after_key_validation(self):
        targets = []

        class FakeZoteroClient(FakeCollectionClient):
            def __init__(self, *, library_id, library_type="users", api_key=""):
                targets.append({"library_id": library_id, "library_type": library_type, "api_key_present": bool(api_key)})
                super().__init__()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[zotero]\nlibrary_type = "groups"\nlibrary_id = "GROUP123"\n', encoding="utf-8")
            (root / ".env").write_text(self.SECRET_ENV_LINE, encoding="utf-8")

            with patch("tools.zotero_setup.validate_key", return_value={"library_type": "users", "library_id": "USER999"}):
                with patch("tools.zotero_bridge.ZoteroClient", FakeZoteroClient):
                    with contextlib.redirect_stdout(io.StringIO()):
                        exit_code = main(["ensure-collections", "--repo", str(root), "--json"])
            text = config.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(targets, [{"library_id": "GROUP123", "library_type": "groups", "api_key_present": True}])
        self.assertIn('library_type = "groups"', text)
        self.assertIn('library_id = "GROUP123"', text)
        self.assertNotIn("USER999", text)


class FakeCollectionClient:
    def __init__(self, collections=None):
        self.collections = list(collections or [])
        self.created = []

    def fetch_collections(self):
        return self.collections

    def create_collection(self, name, parent_collection=""):
        key = f"KEY{len(self.collections) + 1:03d}"
        record = {"key": key, "data": {"key": key, "name": name, "parentCollection": parent_collection or False}}
        self.collections.append(record)
        self.created.append((name, parent_collection, key))
        return record


class ZoteroCollectionTreeTest(unittest.TestCase):
    def test_ensure_collection_tree_creates_standard_tree(self):
        client = FakeCollectionClient()

        result = ensure_collection_tree(client)

        names = [item[0] for item in client.created]
        self.assertEqual(
            names,
            ["Research_Pilot", "00 Inbox", "10 Projects", "20 Research Areas", "30 Review Campaigns", "90 Archive"],
        )
        self.assertEqual(
            result,
            {
                "root_collection_key": "KEY001",
                "inbox_collection_key": "KEY002",
                "projects_collection_key": "KEY003",
                "areas_collection_key": "KEY004",
                "campaigns_collection_key": "KEY005",
                "archive_collection_key": "KEY006",
            },
        )

    def test_ensure_collection_tree_reuses_existing_root(self):
        client = FakeCollectionClient(
            [{"key": "ROOT1", "data": {"key": "ROOT1", "name": "Research_Pilot", "parentCollection": False}}]
        )

        result = ensure_collection_tree(client)

        self.assertEqual(result["root_collection_key"], "ROOT1")
        self.assertNotIn(("Research_Pilot", "", "KEY002"), client.created)

    def test_ensure_collection_tree_reuses_existing_standard_tree(self):
        client = FakeCollectionClient(
            [
                {"key": "ROOT1", "data": {"key": "ROOT1", "name": "Research_Pilot", "parentCollection": False}},
                {"key": "INBOX1", "data": {"key": "INBOX1", "name": "00 Inbox", "parentCollection": "ROOT1"}},
                {"key": "PROJECTS1", "data": {"key": "PROJECTS1", "name": "10 Projects", "parentCollection": "ROOT1"}},
                {"key": "AREAS1", "data": {"key": "AREAS1", "name": "20 Research Areas", "parentCollection": "ROOT1"}},
                {"key": "CAMPAIGNS1", "data": {"key": "CAMPAIGNS1", "name": "30 Review Campaigns", "parentCollection": "ROOT1"}},
                {"key": "ARCHIVE1", "data": {"key": "ARCHIVE1", "name": "90 Archive", "parentCollection": "ROOT1"}},
            ]
        )

        result = ensure_collection_tree(client)

        self.assertEqual(client.created, [])
        self.assertEqual(
            result,
            {
                "root_collection_key": "ROOT1",
                "inbox_collection_key": "INBOX1",
                "projects_collection_key": "PROJECTS1",
                "areas_collection_key": "AREAS1",
                "campaigns_collection_key": "CAMPAIGNS1",
                "archive_collection_key": "ARCHIVE1",
            },
        )

    def test_write_zotero_config_persists_non_secret_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "library_id": "123456",
                    "root_collection_key": "ROOT1",
                    "ZOTERO_API_KEY": "secret-value",
                    "api_key": "other-secret",
                },
            )
            text = (root / ".research-pilot" / "config.toml").read_text(encoding="utf-8")

        self.assertIn('library_type = "users"', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('root_collection_key = "ROOT1"', text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("secret-value", text)
        self.assertNotIn("other-secret", text)

    def test_write_zotero_config_preserves_existing_zotero_non_secret_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'custom_status_tag = "rw/status"',
                        'ZOTERO_API_KEY' + ' = "old-secret"',
                        'api_key = "old-other-secret"',
                        'library_id = "old"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "library_id": "123456",
                    "root_collection_key": "ROOT1",
                    "ZOTERO_API_KEY": "secret-value",
                    "api_key": "other-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_type = "users"', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('root_collection_key = "ROOT1"', text)
        self.assertNotIn('library_id = "old"', text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("secret-value", text)
        self.assertNotIn("old-other-secret", text)
        self.assertNotIn("other-secret", text)

    def test_write_zotero_config_filters_secret_key_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'custom_status_tag = "rw/status"',
                        'zotero_api_key ' + '= "old-secret"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "root_collection_key": "ROOT1",
                    "ZoTeRo-Api-Key": "mixed-secret",
                    "api-key": "dash-secret",
                    "API_KEY": "generic-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_type = "users"', text)
        self.assertIn('root_collection_key = "ROOT1"', text)
        self.assertNotIn("zotero_api_key", text)
        self.assertNotIn("ZoTeRo-Api-Key", text)
        self.assertNotIn("api-key", text)
        self.assertNotIn("API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("mixed-secret", text)
        self.assertNotIn("dash-secret", text)
        self.assertNotIn("generic-secret", text)

    def test_write_zotero_config_filters_quoted_secret_key_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        '"ZOTERO_API_KEY" ' + '= "old-secret"',
                        "'api_key'" + ' = "old-other-secret"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    '"zotero-api-key"': "incoming-secret",
                    "'API_KEY'": "incoming-other-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('library_type = "users"', text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("zotero-api-key", text)
        self.assertNotIn("API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-other-secret", text)
        self.assertNotIn("incoming-secret", text)
        self.assertNotIn("incoming-other-secret", text)

    def test_write_zotero_config_filters_dotted_secret_key_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'api_key.value = "old-secret"',
                        '"ZOTERO_API_KEY".token = "old-token-secret"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "api_key.token": "incoming-secret",
                    '"ZOTERO_API_KEY".value': "incoming-token-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('library_type = "users"', text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-token-secret", text)
        self.assertNotIn("incoming-secret", text)
        self.assertNotIn("incoming-token-secret", text)
        tomllib.loads(text)

    def test_write_zotero_config_filters_nested_dotted_secret_key_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'credentials.api_key = "old-secret"',
                        'credentials."ZOTERO_API_KEY" = "old-token-secret"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "credentials.api_key": "incoming-secret",
                    'credentials."ZOTERO_API_KEY"': "incoming-token-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('library_type = "users"', text)
        self.assertNotIn("credentials", text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-token-secret", text)
        self.assertNotIn("incoming-secret", text)
        self.assertNotIn("incoming-token-secret", text)
        tomllib.loads(text)

    def test_write_zotero_config_drops_secret_zotero_child_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[workspace]',
                        'name = "demo"',
                        '',
                        '[zotero]',
                        'enabled = true',
                        '',
                        '[zotero.credentials.api_key]',
                        'token = "old-secret"',
                        '',
                        '[zotero.profile]',
                        'name = "safe"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[workspace]", text)
        self.assertIn('enabled = true', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn("[zotero.profile]", text)
        self.assertIn('name = "safe"', text)
        self.assertNotIn("[zotero.credentials.api_key]", text)
        self.assertNotIn("old-secret", text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["profile"]["name"], "safe")

    def test_write_zotero_config_drops_secret_zotero_child_tables_without_top_level_zotero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[workspace]',
                        'name = "demo"',
                        '',
                        '["zotero"."api_key"]',
                        'token = "old-secret"',
                        '',
                        '[[zotero.api_key]]',
                        'token = "old-array-secret"',
                        '',
                        '[zotero.profile]',
                        'name = "safe"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[workspace]", text)
        self.assertIn("[zotero]", text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn("[zotero.profile]", text)
        self.assertIn('name = "safe"', text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-array-secret", text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["profile"]["name"], "safe")

    def test_write_zotero_config_drops_secret_zotero_child_tables_with_header_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[workspace]',
                        'name = "demo"',
                        '',
                        '["zotero"."api_key"] # local secret',
                        'token = "old-secret"',
                        '',
                        '[[zotero.api_key]] # local secret',
                        'token = "old-array-secret"',
                        '',
                        '[zotero.profile] # safe',
                        'name = "safe"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[workspace]", text)
        self.assertIn("[zotero]", text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('[zotero.profile] # safe', text)
        self.assertIn('name = "safe"', text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-array-secret", text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["profile"]["name"], "safe")

    def test_write_zotero_config_filters_secret_keys_inside_zotero_child_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero.profile]',
                        'name = "safe"',
                        'api_key = "old-secret"',
                        'nested = { "ZOTERO_API_KEY" = "old-token-secret" }',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[zotero.profile]", text)
        self.assertIn('name = "safe"', text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-token-secret", text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["profile"]["name"], "safe")

    def test_write_zotero_config_preserves_existing_non_scalar_zotero_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'custom_status_tag = "rw/status"',
                        'inline_tags = ["candidate", "approved"]',
                        'metadata = { owner = "agent", enabled = true }',
                        'watched_collections = [',
                        '  "A",',
                        '  "B",',
                        ']',
                        'notes = """',
                        'line one',
                        'line two',
                        '"""',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('inline_tags = ["candidate", "approved"]', text)
        self.assertIn('metadata = { owner = "agent", enabled = true }', text)
        self.assertIn("watched_collections = [", text)
        self.assertIn('  "A",', text)
        self.assertIn('notes = """', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["enabled"], True)
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")
        self.assertEqual(parsed["zotero"]["watched_collections"], ["A", "B"])
        self.assertEqual(parsed["zotero"]["notes"], "line one\nline two\n")

    def test_write_zotero_config_preserves_multiline_string_with_assignment_like_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'notes = """',
                        'library_type = "inside notes"',
                        '"""',
                        'custom_status_tag = "rw/status"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn('notes = """', text)
        self.assertIn('library_type = "inside notes"', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["notes"], 'library_type = "inside notes"\n')
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")

    def test_write_zotero_config_preserves_single_line_triple_quoted_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'notes = """one"""',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn('notes = """one"""', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["notes"], "one")

    def test_write_zotero_config_drops_existing_malformed_zotero_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'bad key = "x"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('library_id = "123456"', text)
        self.assertNotIn("bad key", text)
        self.assertNotIn('"x"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["enabled"], True)

    def test_write_zotero_config_drops_inline_tables_with_secret_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'enabled = true',
                        'credentials = { api_key = "old-secret" }',
                        'nested = { auth = { "ZOTERO_API_KEY" = "old-token-secret" } }',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn('enabled = true', text)
        self.assertIn('library_id = "123456"', text)
        self.assertNotIn("credentials", text)
        self.assertNotIn("nested", text)
        self.assertNotIn("api_key", text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("old-secret", text)
        self.assertNotIn("old-token-secret", text)
        tomllib.loads(text)

    def test_write_zotero_config_resyncs_after_invalid_multiline_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'bad_array = [',
                        'library_type = "groups"',
                        'custom_status_tag = "rw/status"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertNotIn("bad_array", text)
        self.assertIn('library_type = "groups"', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_id = "123456"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["library_type"], "groups")
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")

    def test_write_zotero_config_resyncs_after_invalid_multiline_before_indented_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'bad_array = [',
                        '  library_type = "groups"',
                        '  custom_status_tag = "rw/status"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertNotIn("bad_array", text)
        self.assertIn('library_type = "groups"', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_id = "123456"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["library_type"], "groups")
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")

    def test_write_zotero_config_resyncs_after_invalid_multiline_string_before_indented_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'bad_notes = """',
                        '  library_type = "groups"',
                        '  custom_status_tag = "rw/status"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertNotIn("bad_notes", text)
        self.assertIn('library_type = "groups"', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_id = "123456"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["library_type"], "groups")
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")

    def test_write_zotero_config_resyncs_after_invalid_multiline_string_before_unindented_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero]',
                        'bad_notes = """',
                        'library_type = "groups"',
                        'custom_status_tag = "rw/status"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertNotIn("bad_notes", text)
        self.assertIn('library_type = "groups"', text)
        self.assertIn('custom_status_tag = "rw/status"', text)
        self.assertIn('library_id = "123456"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["library_type"], "groups")
        self.assertEqual(parsed["zotero"]["custom_status_tag"], "rw/status")

    def test_write_zotero_config_drops_invalid_incoming_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_zotero_config(root, {"library_id": "123456", "bad key": "x"})
            text = (root / ".research-pilot" / "config.toml").read_text(encoding="utf-8")

        self.assertIn('library_id = "123456"', text)
        self.assertNotIn("bad key", text)
        self.assertNotIn('"x"', text)
        tomllib.loads(text)

    def test_write_zotero_config_preserves_unrelated_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[workspace]',
                        'name = "demo"',
                        '',
                        '[zotero]',
                        'library_type = "groups"',
                        'library_id = "old"',
                        '',
                        '[project_lifecycle]',
                        'default_status = "active"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "library_id": "123456",
                    "root_collection_key": "ROOT1",
                    "ZOTERO_API_KEY": "secret-value",
                    "api_key": "other-secret",
                },
            )
            text = config.read_text(encoding="utf-8")

        self.assertIn("[workspace]", text)
        self.assertIn('name = "demo"', text)
        self.assertIn("[project_lifecycle]", text)
        self.assertIn('default_status = "active"', text)
        self.assertIn("[zotero]", text)
        self.assertIn('library_type = "users"', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('root_collection_key = "ROOT1"', text)
        self.assertNotIn('library_id = "old"', text)
        self.assertNotIn("ZOTERO_API_KEY", text)
        self.assertNotIn("secret-value", text)
        self.assertNotIn("other-secret", text)

    def test_write_zotero_config_rewrites_commented_zotero_section_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[workspace]',
                        'name = "demo"',
                        '',
                        '[zotero] # comment',
                        'enabled = true',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertEqual(text.count("[zotero]"), 1)
        self.assertIn('enabled = true', text)
        self.assertIn('library_id = "123456"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["enabled"], True)

    def test_write_zotero_config_preserves_commented_zotero_child_after_commented_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero] # comment',
                        'enabled = true',
                        '',
                        '[zotero.profile] # safe',
                        'name = "safe"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[zotero.profile] # safe", text)
        self.assertIn('name = "safe"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["enabled"], True)
        self.assertEqual(parsed["zotero"]["profile"]["name"], "safe")

    def test_write_zotero_config_preserves_commented_unrelated_section_after_commented_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        '[zotero] # comment',
                        'enabled = true',
                        '',
                        '[project_lifecycle] # comment',
                        'default_status = "active"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )

            write_zotero_config(root, {"library_id": "123456"})
            text = config.read_text(encoding="utf-8")

        self.assertIn("[project_lifecycle] # comment", text)
        self.assertIn('default_status = "active"', text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["zotero"]["enabled"], True)
        self.assertEqual(parsed["project_lifecycle"]["default_status"], "active")


if __name__ == "__main__":
    unittest.main()
