import json
import tempfile
import unittest
from pathlib import Path

from tools.build_graph_db import main as build_graph_db_main
from tools.build_project_graph_report import build_project_graph_report, write_project_graph_report


def demo_events() -> list[dict]:
    return [
        json.loads(line)
        for line in Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ProjectGraphReportTest(unittest.TestCase):
    def test_builds_markdown_report_from_graph_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text("\n".join(json.dumps(event) for event in demo_events()) + "\n", encoding="utf-8")
            build_graph_db_main(["--repo", str(root), "--project", "DemoProject"])

            report = build_project_graph_report(root, "DemoProject")

        self.assertIn("<!-- GENERATED FROM graph.db", report)
        self.assertIn("# DemoProject Project Understanding Graph", report)
        self.assertIn("| Claims | 1 |", report)
        self.assertIn("| Evidence | 1 |", report)
        self.assertIn("| Reasoning links | 1 |", report)
        self.assertIn("| Open deltas | 1 |", report)
        self.assertIn("| C0 | Demo claim needs evidence.", report)
        self.assertIn("| E0 | Demo evidence supports the claim.", report)
        self.assertIn("| RL0 | E0 | supports | C0 |", report)
        self.assertIn("| D0 | Connect demo evidence to demo claim.", report)
        self.assertIn("Graph truth lives in `wiki/graphs/events/**/*.jsonl`", report)

    def test_writes_default_project_report_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text("\n".join(json.dumps(event) for event in demo_events()) + "\n", encoding="utf-8")
            build_graph_db_main(["--repo", str(root), "--project", "DemoProject"])

            output = write_project_graph_report(root, "DemoProject")

            self.assertEqual(output, root.resolve() / "wiki" / "projects" / "DemoProject" / "project-understanding-graph.md")
            self.assertTrue(output.exists())
            self.assertIn("DemoProject Project Understanding Graph", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
