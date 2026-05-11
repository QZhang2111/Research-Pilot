import tempfile
import unittest
from pathlib import Path

from tools.build_graph_db import main as build_db_main
from tools.gap_search_cli import build_search_contract, search_from_contract
from tools.project_experiment_cli import build_proposal
from tools.research_gap_discovery_cli import run_gap_discovery


def demo_workspace() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    events_dir = root / "wiki" / "graphs" / "events" / "projects"
    events_dir.mkdir(parents=True)
    (events_dir / "DemoProject.jsonl").write_text(
        Path("examples/demo/events/demo-project.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    build_db_main(["--repo", str(root), "--project", "DemoProject"])
    return tmp


class GapSearchExperimentCliTest(unittest.TestCase):
    def test_experiment_proposal_for_demo_claim(self):
        with demo_workspace() as tmp:
            result = build_proposal(Path(tmp), "DemoProject", "C0")

        self.assertTrue(result["valid"], result)
        proposal = result["experiment_proposal"]
        self.assertEqual(proposal["target_claim"]["id"], "C0")
        self.assertEqual(proposal["expected_graph_update"]["node_types"], ["Evidence"])
        self.assertEqual(result["effects"]["graph_events"], [])

    def test_gap_search_contract_and_discovery_do_not_mutate(self):
        with demo_workspace() as tmp:
            root = Path(tmp)
            contract = build_search_contract(root, "DemoProject", "RL0")
            search = search_from_contract(contract, source="none", max_results=3, root=root)
            discovery = run_gap_discovery(root, "DemoProject", "RL0", source="none")

        self.assertTrue(contract["valid"], contract)
        self.assertEqual(contract["search_contract"]["source_gap"]["gap_type"], "weak_warrant")
        self.assertTrue(search["valid"], search)
        self.assertEqual(search["search"]["source"], "none")
        self.assertTrue(discovery["valid"], discovery)
        self.assertEqual(discovery["effects"]["graph_events"], [])


if __name__ == "__main__":
    unittest.main()
