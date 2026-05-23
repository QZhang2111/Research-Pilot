import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_understanding_store import sample_update


class UnderstandingCliTest(unittest.TestCase):
    def test_append_validate_and_build_project_understanding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update_path = root / "update.json"
            update_path.write_text(json.dumps(sample_update(), ensure_ascii=False), encoding="utf-8")

            append = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "append",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--update",
                    str(update_path),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            validate = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "validate",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            build = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "build-project-understanding",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, append.returncode, append.stderr)
        self.assertTrue(json.loads(append.stdout)["appended"])
        self.assertEqual(0, validate.returncode, validate.stderr)
        self.assertTrue(json.loads(validate.stdout)["valid"])
        self.assertEqual(0, build.returncode, build.stderr)
        build_result = json.loads(build.stdout)
        self.assertTrue(build_result["written"])
        self.assertEqual("wiki/understanding/project-understanding/DemoProject.json", build_result["path"])

    def test_append_invalid_update_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            update_path = root / "bad.json"
            update = sample_update()
            update["confidence"] = "certain"
            update_path.write_text(json.dumps(update, ensure_ascii=False), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/understanding_cli.py",
                    "append",
                    "--repo",
                    str(root),
                    "--project",
                    "DemoProject",
                    "--update",
                    str(update_path),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(1, completed.returncode)
        self.assertIn("unsupported confidence", completed.stdout)


if __name__ == "__main__":
    unittest.main()
