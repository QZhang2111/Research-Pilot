import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_understanding_store import sample_update


def run_cli(*args: str, repo_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/understanding_cli.py", *args],
        cwd=repo_root or Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )


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

    def test_validate_invalid_project_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = run_cli(
                "validate",
                "--repo",
                tmp,
                "--project",
                "../bad",
                "--json",
            )

        self.assertNotEqual(0, completed.returncode)
        result = json.loads(completed.stdout)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_build_invalid_project_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = run_cli(
                "build-project-understanding",
                "--repo",
                tmp,
                "--project",
                "../bad",
                "--json",
            )

        self.assertNotEqual(0, completed.returncode)
        result = json.loads(completed.stdout)
        self.assertFalse(result["valid"])
        self.assertFalse(result["written"])
        self.assertTrue(result["errors"])

    def test_append_with_malformed_existing_event_jsonl_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "understanding" / "events"
            events.mkdir(parents=True)
            (events / "DemoProject.jsonl").write_text("{not-json}\n", encoding="utf-8")
            update_path = root / "update.json"
            update_path.write_text(json.dumps(sample_update(), ensure_ascii=False), encoding="utf-8")

            completed = run_cli(
                "append",
                "--repo",
                str(root),
                "--project",
                "DemoProject",
                "--update",
                str(update_path),
                "--json",
            )

        self.assertNotEqual(0, completed.returncode)
        result = json.loads(completed.stdout)
        self.assertFalse(result["valid"])
        self.assertFalse(result["appended"])
        self.assertTrue(result["errors"])

    def test_validate_with_malformed_existing_event_jsonl_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "understanding" / "events"
            events.mkdir(parents=True)
            (events / "DemoProject.jsonl").write_text("{not-json}\n", encoding="utf-8")

            completed = run_cli(
                "validate",
                "--repo",
                str(root),
                "--project",
                "DemoProject",
                "--json",
            )

        self.assertNotEqual(0, completed.returncode)
        result = json.loads(completed.stdout)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_build_with_malformed_existing_event_jsonl_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "understanding" / "events"
            events.mkdir(parents=True)
            (events / "DemoProject.jsonl").write_text("{not-json}\n", encoding="utf-8")

            completed = run_cli(
                "build-project-understanding",
                "--repo",
                str(root),
                "--project",
                "DemoProject",
                "--json",
            )

        self.assertNotEqual(0, completed.returncode)
        result = json.loads(completed.stdout)
        self.assertFalse(result["valid"])
        self.assertFalse(result["written"])
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
