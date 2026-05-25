import json
import inspect
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from tools.build_dashboard_index import build_index
from tools.build_graph_db import main as build_graph_db_main
from tools.build_graph_snapshot import main as build_snapshot_main
from tools.experiment_store import build_project_experiments
from tools.research_browser_server import (
    ResearchBrowserHandler,
    ensure_dashboard_index,
    handle_experiments_request,
    handle_paper_graph_request,
    handle_project_graph_maintenance_request,
    handle_project_understanding_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class DashboardPublicTest(unittest.TestCase):
    def test_dashboard_static_responses_disable_browser_cache(self):
        source = inspect.getsource(ResearchBrowserHandler.end_headers)

        self.assertIn('request_path.startswith("/dashboard/")', source)
        self.assertIn('request_path.startswith("/api/")', source)
        self.assertIn('"Cache-Control", "no-store, no-cache, must-revalidate"', source)
        self.assertIn('"Pragma", "no-cache"', source)
        self.assertIn('"Expires", "0"', source)

    def test_build_index_exposes_related_work_lineage_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_path = (
                root
                / "wiki"
                / "projects"
                / "DemoProject"
                / "literature-rounds"
                / "vision-world-model-baselines"
                / "related-work-lineage.json"
            )
            lineage_path.parent.mkdir(parents=True)
            lineage_path.write_text(
                json.dumps(
                    {
                        "schema_version": "related-work-lineage-v1",
                        "project": "DemoProject",
                        "round": "vision-world-model-baselines",
                        "title": "Vision World Model Baselines",
                        "status": "candidate",
                        "source_boundary": "related_work_lineage_only_not_graph_truth",
                        "route_narrowing": {
                            "input_mode": "coarse_direction",
                            "user_direction": "Map baseline methods.",
                            "selected_anchor_papers": [],
                            "candidate_routes": [],
                        },
                        "routes": [
                            {
                                "id": "route-1",
                                "label": "Video prediction",
                                "description": "Predict future visual states.",
                                "review_status": "candidate",
                            }
                        ],
                        "papers": [
                            {
                                "id": "paper-1",
                                "kind": "paper",
                                "title": "Demo Paper",
                                "source_url": "https://example.com/demo",
                                "source_evidence": "User-provided baseline.",
                                "route": "route-1",
                                "review_status": "candidate",
                            }
                        ],
                        "explicit_edges": [],
                        "positioning_note": "Demo positioning note.",
                    }
                ),
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(len(index["lineage_maps"]), 1)
        lineage = index["lineage_maps"][0]
        self.assertEqual(lineage["id"], "DemoProject/vision-world-model-baselines")
        self.assertEqual(lineage["project"], "DemoProject")
        self.assertEqual(lineage["paper_count"], 1)
        self.assertEqual(lineage["route_count"], 1)
        self.assertEqual(
            lineage["path"],
            "wiki/projects/DemoProject/literature-rounds/vision-world-model-baselines/related-work-lineage.json",
        )
        self.assertEqual(lineage["source_boundary"], "related_work_lineage_only_not_graph_truth")

    def test_build_index_exposes_corrupt_related_work_lineage_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_path = (
                root
                / "wiki"
                / "projects"
                / "DemoProject"
                / "literature-rounds"
                / "corrupt-round"
                / "related-work-lineage.json"
            )
            lineage_path.parent.mkdir(parents=True)
            lineage_path.write_text("{not-json", encoding="utf-8")

            index = build_index(root)

        self.assertEqual(len(index["lineage_maps"]), 1)
        lineage = index["lineage_maps"][0]
        self.assertEqual(lineage["id"], "DemoProject/corrupt-round")
        self.assertEqual(lineage["project"], "DemoProject")
        self.assertEqual(lineage["round"], "corrupt-round")
        self.assertFalse(lineage["valid"])
        self.assertEqual(lineage["paper_count"], 0)
        self.assertEqual(lineage["route_count"], 0)
        self.assertEqual(lineage["edge_count"], 0)
        self.assertEqual(lineage["route_narrowing"], {})
        self.assertEqual(lineage["routes"], [])
        self.assertEqual(lineage["papers"], [])
        self.assertEqual(lineage["explicit_edges"], [])
        self.assertEqual(lineage["positioning_note"], "")
        self.assertTrue(lineage["errors"])

    def test_build_index_lineage_identity_comes_from_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_path = (
                root
                / "wiki"
                / "projects"
                / "DemoProject"
                / "literature-rounds"
                / "path-round"
                / "related-work-lineage.json"
            )
            lineage_path.parent.mkdir(parents=True)
            lineage_path.write_text(
                json.dumps(
                    {
                        "schema_version": "related-work-lineage-v1",
                        "project": "OtherProject",
                        "round": "other-round",
                        "title": "Mismatched Lineage",
                        "status": "candidate",
                        "source_boundary": "related_work_lineage_only_not_graph_truth",
                        "route_narrowing": {},
                        "routes": [],
                        "papers": [],
                        "explicit_edges": [],
                        "positioning_note": "",
                    }
                ),
                encoding="utf-8",
            )

            index = build_index(root)

        lineage = index["lineage_maps"][0]
        self.assertEqual(lineage["id"], "DemoProject/path-round")
        self.assertEqual(lineage["project"], "DemoProject")
        self.assertEqual(lineage["round"], "path-round")
        self.assertFalse(lineage["valid"])
        self.assertIn("payload project does not match path project: OtherProject != DemoProject", lineage["errors"])
        self.assertIn("payload round does not match path round: other-round != path-round", lineage["errors"])

    def test_build_index_caps_oversized_invalid_lineage_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lineage_path = (
                root
                / "wiki"
                / "projects"
                / "DemoProject"
                / "literature-rounds"
                / "oversized-round"
                / "related-work-lineage.json"
            )
            lineage_path.parent.mkdir(parents=True)
            papers = [
                {
                    "id": f"paper-{index}",
                    "kind": "paper",
                    "title": f"Demo Paper {index}",
                    "source_url": f"https://example.com/{index}",
                    "source_evidence": "Search result.",
                    "route": "route-1",
                    "review_status": "candidate",
                }
                for index in range(25)
            ]
            lineage_path.write_text(
                json.dumps(
                    {
                        "schema_version": "related-work-lineage-v1",
                        "project": "DemoProject",
                        "round": "oversized-round",
                        "title": "Oversized Lineage",
                        "status": "candidate",
                        "source_boundary": "related_work_lineage_only_not_graph_truth",
                        "route_narrowing": {},
                        "routes": [
                            {
                                "id": "route-1",
                                "label": "Route",
                                "description": "Route description.",
                                "review_status": "candidate",
                            }
                        ],
                        "papers": papers,
                        "explicit_edges": [],
                        "positioning_note": "",
                    }
                ),
                encoding="utf-8",
            )

            index = build_index(root)

        lineage = index["lineage_maps"][0]
        self.assertFalse(lineage["valid"])
        self.assertEqual(lineage["paper_count"], 25)
        self.assertLessEqual(len(lineage["papers"]), 20)

    def test_build_index_exposes_graph_only_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            event_path.parent.mkdir(parents=True)
            event_path.write_text(Path("examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            build_snapshot_main(["--repo", str(root), "--project", "DemoProject", "--generated-at", "2026-05-11T00:01:00Z"])

            index = build_index(root)

        self.assertEqual(index["projects"][0]["id"], "DemoProject")
        self.assertFalse(index["projects"][0]["demo"])
        self.assertEqual(index["project_graphs"][0]["project"], "DemoProject")
        self.assertEqual(index["project_graphs"][0]["nodes"][0]["id"], "C0")
        json.dumps(index)

    def test_project_index_exposes_demo_flag_from_overview_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\ndemo: true\n---\n# Demo Project\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertTrue(index["projects"][0]["demo"])

    def test_build_index_exposes_durable_job_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_dir = root / ".research-pilot" / "jobs"
            jobs_dir.mkdir(parents=True)
            (jobs_dir / "job-1.json").write_text(
                json.dumps(
                    {
                        "id": "job-1",
                        "type": "paper_search",
                        "project": "DemoProject",
                        "status": "queued",
                        "created_at": "2026-05-12T00:00:00Z",
                        "updated_at": "2026-05-12T00:00:00Z",
                        "owner": "agent",
                        "human_gate": "required_before_graph_update",
                        "truth_boundary": "execution_state_only",
                        "inputs": {"gap_id": "RL0"},
                        "artifacts": [],
                        "result_summary": "Queued search. No graph truth changed.",
                    }
                ),
                encoding="utf-8",
            )
            (jobs_dir / "job-corrupt.json").write_text("{not-json", encoding="utf-8")
            (jobs_dir / "job-non-utf8.json").write_bytes(b"\xff\xfe\x00\x00")
            (jobs_dir / "job-invalid.json").write_text(
                json.dumps(
                    {
                        "id": "job-invalid",
                        "type": "paper_search",
                        "project": "DemoProject",
                        "status": "queued",
                        "human_gate": "required_before_graph_update",
                        "truth_boundary": "graph_truth_changed",
                    }
                ),
                encoding="utf-8",
            )
            (jobs_dir / "job-missing-project.json").write_text(
                json.dumps(
                    {
                        "id": "job-missing-project",
                        "type": "paper_search",
                        "status": "queued",
                        "created_at": "2026-05-12T00:00:00Z",
                        "updated_at": "2026-05-12T00:00:00Z",
                        "owner": "agent",
                        "human_gate": "required_before_graph_update",
                        "truth_boundary": "execution_state_only",
                        "inputs": {"gap_id": "RL0"},
                        "artifacts": [],
                        "result_summary": "Missing project.",
                    }
                ),
                encoding="utf-8",
            )
            (jobs_dir / "job-a.json").write_text(
                json.dumps(
                    {
                        "id": "job-b",
                        "type": "paper_search",
                        "project": "DemoProject",
                        "status": "queued",
                        "created_at": "2026-05-12T00:00:00Z",
                        "updated_at": "2026-05-12T00:00:00Z",
                        "owner": "agent",
                        "human_gate": "required_before_graph_update",
                        "truth_boundary": "execution_state_only",
                        "inputs": {"gap_id": "RL0"},
                        "artifacts": [],
                        "result_summary": "Mismatched id.",
                    }
                ),
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(len(index["jobs"]), 1)
        self.assertEqual(index["jobs"][0]["id"], "job-1")
        self.assertEqual(index["jobs"][0]["truth_boundary"], "execution_state_only")

    def test_build_index_expands_home_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / "workspace"
            jobs_dir = root / ".research-pilot" / "jobs"
            jobs_dir.mkdir(parents=True)
            (jobs_dir / "job-home.json").write_text(
                json.dumps(
                    {
                        "id": "job-home",
                        "type": "paper_search",
                        "project": "DemoProject",
                        "status": "queued",
                        "created_at": "2026-05-12T00:00:00Z",
                        "updated_at": "2026-05-12T00:00:00Z",
                        "owner": "agent",
                        "human_gate": "required_before_graph_update",
                        "truth_boundary": "execution_state_only",
                        "inputs": {"gap_id": "RL0"},
                        "artifacts": [],
                        "result_summary": "Home-expanded job.",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"HOME": str(home)}):
                index = build_index(Path("~/workspace"))

        self.assertEqual(index["jobs"][0]["id"], "job-home")

    def test_server_ensures_missing_dashboard_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo Project\n",
                encoding="utf-8",
            )
            index_path = root / ".dashboard" / "index.json"

            ensured = ensure_dashboard_index(root)
            payload = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertEqual(ensured, index_path)
        self.assertEqual(payload["projects"][0]["id"], "DemoProject")

    def test_project_graph_maintenance_api_serves_read_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_path = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            event_path.parent.mkdir(parents=True)
            event_path.write_text(Path("examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            build_graph_db_main(["--repo", str(root), "--project", "DemoProject"])

            status, payload = handle_project_graph_maintenance_request(root, "/api/project-graph-maintenance?project=DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["schema_version"], "graph-maintenance-v1")
        self.assertEqual(model["project"], "DemoProject")
        self.assertEqual([delta["id"] for delta in model["open_deltas"]], ["D0"])
        self.assertEqual([delta["id"] for delta in model["review_queue"]["deltas"]], ["D0"])
        self.assertEqual(model["claim_paths"][0]["claim"]["id"], "C0")
        self.assertEqual(model["claim_paths"][0]["supporting_links"][0]["premises"][0]["id"], "E0")

    def test_project_understanding_api_serves_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "wiki" / "understanding" / "events" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text(
                json.dumps(
                    {
                        "schema_version": "understanding-update-v1",
                        "update_id": "UU-demo",
                        "project_id": "DemoProject",
                        "created_at": "2026-05-23T00:00:00Z",
                        "actor": "agent",
                        "task": {
                            "kind": "read_source",
                            "summary": "Read demo source and update project understanding.",
                        },
                        "source_refs": ["wiki/projects/DemoProject/papers/demo-paper/index.md"],
                        "new_sources": [
                            {
                                "source_id": "S-demo",
                                "type": "markdown_note",
                                "title": "Demo Paper",
                                "status": "read",
                                "locator": "wiki/projects/DemoProject/papers/demo-paper/index.md",
                                "relevance": "Supports the demo claim.",
                            }
                        ],
                        "changed_claims": [
                            {
                                "claim_id": "C-demo",
                                "text": "Demo claim is source-backed but weak.",
                                "status": "weak",
                                "supporting_sources": ["S-demo"],
                                "weakness": "Evidence is illustrative.",
                            }
                        ],
                        "new_gaps": [
                            {
                                "gap_id": "G-demo",
                                "type": "missing evidence",
                                "text": "Need direct evidence beyond the demo note.",
                                "related_claims": ["C-demo"],
                            }
                        ],
                        "recent_change_summary": "Qualified the demo claim and added an evidence gap.",
                        "next_moves": [
                            {
                                "move_id": "N-demo",
                                "type": "search",
                                "text": "Search for stronger evidence.",
                                "rationale": "Current support is weak.",
                                "suggested_prompt": "Find stronger evidence for the demo claim.",
                            }
                        ],
                        "confidence": "source-backed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            status, payload = handle_project_understanding_request(root, "/api/project-understanding?project=DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["schema_version"], "project-understanding-v1")
        self.assertEqual(model["project_id"], "DemoProject")
        self.assertEqual(model["recent_changes"][0]["summary"], "Qualified the demo claim and added an evidence gap.")
        self.assertEqual(model["next_moves"][0]["suggested_prompt"], "Find stronger evidence for the demo claim.")

    def test_project_understanding_api_rejects_nested_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = handle_project_understanding_request(Path(tmp), "/api/project-understanding?project=../DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 404)
        self.assertEqual(model["error"], "Not Found")

    def test_project_experiments_api_serves_designs_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments_path = root / "wiki" / "projects" / "DemoProject" / "experiments" / "experiments.json"
            experiments_path.parent.mkdir(parents=True)
            experiments_path.write_text(
                json.dumps(
                    {
                        "schema_version": "experiments-v1",
                        "summary": {
                            "total_experiments": 1,
                            "planned": 1,
                            "completed_runs": 1,
                            "strongest_current_evidence": "Imported evidence supports demo claim.",
                            "highest_priority_unresolved": "Run local reproduction.",
                        },
                        "experiments": [
                            {
                                "id": "EXP-demo",
                                "title": "Demo Experiment",
                                "status": "planned",
                            }
                        ],
                        "runs": [
                            {
                                "id": "RUN-demo",
                                "experiment_id": "EXP-demo",
                                "status": "completed",
                                "evidence_type": "imported_paper_evidence",
                            }
                        ],
                        "next_moves": [
                            {
                                "id": "NEXT-demo",
                                "text": "Import more paper evidence.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            direct_model = build_project_experiments(root, "DemoProject")
            status, payload = handle_experiments_request(root, "/api/experiments?project=DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(direct_model["schema_version"], "experiments-v1")
        self.assertEqual(status, 200)
        self.assertEqual(model["schema_version"], "experiments-v1")
        self.assertEqual(model["project_id"], "DemoProject")
        self.assertEqual(model["summary"]["total_experiments"], 1)
        self.assertEqual(model["summary"]["planned"], 1)
        self.assertEqual(model["summary"]["completed_runs"], 1)
        self.assertEqual(model["summary"]["imported_paper_evidence_runs"], 1)
        self.assertEqual(model["summary"]["imported_evidence_runs"], 1)
        self.assertEqual(model["summary"]["local_result_runs"], 0)
        self.assertEqual(model["summary"]["strongest_current_evidence"], "Imported evidence supports demo claim.")
        self.assertEqual(model["summary"]["highest_priority_unresolved"], "Run local reproduction.")
        self.assertEqual(model["runs"][0]["evidence_type"], "imported_paper_evidence")
        self.assertFalse(model["mutating"])

    def test_project_experiments_api_rejects_nested_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = handle_experiments_request(Path(tmp), "/api/experiments?project=../DemoProject")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 404)
        self.assertEqual(model["error"], "Not Found")

    def test_paper_graph_api_derives_contribution_from_project_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper_path = root / "wiki" / "projects" / "DemoProject" / "papers" / "demo-paper" / "index.md"
            paper_path.parent.mkdir(parents=True)
            paper_path.write_text(
                "---\ntitle: Demo Paper\ntype: paper-dossier\n---\n# Demo Paper\n\n## Deep Read Notes\n\nDemo notes.\n",
                encoding="utf-8",
            )
            rel_paper = "wiki/projects/DemoProject/papers/demo-paper/index.md"
            snapshot_path = root / "wiki" / "graphs" / "snapshots" / "projects" / "DemoProject.graph.json"
            snapshot_path.parent.mkdir(parents=True)
            snapshot_path.write_text(
                json.dumps(
                    {
                        "schema_version": "graph-snapshot-v1",
                        "graph_id": "project:DemoProject",
                        "generated_at": "2026-05-15T00:00:00Z",
                        "event_count": 3,
                        "nodes": [
                            {
                                "node_id": "project:DemoProject:C0",
                                "local_id": "C0",
                                "node_type": "Claim",
                                "text": "Project claim from paper.",
                                "scope": "project",
                                "project_id": "DemoProject",
                                "paper_id": None,
                                "status": "active",
                                "lifecycle_status": "active",
                                "confidence": "medium",
                                "human_review": "approved",
                                "source_refs": [rel_paper],
                                "supersedes": [],
                                "superseded_by": [],
                                "derived_from": [],
                                "metadata": {"status": "primary"},
                            },
                            {
                                "node_id": "project:DemoProject:E0",
                                "local_id": "E0",
                                "node_type": "Evidence",
                                "text": "Paper evidence.",
                                "scope": "project",
                                "project_id": "DemoProject",
                                "paper_id": None,
                                "status": "active",
                                "lifecycle_status": "active",
                                "confidence": "medium",
                                "human_review": "approved",
                                "source_refs": [rel_paper],
                                "supersedes": [],
                                "superseded_by": [],
                                "derived_from": [],
                                "metadata": {"evidence_kind": "baseline"},
                            },
                            {
                                "node_id": "project:DemoProject:W0",
                                "local_id": "W0",
                                "node_type": "Warrant",
                                "text": "Paper warrant.",
                                "scope": "project",
                                "project_id": "DemoProject",
                                "paper_id": None,
                                "status": "active",
                                "lifecycle_status": "active",
                                "confidence": "medium",
                                "human_review": "approved",
                                "source_refs": [rel_paper],
                                "supersedes": [],
                                "superseded_by": [],
                                "derived_from": [],
                                "metadata": {"basis": "demo warrant"},
                            },
                        ],
                        "links": [
                            {
                                "link_id": "project:DemoProject:RL0",
                                "local_id": "RL0",
                                "link_type": "ReasoningLink",
                                "relation": "supports",
                                "from_nodes": ["project:DemoProject:E0"],
                                "to_nodes": ["project:DemoProject:C0"],
                                "warrant_nodes": ["project:DemoProject:W0"],
                                "limitation_nodes": [],
                                "confidence": "medium",
                                "human_review": "approved",
                                "source_refs": [rel_paper],
                            }
                        ],
                        "deltas": [
                            {
                                "delta_id": "project:DemoProject:D1",
                                "local_id": "D1",
                                "operation": ["add_node"],
                                "summary": "Add project claim.",
                                "source_refs": [rel_paper],
                                "source_dossier": rel_paper,
                                "source_paper_nodes": [],
                                "affected_nodes": ["project:DemoProject:C0"],
                                "affected_links": ["project:DemoProject:RL0"],
                                "status": "accepted",
                                "lifecycle_status": "accepted",
                                "human_review": "approved",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = handle_paper_graph_request(root, f"/api/paper-graph?path={quote(rel_paper)}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["schema_version"], "paper-graph-v1")
        self.assertEqual(model["paper"], "demo-paper")
        self.assertEqual([node["id"] for node in model["nodes"]], ["P-C0", "P-E0", "P-W0"])
        self.assertEqual(model["paper_links"][0]["premises"], ["P-E0"])
        self.assertEqual(model["paper_links"][0]["target"], "P-C0")
        self.assertEqual(model["paper_links"][0]["warrant"], "P-W0")
        self.assertEqual(model["translations"][0]["paper_nodes"], ["P-C0"])
        self.assertEqual(model["translations"][0]["project_nodes"], ["C0"])
        self.assertEqual(model["deltas"][0]["id"], "D1")

    def test_paper_graph_api_prefers_dataset_paper_understanding(self):
        from tools.research_dataset import initialize_dataset
        from tools.research_dataset_import import import_demo_visual_affordance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            shutil.copytree(REPO_ROOT / "examples" / "workspaces", root)
            initialize_dataset(root)
            import_demo_visual_affordance(root, reset=True)
            rel_paper = "wiki/projects/DemoVisualAffordance/papers/do2017-affordancenet/index.md"

            status, payload = handle_paper_graph_request(root, f"/api/paper-graph?path={quote(rel_paper)}")
            model = json.loads(payload.decode("utf-8"))

        self.assertEqual(status, 200)
        self.assertEqual(model["source"], "research-pilot.db")
        self.assertEqual(model["source_boundary"], "paper_understanding_from_research_dataset")
        self.assertEqual({node["kind"] for node in model["nodes"]}, {"question", "claim", "evidence", "warrant", "limitation"})
        self.assertEqual(model["paper_links"][0]["target"], "P-C1")

    def test_project_card_prefers_overview_display_title_over_query_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Overview\ndisplay_title: Demo Display Title\ntype: project-overview\nmaturity_stage: project_shell\n---\n"
                "# Demo Display Title\n\n## Project Direction\n\nBroad direction.\n\n## Seed Questions\n\n- Setup prompt\n",
                encoding="utf-8",
            )
            (project / "project-query-pack.md").write_text(
                "---\ntitle: Demo Query Pack\ntype: project-query-pack\n---\n# Demo Query Pack\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["title"], "Demo Display Title")
        self.assertEqual(index["projects"][0]["overview"]["seed_questions"], ["Setup prompt"])
        self.assertEqual(index["projects"][0]["overview"]["accepted_questions"], [])
        self.assertNotIn("Setup prompt", index["projects"][0]["overview"]["current_questions"])

    def test_project_card_uses_query_pack_title_when_overview_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "project-query-pack.md").write_text(
                "---\ntitle: Demo Query Pack\ntype: project-query-pack\n---\n# Demo Query Pack\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["title"], "Demo Query Pack")

    def test_dashboard_accepted_questions_come_from_graph_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo\n\n## Search Questions\n\n- Search prompt\n",
                encoding="utf-8",
            )
            (project / "project-understanding-graph.md").write_text(
                "---\ntitle: Demo Graph\ntype: project-understanding-graph\n---\n"
                "# Demo Graph\n\n## Project Questions\n\n"
                "| ID | Question | Role | Status | Confidence | Human Review | Source Refs | Bounds |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q0 | Does the model encode interaction knowledge? | main | active | medium | accepted | human | none |\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(
            index["projects"][0]["overview"]["accepted_questions"],
            ["Does the model encode interaction knowledge?"],
        )
        self.assertEqual(index["projects"][0]["overview"]["search_questions"], ["Search prompt"])

    def test_dashboard_pending_active_graph_questions_are_not_accepted_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo\n",
                encoding="utf-8",
            )
            (project / "project-understanding-graph.md").write_text(
                "---\ntitle: Demo Graph\ntype: project-understanding-graph\n---\n"
                "# Demo Graph\n\n## Project Questions\n\n"
                "| ID | Question | Role | Status | Confidence | Human Review | Source Refs | Bounds |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q0 | Does the model encode interaction knowledge? | main | active | medium | pending | human | none |\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["overview"]["accepted_questions"], [])
        self.assertNotIn(
            "Does the model encode interaction knowledge?",
            index["projects"][0]["overview"]["current_questions"],
        )


if __name__ == "__main__":
    unittest.main()
