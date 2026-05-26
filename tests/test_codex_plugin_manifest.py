import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class CodexPluginManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = REPO / ".codex-plugin" / "plugin.json"
        self.manifest = json.loads(self.path.read_text())

    def test_manifest_identity(self) -> None:
        self.assertEqual(self.manifest["name"], "research-pilot")
        self.assertRegex(self.manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("research memory", self.manifest["description"].lower())
        self.assertEqual(self.manifest["skills"], "./skills/")

    def test_manifest_interface(self) -> None:
        interface = self.manifest["interface"]
        self.assertEqual(interface["displayName"], "Research Pilot")
        self.assertEqual(interface["category"], "Productivity")
        self.assertIn("Interactive", interface["capabilities"])
        self.assertIn("Read", interface["capabilities"])
        self.assertIn("Write", interface["capabilities"])
        self.assertIn("local project memory", interface["longDescription"])
        self.assertIn("read-only dashboard", interface["longDescription"])
        self.assertNotIn("human-gated", interface["longDescription"])
        self.assertNotIn("Zotero remains", interface["longDescription"])
        self.assertRegex(interface["brandColor"], r"^#[0-9A-Fa-f]{6}$")

    def test_manifest_keywords_match_chat_first_positioning(self) -> None:
        self.assertEqual(
            self.manifest["keywords"],
            [
                "research",
                "agent-memory",
                "local-first",
                "project-memory",
                "dashboard",
                "codex",
            ],
        )

    def test_default_prompts_stay_codex_sized(self) -> None:
        prompts = self.manifest["interface"]["defaultPrompt"]
        self.assertGreaterEqual(len(prompts), 1)
        self.assertLessEqual(len(prompts), 3)
        for prompt in prompts:
            self.assertLessEqual(len(prompt), 128)
        self.assertEqual(
            prompts,
            [
                "Use Research Pilot to track this project.",
                "Read this source and record what matters for the project.",
                "Open the Research Pilot dashboard.",
            ],
        )

    def test_referenced_assets_exist(self) -> None:
        interface = self.manifest["interface"]
        for key in ("composerIcon", "logo"):
            value = interface[key]
            self.assertTrue(value.startswith("./assets/"))
            self.assertTrue((REPO / value.removeprefix("./")).exists(), value)
        for screenshot in interface.get("screenshots", []):
            self.assertTrue(screenshot.startswith("./assets/"))
            self.assertEqual(Path(screenshot).suffix, ".png")
            self.assertTrue((REPO / screenshot.removeprefix("./")).exists(), screenshot)

    def test_manifest_has_no_placeholders_or_private_paths(self) -> None:
        raw = json.dumps(self.manifest, ensure_ascii=False)
        self.assertNotRegex(raw, re.compile(r"\[TODO|TODO|example\.com"))
        self.assertNotIn("/Users/" + "qing", raw)
        self.assertNotIn("Personal" + "ResearchWiki", raw)

    def test_manifest_skills_path_points_to_router_skill(self) -> None:
        skills_dir = REPO / self.manifest["skills"].removeprefix("./")
        self.assertTrue((skills_dir / "research-pilot" / "SKILL.md").exists())
        self.assertTrue((skills_dir / "research-pilot-first-run" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
