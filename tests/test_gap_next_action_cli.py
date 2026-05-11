import tempfile
import unittest
from pathlib import Path

from tools.build_graph_db import main as build_db_main
from tools.project_gap_cli import detect_gaps
from tools.project_next_action_cli import suggest_next_actions


class GapNextActionCliTest(unittest.TestCase):
    def test_detect_gaps_and_suggest_next_action_from_demo_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events_dir = root / "wiki" / "graphs" / "events" / "projects"
            events_dir.mkdir(parents=True)
            (events_dir / "DemoProject.jsonl").write_text(
                Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            build_db_main(["--repo", str(root), "--project", "DemoProject"])

            gaps = detect_gaps(root, "DemoProject")
            next_actions = suggest_next_actions(root, "DemoProject")

        self.assertTrue(gaps["valid"], gaps)
        self.assertIn("gaps", gaps["counts"])
        self.assertTrue(next_actions["valid"], next_actions)
        self.assertIn("project_readout", next_actions)
        self.assertTrue(next_actions["recommended_next_moves"])
        self.assertEqual(next_actions["recommended_next_moves"][0]["type"], "human_gate_review")


if __name__ == "__main__":
    unittest.main()
