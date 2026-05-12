import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.project_shell_cli import create_project_shell
from tools.research_pilot_init import main as init_workspace_main


class ProjectShellCliTest(unittest.TestCase):
    def test_create_project_shell_without_graph_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])

            result = create_project_shell(
                root,
                project_id="AAAI2027Affordance",
                display_title="AAAI 2027 Affordance Estimation",
                target_venue="AAAI 2027",
                maturity_stage="project_shell",
                research_direction="Affordance estimation from visual observations.",
                baseline_anchors=["Gibson 1979", "Do et al. 2018"],
                seed_questions=["Which baselines define the contribution bar?"],
                search_questions=["Find affordance estimation baselines for AAAI."],
                overwrite=False,
            )

            overview = root / "wiki" / "projects" / "AAAI2027Affordance" / "overview.md"
            query_pack = root / "wiki" / "projects" / "AAAI2027Affordance" / "project-query-pack.md"
            decisions = root / "wiki" / "projects" / "AAAI2027Affordance" / "decisions.md"
            papers_gitkeep = root / "wiki" / "projects" / "AAAI2027Affordance" / "papers" / ".gitkeep"
            experiments_gitkeep = (
                root
                / "wiki"
                / "projects"
                / "AAAI2027Affordance"
                / "experiment-proposals"
                / ".gitkeep"
            )
            graph_events = root / "wiki" / "graphs" / "events" / "projects" / "AAAI2027Affordance.jsonl"

            self.assertTrue(result["created"])
            self.assertTrue(overview.exists())
            self.assertTrue(query_pack.exists())
            self.assertTrue(decisions.exists())
            self.assertTrue(papers_gitkeep.exists())
            self.assertTrue(experiments_gitkeep.exists())
            self.assertFalse(graph_events.exists())
            text = overview.read_text(encoding="utf-8")
            self.assertIn('display_title: "AAAI 2027 Affordance Estimation"', text)
            self.assertIn('target_venue: "AAAI 2027"', text)
            self.assertIn("maturity_stage: project_shell", text)
            self.assertIn("## Seed Questions", text)
            self.assertIn("Which baselines define the contribution bar?", text)

    def test_existing_shell_is_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            first = create_project_shell(root, "Demo", "Demo", "", "project_shell", "First", [], [], [], False)
            second = create_project_shell(root, "Demo", "Demo Changed", "", "project_shell", "Second", [], [], [], False)
            overview = root / "wiki" / "projects" / "Demo" / "overview.md"

            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertIn("First", overview.read_text(encoding="utf-8"))

    def test_invalid_project_ids_are_rejected_before_writes(self):
        invalid_ids = ["/tmp/x", "../x", "a/b", ".", ".."]
        for project_id in invalid_ids:
            with self.subTest(project_id=project_id):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    init_workspace_main([str(root), "--no-git"])
                    outside = root.parent / "x"
                    projects_root = root / "wiki" / "projects"
                    before = sorted(path.relative_to(projects_root) for path in projects_root.rglob("*"))

                    with self.assertRaises(ValueError):
                        create_project_shell(root, project_id, "Bad", "", "project_shell", "", [], [], [], False)

                    self.assertFalse(outside.exists())
                    after = sorted(path.relative_to(projects_root) for path in projects_root.rglob("*"))
                    self.assertEqual(before, after)

    def test_direct_cli_prints_json_and_creates_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/project_shell_cli.py",
                    "--repo",
                    str(root),
                    "--project",
                    "CliDemo",
                    "--title",
                    "CLI Demo",
                    "--target-venue",
                    "AAAI 2027",
                    "--maturity-stage",
                    "project_shell",
                    "--direction",
                    "Command-line shell creation.",
                    "--baseline-anchor",
                    "Gibson 1979",
                    "--seed-question",
                    "Which baseline matters?",
                    "--search-question",
                    "Find baseline papers.",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            result = json.loads(completed.stdout)
            overview = root / "wiki" / "projects" / "CliDemo" / "overview.md"
            query_pack = root / "wiki" / "projects" / "CliDemo" / "project-query-pack.md"

            self.assertTrue(result["created"])
            self.assertEqual(False, result["graph_events_created"])
            self.assertTrue(overview.exists())
            self.assertTrue(query_pack.exists())
            self.assertIn("Command-line shell creation.", overview.read_text(encoding="utf-8"))

    def test_overwrite_true_updates_existing_overview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            first = create_project_shell(root, "Demo", "Demo", "", "project_shell", "First", [], [], [], False)
            second = create_project_shell(root, "Demo", "Demo Changed", "", "project_shell", "Second", [], [], [], True)
            overview = root / "wiki" / "projects" / "Demo" / "overview.md"

            self.assertTrue(first["created"])
            self.assertTrue(second["created"])
            text = overview.read_text(encoding="utf-8")
            self.assertIn("Second", text)
            self.assertNotIn("First", text)


if __name__ == "__main__":
    unittest.main()
