# Workspace Graph Contract v2 Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend `WorkspaceScene` and `ProjectedGraph` contract beside the current `workspace-graph-v1` API so Research Pilot can separate DB truth, semantic graph meaning, and frontend projection.

**Architecture:** Keep `research-pilot.db` as the only durable source. Add `workspace-scene-v2` builders that expose semantic entities, relations, groups, portals, capabilities, and provenance without canvas/display/drill fields. Add `workspace-projection-v1` as a separate adapter over scenes. Keep the current default `/api/workspace-graph` response unchanged while adding `?schema=scene-v2` and `?schema=projection-v1`.

**Tech Stack:** Python stdlib, SQLite, `unittest`, existing `tools/research_dataset_read_models.py`, existing `tools/research_browser_server.py`, existing static dashboard.

---

## Current State

- Durable data already lives in `examples/workspaces/research-pilot.db`.
- The DB schema is in `tools/research_dataset.py`.
- Typed writes are in `tools/research_dataset_writer.py`.
- Current graph API implementation is `tools/workspace_graph_read_models.py`.
- Current API handler is `tools/research_browser_server.py::handle_workspace_graph_request`.
- Current API contract is `workspace-graph-v1`, which mixes semantic data with UI fields: `canvas`, `drill`, `display`, `inspector`, and `breadcrumb`.
- Target contract is documented in `docs/superpowers/specs/2026-05-27-workspace-graph-system-framework-design.md`.

## File Map

Create:

- `tools/workspace_scene_contract.py`
  - Shared constants, layer normalization, canonical ids, provenance helpers, and lightweight validators for scenes/projections.

- `tools/workspace_scene_builders/__init__.py`
  - Public builder dispatch: `build_workspace_scene(...)`.

- `tools/workspace_scene_builders/provenance.py`
  - Helpers for DB row provenance and derived provenance.

- `tools/workspace_scene_builders/understanding_scene.py`
  - Builds `understanding.project_overview` and `understanding.claim_focus` scenes from DB-backed project graph read models.

- `tools/workspace_graph_projection.py`
  - Converts scene objects into `workspace-projection-v1` graph objects.

- `tests/test_workspace_scene_contract.py`
  - Contract tests for scene/projection boundary.

Modify:

- `tools/research_browser_server.py`
  - Add `schema=scene-v2` and `schema=projection-v1` support to `/api/workspace-graph`.

- `tests/test_workspace_graph_read_models.py`
  - Add API schema routing tests while preserving current default `workspace-graph-v1`.

Do not modify in this plan:

- `tools/research_dataset.py`
- `tools/research_dataset_writer.py`
- `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- built dashboard bundles
- `examples/workspaces/research-pilot.db`

## Task 1: Contract Guardrail Tests

**Files:**
- Create: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Write failing contract tests**

Create `tests/test_workspace_scene_contract.py`:

```python
import unittest

from tools.workspace_scene_contract import (
    V1_TO_V2_LAYER,
    canonical_source_id,
    normalize_workspace_layer,
    validate_projected_graph,
    validate_workspace_scene,
)


class WorkspaceSceneContractTest(unittest.TestCase):
    def test_normalize_workspace_layer_maps_current_v1_names(self):
        self.assertEqual("understanding.project_overview", normalize_workspace_layer("understanding", "project_overview"))
        self.assertEqual("understanding.claim_focus", normalize_workspace_layer("understanding", "claim_focus"))
        self.assertEqual("understanding.paper_focus", normalize_workspace_layer("understanding", "paper_focus"))
        self.assertEqual("literature.overview", normalize_workspace_layer("literature", "literature_overview"))
        self.assertEqual("literature.route_focus", normalize_workspace_layer("literature", "literature_route_focus"))
        self.assertEqual("literature.paper_focus", normalize_workspace_layer("literature", "literature_paper_focus"))
        self.assertEqual("experiments.evaluation_overview", normalize_workspace_layer("experiments", "evaluation_overview"))
        self.assertEqual("experiments.evaluation_setting_focus", normalize_workspace_layer("experiments", "evaluation_setting_focus"))
        self.assertEqual("experiments.experiment_design_focus", normalize_workspace_layer("experiments", "experiment_design_focus"))

    def test_v1_to_v2_mapping_covers_current_workspace_layers(self):
        self.assertEqual(
            {
                ("understanding", "project_overview"),
                ("understanding", "claim_focus"),
                ("understanding", "paper_focus"),
                ("literature", "literature_overview"),
                ("literature", "literature_route_focus"),
                ("literature", "literature_paper_focus"),
                ("experiments", "evaluation_overview"),
                ("experiments", "evaluation_setting_focus"),
                ("experiments", "experiment_design_focus"),
            },
            set(V1_TO_V2_LAYER),
        )

    def test_canonical_source_id_wraps_db_source_id_without_losing_prefixes(self):
        self.assertEqual("source:paper:do2017-affordancenet", canonical_source_id("paper:do2017-affordancenet"))
        self.assertEqual("source:S-demo-luo2022-agd20k", canonical_source_id("S-demo-luo2022-agd20k"))

    def test_scene_validator_rejects_ui_payload_fields(self):
        scene = {
            "schema_version": "workspace-scene-v2",
            "project_id": "DemoVisualAffordance",
            "mode": "understanding",
            "layer": "understanding.project_overview",
            "focus_id": "",
            "source": "research-pilot.db",
            "entities": [
                {
                    "canonical_id": "understanding:project:DemoVisualAffordance:claim:C2",
                    "display_id": "C2",
                    "entity_type": "claim",
                    "title": "Claim text",
                    "summary": "",
                    "status": "active",
                    "confidence": "medium",
                    "capabilities": ["inspectable", "drillable"],
                    "source": {"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:C2"},
                    "metadata": {},
                    "drill": {"mode": "understanding", "layer": "claim_focus"},
                }
            ],
            "relations": [],
            "groups": [],
            "portals": [],
            "inspector": {},
            "warnings": [],
            "canvas": {"nodes": []},
        }

        with self.assertRaisesRegex(ValueError, "WorkspaceScene must not contain UI field"):
            validate_workspace_scene(scene)

    def test_projection_validator_rejects_terminal_drill(self):
        projected = {
            "schema_version": "workspace-projection-v1",
            "project_id": "DemoVisualAffordance",
            "mode": "understanding",
            "layer": "understanding.claim_focus",
            "focus_id": "understanding:project:DemoVisualAffordance:claim:C2",
            "breadcrumb": [],
            "nodes": [
                {
                    "projected_id": "node:evidence:E1",
                    "semantic_id": "understanding:project:DemoVisualAffordance:evidence:E1",
                    "role": "terminal",
                    "visual_kind": "evidence",
                    "title": "Evidence text",
                    "display_id": "E1",
                    "interaction": {"kind": "drill", "target": {"mode": "understanding", "layer": "claim_focus"}},
                    "source": {"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:E1"},
                    "layout_hints": {},
                }
            ],
            "edges": [],
            "frames": [],
            "portals": [],
            "inspector_default_id": "",
            "layout": {"kind": "layered"},
            "warnings": [],
        }

        with self.assertRaisesRegex(ValueError, "terminal projected nodes must not drill"):
            validate_projected_graph(projected)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.workspace_scene_contract'`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_workspace_scene_contract.py
git commit -m "test: define workspace scene contract guardrails"
```

## Task 2: Shared Contract Module

**Files:**
- Create: `tools/workspace_scene_contract.py`
- Test: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Implement contract helpers and validators**

Create `tools/workspace_scene_contract.py`:

```python
#!/usr/bin/env python3
"""Workspace scene and projection contract helpers."""

from __future__ import annotations

from typing import Any


SCENE_SCHEMA_VERSION = "workspace-scene-v2"
PROJECTION_SCHEMA_VERSION = "workspace-projection-v1"
DB_SOURCE = "research-pilot.db"

V1_TO_V2_LAYER: dict[tuple[str, str], str] = {
    ("understanding", "project_overview"): "understanding.project_overview",
    ("understanding", "claim_focus"): "understanding.claim_focus",
    ("understanding", "paper_focus"): "understanding.paper_focus",
    ("literature", "literature_overview"): "literature.overview",
    ("literature", "literature_route_focus"): "literature.route_focus",
    ("literature", "literature_paper_focus"): "literature.paper_focus",
    ("experiments", "evaluation_overview"): "experiments.evaluation_overview",
    ("experiments", "evaluation_setting_focus"): "experiments.evaluation_setting_focus",
    ("experiments", "experiment_design_focus"): "experiments.experiment_design_focus",
}

DEFAULT_V1_LAYERS: dict[str, str] = {
    "understanding": "project_overview",
    "literature": "literature_overview",
    "experiments": "evaluation_overview",
}

SCENE_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "nodeTypes", "edgeTypes"}
ENTITY_FORBIDDEN_FIELDS = {"canvas", "drill", "position", "display", "style", "className"}
VALID_CAPABILITIES = {"inspectable", "drillable", "portalable", "none"}
VALID_PROJECTED_INTERACTIONS = {"none", "inspect", "drill", "portal"}
VALID_PROJECTED_ROLES = {"anchor", "entity", "terminal", "portal"}


def normalize_workspace_layer(mode: str, layer: str = "") -> str:
    normalized_mode = str(mode or "understanding").strip()
    normalized_layer = str(layer or DEFAULT_V1_LAYERS.get(normalized_mode, "")).strip()
    if "." in normalized_layer:
        return normalized_layer
    try:
        return V1_TO_V2_LAYER[(normalized_mode, normalized_layer)]
    except KeyError as exc:
        raise ValueError(f"unknown workspace layer: {normalized_mode}/{normalized_layer}") from exc


def canonical_source_id(source_id: str) -> str:
    value = str(source_id or "").strip()
    if not value:
        raise ValueError("source_id must be non-empty")
    return value if value.startswith("source:") else f"source:{value}"


def canonical_understanding_id(project_id: str, node_type: str, local_id: str) -> str:
    value = str(local_id or "").strip()
    if not value:
        raise ValueError("understanding local id must be non-empty")
    return f"understanding:project:{project_id}:{node_type}:{value}"


def db_row_source(table: str, primary_key: str) -> dict[str, str]:
    return {"kind": "db_row", "table": table, "primary_key": primary_key}


def derived_source(rule: str, inputs: list[Any]) -> dict[str, Any]:
    return {"kind": "derived", "rule": rule, "inputs": inputs}


def validate_workspace_scene(scene: dict[str, Any]) -> dict[str, Any]:
    if scene.get("schema_version") != SCENE_SCHEMA_VERSION:
        raise ValueError("WorkspaceScene schema_version must be workspace-scene-v2")
    forbidden = SCENE_FORBIDDEN_FIELDS & set(scene)
    if forbidden:
        raise ValueError(f"WorkspaceScene must not contain UI field: {sorted(forbidden)[0]}")
    for key in ("project_id", "mode", "layer", "source", "entities", "relations", "groups", "portals", "inspector", "warnings"):
        if key not in scene:
            raise ValueError(f"WorkspaceScene missing required field: {key}")
    for entity in scene.get("entities", []):
        forbidden_entity = ENTITY_FORBIDDEN_FIELDS & set(entity)
        if forbidden_entity:
            raise ValueError(f"WorkspaceScene entity must not contain UI field: {sorted(forbidden_entity)[0]}")
        for key in ("canonical_id", "display_id", "entity_type", "title", "capabilities", "source"):
            if key not in entity:
                raise ValueError(f"WorkspaceScene entity missing required field: {key}")
        capabilities = set(entity.get("capabilities") or [])
        if not capabilities <= VALID_CAPABILITIES:
            raise ValueError("WorkspaceScene entity has invalid capability")
        source = entity.get("source") or {}
        if source.get("kind") not in {"db_row", "derived"}:
            raise ValueError("WorkspaceScene entity source.kind must be db_row or derived")
    for relation in scene.get("relations", []):
        for key in ("canonical_id", "relation_type", "source_id", "target_id", "source"):
            if key not in relation:
                raise ValueError(f"WorkspaceScene relation missing required field: {key}")
    for group in scene.get("groups", []):
        source = group.get("source") or {}
        if source.get("kind") != "derived":
            raise ValueError("WorkspaceScene groups must be derived")
    return scene


def validate_projected_graph(projected: dict[str, Any]) -> dict[str, Any]:
    if projected.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        raise ValueError("ProjectedGraph schema_version must be workspace-projection-v1")
    for key in ("project_id", "mode", "layer", "nodes", "edges", "frames", "portals", "layout", "warnings"):
        if key not in projected:
            raise ValueError(f"ProjectedGraph missing required field: {key}")
    for node in projected.get("nodes", []):
        role = node.get("role")
        if role not in VALID_PROJECTED_ROLES:
            raise ValueError("ProjectedGraph node has invalid role")
        interaction = node.get("interaction") or {}
        kind = interaction.get("kind")
        if kind not in VALID_PROJECTED_INTERACTIONS:
            raise ValueError("ProjectedGraph node has invalid interaction")
        if role == "terminal" and kind == "drill":
            raise ValueError("terminal projected nodes must not drill")
        for key in ("projected_id", "semantic_id", "visual_kind", "title", "display_id", "source"):
            if key not in node:
                raise ValueError(f"ProjectedGraph node missing required field: {key}")
    for edge in projected.get("edges", []):
        if edge.get("aggregation") and not edge.get("member_relation_ids"):
            raise ValueError("aggregated projected edges must retain member_relation_ids")
    return projected
```

- [ ] **Step 2: Run tests**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: PASS.

- [ ] **Step 3: Commit contract module**

```bash
git add tools/workspace_scene_contract.py tests/test_workspace_scene_contract.py
git commit -m "feat: add workspace scene contract helpers"
```

## Task 3: Understanding Scene Builder Tests

**Files:**
- Modify: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Add scene builder tests**

Append these imports:

```python
from pathlib import Path

from tools.workspace_scene_builders import build_workspace_scene
```

Add constants near the imports:

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT / "examples" / "workspaces"
PROJECT_ID = "DemoVisualAffordance"
```

Append these tests to `WorkspaceSceneContractTest`:

```python
    def test_understanding_project_overview_scene_has_semantic_entities_not_canvas(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
        )

        validate_workspace_scene(scene)
        self.assertEqual("workspace-scene-v2", scene["schema_version"])
        self.assertEqual("understanding.project_overview", scene["layer"])
        self.assertNotIn("canvas", scene)
        self.assertNotIn("breadcrumb", scene)
        entity_types = {entity["entity_type"] for entity in scene["entities"]}
        self.assertEqual({"question", "claim"}, entity_types)
        c2 = next(entity for entity in scene["entities"] if entity["display_id"] == "C2")
        self.assertEqual("understanding:project:DemoVisualAffordance:claim:C2", c2["canonical_id"])
        self.assertEqual({"inspectable", "drillable"}, set(c2["capabilities"]))
        self.assertEqual({"kind": "db_row", "table": "understanding_nodes", "primary_key": "project:DemoVisualAffordance:C2"}, c2["source"])

    def test_understanding_claim_focus_scene_keeps_argument_atoms_terminal_by_capability(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        validate_workspace_scene(scene)
        self.assertEqual("understanding.claim_focus", scene["layer"])
        self.assertEqual("understanding:project:DemoVisualAffordance:claim:C2", scene["focus_id"])
        entity_types = {entity["entity_type"] for entity in scene["entities"]}
        self.assertIn("claim", entity_types)
        self.assertIn("evidence", entity_types)
        self.assertIn("warrant", entity_types)
        self.assertIn("limitation", entity_types)
        self.assertIn("source", entity_types)
        atoms = [entity for entity in scene["entities"] if entity["entity_type"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(entity["capabilities"] == ["inspectable"] for entity in atoms))
        self.assertTrue(all("drill" not in entity for entity in atoms))

    def test_understanding_claim_focus_scene_groups_are_derived(self):
        scene = build_workspace_scene(
            WORKSPACE_ROOT,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        validate_workspace_scene(scene)
        group_types = {group["group_type"] for group in scene["groups"]}
        self.assertGreaterEqual(group_types, {"lane"})
        titles = {group["title"] for group in scene["groups"]}
        self.assertIn("Evidence / Grounds", titles)
        self.assertIn("Warrants / Bridges", titles)
        self.assertIn("Limitations / Boundaries", titles)
        self.assertTrue(all(group["source"]["kind"] == "derived" for group in scene["groups"]))
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.workspace_scene_builders'`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_workspace_scene_contract.py
git commit -m "test: define understanding workspace scene builder"
```

## Task 4: Understanding Scene Builders

**Files:**
- Create: `tools/workspace_scene_builders/__init__.py`
- Create: `tools/workspace_scene_builders/provenance.py`
- Create: `tools/workspace_scene_builders/understanding_scene.py`
- Test: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Add provenance helpers**

Create `tools/workspace_scene_builders/provenance.py`:

```python
#!/usr/bin/env python3
"""Workspace scene provenance helpers."""

from __future__ import annotations

from typing import Any

from tools.workspace_scene_contract import db_row_source, derived_source


def db_row(table: str, primary_key: str) -> dict[str, str]:
    return db_row_source(table, primary_key)


def derived(rule: str, inputs: list[Any]) -> dict[str, Any]:
    return derived_source(rule, inputs)
```

- [ ] **Step 2: Add scene builder dispatch**

Create `tools/workspace_scene_builders/__init__.py`:

```python
#!/usr/bin/env python3
"""Workspace scene builder dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.workspace_scene_contract import normalize_workspace_layer, validate_workspace_scene
from tools.workspace_scene_builders.understanding_scene import build_understanding_scene


def build_workspace_scene(
    root: Path,
    project_id: str,
    *,
    mode: str = "understanding",
    layer: str = "",
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    v2_layer = normalize_workspace_layer(mode, layer)
    if v2_layer.startswith("understanding."):
        scene = build_understanding_scene(root, project_id, v2_layer, focus_id=focus_id, selected_id=selected_id)
        return validate_workspace_scene(scene)
    raise ValueError(f"workspace-scene-v2 not implemented for layer: {v2_layer}")
```

- [ ] **Step 3: Implement Understanding scene builder**

Create `tools/workspace_scene_builders/understanding_scene.py`:

```python
#!/usr/bin/env python3
"""Understanding mode WorkspaceScene builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.research_dataset_read_models import build_project_graph_model, build_sources_model
from tools.workspace_scene_builders.provenance import db_row, derived
from tools.workspace_scene_contract import (
    DB_SOURCE,
    SCENE_SCHEMA_VERSION,
    canonical_source_id,
    canonical_understanding_id,
)


def build_understanding_scene(
    root: Path,
    project_id: str,
    layer: str,
    *,
    focus_id: str = "",
    selected_id: str = "",
) -> dict[str, Any]:
    graph = build_project_graph_model(root, project_id)
    if layer == "understanding.project_overview":
        return _project_overview_scene(project_id, graph, selected_id=selected_id)
    if layer == "understanding.claim_focus":
        return _claim_focus_scene(root, project_id, graph, focus_id=focus_id, selected_id=selected_id)
    raise ValueError(f"workspace-scene-v2 not implemented for layer: {layer}")


def _base_scene(project_id: str, layer: str, focus_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCENE_SCHEMA_VERSION,
        "project_id": project_id,
        "mode": "understanding",
        "layer": layer,
        "focus_id": focus_id,
        "source": DB_SOURCE,
        "entities": [],
        "relations": [],
        "groups": [],
        "portals": [],
        "inspector": {},
        "warnings": [],
    }


def _project_overview_scene(project_id: str, graph: dict[str, Any], *, selected_id: str = "") -> dict[str, Any]:
    scene = _base_scene(project_id, "understanding.project_overview")
    scene["entities"] = [
        _understanding_entity(project_id, node)
        for node in graph.get("nodes", [])
        if node.get("kind") in {"question", "claim"}
    ]
    visible_ids = {entity["canonical_id"] for entity in scene["entities"]}
    scene["relations"] = [
        relation
        for relation in _understanding_relations(project_id, graph)
        if relation["source_id"] in visible_ids and relation["target_id"] in visible_ids
    ]
    scene["groups"] = [
        _derived_group("understanding.project_overview", "questions", "Questions", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "question"]),
        _derived_group("understanding.project_overview", "claims", "Claims", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "claim"]),
    ]
    scene["inspector"] = {"kind": "overview", "subject_id": "", "title": "Questions"}
    return scene


def _claim_focus_scene(root: Path, project_id: str, graph: dict[str, Any], *, focus_id: str, selected_id: str = "") -> dict[str, Any]:
    claim = _node_by_graph_id(graph, focus_id)
    if not claim or claim.get("kind") != "claim":
        raise ValueError(f"unknown claim focus: {focus_id}")
    focus_canonical_id = _entity_id(project_id, claim)
    scene = _base_scene(project_id, "understanding.claim_focus", focus_canonical_id)
    related_nodes = _claim_related_nodes(graph, claim)
    source_entities = _source_entities_for_nodes(root, project_id, [claim, *related_nodes])
    scene["entities"] = [
        _understanding_entity(project_id, claim, force_capabilities=["inspectable"]),
        *[_understanding_entity(project_id, node, force_capabilities=["inspectable"]) for node in related_nodes if node.get("kind") in {"evidence", "warrant", "limitation"}],
        *source_entities,
    ]
    visible_ids = {entity["canonical_id"] for entity in scene["entities"]}
    scene["relations"] = [
        relation
        for relation in _understanding_relations(project_id, graph)
        if relation["source_id"] in visible_ids and relation["target_id"] in visible_ids
    ]
    scene["groups"] = [
        _derived_group("understanding.claim_focus", "evidence", "Evidence / Grounds", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "evidence"], focus_canonical_id),
        _derived_group("understanding.claim_focus", "warrants", "Warrants / Bridges", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "warrant"], focus_canonical_id),
        _derived_group("understanding.claim_focus", "limitations", "Limitations / Boundaries", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "limitation"], focus_canonical_id),
        _derived_group("understanding.claim_focus", "sources", "Source Papers", [entity["canonical_id"] for entity in scene["entities"] if entity["entity_type"] == "source"], focus_canonical_id),
    ]
    scene["inspector"] = {"kind": "claim_detail", "subject_id": focus_canonical_id, "title": _local_id(claim)}
    return scene


def _understanding_entity(project_id: str, node: dict[str, Any], force_capabilities: list[str] | None = None) -> dict[str, Any]:
    kind = str(node.get("kind") or "")
    local_id = _local_id(node)
    capabilities = force_capabilities or (["inspectable", "drillable"] if kind == "claim" else ["inspectable"])
    return {
        "canonical_id": canonical_understanding_id(project_id, kind, local_id),
        "display_id": local_id,
        "entity_type": kind,
        "title": node.get("label") or node.get("text") or local_id,
        "summary": "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "capabilities": capabilities,
        "source": db_row("understanding_nodes", str(node.get("id") or "")),
        "metadata": node.get("metadata") or {},
    }


def _source_entities_for_nodes(root: Path, project_id: str, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = build_sources_model(root, project_id).get("sources", [])
    by_key: dict[str, dict[str, Any]] = {}
    for source in sources:
        for key in (source.get("source_id"), source.get("locator"), source.get("title"), source.get("url"), source.get("doi"), source.get("arxiv_id")):
            if key:
                by_key[str(key)] = source
    result = []
    seen = set()
    for node in nodes:
        for ref in node.get("source_refs") or []:
            source = by_key.get(str(ref))
            if not source:
                continue
            source_id = str(source.get("source_id") or "")
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            result.append(
                {
                    "canonical_id": canonical_source_id(source_id),
                    "display_id": source_id,
                    "entity_type": "source",
                    "title": source.get("title") or source_id,
                    "summary": source.get("short_summary") or "",
                    "status": source.get("reading_status") or "",
                    "confidence": "",
                    "capabilities": ["inspectable", "drillable"],
                    "source": db_row("sources", source_id),
                    "metadata": source,
                }
            )
    return result


def _understanding_relations(project_id: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    relations = []
    for link in graph.get("links", []):
        relation_type = str(link.get("relation") or "related")
        targets = link.get("target") or []
        sources = link.get("premises") or link.get("source") or []
        for source_db_id in sources:
            for target_db_id in targets:
                source = by_db_id.get(source_db_id)
                target = by_db_id.get(target_db_id)
                if not source or not target:
                    continue
                relations.append(
                    {
                        "canonical_id": f"relation:project:{project_id}:{_local_id_from_value(link.get('id'))}:{_local_id(source)}:{_local_id(target)}",
                        "relation_type": relation_type,
                        "source_id": _entity_id(project_id, source),
                        "target_id": _entity_id(project_id, target),
                        "direction": "forward",
                        "weight": 1,
                        "source": db_row("understanding_links", str(link.get("id") or "")),
                    }
                )
    return relations


def _claim_related_nodes(graph: dict[str, Any], claim: dict[str, Any]) -> list[dict[str, Any]]:
    by_db_id = {node["id"]: node for node in graph.get("nodes", [])}
    claim_db_id = claim.get("id")
    related_ids: set[str] = set()
    for link in graph.get("links", []):
        targets = set(link.get("target") or [])
        sources = set(link.get("premises") or link.get("source") or [])
        warrants = set(link.get("warrant") or [])
        limitations = set(link.get("limitations") or [])
        if claim_db_id in targets:
            related_ids.update(sources | warrants | limitations)
        if claim_db_id in sources:
            related_ids.update(targets | warrants | limitations)
    return [by_db_id[node_id] for node_id in sorted(related_ids) if node_id in by_db_id and node_id != claim_db_id]


def _derived_group(layer: str, slug: str, title: str, member_ids: list[str], focus_id: str = "") -> dict[str, Any]:
    inputs = [focus_id] if focus_id else list(member_ids)
    return {
        "canonical_id": f"derived:group:{layer}:{slug}",
        "group_type": "lane",
        "title": title,
        "member_ids": member_ids,
        "visual_role": "frame",
        "source": derived(f"{title} members for {layer}", inputs),
    }


def _node_by_graph_id(graph: dict[str, Any], graph_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if f"{node.get('kind')}:{_local_id(node)}" == graph_id:
            return node
    return None


def _entity_id(project_id: str, node: dict[str, Any]) -> str:
    return canonical_understanding_id(project_id, str(node.get("kind") or ""), _local_id(node))


def _local_id(node: dict[str, Any]) -> str:
    metadata = node.get("metadata") or {}
    return str(node.get("local_id") or metadata.get("local_id") or _local_id_from_value(node.get("id")))


def _local_id_from_value(value: Any) -> str:
    return str(value or "").rsplit(":", 1)[-1]
```

- [ ] **Step 4: Run tests**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: PASS.

- [ ] **Step 5: Commit scene builders**

```bash
git add tools/workspace_scene_builders tests/test_workspace_scene_contract.py
git commit -m "feat: build understanding workspace scenes"
```

## Task 5: Projected Graph Tests

**Files:**
- Modify: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Add projection tests**

Append import:

```python
from tools.workspace_graph_projection import build_projected_graph
```

Append tests:

```python
    def test_projected_understanding_overview_has_frames_and_interactions(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="project_overview")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        self.assertEqual("workspace-projection-v1", projected["schema_version"])
        self.assertEqual("understanding.project_overview", projected["layer"])
        self.assertTrue(projected["frames"])
        c2 = next(node for node in projected["nodes"] if node["display_id"] == "C2")
        self.assertEqual("entity", c2["role"])
        self.assertEqual("drill", c2["interaction"]["kind"])
        self.assertEqual("understanding.claim_focus", c2["interaction"]["target"]["layer"])
        q1 = next(node for node in projected["nodes"] if node["display_id"] == "Q1")
        self.assertEqual("inspect", q1["interaction"]["kind"])

    def test_projected_claim_focus_argument_atoms_are_terminal_inspect_only(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        atoms = [node for node in projected["nodes"] if node["visual_kind"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(node["role"] == "terminal" for node in atoms))
        self.assertTrue(all(node["interaction"]["kind"] == "inspect" for node in atoms))
        self.assertFalse(any(node["interaction"]["kind"] == "drill" for node in atoms))

    def test_projected_edges_retain_relation_provenance(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)

        validate_projected_graph(projected)
        self.assertTrue(projected["edges"])
        self.assertTrue(all(edge["member_relation_ids"] for edge in projected["edges"]))
        self.assertTrue(all(edge["source"]["kind"] in {"db_row", "derived"} for edge in projected["edges"]))
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.workspace_graph_projection'`.

- [ ] **Step 3: Commit failing projection tests**

```bash
git add tests/test_workspace_scene_contract.py
git commit -m "test: define workspace graph projection contract"
```

## Task 6: Projection Module

**Files:**
- Create: `tools/workspace_graph_projection.py`
- Test: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Implement projected graph builder**

Create `tools/workspace_graph_projection.py`:

```python
#!/usr/bin/env python3
"""Project WorkspaceScene objects into render-ready graph contracts."""

from __future__ import annotations

from typing import Any

from tools.workspace_scene_contract import PROJECTION_SCHEMA_VERSION, validate_projected_graph


TERMINAL_ENTITY_TYPES = {"evidence", "warrant", "limitation", "run", "metric", "artifact"}


def build_projected_graph(scene: dict[str, Any]) -> dict[str, Any]:
    nodes = [_project_node(scene, entity) for entity in scene.get("entities", [])]
    semantic_to_projected = {node["semantic_id"]: node["projected_id"] for node in nodes}
    projected = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "project_id": scene["project_id"],
        "mode": scene["mode"],
        "layer": scene["layer"],
        "focus_id": scene.get("focus_id", ""),
        "breadcrumb": _breadcrumb(scene),
        "nodes": nodes,
        "edges": [_project_edge(relation, semantic_to_projected) for relation in scene.get("relations", [])],
        "frames": [_project_frame(group, semantic_to_projected) for group in scene.get("groups", [])],
        "portals": [_project_portal(portal, semantic_to_projected) for portal in scene.get("portals", [])],
        "inspector_default_id": scene.get("focus_id", ""),
        "layout": {"kind": "layered", "direction": "vertical"},
        "warnings": list(scene.get("warnings") or []),
    }
    return validate_projected_graph(projected)


def _project_node(scene: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
    role = _node_role(scene, entity)
    interaction = _interaction(scene, entity, role)
    return {
        "projected_id": f"node:{entity['canonical_id']}",
        "semantic_id": entity["canonical_id"],
        "role": role,
        "visual_kind": entity["entity_type"],
        "title": entity["title"],
        "display_id": entity["display_id"],
        "interaction": interaction,
        "source": entity["source"],
        "layout_hints": _layout_hints(scene, entity, role),
    }


def _node_role(scene: dict[str, Any], entity: dict[str, Any]) -> str:
    if scene.get("focus_id") and entity["canonical_id"] == scene.get("focus_id"):
        return "anchor"
    if entity["entity_type"] in TERMINAL_ENTITY_TYPES:
        return "terminal"
    return "entity"


def _interaction(scene: dict[str, Any], entity: dict[str, Any], role: str) -> dict[str, Any]:
    capabilities = set(entity.get("capabilities") or [])
    if role == "terminal":
        return {"kind": "inspect", "inspector_id": entity["canonical_id"]} if "inspectable" in capabilities else {"kind": "none"}
    if "drillable" in capabilities and entity["entity_type"] == "claim" and scene["layer"] == "understanding.project_overview":
        return {"kind": "drill", "target": {"mode": "understanding", "layer": "understanding.claim_focus", "focus_id": entity["canonical_id"]}}
    if "drillable" in capabilities and entity["entity_type"] == "source":
        return {"kind": "drill", "target": {"mode": "understanding", "layer": "understanding.paper_focus", "selected_id": entity["canonical_id"]}}
    if "inspectable" in capabilities:
        return {"kind": "inspect", "inspector_id": entity["canonical_id"]}
    return {"kind": "none"}


def _layout_hints(scene: dict[str, Any], entity: dict[str, Any], role: str) -> dict[str, Any]:
    lane = ""
    for group in scene.get("groups", []):
        if entity["canonical_id"] in group.get("member_ids", []):
            lane = str(group.get("title") or "")
            break
    return {"role": role, "lane": lane}


def _project_edge(relation: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    member_id = relation["canonical_id"]
    return {
        "projected_id": f"edge:{member_id}",
        "relation_type": relation["relation_type"],
        "source_id": semantic_to_projected.get(relation["source_id"], relation["source_id"]),
        "target_id": semantic_to_projected.get(relation["target_id"], relation["target_id"]),
        "label": relation["relation_type"],
        "member_relation_ids": [member_id],
        "aggregation": None,
        "source": relation["source"],
    }


def _project_frame(group: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    return {
        "projected_id": f"frame:{group['canonical_id']}",
        "semantic_id": group["canonical_id"],
        "frame_kind": group.get("group_type") or "frame",
        "title": group["title"],
        "member_node_ids": [semantic_to_projected[member_id] for member_id in group.get("member_ids", []) if member_id in semantic_to_projected],
        "interaction": {"kind": "none"},
        "source": group["source"],
    }


def _project_portal(portal: dict[str, Any], semantic_to_projected: dict[str, str]) -> dict[str, Any]:
    from_id = portal.get("from_id", "")
    return {
        "projected_id": portal["canonical_id"],
        "from_node_id": semantic_to_projected.get(from_id, from_id),
        "label": portal.get("title") or "",
        "target": portal.get("target") or {},
        "source": portal["source"],
    }


def _breadcrumb(scene: dict[str, Any]) -> list[dict[str, str]]:
    items = [{"label": "Workspace", "mode": scene["mode"], "layer": scene["layer"], "focus_id": ""}]
    if scene.get("focus_id"):
        items.append({"label": str(scene.get("focus_id")).rsplit(":", 1)[-1], "mode": scene["mode"], "layer": scene["layer"], "focus_id": scene["focus_id"]})
    return items
```

- [ ] **Step 2: Run tests**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: PASS.

- [ ] **Step 3: Commit projection module**

```bash
git add tools/workspace_graph_projection.py tests/test_workspace_scene_contract.py
git commit -m "feat: project workspace scenes into graph contract"
```

## Task 7: API Schema Routing Tests

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add API schema tests**

Append to `WorkspaceGraphReadModelsTest`:

```python
    def test_workspace_graph_handler_returns_scene_v2_when_requested(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview&schema=scene-v2",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-scene-v2", data["schema_version"])
        self.assertEqual("understanding.project_overview", data["layer"])
        self.assertIn("entities", data)
        self.assertNotIn("canvas", data)
        self.assertNotIn("drill", json.dumps(data))

    def test_workspace_graph_handler_returns_projection_v1_when_requested(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=claim_focus&focus_id=claim:C2&schema=projection-v1",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-projection-v1", data["schema_version"])
        self.assertEqual("understanding.claim_focus", data["layer"])
        self.assertIn("nodes", data)
        self.assertIn("frames", data)
        self.assertNotIn("canvas", data)
        atoms = [node for node in data["nodes"] if node["visual_kind"] in {"evidence", "warrant", "limitation"}]
        self.assertTrue(atoms)
        self.assertTrue(all(node["role"] == "terminal" for node in atoms))

    def test_workspace_graph_handler_default_remains_v1_for_frontend_compatibility(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-v1", data["schema_version"])
        self.assertIn("canvas", data)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_scene_v2_when_requested tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_projection_v1_when_requested tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_default_remains_v1_for_frontend_compatibility -v
```

Expected: FAIL because `schema` query parameter is ignored and API returns `workspace-graph-v1`.

- [ ] **Step 3: Commit failing API tests**

```bash
git add tests/test_workspace_graph_read_models.py
git commit -m "test: define workspace graph schema routing"
```

## Task 8: API Schema Routing Implementation

**Files:**
- Modify: `tools/research_browser_server.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Import v2 builders**

In `tools/research_browser_server.py`, add imports near the current workspace import:

```python
from tools.workspace_graph_projection import build_projected_graph
from tools.workspace_scene_builders import build_workspace_scene
```

- [ ] **Step 2: Route schema parameter in workspace handler**

Replace `handle_workspace_graph_request` body from `mode = ...` through `return json_response(model)` with:

```python
    mode = query.get("mode", ["understanding"])[0].strip() or "understanding"
    layer = query.get("layer", [""])[0].strip()
    focus_id = query.get("focus_id", [""])[0].strip()
    selected_id = query.get("selected_id", [""])[0].strip()
    schema = query.get("schema", ["workspace-graph-v1"])[0].strip() or "workspace-graph-v1"
    try:
        if schema == "scene-v2":
            model = build_workspace_scene(
                root.resolve(),
                project_id,
                mode=mode,
                layer=layer,
                focus_id=focus_id,
                selected_id=selected_id,
            )
            return json_response(model)
        if schema == "projection-v1":
            scene = build_workspace_scene(
                root.resolve(),
                project_id,
                mode=mode,
                layer=layer,
                focus_id=focus_id,
                selected_id=selected_id,
            )
            return json_response(build_projected_graph(scene))
        if schema != "workspace-graph-v1":
            raise ValueError(f"unknown workspace graph schema: {schema}")
        model = build_workspace_graph_model(
            root.resolve(),
            project_id,
            mode=mode,
            layer=layer,
            focus_id=focus_id,
            selected_id=selected_id,
        )
    except (ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
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

- [ ] **Step 3: Run API schema tests**

```bash
python3 -m unittest tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_scene_v2_when_requested tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_returns_projection_v1_when_requested tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_default_remains_v1_for_frontend_compatibility -v
```

Expected: PASS.

- [ ] **Step 4: Run full workspace graph tests**

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: PASS.

- [ ] **Step 5: Commit API routing**

```bash
git add tools/research_browser_server.py tests/test_workspace_graph_read_models.py
git commit -m "feat: expose workspace scene and projection schemas"
```

## Task 9: Boundary Regression Tests

**Files:**
- Modify: `tests/test_workspace_scene_contract.py`

- [ ] **Step 1: Add boundary tests for unsupported layers and source provenance**

Change the first import block from:

```python
import unittest
```

to:

```python
import json
import unittest
```

Append tests:

```python
    def test_scene_v2_rejects_unimplemented_non_understanding_layers_explicitly(self):
        with self.assertRaisesRegex(ValueError, "workspace-scene-v2 not implemented"):
            build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="experiments", layer="evaluation_overview")

    def test_scene_entities_all_have_db_or_derived_sources(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")

        for entity in scene["entities"]:
            self.assertIn(entity["source"]["kind"], {"db_row", "derived"})
            if entity["source"]["kind"] == "db_row":
                self.assertTrue(entity["source"].get("table"))
                self.assertTrue(entity["source"].get("primary_key"))

    def test_projection_does_not_emit_canvas_or_frontend_node_type_fields(self):
        scene = build_workspace_scene(WORKSPACE_ROOT, PROJECT_ID, mode="understanding", layer="claim_focus", focus_id="claim:C2")
        projected = build_projected_graph(scene)
        serialized = json.dumps(projected)

        self.assertNotIn('"canvas"', serialized)
        self.assertNotIn('"nodeTypes"', serialized)
        self.assertNotIn('"edgeTypes"', serialized)
        self.assertNotIn('"className"', serialized)
```

- [ ] **Step 2: Run scene tests**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: PASS.

- [ ] **Step 3: Commit boundary tests**

```bash
git add tests/test_workspace_scene_contract.py
git commit -m "test: lock workspace scene projection boundaries"
```

## Task 10: Full Verification

**Files:**
- No planned file changes.

- [ ] **Step 1: Run backend contract tests**

```bash
python3 -m unittest tests.test_workspace_scene_contract -v
```

Expected: PASS.

- [ ] **Step 2: Run workspace graph tests**

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: PASS.

- [ ] **Step 3: Run dataset read/write tests**

```bash
python3 -m unittest tests.test_research_dataset_schema tests.test_research_dataset_writer tests.test_research_dataset_read_models -v
```

Expected: PASS.

- [ ] **Step 4: Run dashboard source guard tests**

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

- [ ] **Step 5: Manual API smoke checks**

If dashboard server is running on `127.0.0.1:8765`, run:

```bash
curl -s "http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview&schema=scene-v2" | python3 -m json.tool | head -n 20
curl -s "http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=claim_focus&focus_id=claim:C2&schema=projection-v1" | python3 -m json.tool | head -n 20
curl -s "http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview" | python3 -m json.tool | head -n 20
```

Expected:

- First response contains `"schema_version": "workspace-scene-v2"` and no `"canvas"`.
- Second response contains `"schema_version": "workspace-projection-v1"` and `"frames"`.
- Third response contains `"schema_version": "workspace-graph-v1"` and `"canvas"`.

- [ ] **Step 6: Check working tree**

```bash
git status --short --branch
```

Expected: clean branch after all commits.

## Acceptance Criteria

- `/api/workspace-graph` default behavior remains `workspace-graph-v1`.
- `/api/workspace-graph?...&schema=scene-v2` returns `workspace-scene-v2`.
- `/api/workspace-graph?...&schema=projection-v1` returns `workspace-projection-v1`.
- Scene payloads contain semantic entities, relations, groups, portals, capabilities, and provenance.
- Scene payloads do not contain `canvas`, `drill`, `display`, `position`, React Flow node types, or CSS fields.
- Projection payloads contain node roles, interactions, frames, edges, portals, layout hints, and provenance.
- Terminal projected nodes never drill.
- Understanding `project_overview` and `claim_focus` are implemented in v2.
- Literature and Experiments v2 requests fail explicitly until implemented, instead of silently returning mixed v1 data.
- Existing frontend remains compatible because default API response is unchanged.

## Follow-Up Plan Boundary

This plan deliberately does not implement:

- `understanding.paper_focus` scene/projection.
- `literature.*` scene/projection.
- `experiments.*` scene/projection.
- frontend React Flow adapter refactor.
- DB schema migration.
- canonical source id data migration.

Those should be separate plans after this foundation lands.
