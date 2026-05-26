# Unified Research Island Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Workspace-first dashboard island with `Understanding`, `Literature`, and `Experiments` modes, backed by lazy workspace graph read models and preserving Papers as a separate source library.

**Architecture:** Add a read-only `/api/workspace-graph` endpoint over `research-pilot.db`, with mode/layer builders in a new backend read-model module. Add a new React island for Workspace that consumes the mode/layer contract, renders a shared canvas/inspector shell, and uses mode-specific adapters. Keep old page APIs during migration.

**Tech Stack:** Python stdlib `unittest` + SQLite read models, `tools/research_browser_server.py`, static dashboard HTML/CSS/JS, React 19, Vite, `@xyflow/react`.

---

## Scope And Sequencing

This is one product initiative with two coupled tracks:

- Backend/read-model track: contract, stable IDs, mode/layer lazy data, evaluation settings, claim impact mapping.
- Frontend track: Workspace page, unified island shell, Understanding/Literature/Experiments adapters, cleanup.

Do backend contract and tests first. Frontend must not consume old page-specific APIs directly once `/api/workspace-graph` exists.

## File Map

Create:

- `tools/workspace_graph_read_models.py`  
  Owns `/api/workspace-graph` read models: request parsing helpers, stable graph IDs, payload assembly, mode/layer builders, evaluation setting normalization.

- `tests/test_workspace_graph_read_models.py`  
  Tests backend workspace graph payloads for all modes/layers using imported Demo Visual Affordance workspace.

- `dashboard/workspace.html`  
  New Workspace page. Loads shared dashboard CSS/JS and workspace island bundle.

- `dashboard/workspace-island/package.json` is not needed; use root `dashboard/package.json`.

- `dashboard/workspace-island/vite.config.mjs`  
  Vite config for Workspace island bundle.

- `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`  
  React entry point and shared shell.

- `dashboard/workspace-island/src/workspace-island.css`  
  Island-specific styles for shell, React Flow nodes, inspector, controls, light/dark compatibility.

Modify:

- `tools/research_browser_server.py`  
  Add import and `/api/workspace-graph` handler.

- `dashboard/package.json`  
  Add `build:workspace-island` script.

- `dashboard/app.js`  
  Add Workspace URL/nav/page renderer, `loadWorkspaceGraphFromApi`, mount Workspace island, low-risk cleanup.

- `dashboard/index.html`  
  Project index remains but project open action should go to Workspace.

- `dashboard/project.html`  
  Keep compatibility route or redirect/render Workspace shell for existing URLs.

- `dashboard/lineage.html` and `dashboard/experiments.html`  
  Keep compatibility routes. They can render Workspace with selected mode in later tasks.

- `dashboard/styles.css`  
  Workspace shell container, top-level cleanup, Papers filter cleanup, Paper detail read-only state hiding.

- `tests/test_related_work_lineage_dashboard.py`  
  Update dashboard page/nav/source assertions.

Do not modify `dashboard/project-graph/src/ProjectGraphApp.jsx` or `dashboard/lineage-atlas/src/LineageAtlasApp.jsx` in this plan. Workspace island consumes `/api/workspace-graph` read models directly.

## Task 1: Backend Contract Freeze And Failing Tests

**Files:**
- Create: `tests/test_workspace_graph_read_models.py`
- Read: `docs/superpowers/specs/2026-05-26-unified-research-island-dashboard-prd.md`
- Read: `tests/test_research_dataset_read_models.py`

- [ ] **Step 1: Create failing backend contract test file**

Create `tests/test_workspace_graph_read_models.py`:

```python
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.research_dataset import initialize_dataset
from tools.research_dataset_import import import_demo_visual_affordance
from tools.workspace_graph_read_models import build_workspace_graph_model


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"


class WorkspaceGraphReadModelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "example-workspace"
        shutil.copytree(DEMO_ROOT, self.root)
        initialize_dataset(self.root)
        import_demo_visual_affordance(self.root, reset=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_understanding_project_overview_contract(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        self.assertEqual("workspace-graph-v1", model["schema_version"])
        self.assertEqual("research-pilot.db", model["source"])
        self.assertEqual(PROJECT_ID, model["project_id"])
        self.assertEqual("understanding", model["mode"])
        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertEqual("Questions", model["inspector"]["title"])
        self.assertTrue(any(node["entity_type"] == "question" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "claim" for node in model["canvas"]["nodes"]))
        question_section = next(section for section in model["inspector"]["sections"] if section["kind"] == "question_list")
        self.assertTrue(any(item["local_id"] == "Q1" for item in question_section["items"]))
        c2 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "C2")
        self.assertEqual("claim:C2", c2["id"])
        self.assertEqual("project:DemoVisualAffordance:C2", c2["db_id"])
        self.assertEqual({"mode": "understanding", "layer": "claim_focus", "focus_id": "claim:C2"}, c2["drill"])

    def test_understanding_question_selection_stays_on_project_overview(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
            selected_id="question:Q1",
        )

        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("question_detail", model["inspector"]["kind"])
        self.assertEqual("question:Q1", model["selected_id"])
        self.assertTrue(any(section["kind"] == "linked_claims" for section in model["inspector"]["sections"]))

    def test_understanding_claim_focus_contract(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        self.assertEqual("claim_focus", model["layer"])
        self.assertEqual("claim:C2", model["focus_id"])
        self.assertEqual("claim_detail", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "evidence" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "warrant" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "limitation" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "source" for node in model["canvas"]["nodes"]))

    def test_understanding_paper_focus_contract(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="paper_focus",
            focus_id="claim:C2",
            selected_id="source:paper:do2017-affordancenet",
        )

        self.assertEqual("paper_focus", model["layer"])
        self.assertEqual("claim:C2", model["focus_id"])
        self.assertEqual("source:paper:do2017-affordancenet", model["selected_id"])
        self.assertEqual("paper_layer", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "paper_claim" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "project_claim_anchor" for node in model["canvas"]["nodes"]))

    def test_literature_overview_contract(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")

        self.assertEqual("literature", model["mode"])
        self.assertEqual("literature_overview", model["layer"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "literature_lane" for node in model["canvas"]["nodes"]))
        self.assertTrue(any(node["entity_type"] == "source" for node in model["canvas"]["nodes"]))
        self.assertTrue(all(len(node["label"]) <= 120 for node in model["canvas"]["nodes"]))

    def test_experiments_evaluation_overview_uses_settings_not_claims(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("experiments", model["mode"])
        self.assertEqual("evaluation_overview", model["layer"])
        self.assertEqual("Evaluation Settings", model["inspector"]["title"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertEqual({"evaluation_setting"}, entity_types)
        setting_labels = " ".join(node["label"] for node in model["canvas"]["nodes"])
        self.assertIn("AGD20K", setting_labels)
        self.assertIn("UMD", setting_labels)
        self.assertNotIn("C2", setting_labels)

    def test_experiments_setting_focus_excludes_run_nodes(self):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        setting_id = next(node["id"] for node in overview["canvas"]["nodes"] if "AGD20K" in node["label"])

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_setting_focus",
            focus_id=setting_id,
        )

        self.assertEqual("evaluation_setting_focus", model["layer"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertIn("evaluation_setting", entity_types)
        self.assertIn("dataset", entity_types)
        self.assertIn("benchmark", entity_types)
        self.assertIn("metric_family", entity_types)
        self.assertIn("experiment", entity_types)
        self.assertNotIn("run", entity_types)

    def test_experiments_design_focus_and_run_selection(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="experiment_design_focus",
            focus_id="experiment:EXP3",
            selected_id="run:RUN3",
        )

        self.assertEqual("experiment_design_focus", model["layer"])
        self.assertEqual("experiment:EXP3", model["focus_id"])
        self.assertEqual("run:RUN3", model["selected_id"])
        self.assertEqual("run_detail", model["inspector"]["kind"])
        self.assertTrue(any(node["entity_type"] == "run" for node in model["canvas"]["nodes"]))
        self.assertFalse(any(node["entity_type"] == "evaluation_setting" for node in model["canvas"]["nodes"]))
        impact = next(section for section in model["inspector"]["sections"] if section["kind"] == "project_understanding_impact")
        self.assertTrue(any(item["target_id"] == "claim:C4" for item in impact["items"]))

    def test_invalid_layer_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="run_detail")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.workspace_graph_read_models'`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_workspace_graph_read_models.py
git commit -m "test: define workspace graph read model contract"
```

## Task 2: Backend Read Model Skeleton And Shared Helpers

**Files:**
- Create: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Create workspace read model module with skeleton**

Create `tools/workspace_graph_read_models.py`:

```python
"""Workspace graph read models for the dashboard island."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from tools.research_dataset import dataset_path
from tools.research_dataset_read_models import (
    build_experiments_model,
    build_literature_model,
    build_paper_graph_model,
    build_project_graph_model,
    build_sources_model,
)


SCHEMA_VERSION = "workspace-graph-v1"
DB_SOURCE = "research-pilot.db"
DEFAULT_LAYERS = {
    "understanding": "project_overview",
    "literature": "literature_overview",
    "experiments": "evaluation_overview",
}
VALID_LAYERS = {
    "understanding": {"project_overview", "claim_focus", "paper_focus"},
    "literature": {"literature_overview", "literature_route_focus", "literature_paper_focus"},
    "experiments": {"evaluation_overview", "evaluation_setting_focus", "experiment_design_focus"},
}


def build_workspace_graph_model(
    root: Path,
    project_id: str,
    *,
    mode: str = "understanding",
    layer: str = "",
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    mode = (mode or "understanding").strip()
    if mode not in DEFAULT_LAYERS:
        raise ValueError(f"unknown workspace graph mode: {mode}")
    layer = (layer or DEFAULT_LAYERS[mode]).strip()
    if layer not in VALID_LAYERS[mode]:
        raise ValueError(f"unknown workspace graph layer for {mode}: {layer}")
    if mode == "understanding":
        return _build_understanding(root, project_id, layer, focus_id, selected_id)
    if mode == "literature":
        return _build_literature(root, project_id, layer, focus_id, selected_id)
    return _build_experiments(root, project_id, layer, focus_id, selected_id)


def _base_payload(project_id: str, mode: str, layer: str, focus_id: str = "", selected_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": DB_SOURCE,
        "project_id": project_id,
        "mode": mode,
        "layer": layer,
        "focus_id": focus_id,
        "selected_id": selected_id,
        "breadcrumb": [{"label": "Workspace", "mode": "understanding", "layer": "project_overview", "focus_id": ""}],
        "canvas": {"layout_hint": "island", "nodes": [], "edges": []},
        "inspector": {"kind": "overview", "title": "", "summary": "", "sections": [], "actions": []},
        "available_layers": sorted(VALID_LAYERS[mode]),
        "cross_mode_jumps": [],
        "empty_state": None,
        "warnings": [],
    }


def _json_loads(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:96] or "unknown"


def _local_id(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return text.rsplit(":", 1)[-1]


def _node_graph_id(kind: str, node: dict[str, Any]) -> str:
    return f"{kind}:{node.get('local_id') or _local_id(node.get('id'))}"


def _source_graph_id(source_id: str) -> str:
    return f"source:{source_id}"


def _experiment_graph_id(experiment_id: str) -> str:
    return f"experiment:{experiment_id}"


def _run_graph_id(run_id: str) -> str:
    return f"run:{run_id}"


def _strip_prefix(value: str, prefix: str) -> str:
    text = str(value or "")
    return text[len(prefix):] if text.startswith(prefix) else text


def _connection(root: Path) -> sqlite3.Connection:
    path = dataset_path(root)
    if not path.exists():
        raise ValueError("research-pilot.db not found")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _build_understanding(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    raise NotImplementedError


def _build_literature(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    raise NotImplementedError


def _build_experiments(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    raise NotImplementedError
```

- [ ] **Step 2: Run tests and verify skeleton failure**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: FAIL with `NotImplementedError` from `_build_understanding`.

- [ ] **Step 3: Commit skeleton**

```bash
git add tools/workspace_graph_read_models.py
git commit -m "feat: add workspace graph read model skeleton"
```

## Task 3: Understanding Workspace Layers

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Implement Understanding helpers and layers**

In `tools/workspace_graph_read_models.py`, replace `_build_understanding` with this implementation and add helper functions above it:

```python
def _project_graph(root: Path, project_id: str) -> dict[str, Any]:
    return build_project_graph_model(root, project_id)


def _project_node_maps(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    by_graph_id = {}
    for node in graph.get("nodes", []):
        kind = node.get("kind", "")
        graph_id = _node_graph_id(kind, node)
        by_graph_id[graph_id] = node
    return by_db_id, by_graph_id


def _understanding_node(node: dict[str, Any], *, selected_id: str = "") -> dict[str, Any]:
    kind = str(node.get("kind") or "")
    graph_id = _node_graph_id(kind, node)
    local_id = str(node.get("local_id") or _local_id(node.get("id")))
    drill = None
    inspector = {"selected_id": graph_id}
    if kind == "claim":
        drill = {"mode": "understanding", "layer": "claim_focus", "focus_id": graph_id}
    return {
        "id": graph_id,
        "entity_type": kind,
        "db_id": node.get("id", ""),
        "local_id": local_id,
        "label": node.get("label") or node.get("text") or local_id,
        "subtitle": node.get("subtitle") or node.get("status") or "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "drill": drill,
        "inspector": inspector,
        "selected": graph_id == selected_id,
        "metadata": node.get("metadata") or {},
    }


def _question_claim_ids(graph: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
    for link in graph.get("links", []):
        relation = str(link.get("relation") or "").lower()
        if relation != "answers":
            continue
        for source_id in link.get("premises") or link.get("source") or []:
            source = node_by_id.get(source_id)
            if source and source.get("kind") == "question":
                for target_id in link.get("target") or []:
                    target = node_by_id.get(target_id)
                    if target and target.get("kind") == "claim":
                        result[_node_graph_id("question", source)].append(_node_graph_id("claim", target))
    for question in [node for node in graph.get("nodes", []) if node.get("kind") == "question"]:
        qid = _node_graph_id("question", question)
        if qid not in result:
            result[qid] = [
                _node_graph_id("claim", node)
                for node in graph.get("nodes", [])
                if node.get("kind") == "claim" and question.get("local_id") in (node.get("question_ids") or [])
            ]
    return result


def _understanding_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id, _ = _project_node_maps(graph)
    edges: list[dict[str, Any]] = []
    for link in graph.get("links", []):
        relation = str(link.get("relation") or "related")
        targets = link.get("target") or []
        sources = link.get("premises") or link.get("source") or []
        for source_db_id in sources:
            for target_db_id in targets:
                source = by_db_id.get(source_db_id)
                target = by_db_id.get(target_db_id)
                if not source or not target:
                    continue
                source_id = _node_graph_id(source.get("kind", ""), source)
                target_id = _node_graph_id(target.get("kind", ""), target)
                edges.append({
                    "id": f"edge:{_local_id(link.get('id'))}:{source_id}:{target_id}",
                    "source": source_id,
                    "target": target_id,
                    "source_db_id": source_db_id,
                    "target_db_id": target_db_id,
                    "relation": relation,
                    "label": relation,
                    "metadata": {"link_id": link.get("id"), "local_id": link.get("local_id")},
                })
    return edges


def _question_list_section(graph: dict[str, Any]) -> dict[str, Any]:
    claim_ids_by_question = _question_claim_ids(graph)
    items = []
    for node in graph.get("nodes", []):
        if node.get("kind") != "question":
            continue
        graph_id = _node_graph_id("question", node)
        items.append({
            "id": graph_id,
            "db_id": node.get("id", ""),
            "local_id": node.get("local_id") or _local_id(node.get("id")),
            "label": node.get("label") or "",
            "claim_count": len(claim_ids_by_question.get(graph_id, [])),
            "inspector": {"selected_id": graph_id},
        })
    return {"title": "Questions", "kind": "question_list", "items": items}


def _question_detail(graph: dict[str, Any], selected_id: str) -> dict[str, Any]:
    _, by_graph_id = _project_node_maps(graph)
    question = by_graph_id.get(selected_id)
    claim_ids = _question_claim_ids(graph).get(selected_id, [])
    claims = []
    for claim_id in claim_ids:
        claim = by_graph_id.get(claim_id)
        if claim:
            claims.append({
                "id": claim_id,
                "db_id": claim.get("id", ""),
                "local_id": claim.get("local_id") or _local_id(claim.get("id")),
                "label": claim.get("label") or "",
                "drill": {"mode": "understanding", "layer": "claim_focus", "focus_id": claim_id},
            })
    return {
        "kind": "question_detail",
        "title": question.get("local_id") if question else "Question",
        "summary": question.get("label", "") if question else "",
        "sections": [{"title": "Linked Claims", "kind": "linked_claims", "items": claims}],
        "actions": [],
    }


def _claim_related_nodes(graph: dict[str, Any], claim_graph_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    by_db_id, by_graph_id = _project_node_maps(graph)
    claim = by_graph_id.get(claim_graph_id)
    if not claim:
        return None, [], []
    claim_db_id = claim.get("id")
    related_db_ids: set[str] = set()
    for link in graph.get("links", []):
        targets = set(link.get("target") or [])
        sources = set(link.get("premises") or link.get("source") or [])
        if claim_db_id in targets:
            related_db_ids.update(sources)
            related_db_ids.update(link.get("warrant") or [])
            related_db_ids.update(link.get("limitations") or [])
        if claim_db_id in sources:
            related_db_ids.update(targets)
    related_nodes = [by_db_id[node_id] for node_id in sorted(related_db_ids) if node_id in by_db_id]
    source_nodes = []
    seen_sources = set()
    for node in [claim, *related_nodes]:
        for source in node.get("sources") or []:
            source_id = source.get("source_id") or source.get("path") or source.get("label")
            if not source_id or source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            source_nodes.append({
                "id": _source_graph_id(str(source_id)),
                "entity_type": "source",
                "source_id": source_id,
                "path": source.get("path", ""),
                "label": source.get("label") or source_id,
                "subtitle": "paper/source",
                "status": "",
                "confidence": "",
                "drill": {"mode": "understanding", "layer": "paper_focus", "focus_id": claim_graph_id, "selected_id": _source_graph_id(str(source_id))},
                "inspector": {"selected_id": _source_graph_id(str(source_id))},
                "metadata": source,
            })
    return claim, related_nodes, source_nodes


def _claim_detail(claim: dict[str, Any], related_nodes: list[dict[str, Any]], source_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    sections = []
    for kind, title in [
        ("claim", "Supporting Claims"),
        ("evidence", "Evidence / Grounds"),
        ("warrant", "Warrants / Bridges"),
        ("limitation", "Limitations / Boundaries"),
    ]:
        items = [
            {
                "id": _node_graph_id(kind, node),
                "db_id": node.get("id", ""),
                "local_id": node.get("local_id") or _local_id(node.get("id")),
                "label": node.get("label") or "",
                "subtitle": node.get("subtitle") or node.get("status") or "",
            }
            for node in related_nodes
            if node.get("kind") == kind
        ]
        sections.append({"title": title, "kind": kind, "items": items})
    sections.append({"title": "Source Papers", "kind": "sources", "items": source_nodes})
    return {
        "kind": "claim_detail",
        "title": claim.get("local_id") or _local_id(claim.get("id")),
        "summary": claim.get("label") or "",
        "sections": sections,
        "actions": [{"label": "View related experiment results", "kind": "cross_mode_jump", "target": {"mode": "experiments", "layer": "evaluation_overview", "focus_id": "", "selected_id": _node_graph_id("claim", claim)}}],
    }


def _build_understanding(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    graph = _project_graph(root, project_id)
    payload = _base_payload(project_id, "understanding", layer, focus_id, selected_id)
    if layer == "project_overview":
        selected_id = selected_id if selected_id.startswith("question:") else selected_id
        nodes = [_understanding_node(node, selected_id=selected_id) for node in graph.get("nodes", []) if node.get("kind") in {"question", "claim"}]
        payload["canvas"]["nodes"] = nodes
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"].startswith("question:") or edge["target"].startswith("claim:")]
        payload["inspector"] = _question_detail(graph, selected_id) if selected_id.startswith("question:") else {
            "kind": "overview",
            "title": "Questions",
            "summary": "Project questions organize the top-level Understanding graph.",
            "sections": [_question_list_section(graph)],
            "actions": [],
        }
        return payload

    if layer == "claim_focus":
        claim_id = focus_id or selected_id
        claim, related_nodes, source_nodes = _claim_related_nodes(graph, claim_id)
        if not claim:
            raise ValueError(f"unknown claim focus: {claim_id}")
        payload["focus_id"] = claim_id
        payload["canvas"]["nodes"] = [
            _understanding_node(claim, selected_id=selected_id or claim_id),
            *[_understanding_node(node, selected_id=selected_id) for node in related_nodes],
            *source_nodes,
        ]
        related_ids = {node["id"] for node in payload["canvas"]["nodes"]}
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"] in related_ids and edge["target"] in related_ids]
        payload["inspector"] = _claim_detail(claim, related_nodes, source_nodes)
        return payload

    if layer == "paper_focus":
        claim_id = focus_id
        source_id = _strip_prefix(selected_id, "source:")
        sources_model = build_sources_model(root, project_id)
        source = next((item for item in sources_model.get("sources", []) if item.get("source_id") == source_id), None)
        if not source or not source.get("locator"):
            raise ValueError(f"unknown paper source: {selected_id}")
        paper_path = root / source["locator"]
        paper_graph = build_paper_graph_model(root, paper_path)
        claim, _related_nodes, _source_nodes = _claim_related_nodes(graph, claim_id)
        if not claim:
            raise ValueError(f"unknown claim focus: {claim_id}")
        payload["focus_id"] = claim_id
        payload["selected_id"] = selected_id
        payload["canvas"]["nodes"] = [
            {
                "id": claim_id,
                "entity_type": "project_claim_anchor",
                "db_id": claim.get("id", ""),
                "local_id": claim.get("local_id") or _local_id(claim.get("id")),
                "label": claim.get("label") or claim_id,
                "subtitle": "project claim anchor",
                "status": claim.get("status") or "",
                "confidence": claim.get("confidence") or "",
                "drill": {"mode": "understanding", "layer": "claim_focus", "focus_id": claim_id},
                "inspector": {"selected_id": claim_id},
                "metadata": claim,
            },
            *[
                {
                    "id": f"paper_node:{source_id}:{node['id']}",
                    "entity_type": f"paper_{node.get('kind', 'node')}",
                    "db_id": node.get("id", ""),
                    "local_id": node.get("id", ""),
                    "label": node.get("label") or node.get("id") or "",
                    "subtitle": node.get("subtitle") or node.get("kind") or "",
                    "status": "",
                    "confidence": "",
                    "drill": None,
                    "inspector": {"selected_id": f"paper_node:{source_id}:{node['id']}"},
                    "metadata": node,
                }
                for node in paper_graph.get("nodes", [])
            ],
        ]
        payload["canvas"]["edges"] = [
            {
                "id": f"paper_edge:{source_id}:{link.get('id')}:{premise}:{link.get('target')}",
                "source": f"paper_node:{source_id}:{premise}",
                "target": f"paper_node:{source_id}:{link.get('target')}",
                "relation": link.get("relation") or "supports",
                "label": link.get("relation") or "supports",
                "metadata": link,
            }
            for link in paper_graph.get("paper_links", [])
            for premise in link.get("premises", [])
        ]
        payload["inspector"] = {
            "kind": "paper_layer",
            "title": paper_graph.get("title") or source.get("title") or source_id,
            "summary": "Paper argument layer projected beside the selected project claim.",
            "sections": [
                {"title": "Paper Nodes", "kind": "paper_node_list", "items": paper_graph.get("nodes", [])},
                {"title": "Translation Bridge", "kind": "translation_bridge", "items": paper_graph.get("translations", [])},
            ],
            "actions": [],
        }
        return payload

    raise ValueError(f"unknown understanding layer: {layer}")
```

- [ ] **Step 2: Run Understanding tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_project_overview_contract tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_question_selection_stays_on_project_overview tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_claim_focus_contract tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_paper_focus_contract -v
```

Expected: PASS for the four Understanding tests.

- [ ] **Step 3: Commit Understanding layers**

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "feat: add workspace understanding graph layers"
```

## Task 4: Literature Workspace Layers

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Implement Literature mode**

In `tools/workspace_graph_read_models.py`, replace `_build_literature` with:

```python
def _literature_node_id(kind: str, raw_id: str) -> str:
    return f"{kind}:{_slug(raw_id)}"


def _build_literature(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_literature_model(root, project_id)
    payload = _base_payload(project_id, "literature", layer, focus_id, selected_id)
    routes = model.get("routes") or []
    papers = model.get("papers") or []
    edges = model.get("explicit_edges") or []

    if layer == "literature_overview":
        nodes = []
        for route in routes:
            route_id = str(route.get("id") or route.get("lane_id") or route.get("label") or "")
            nodes.append({
                "id": _literature_node_id("literature_lane", route_id),
                "entity_type": "literature_lane",
                "db_id": route.get("lane_id") or route_id,
                "local_id": route_id,
                "label": str(route.get("label") or route_id)[:120],
                "subtitle": str(route.get("status") or route.get("axis") or "route"),
                "status": str(route.get("status") or ""),
                "confidence": "",
                "drill": {"mode": "literature", "layer": "literature_route_focus", "focus_id": _literature_node_id("literature_lane", route_id)},
                "inspector": {"selected_id": _literature_node_id("literature_lane", route_id)},
                "metadata": route,
            })
        for paper in papers:
            source_id = str(paper.get("source_id") or paper.get("id") or paper.get("title") or "")
            nodes.append({
                "id": _source_graph_id(source_id),
                "entity_type": "source",
                "source_id": source_id,
                "local_id": str(paper.get("id") or source_id),
                "label": str(paper.get("title") or paper.get("label") or source_id)[:120],
                "subtitle": str(paper.get("year") or paper.get("role") or "paper"),
                "status": str(paper.get("status") or ""),
                "confidence": "",
                "drill": {"mode": "literature", "layer": "literature_paper_focus", "focus_id": _source_graph_id(source_id)},
                "inspector": {"selected_id": _source_graph_id(source_id)},
                "metadata": paper,
            })
        payload["canvas"]["nodes"] = nodes
        payload["canvas"]["edges"] = [
            {
                "id": f"literature_edge:{index}",
                "source": _source_graph_id(str(edge.get("source") or "")),
                "target": _source_graph_id(str(edge.get("target") or "")),
                "relation": str(edge.get("relation") or "related"),
                "label": str(edge.get("relation") or "related"),
                "metadata": edge,
            }
            for index, edge in enumerate(edges)
            if edge.get("source") and edge.get("target")
        ]
        payload["inspector"] = {
            "kind": "overview",
            "title": "Literature Routes",
            "summary": "Paper-only lineage that supports but does not replace Project Understanding.",
            "sections": [{
                "title": "Routes",
                "kind": "route_list",
                "items": [
                    {
                        "id": _literature_node_id("literature_lane", str(route.get("id") or route.get("lane_id") or "")),
                        "label": route.get("label") or route.get("id") or "",
                        "paper_count": route.get("paper_count", 0),
                    }
                    for route in routes
                ],
            }],
            "actions": [],
        }
        return payload

    if layer == "literature_route_focus":
        route_key = _strip_prefix(focus_id, "literature_lane:")
        route = next((item for item in routes if _slug(item.get("id") or item.get("lane_id") or "") == route_key), None)
        if not route:
            raise ValueError(f"unknown literature route: {focus_id}")
        route_papers = [paper for paper in papers if paper.get("lane_id") == route.get("lane_id") or route.get("id") in (paper.get("route_ids") or [])]
        payload["focus_id"] = focus_id
        payload["canvas"]["nodes"] = [
            {
                "id": focus_id,
                "entity_type": "literature_lane",
                "db_id": route.get("lane_id") or route.get("id") or "",
                "local_id": route.get("id") or route.get("lane_id") or "",
                "label": str(route.get("label") or route.get("id") or "")[:120],
                "subtitle": "route",
                "status": route.get("status") or "",
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": focus_id},
                "metadata": route,
            },
            *[
                {
                    "id": _source_graph_id(str(paper.get("source_id") or paper.get("id") or "")),
                    "entity_type": "source",
                    "source_id": paper.get("source_id") or paper.get("id") or "",
                    "local_id": paper.get("id") or paper.get("source_id") or "",
                    "label": str(paper.get("title") or paper.get("label") or paper.get("id") or "")[:120],
                    "subtitle": str(paper.get("year") or paper.get("role") or "paper"),
                    "status": paper.get("status") or "",
                    "confidence": "",
                    "drill": {"mode": "literature", "layer": "literature_paper_focus", "focus_id": _source_graph_id(str(paper.get("source_id") or paper.get("id") or ""))},
                    "inspector": {"selected_id": _source_graph_id(str(paper.get("source_id") or paper.get("id") or ""))},
                    "metadata": paper,
                }
                for paper in route_papers
            ],
        ]
        payload["inspector"] = {
            "kind": "route_detail",
            "title": route.get("label") or route.get("id") or "Route",
            "summary": route.get("summary") or route.get("description") or "",
            "sections": [{"title": "Papers", "kind": "paper_list", "items": route_papers}],
            "actions": [],
        }
        return payload

    if layer == "literature_paper_focus":
        source_key = _strip_prefix(focus_id, "source:")
        paper = next((item for item in papers if str(item.get("source_id") or item.get("id") or "") == source_key), None)
        if not paper:
            raise ValueError(f"unknown literature paper: {focus_id}")
        payload["focus_id"] = focus_id
        payload["canvas"]["nodes"] = [{
            "id": focus_id,
            "entity_type": "source",
            "source_id": source_key,
            "local_id": paper.get("id") or source_key,
            "label": str(paper.get("title") or source_key)[:120],
            "subtitle": str(paper.get("year") or paper.get("role") or "paper"),
            "status": paper.get("status") or "",
            "confidence": "",
            "drill": None,
            "inspector": {"selected_id": focus_id},
            "metadata": paper,
        }]
        payload["inspector"] = {
            "kind": "paper_detail",
            "title": paper.get("title") or source_key,
            "summary": paper.get("summary") or paper.get("field_position") or "",
            "sections": [{"title": "Source Metadata", "kind": "source_metadata", "items": [paper]}],
            "actions": [{"label": "Open Paper Detail", "kind": "open_page", "target": {"page": "paper", "source_id": source_key}}],
        }
        return payload

    raise ValueError(f"unknown literature layer: {layer}")
```

- [ ] **Step 2: Run Literature test**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_literature_overview_contract -v
```

Expected: PASS.

- [ ] **Step 3: Commit Literature layers**

```bash
git add tools/workspace_graph_read_models.py
git commit -m "feat: add workspace literature graph layers"
```

## Task 5: Experiments Workspace Layers

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Implement experiment metadata and setting helpers**

In `tools/workspace_graph_read_models.py`, add these helpers above `_build_experiments`:

```python
EVALUATION_METRIC_HINTS = {
    "miou": "segmentation overlap",
    "iou": "segmentation overlap",
    "kld": "saliency/heatmap alignment",
    "sim": "saliency/heatmap alignment",
    "nss": "saliency/heatmap alignment",
    "auc": "saliency/heatmap alignment",
    "accuracy": "classification accuracy",
    "top-1": "classification accuracy",
    "top-5": "classification accuracy",
    "cosine": "representation similarity",
    "activation similarity": "representation similarity",
    "qualitative": "qualitative assessment",
    "human rating": "qualitative assessment",
    "rubric": "qualitative assessment",
}
DESCRIPTIVE_METRIC_HINTS = {
    "train images",
    "test images",
    "affordance categories",
    "supervision",
    "hold localization",
    "cut localization",
    "drink localization",
    "evidence type",
    "full-scene response",
    "simplified shape response",
}


def _metadata_list(item: dict[str, Any], key: str) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    value = metadata.get(key, [])
    if isinstance(value, list):
        return [str(entry) for entry in value if str(entry).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _metadata_text(item: dict[str, Any], key: str) -> str:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return str(metadata.get(key) or "").strip()


def _metric_family_from_names(names: list[str]) -> str:
    families = []
    for name in names:
        lower = name.lower()
        if any(hint in lower for hint in DESCRIPTIVE_METRIC_HINTS):
            continue
        for hint, family in EVALUATION_METRIC_HINTS.items():
            if hint in lower:
                families.append(family)
                break
    unique_families = sorted(set(families))
    if unique_families:
        return " + ".join(unique_families)
    return ""


def _planned_metric_family(experiment: dict[str, Any]) -> str:
    return _metric_family_from_names(_metadata_list(experiment, "metrics")) or "qualitative assessment"


def _experiment_setting(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [metric.get("name", "") for run in runs for metric in run.get("metrics", [])]
    benchmark = next((metric.get("benchmark") or metric.get("benchmark_name") for run in runs for metric in run.get("metrics", []) if metric.get("benchmark") or metric.get("benchmark_name")), "")
    dataset = next((metric.get("dataset") or metric.get("dataset_name") for run in runs for metric in run.get("metrics", []) if metric.get("dataset") or metric.get("dataset_name")), "")
    benchmark = str(benchmark or experiment.get("benchmark") or experiment.get("benchmark_name") or _metadata_text(experiment, "benchmark") or "Unspecified benchmark")
    dataset = str(dataset or experiment.get("dataset") or experiment.get("dataset_name") or _metadata_text(experiment, "dataset") or "Unspecified dataset")
    family = _metric_family_from_names(metric_names) or _planned_metric_family(experiment) or "Qualitative"
    setting_id = f"evaluation_setting:{_slug(benchmark)}:{_slug(dataset)}:{_slug(family)}"
    return {
        "id": setting_id,
        "entity_type": "evaluation_setting",
        "label": f"{benchmark} / {dataset} / {family}",
        "benchmark": benchmark,
        "dataset": dataset,
        "metric_family": family,
        "metadata": {"raw_benchmark": benchmark, "raw_dataset": dataset},
    }


def _experiments_by_id(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {experiment["id"]: experiment for experiment in model.get("experiments", [])}


def _runs_by_experiment(model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in model.get("runs", []):
        grouped[run.get("experiment_id", "")].append(run)
    return grouped


def _evaluation_settings(model: dict[str, Any]) -> list[dict[str, Any]]:
    runs_by_experiment = _runs_by_experiment(model)
    by_id: dict[str, dict[str, Any]] = {}
    for experiment in model.get("experiments", []):
        runs = runs_by_experiment.get(experiment.get("id"), [])
        setting = _experiment_setting(experiment, runs)
        current = by_id.setdefault(setting["id"], {**setting, "experiment_ids": set(), "run_ids": set(), "imported": 0, "local": 0})
        current["experiment_ids"].add(experiment.get("id", ""))
        for run in runs:
            current["run_ids"].add(run.get("id", ""))
            if run.get("origin_type") == "imported_paper":
                current["imported"] += 1
            if run.get("origin_type") == "local":
                current["local"] += 1
    result = []
    for setting in by_id.values():
        experiment_ids = sorted(item for item in setting.pop("experiment_ids") if item)
        run_ids = sorted(item for item in setting.pop("run_ids") if item)
        result.append({
            **setting,
            "experiment_ids": experiment_ids,
            "run_ids": run_ids,
            "experiment_count": len(experiment_ids),
            "run_count": len(run_ids),
            "imported_evidence_count": setting.pop("imported"),
            "local_result_count": setting.pop("local"),
        })
    return sorted(result, key=lambda item: item["label"])


def _claim_impacts(root: Path, project_id: str, run_id: str) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    with closing(_connection(root)) as connection:
        rows = connection.execute(
            """
            SELECT relation_type, to_entity_id, metadata_json
            FROM entity_links
            WHERE project_id = ?
              AND from_entity_type = 'experiment_run'
              AND from_entity_id = ?
              AND relation_type LIKE 'claim_impact:%'
            ORDER BY relation_type, to_entity_id
            """,
            (project_id, run_id),
        ).fetchall()
    for row in rows:
        metadata = _json_loads(row["metadata_json"], {})
        impact = row["relation_type"].split(":", 1)[-1]
        local_claim = metadata.get("claim") or _local_id(row["to_entity_id"])
        impacts.append({
            "id": f"claim_impact:{run_id}:{impact}:{local_claim}",
            "target_id": f"claim:{local_claim}",
            "target_db_id": row["to_entity_id"],
            "impact": impact,
            "strength": metadata.get("strength", ""),
            "metadata": metadata,
            "jump": {"mode": "understanding", "layer": "claim_focus", "focus_id": f"claim:{local_claim}"},
        })
    return impacts
```

- [ ] **Step 2: Implement `_build_experiments`**

Replace `_build_experiments` in `tools/workspace_graph_read_models.py`:

```python
def _build_experiments(root: Path, project_id: str, layer: str, focus_id: str, selected_id: str) -> dict[str, Any]:
    model = build_experiments_model(root, project_id)
    payload = _base_payload(project_id, "experiments", layer, focus_id, selected_id)
    experiments = _experiments_by_id(model)
    runs_by_experiment = _runs_by_experiment(model)
    settings = _evaluation_settings(model)

    if layer == "evaluation_overview":
        payload["canvas"]["nodes"] = [
            {
                "id": setting["id"],
                "entity_type": "evaluation_setting",
                "label": setting["label"],
                "subtitle": f"{setting['experiment_count']} experiments / {setting['run_count']} runs",
                "status": "",
                "confidence": "",
                "drill": {"mode": "experiments", "layer": "evaluation_setting_focus", "focus_id": setting["id"]},
                "inspector": {"selected_id": setting["id"]},
                "metadata": setting,
            }
            for setting in settings
        ]
        payload["inspector"] = {
            "kind": "overview",
            "title": "Evaluation Settings",
            "summary": "Datasets, benchmarks/tasks, and metric families organize Experiments before claim impact.",
            "sections": [{"title": "Evaluation Settings", "kind": "evaluation_setting_list", "items": settings}],
            "actions": [],
        }
        return payload

    if layer == "evaluation_setting_focus":
        setting = next((item for item in settings if item["id"] == focus_id), None)
        if not setting:
            raise ValueError(f"unknown evaluation setting: {focus_id}")
        payload["focus_id"] = focus_id
        metric_id = f"metric_family:{_slug(setting['metric_family'])}"
        benchmark_id = f"benchmark:{_slug(setting['benchmark'])}"
        dataset_id = f"dataset:{_slug(setting['dataset'])}"
        experiment_nodes = []
        for experiment_id in setting["experiment_ids"]:
            experiment = experiments.get(experiment_id)
            if not experiment:
                continue
            runs = runs_by_experiment.get(experiment_id, [])
            experiment_nodes.append({
                "id": _experiment_graph_id(experiment_id),
                "entity_type": "experiment",
                "db_id": experiment_id,
                "local_id": experiment_id,
                "label": experiment.get("title") or experiment_id,
                "subtitle": f"{len(runs)} runs / {experiment.get('status', '')}",
                "status": experiment.get("status") or "",
                "confidence": "",
                "drill": {"mode": "experiments", "layer": "experiment_design_focus", "focus_id": _experiment_graph_id(experiment_id)},
                "inspector": {"selected_id": _experiment_graph_id(experiment_id)},
                "metadata": experiment,
            })
        payload["canvas"]["nodes"] = [
            {
                "id": setting["id"],
                "entity_type": "evaluation_setting",
                "label": setting["label"],
                "subtitle": "selected setting",
                "status": "",
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": setting["id"]},
                "metadata": setting,
            },
            {"id": dataset_id, "entity_type": "dataset", "label": setting["dataset"], "subtitle": "dataset", "metadata": setting, "drill": None, "inspector": {"selected_id": dataset_id}},
            {"id": benchmark_id, "entity_type": "benchmark", "label": setting["benchmark"], "subtitle": "benchmark/task", "metadata": setting, "drill": None, "inspector": {"selected_id": benchmark_id}},
            {"id": metric_id, "entity_type": "metric_family", "label": setting["metric_family"], "subtitle": "metric family", "metadata": setting, "drill": None, "inspector": {"selected_id": metric_id}},
            *experiment_nodes,
        ]
        payload["canvas"]["edges"] = [
            {"id": f"setting-dataset:{focus_id}", "source": dataset_id, "target": focus_id, "relation": "defines", "label": "defines", "metadata": {}},
            {"id": f"setting-benchmark:{focus_id}", "source": benchmark_id, "target": focus_id, "relation": "defines", "label": "defines", "metadata": {}},
            {"id": f"setting-metric:{focus_id}", "source": metric_id, "target": focus_id, "relation": "measured_by", "label": "measured by", "metadata": {}},
            *[
                {"id": f"setting-exp:{focus_id}:{node['id']}", "source": focus_id, "target": node["id"], "relation": "used_by", "label": "used by", "metadata": {}}
                for node in experiment_nodes
            ],
        ]
        payload["inspector"] = {
            "kind": "evaluation_setting_detail",
            "title": setting["label"],
            "summary": "This setting groups experiment designs by benchmark/task, dataset, and metric family.",
            "sections": [
                {"title": "Dataset", "kind": "dataset", "items": [{"label": setting["dataset"]}]},
                {"title": "Benchmark / Task", "kind": "benchmark", "items": [{"label": setting["benchmark"]}]},
                {"title": "Metric Family", "kind": "metric_family", "items": [{"label": setting["metric_family"]}]},
                {"title": "Experiment Designs", "kind": "experiment_list", "items": experiment_nodes},
            ],
            "actions": [],
        }
        return payload

    if layer == "experiment_design_focus":
        experiment_id = _strip_prefix(focus_id, "experiment:")
        experiment = experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"unknown experiment: {focus_id}")
        runs = runs_by_experiment.get(experiment_id, [])
        payload["focus_id"] = _experiment_graph_id(experiment_id)
        run_nodes = [
            {
                "id": _run_graph_id(run["id"]),
                "entity_type": "run",
                "db_id": run["id"],
                "local_id": run["id"],
                "label": run.get("run_label") or run.get("id"),
                "subtitle": f"{run.get('origin_type', '')} / {run.get('status', '')}",
                "status": run.get("status") or "",
                "confidence": "",
                "drill": None,
                "inspector": {"selected_id": _run_graph_id(run["id"])},
                "metadata": run,
            }
            for run in runs
        ]
        exp_node = {
            "id": _experiment_graph_id(experiment_id),
            "entity_type": "experiment",
            "db_id": experiment_id,
            "local_id": experiment_id,
            "label": experiment.get("title") or experiment_id,
            "subtitle": experiment.get("status") or "experiment",
            "status": experiment.get("status") or "",
            "confidence": "",
            "drill": None,
            "inspector": {"selected_id": _experiment_graph_id(experiment_id)},
            "metadata": experiment,
        }
        support_nodes = []
        for kind, values in [
            ("model", _metadata_list(experiment, "models")),
            ("baseline", _metadata_list(experiment, "baselines")),
            ("protocol", experiment.get("protocol") or _metadata_list(experiment, "protocol")),
            ("metric_family", _metadata_list(experiment, "metrics")),
        ]:
            for index, value in enumerate(values, start=1):
                support_nodes.append({
                    "id": f"{kind}:{experiment_id}:{index}",
                    "entity_type": kind,
                    "label": str(value),
                    "subtitle": kind,
                    "metadata": {"experiment_id": experiment_id, "value": value},
                    "drill": None,
                    "inspector": {"selected_id": f"{kind}:{experiment_id}:{index}"},
                })
        payload["canvas"]["nodes"] = [exp_node, *support_nodes, *run_nodes]
        payload["canvas"]["edges"] = [
            *[
                {"id": f"exp-support:{node['id']}", "source": node["id"], "target": exp_node["id"], "relation": "defines", "label": "defines", "metadata": {}}
                for node in support_nodes
            ],
            *[
                {"id": f"exp-run:{experiment_id}:{run['id']}", "source": exp_node["id"], "target": run["id"], "relation": "produces", "label": "produces", "metadata": {}}
                for run in run_nodes
            ],
        ]
        payload["inspector"] = _run_inspector(root, project_id, selected_id, runs) if selected_id.startswith("run:") else {
            "kind": "experiment_detail",
            "title": experiment.get("title") or experiment_id,
            "summary": experiment.get("question") or "",
            "sections": [
                {"title": "Hypothesis", "kind": "text", "items": [{"text": experiment.get("hypothesis") or ""}]},
                {"title": "Expected Evidence", "kind": "text", "items": [{"text": _metadata_text(experiment, "expected_evidence")}]},
                {"title": "Risks", "kind": "risk_list", "items": [{"text": item} for item in _metadata_list(experiment, "risks")]},
                {"title": "Runs", "kind": "run_list", "items": run_nodes},
            ],
            "actions": [],
        }
        payload["selected_id"] = selected_id
        return payload

    raise ValueError(f"unknown experiments layer: {layer}")


def _run_inspector(root: Path, project_id: str, selected_id: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = _strip_prefix(selected_id, "run:")
    run = next((item for item in runs if item.get("id") == run_id), None)
    if not run:
        raise ValueError(f"unknown run: {selected_id}")
    impacts = _claim_impacts(root, project_id, run_id)
    return {
        "kind": "run_detail",
        "title": run.get("run_label") or run_id,
        "summary": run.get("summary") or "",
        "sections": [
            {"title": "Metric Values", "kind": "metric_values", "items": run.get("metrics") or []},
            {"title": "Artifacts", "kind": "artifacts", "items": run.get("artifacts") or []},
            {"title": "Interpretation", "kind": "text", "items": [{"text": _metadata_text(run, "interpretation")}]},
            {"title": "Weaknesses", "kind": "weakness_list", "items": [{"text": item} for item in _metadata_list(run, "weaknesses")]},
            {"title": "Project Understanding Impact", "kind": "project_understanding_impact", "items": impacts},
        ],
        "actions": [item["jump"] | {"label": f"Open {item['target_id']}", "kind": "cross_mode_jump"} for item in impacts],
    }
```

- [ ] **Step 3: Run Experiments tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_experiments_evaluation_overview_uses_settings_not_claims tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_experiments_setting_focus_excludes_run_nodes tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_experiments_design_focus_and_run_selection tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_invalid_layer_raises_value_error -v
```

Expected: PASS.

- [ ] **Step 4: Run full workspace read model test file**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit Experiments layers**

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "feat: add workspace experiments graph layers"
```

## Task 6: `/api/workspace-graph` Server Endpoint

**Files:**
- Modify: `tools/research_browser_server.py`
- Test: `tests/test_workspace_graph_read_models.py`
- Create or Modify: `tests/test_research_browser_server.py` if existing server tests are present; otherwise extend `tests/test_workspace_graph_read_models.py` with handler-level tests.

- [ ] **Step 1: Add handler tests**

Append to `tests/test_workspace_graph_read_models.py`:

```python
from http import HTTPStatus

from tools.research_browser_server import handle_workspace_graph_request
```

Add methods inside `WorkspaceGraphReadModelsTest`:

```python
    def test_workspace_graph_handler_returns_json(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=evaluation_overview",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-v1", data["schema_version"])
        self.assertEqual("experiments", data["mode"])
        self.assertEqual("evaluation_overview", data["layer"])

    def test_workspace_graph_handler_rejects_invalid_layer(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=run_detail",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("unknown workspace graph layer", data["message"])
```

- [ ] **Step 2: Run handler tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_json tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_rejects_invalid_layer -v
```

Expected: FAIL with `ImportError` for `handle_workspace_graph_request`.

- [ ] **Step 3: Implement endpoint handler**

In `tools/research_browser_server.py`, add import near other read model imports:

```python
from tools.workspace_graph_read_models import build_workspace_graph_model
```

Add function near `handle_experiments_request`:

```python
def handle_workspace_graph_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    query = parse_qs(urlsplit(request_path).query)
    project_id = query.get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    mode = query.get("mode", ["understanding"])[0].strip() or "understanding"
    layer = query.get("layer", [""])[0].strip()
    focus_id = query.get("focus_id", [""])[0].strip()
    selected_id = query.get("selected_id", [""])[0].strip()
    try:
        model = build_workspace_graph_model(
            root.resolve(),
            project_id,
            mode=mode,
            layer=layer,
            focus_id=focus_id,
            selected_id=selected_id,
        )
    except ValueError as exc:
        return json_response(
            {
                "error": "Invalid workspace graph request",
                "message": str(exc),
                "schema_version": "workspace-graph-error-v1",
            },
            HTTPStatus.BAD_REQUEST,
        )
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        return json_response(
            {
                "error": "Invalid workspace graph request",
                "message": str(exc),
                "schema_version": "workspace-graph-error-v1",
            },
            HTTPStatus.BAD_REQUEST,
        )
    return json_response(model)
```

In `ResearchBrowserHandler.do_GET`, add before `/api/project-graph`:

```python
        elif request_api_path == "/api/workspace-graph":
            status, payload = handle_workspace_graph_request(root, self.path)
```

- [ ] **Step 4: Run handler tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_json tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_rejects_invalid_layer -v
```

Expected: PASS.

- [ ] **Step 5: Run backend read model regression tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models tests.test_research_dataset_read_models -v
```

Expected: PASS.

- [ ] **Step 6: Commit endpoint**

```bash
git add tools/research_browser_server.py tests/test_workspace_graph_read_models.py
git commit -m "feat: expose workspace graph API"
```

## Task 7: Workspace Island Scaffold

**Files:**
- Create: `dashboard/workspace.html`
- Create: `dashboard/workspace-island/vite.config.mjs`
- Create: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Create: `dashboard/workspace-island/src/workspace-island.css`
- Modify: `dashboard/package.json`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add dashboard source tests**

Append test methods to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_workspace_page_and_island_bundle_exist(self):
        html = (ROOT / "dashboard" / "workspace.html").read_text(encoding="utf-8")
        package = json.loads((ROOT / "dashboard" / "package.json").read_text(encoding="utf-8"))

        self.assertIn('data-page="workspace"', html)
        self.assertIn("workspace-island.bundle.js?v=english-dashboard-20260523", html)
        self.assertIn("workspace-island.bundle.css?v=english-dashboard-20260523", html)
        self.assertEqual(
            "vite build --config workspace-island/vite.config.mjs",
            package["scripts"].get("build:workspace-island"),
        )
        self.assertTrue((ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").is_file())
        self.assertTrue((ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").is_file())
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_page_and_island_bundle_exist -v
```

Expected: FAIL because files and script are missing.

- [ ] **Step 3: Create `dashboard/workspace.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Research Browser · Workspace</title>
    <link rel="stylesheet" href="./styles.css?v=english-dashboard-20260523" />
    <link rel="stylesheet" href="./workspace-island.bundle.css?v=english-dashboard-20260523" />
  </head>
  <body data-page="workspace">
    <div id="app">
      <main class="app-shell">
        <div class="empty-state">Loading workspace...</div>
      </main>
    </div>
    <script src="./app.js?v=english-dashboard-20260523" defer></script>
    <script src="./workspace-island.bundle.js?v=english-dashboard-20260523" defer></script>
  </body>
</html>
```

- [ ] **Step 4: Add Vite config**

Create `dashboard/workspace-island/vite.config.mjs`:

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../",
    emptyOutDir: false,
    lib: {
      entry: "src/WorkspaceIslandApp.jsx",
      name: "ResearchBrowserWorkspaceIsland",
      formats: ["iife"],
      fileName: () => "workspace-island.bundle.js",
    },
    rollupOptions: {
      output: {
        assetFileNames: "workspace-island.bundle.css",
      },
    },
  },
});
```

- [ ] **Step 5: Add initial Workspace island source**

Create `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`:

```jsx
import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./workspace-island.css";

const mountedRoots = new WeakMap();
const modes = ["understanding", "literature", "experiments"];
const modeLabels = {
  understanding: "Understanding",
  literature: "Literature",
  experiments: "Experiments",
};

function nodeColor(node) {
  const type = node?.data?.entity_type || "";
  if (type === "question") return "#8ec7ff";
  if (type === "claim" || type === "evaluation_setting") return "#d6a84f";
  if (type === "experiment" || type === "run") return "#70d6a3";
  if (type === "source") return "#68c7d4";
  return "#8f98a8";
}

function toFlowNode(node, index, onNodeAction) {
  return {
    id: node.id,
    type: "default",
    position: node.position || { x: (index % 4) * 340, y: Math.floor(index / 4) * 180 },
    data: {
      label: (
        <button type="button" className="workspace-node-button" onClick={() => onNodeAction(node)}>
          <span>{node.local_id || node.entity_type}</span>
          <strong>{node.label}</strong>
          {node.subtitle ? <em>{node.subtitle}</em> : null}
        </button>
      ),
      entity_type: node.entity_type,
    },
    style: { width: node.entity_type === "source" ? 300 : 280, minHeight: 104 },
  };
}

function toFlowEdge(edge) {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: "smoothstep",
  };
}

function WorkspaceInspector({ inspector }) {
  const sections = Array.isArray(inspector?.sections) ? inspector.sections : [];
  return (
    <aside className="workspace-inspector" aria-label="Workspace inspector">
      <p className="eyebrow">{inspector?.kind || "Inspector"}</p>
      <h2>{inspector?.title || "Workspace"}</h2>
      {inspector?.summary ? <p>{inspector.summary}</p> : null}
      {sections.map((section, index) => (
        <section key={`${section.kind || "section"}:${index}`}>
          <h3>{section.title || section.kind || "Section"}</h3>
          <div className="workspace-inspector-list">
            {(section.items || []).map((item, itemIndex) => (
              <article key={item.id || item.local_id || item.label || itemIndex}>
                <span>{item.local_id || item.id || item.kind || ""}</span>
                <strong>{item.label || item.title || item.text || item.target_id || ""}</strong>
                {item.subtitle || item.impact ? <em>{item.subtitle || item.impact}</em> : null}
              </article>
            ))}
            {!section.items?.length ? <em>No records.</em> : null}
          </div>
        </section>
      ))}
    </aside>
  );
}

function WorkspaceIslandApp({ model, onNavigate }) {
  const [activeMode, setActiveMode] = useState(model?.mode || "understanding");
  const nodes = useMemo(
    () => (model?.canvas?.nodes || []).map((node, index) => toFlowNode(node, index, (item) => onNavigate?.(item.drill || item.inspector || { selected_id: item.id }))),
    [model, onNavigate],
  );
  const edges = useMemo(() => (model?.canvas?.edges || []).map(toFlowEdge), [model]);
  return (
    <ReactFlowProvider>
      <section className="workspace-island-shell">
        <header className="workspace-island-toolbar">
          <nav aria-label="Workspace modes">
            {modes.map((mode) => (
              <button
                key={mode}
                type="button"
                className={mode === activeMode ? "is-active" : ""}
                onClick={() => {
                  setActiveMode(mode);
                  onNavigate?.({ mode });
                }}
              >
                {modeLabels[mode]}
              </button>
            ))}
          </nav>
        </header>
        <div className="workspace-island-body">
          <div className="workspace-canvas" aria-label="Workspace graph canvas">
            <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.05} maxZoom={2} proOptions={{ hideAttribution: true }}>
              <Background variant={BackgroundVariant.Lines} gap={42} size={1} />
              <Controls position="top-right" showInteractive={false} />
              <MiniMap position="bottom-right" nodeColor={nodeColor} pannable zoomable />
            </ReactFlow>
          </div>
          <WorkspaceInspector inspector={model?.inspector || {}} />
        </div>
      </section>
    </ReactFlowProvider>
  );
}

function mount(root, props) {
  if (!root) return null;
  const previous = mountedRoots.get(root);
  if (previous) previous.unmount();
  const reactRoot = createRoot(root);
  reactRoot.render(<WorkspaceIslandApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

window.ResearchBrowserWorkspaceIsland = { mount, WorkspaceIslandApp };
```

- [ ] **Step 6: Add initial Workspace island CSS**

Create `dashboard/workspace-island/src/workspace-island.css`:

```css
.workspace-island-shell {
  min-height: calc(100vh - 150px);
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-1);
  overflow: hidden;
}

.workspace-island-toolbar {
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border);
  padding: 10px;
}

.workspace-island-toolbar nav {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 4px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px;
  background: var(--surface-2);
}

.workspace-island-toolbar button {
  min-height: 42px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-weight: 800;
  cursor: pointer;
}

.workspace-island-toolbar button.is-active {
  border-color: var(--accent);
  color: var(--text);
  background: var(--accent-soft);
}

.workspace-island-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  min-height: calc(100vh - 215px);
}

.workspace-canvas {
  min-height: calc(100vh - 215px);
  background: var(--graph-bg, var(--surface-0));
}

.workspace-inspector {
  border-left: 1px solid var(--border);
  padding: 18px;
  overflow: auto;
  background: var(--surface-1);
}

.workspace-inspector h2,
.workspace-inspector h3 {
  margin: 0;
}

.workspace-inspector section {
  border-top: 1px solid var(--border);
  margin-top: 16px;
  padding-top: 16px;
}

.workspace-inspector-list {
  display: grid;
  gap: 8px;
}

.workspace-inspector-list article {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  background: var(--surface-2);
}

.workspace-inspector-list span,
.workspace-inspector-list em {
  display: block;
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 12px;
}

.workspace-node-button {
  width: 100%;
  min-height: 92px;
  display: grid;
  gap: 6px;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  color: var(--text);
  background: var(--surface-2);
  cursor: pointer;
}

.workspace-node-button span,
.workspace-node-button em {
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 12px;
}

@media (max-width: 900px) {
  .workspace-island-body {
    grid-template-columns: 1fr;
  }

  .workspace-inspector {
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}
```

- [ ] **Step 7: Add build script**

Modify `dashboard/package.json` scripts:

```json
"build:workspace-island": "vite build --config workspace-island/vite.config.mjs"
```

- [ ] **Step 8: Run source test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_page_and_island_bundle_exist -v
```

Expected: PASS.

- [ ] **Step 9: Build Workspace island**

Run:

```bash
cd dashboard && npm run build:workspace-island
```

Expected: Vite builds `workspace-island.bundle.js` and `workspace-island.bundle.css`.

- [ ] **Step 10: Commit Workspace scaffold**

```bash
git add dashboard/workspace.html dashboard/workspace-island dashboard/package.json dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_related_work_lineage_dashboard.py
git commit -m "feat: add workspace island scaffold"
```

## Task 8: Dashboard Routing, Nav, And Lazy Workspace Loading

**Files:**
- Modify: `dashboard/app.js`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add routing tests**

Append to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_workspace_page_hooks_and_primary_nav(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function workspaceUrl(projectId, mode = \"understanding\")", app)
        self.assertIn("async function loadWorkspaceGraphFromApi", app)
        self.assertIn("async function renderWorkspacePage()", app)
        self.assertIn("ResearchBrowserWorkspaceIsland.mount", app)
        self.assertIn('current === "workspace"', app)
        self.assertIn(">Workspace</a>", app)
        self.assertIn(">Papers</a>", app)
        self.assertNotIn(">Technical Lineage</a>", app)
        self.assertNotIn(">Experiments</a>", app)
```

- [ ] **Step 2: Run routing test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_page_hooks_and_primary_nav -v
```

Expected: FAIL because app hooks are missing.

- [ ] **Step 3: Add Workspace state and URL helper**

In `dashboard/app.js`, near existing URL helpers, add:

```javascript
function workspaceUrl(projectId, mode = "understanding") {
  return dashboardPageUrl("workspace", { project: projectId, mode });
}
```

- [ ] **Step 4: Update project nav**

In `renderProjectNav(project, current)`, replace separate Project/Lineage/Experiments links with:

```javascript
  const workspaceCurrent = ["workspace", "project", "lineage", "experiments"].includes(current) ? ' aria-current="page"' : "";
  const papersCurrent = ["papers", "round", "paper", "deep-reads"].includes(current) ? ' aria-current="page"' : "";
  return `
    <nav class="project-nav" aria-label="Project sections">
      <a href="${escapeAttr(workspaceUrl(project.id))}"${workspaceCurrent}>Workspace</a>
      <a href="${escapeAttr(papersUrl(project.id))}"${papersCurrent}>Papers</a>
    </nav>
  `;
```

- [ ] **Step 5: Add workspace API loader**

In `dashboard/app.js`, near other API loaders:

```javascript
async function loadWorkspaceGraphFromApi(projectId, options = {}) {
  if (!projectId) return null;
  const search = new URLSearchParams();
  search.set("project", projectId);
  search.set("mode", options.mode || "understanding");
  if (options.layer) search.set("layer", options.layer);
  if (options.focus_id) search.set("focus_id", options.focus_id);
  if (options.selected_id) search.set("selected_id", options.selected_id);
  const response = await fetch(`/api/workspace-graph?${search.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.message || payload.error || `Workspace graph failed: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 6: Add Workspace page renderer**

In `dashboard/app.js`, add:

```javascript
async function renderWorkspacePage() {
  const project = selectedProject();
  if (!project) {
    renderProjectIndex();
    return;
  }
  const mode = normalizeToken(params().get("mode") || "understanding");
  setHeader("Workspace", project.title || project.name || project.id, "Project understanding, literature, and experiments.");
  setProjectNav(project, "workspace");
  el.content.innerHTML = `
    <section class="workspace-page-shell" aria-label="Project workspace">
      <div id="workspace-island-root" class="workspace-island-root">
        <div class="empty-state">Loading workspace graph...</div>
      </div>
    </section>
  `;
  const root = document.getElementById("workspace-island-root");
  const mountApi = window.ResearchBrowserWorkspaceIsland;
  if (!root || !mountApi?.mount) {
    root.innerHTML = `<div class="empty-state">Workspace island bundle unavailable.</div>`;
    return;
  }
  const model = await loadWorkspaceGraphFromApi(project.id, { mode });
  const navigate = async (target = {}) => {
    const nextMode = target.mode || model.mode || "understanding";
    const nextLayer = target.layer || "";
    const nextFocus = target.focus_id || "";
    const nextSelected = target.selected_id || "";
    const nextModel = await loadWorkspaceGraphFromApi(project.id, {
      mode: nextMode,
      layer: nextLayer,
      focus_id: nextFocus,
      selected_id: nextSelected,
    });
    mountApi.mount(root, { model: nextModel, onNavigate: navigate });
  };
  mountApi.mount(root, { model, onNavigate: navigate });
}
```

- [ ] **Step 7: Wire page dispatch**

In the main render dispatch, add before project/lineage/experiments legacy pages:

```javascript
  else if (state.page === "workspace") await renderWorkspacePage();
```

- [ ] **Step 8: Make Project page compatibility render Workspace**

In `renderProjectWorkspace()`, either call `renderWorkspacePage()` directly or replace the body with a redirect link. Preferred for compatibility:

```javascript
async function renderProjectWorkspace() {
  await renderWorkspacePage();
}
```

- [ ] **Step 9: Run routing tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_page_hooks_and_primary_nav tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_project_page_hides_old_workflow_panels -v
```

Expected: PASS.

- [ ] **Step 10: Commit routing**

```bash
git add dashboard/app.js tests/test_related_work_lineage_dashboard.py
git commit -m "feat: route dashboard workspace through unified island"
```

## Task 9: Workspace Island Interaction Hardening

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add source guards for shell behavior**

Append to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_workspace_island_contains_layer_overview_and_terminal_run_rules(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("WorkspaceInspector", source)
        self.assertIn("onNavigate?.(item.drill || item.inspector", source)
        self.assertIn("modeLabels", source)
        self.assertIn("understanding", source)
        self.assertIn("literature", source)
        self.assertIn("experiments", source)
        self.assertNotIn("run_detail", source)
```

- [ ] **Step 2: Run test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_contains_layer_overview_and_terminal_run_rules -v
```

Expected: PASS if Task 7 source exists and does not hardcode run_detail navigation.

- [ ] **Step 3: Improve React node dimensions and inspector actions**

In `WorkspaceIslandApp.jsx`, update `WorkspaceInspector` to render actions:

```jsx
      {Array.isArray(inspector?.actions) && inspector.actions.length ? (
        <section>
          <h3>Actions</h3>
          <div className="workspace-inspector-actions">
            {inspector.actions.map((action, index) => (
              <button key={action.label || index} type="button" onClick={() => window.dispatchEvent(new CustomEvent("workspace-island-action", { detail: action.target || action }))}>
                {action.label || "Open"}
              </button>
            ))}
          </div>
        </section>
      ) : null}
```

Add listener in `WorkspaceIslandApp` before return:

```jsx
  React.useEffect(() => {
    const handler = (event) => onNavigate?.(event.detail || {});
    window.addEventListener("workspace-island-action", handler);
    return () => window.removeEventListener("workspace-island-action", handler);
  }, [onNavigate]);
```

- [ ] **Step 4: Improve CSS for readable nodes**

In `workspace-island.css`, add:

```css
.workspace-inspector-actions {
  display: grid;
  gap: 8px;
}

.workspace-inspector-actions button {
  min-height: 38px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--text);
  font-weight: 800;
  cursor: pointer;
}

.react-flow__node-default {
  border: 0;
  padding: 0;
  background: transparent;
}
```

- [ ] **Step 5: Build and test island**

Run:

```bash
cd dashboard && npm run build:workspace-island
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_contains_layer_overview_and_terminal_run_rules -v
```

Expected: Vite build PASS and test PASS.

- [ ] **Step 6: Commit interaction hardening**

```bash
git add dashboard/workspace-island dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_related_work_lineage_dashboard.py
git commit -m "feat: harden workspace island interactions"
```

## Task 10: Low-Risk Cleanup

**Files:**
- Modify: `dashboard/app.js`
- Modify: `dashboard/styles.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add cleanup tests**

Append to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_dashboard_cleanup_removes_low_value_metrics_and_read_only_state(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        project_index_start = app.index("function renderProjectIndex()")
        project_index_end = app.index("async function renderProjectWorkspace()", project_index_start)
        project_index = app[project_index_start:project_index_end]
        self.assertNotIn("Candidate", project_index)
        self.assertNotIn("ProjectPaper", project_index)
        self.assertNotIn("paper_count", project_index)
        self.assertNotIn("Rounds", project_index)
        self.assertNotIn("Claims", project_index)

        paper_detail_start = app.index("async function renderPaperPage()")
        paper_detail_end = app.index("function paperDetail", paper_detail_start) if "function paperDetail" in app[paper_detail_start:] else paper_detail_start + 8000
        paper_detail = app[paper_detail_start:paper_detail_end]
        self.assertNotIn("READ-ONLY PAPER STATE", paper_detail)
```

- [ ] **Step 2: Run cleanup test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_dashboard_cleanup_removes_low_value_metrics_and_read_only_state -v
```

Expected: FAIL until cleanup is done.

- [ ] **Step 3: Remove project index internal metric strip**

In `dashboard/app.js`, inside `renderProjectIndex()`, remove the `<dl>` block containing:

```javascript
Candidate
ProjectPaper
paper_count
Rounds
Claims
```

Keep title, demo pill, question, status copy, and action links.

- [ ] **Step 4: Hide Paper detail read-only state block**

In `dashboard/app.js`, in paper detail rendering, remove the visible section headed:

```text
READ-ONLY PAPER STATE
```

Preserve title metadata chips and paper content sections. Do not render `review_status`, `current_state`, `read_level`, `summary_status`, `human_review`, `project_core_for`, or `global_core` as a primary block.

- [ ] **Step 5: Fix Papers filter overflow**

In `dashboard/styles.css`, update the existing `.paper-library-filters` selectors:

```css
.paper-library-filters {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px) minmax(160px, 220px);
  gap: 10px;
  align-items: end;
}

.paper-library-filters input,
.paper-library-filters select,
.paper-library-filters button {
  min-width: 0;
  width: 100%;
}

@media (max-width: 900px) {
  .paper-library-filters {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 6: Run cleanup test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_dashboard_cleanup_removes_low_value_metrics_and_read_only_state -v
```

Expected: PASS.

- [ ] **Step 7: Commit cleanup**

```bash
git add dashboard/app.js dashboard/styles.css tests/test_related_work_lineage_dashboard.py
git commit -m "fix: clean up dashboard workspace surfaces"
```

## Task 11: Compatibility Routes For Legacy Project/Lineage/Experiments URLs

**Files:**
- Modify: `dashboard/app.js`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add compatibility test**

Append to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_legacy_graph_pages_delegate_to_workspace_modes(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function legacyWorkspaceModeForPage", app)
        self.assertIn('if (state.page === "lineage") return "literature";', app)
        self.assertIn('if (state.page === "experiments") return "experiments";', app)
```

- [ ] **Step 2: Implement compatibility helper**

In `dashboard/app.js`, add:

```javascript
function legacyWorkspaceModeForPage(page = state.page) {
  if (page === "lineage") return "literature";
  if (page === "experiments") return "experiments";
  return "understanding";
}
```

In `renderWorkspacePage()`, change mode line to:

```javascript
  const mode = normalizeToken(params().get("mode") || legacyWorkspaceModeForPage(state.page));
```

In dispatch, route legacy pages:

```javascript
  else if (["workspace", "project", "lineage", "experiments"].includes(state.page)) await renderWorkspacePage();
```

Remove later separate `lineage` and `experiments` dispatch branches, or leave unreachable only if tests allow. Preferred remove duplicate branches.

- [ ] **Step 3: Run compatibility test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_legacy_graph_pages_delegate_to_workspace_modes -v
```

Expected: PASS.

- [ ] **Step 4: Commit compatibility routes**

```bash
git add dashboard/app.js tests/test_related_work_lineage_dashboard.py
git commit -m "feat: delegate legacy graph pages to workspace modes"
```

## Task 12: Full Verification

**Files:**
- Verification starts with no planned source changes. Defects found during verification get fixed in the same task before final handoff.

- [ ] **Step 1: Run backend tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models tests.test_research_dataset_read_models -v
```

Expected: PASS.

- [ ] **Step 2: Run dashboard source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

- [ ] **Step 3: Build React islands**

Run:

```bash
cd dashboard && npm run build:project-graph && npm run build:lineage-atlas && npm run build:workspace-island
```

Expected: all Vite builds PASS.

- [ ] **Step 4: Start local dashboard server**

Run:

```bash
python3 tools/research_browser_server.py --root examples/workspaces --port 8765
```

Expected: server starts and serves dashboard files.

- [ ] **Step 5: Manual browser smoke**

Open:

```text
http://127.0.0.1:8765/dashboard/workspace.html?v=english-dashboard-20260523&project=DemoVisualAffordance
```

Check:

- Workspace opens `Understanding`.
- Inspector default lists Questions.
- Clicking a Question updates inspector only.
- Clicking a Claim drills to Claim Focus.
- Switching `Literature` shows paper/source lineage nodes with readable titles.
- Switching `Experiments` shows Evaluation Setting nodes only.
- Clicking Evaluation Setting shows dataset/benchmark/metric/experiment design nodes, not runs.
- Clicking EXP3 shows run nodes.
- Clicking RUN3 opens run detail inspector with Project Understanding Impact at bottom.
- Theme toggle works in dark and light.

- [ ] **Step 6: Commit verification fixes if any**

When verification requires fixes:

```bash
git add <changed-files>
git commit -m "fix: stabilize unified workspace dashboard"
```

If no fixes needed, do not create an empty commit.

## Plan Self-Review

Spec coverage:

- Workspace primary tab: Tasks 7-8.
- Unified island shell: Tasks 7-9.
- Understanding Project -> Claim -> Paper preservation: Tasks 3 and 8.
- Literature Technical Lineage semantics and readability: Tasks 4, 7-9.
- Experiments Evaluation Setting hierarchy: Task 5.
- Backend `/api/workspace-graph`: Task 6.
- Lazy loading: Tasks 6 and 8.
- Stable IDs: Tasks 2-5.
- Run terminal inspector: Task 5.
- Low-risk cleanup: Task 10.
- Legacy compatibility: Task 11.
- Verification: Task 12.

Implementation notes:

- Paper Focus is implemented as `/api/workspace-graph?mode=understanding&layer=paper_focus&focus_id=claim:<id>&selected_id=source:<source_id>` and internally reuses `build_paper_graph_model`.
- Task 4 assumes `build_literature_model` exposes `routes`, `papers`, and `explicit_edges`, which matches the current DB read model contract.
- Task 10 uses the current `.paper-library-filters` selector from `dashboard/styles.css`.
