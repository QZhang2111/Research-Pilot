# Unified Research Island Dashboard Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the existing Workspace island so `research-pilot.db` remains source of truth, `/api/workspace-graph` becomes the only dashboard display contract, and the frontend cannot render arbitrary agent metadata as visible UI.

**Architecture:** Current repo already contains `tools/workspace_graph_read_models.py`, `/api/workspace-graph`, `dashboard/workspace.html`, and `dashboard/workspace-island`. This plan modifies those existing pieces. Backend read models normalize DB rows into stable canvas/inspector payloads with explicit `display` fields; frontend renders only `display`, never raw metadata.

**Tech Stack:** Python stdlib `unittest`, SQLite-backed read models, `tools/research_browser_server.py`, static dashboard HTML/CSS/JS, React 19, Vite, `@xyflow/react`.

---

## Current-State Assumptions

- `examples/workspaces/research-pilot.db` is the example workspace DB and contains `DemoVisualAffordance`.
- `tools/workspace_graph_read_models.py` already builds Understanding, Literature, and Experiments workspace graph payloads.
- `dashboard/workspace-island/src/WorkspaceIslandApp.jsx` currently renders at least one raw `node.metadata?.role` value. This must be removed.
- No `research-pilot.db` schema migration is in scope.
- No dashboard editing/mutation is in scope.
- Do not delete `DemoVisualAffordance`.
- Do not replace existing page-specific APIs during this slice.
- The older plan `docs/superpowers/plans/2026-05-26-unified-research-island-dashboard.md` describes initial scaffold work. Use this current-state hardening plan for the next implementation round.

## File Map

Modify:

- `tools/workspace_graph_read_models.py`
  Add display governance helpers, final payload normalization, controlled role/badge allowlist, and node contract consistency across all modes/layers.

- `tests/test_workspace_graph_read_models.py`
  Add tests for `display`, unknown metadata hiding, allowed legacy role mapping, all-layer node contract, empty-state/error behavior.

- `tools/research_browser_server.py`
  Keep `/api/workspace-graph` read-only. Adjust only if error payload or parameter validation does not match tests.

- `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
  Render `node.display.badges`, `node.display.tone`, and read-model inspector sections. Remove all visible raw `metadata` rendering.

- `dashboard/workspace-island/src/workspace-island.css`
  Add badge/tone styling and keep graph node text readable.

- `tests/test_related_work_lineage_dashboard.py`
  Add source guards for no raw `metadata.role`, display-only rendering, route compatibility, and build artifacts.

- `dashboard/app.js`
  Adjust only if Workspace mode/layer navigation or legacy route delegation fails tests.

- `dashboard/package.json` and built bundles
  Rebuild `workspace-island.bundle.js` and `workspace-island.bundle.css` after frontend changes.

Do not modify:

- `tools/research_dataset.py` schema.
- `examples/workspaces/research-pilot.db`, except during temporary test setup copies.
- `dashboard/project-graph/src/ProjectGraphApp.jsx`, unless a test proves the legacy project graph is still being used by Workspace.

## Task 1: Contract Tests For Source-Of-Truth And Display Governance

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add DB helper import**

In `tests/test_workspace_graph_read_models.py`, change the existing import:

```python
from tools.research_dataset import initialize_dataset
```

to:

```python
from tools.research_dataset import connect_dataset, initialize_dataset
```

- [ ] **Step 2: Add node contract assertion helper**

Inside `WorkspaceGraphReadModelsTest`, above `test_understanding_project_overview_contract`, add:

```python
    def assert_workspace_node_contract(self, node):
        self.assertIn("id", node)
        self.assertIn("entity_type", node)
        self.assertIn("label", node)
        self.assertIn("metadata", node)
        self.assertIn("display", node)
        self.assertIsInstance(node["metadata"], dict)
        self.assertIsInstance(node["display"], dict)
        self.assertIn("tone", node["display"])
        self.assertIn("badges", node["display"])
        self.assertIn("warnings", node["display"])
        self.assertIsInstance(node["display"]["badges"], list)
        self.assertIsInstance(node["display"]["warnings"], list)
```

- [ ] **Step 3: Add all-layer display contract test**

Append to `WorkspaceGraphReadModelsTest`:

```python
    def test_all_workspace_canvas_nodes_have_display_contract(self):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        setting_id = next(node["id"] for node in overview["canvas"]["nodes"] if "AGD20K" in node["label"])
        cases = [
            ("understanding", "project_overview", "", ""),
            ("understanding", "claim_focus", "claim:C2", ""),
            ("understanding", "paper_focus", "claim:C2", "source:paper:do2017-affordancenet"),
            ("literature", "literature_overview", "", ""),
            ("experiments", "evaluation_overview", "", ""),
            ("experiments", "evaluation_setting_focus", setting_id, ""),
            ("experiments", "experiment_design_focus", "experiment:EXP3", "run:RUN3"),
        ]

        for mode, layer, focus_id, selected_id in cases:
            with self.subTest(mode=mode, layer=layer):
                model = build_workspace_graph_model(
                    self.root,
                    PROJECT_ID,
                    mode=mode,
                    layer=layer,
                    focus_id=focus_id,
                    selected_id=selected_id,
                )
                self.assertTrue(model["canvas"]["nodes"])
                for node in model["canvas"]["nodes"]:
                    self.assert_workspace_node_contract(node)
```

- [ ] **Step 4: Add allowed legacy role mapping test**

Append:

```python
    def test_display_contract_maps_allowed_demo_roles(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        q1 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "Q1")
        c2 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "C2")
        q1_badges = {(badge["key"], badge["label"]) for badge in q1["display"]["badges"]}
        c2_badges = {(badge["key"], badge["label"]) for badge in c2["display"]["badges"]}

        self.assertIn(("question_role", "Framing"), q1_badges)
        self.assertIn(("claim_role", "Geometry Primitive"), c2_badges)
        self.assertEqual([], q1["display"]["warnings"])
```

- [ ] **Step 5: Add unknown metadata role blocking test**

Append:

```python
    def test_display_contract_blocks_unknown_metadata_role(self):
        with connect_dataset(self.root) as connection:
            connection.execute(
                """
                UPDATE understanding_nodes
                SET metadata_json = ?
                WHERE project_id = ? AND node_id = ?
                """,
                (
                    json.dumps({"demo": True, "local_id": "Q1", "role": "agent invented role"}),
                    PROJECT_ID,
                    "project:DemoVisualAffordance:Q1",
                ),
            )

        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")
        q1 = next(node for node in model["canvas"]["nodes"] if node.get("local_id") == "Q1")
        badge_labels = [badge["label"] for badge in q1["display"]["badges"]]

        self.assertEqual("agent invented role", q1["metadata"]["role"])
        self.assertNotIn("Agent Invented Role", badge_labels)
        self.assertIn("Unsupported metadata.role was not rendered.", q1["display"]["warnings"])
        self.assertTrue(any(item["node_id"] == "question:Q1" for item in model["warnings"]))
```

- [ ] **Step 6: Add frontend source guard**

Append to `tests/test_related_work_lineage_dashboard.py`:

```python
    def test_workspace_island_renders_display_not_raw_metadata(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function DisplayBadges", source)
        self.assertIn("node.display", source)
        self.assertIn("display?.badges", source)
        self.assertIn("display?.tone", source)
        self.assertNotIn("metadata?.role", source)
        self.assertNotIn("node.metadata.role", source)
```

- [ ] **Step 7: Run focused failing tests**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_all_workspace_canvas_nodes_have_display_contract \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_display_contract_maps_allowed_demo_roles \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_display_contract_blocks_unknown_metadata_role \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_renders_display_not_raw_metadata \
  -v
```

Expected before implementation: FAIL because backend nodes lack `display`, and frontend still contains `metadata?.role`.

- [ ] **Step 8: Commit tests**

```bash
git add tests/test_workspace_graph_read_models.py tests/test_related_work_lineage_dashboard.py
git commit -m "test: lock workspace display governance contract"
```

## Task 2: Backend Display Contract Normalization

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add display constants**

In `tools/workspace_graph_read_models.py`, below `VALID_LAYERS`, add:

```python
ENTITY_DISPLAY = {
    "question": {"tone": "question", "label": "Question"},
    "claim": {"tone": "claim", "label": "Claim"},
    "evidence": {"tone": "evidence", "label": "Evidence"},
    "warrant": {"tone": "warrant", "label": "Warrant"},
    "limitation": {"tone": "limitation", "label": "Limitation"},
    "source": {"tone": "source", "label": "Source"},
    "paper": {"tone": "source", "label": "Paper"},
    "literature_lane": {"tone": "source", "label": "Literature Lane"},
    "evaluation_setting": {"tone": "claim", "label": "Evaluation Setting"},
    "experiment": {"tone": "evidence", "label": "Experiment"},
    "run": {"tone": "run", "label": "Run"},
    "dataset": {"tone": "source", "label": "Dataset"},
    "benchmark": {"tone": "source", "label": "Benchmark"},
    "metric_family": {"tone": "warrant", "label": "Metric Family"},
    "model": {"tone": "warrant", "label": "Model"},
    "baseline": {"tone": "limitation", "label": "Baseline"},
    "protocol": {"tone": "warrant", "label": "Protocol"},
    "project_claim_anchor": {"tone": "claim", "label": "Project Claim"},
    "paper_question": {"tone": "question", "label": "Paper Question"},
    "paper_claim": {"tone": "claim", "label": "Paper Claim"},
    "paper_evidence": {"tone": "evidence", "label": "Paper Evidence"},
    "paper_warrant": {"tone": "warrant", "label": "Paper Warrant"},
    "paper_limitation": {"tone": "limitation", "label": "Paper Limitation"},
}

ROLE_BADGE_ALLOWLIST = {
    ("question", "framing"): {"key": "question_role", "label": "Framing", "tone": "question"},
    ("question", "primary"): {"key": "question_role", "label": "Primary", "tone": "question"},
    ("question", "validation"): {"key": "question_role", "label": "Validation", "tone": "question"},
    ("claim", "central thesis"): {"key": "claim_role", "label": "Central Thesis", "tone": "claim"},
    ("claim", "geometry primitive"): {"key": "claim_role", "label": "Geometry Primitive", "tone": "claim"},
    ("claim", "interaction primitive"): {"key": "claim_role", "label": "Interaction Primitive", "tone": "claim"},
    ("claim", "mechanistic bridge"): {"key": "claim_role", "label": "Mechanistic Bridge", "tone": "claim"},
}
```

- [ ] **Step 2: Add display helper functions**

Below `_json_loads`, add:

```python
def _display_for_entity(entity_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata if isinstance(metadata, dict) else {}
    entity = ENTITY_DISPLAY.get(entity_type, {"tone": "unknown", "label": entity_type or "Node"})
    badges = [{"key": "entity_type", "label": entity["label"], "tone": entity["tone"]}]
    warnings = []
    raw_role = str(metadata.get("role") or "").strip().lower()
    if raw_role:
        role_badge = ROLE_BADGE_ALLOWLIST.get((entity_type, raw_role))
        if role_badge:
            badges.append(dict(role_badge))
        else:
            warnings.append("Unsupported metadata.role was not rendered.")
    return {"tone": entity["tone"], "badges": badges, "warnings": warnings}


def _normalize_node_display(node: dict[str, Any]) -> dict[str, Any]:
    entity_type = str(node.get("entity_type") or "unknown")
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    node["metadata"] = metadata
    node["display"] = _display_for_entity(entity_type, metadata)
    return node


def _finalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    warnings = list(payload.get("warnings") or [])
    for node in payload.get("canvas", {}).get("nodes", []):
        _normalize_node_display(node)
        for warning in node["display"]["warnings"]:
            warnings.append({"node_id": node.get("id", ""), "message": warning})
    payload["warnings"] = warnings
    return payload
```

- [ ] **Step 3: Wrap top-level builder with finalizer**

Replace the return section in `build_workspace_graph_model`:

```python
    if mode == "understanding":
        return _build_understanding(root, project_id, layer, focus_id, selected_id)
    if mode == "literature":
        return _build_literature(root, project_id, layer, focus_id, selected_id)
    return _build_experiments(root, project_id, layer, focus_id, selected_id)
```

with:

```python
    if mode == "understanding":
        model = _build_understanding(root, project_id, layer, focus_id, selected_id)
    elif mode == "literature":
        model = _build_literature(root, project_id, layer, focus_id, selected_id)
    else:
        model = _build_experiments(root, project_id, layer, focus_id, selected_id)
    return _finalize_payload(model)
```

- [ ] **Step 4: Run backend display tests**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_all_workspace_canvas_nodes_have_display_contract \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_display_contract_maps_allowed_demo_roles \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_display_contract_blocks_unknown_metadata_role \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit backend display contract**

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "feat: normalize workspace graph display contract"
```

## Task 3: Backend Mode/Layer Contract Completion

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`
- Modify: `tools/workspace_graph_read_models.py`

- [ ] **Step 1: Add mode/layer structural tests**

Append:

```python
    def test_workspace_payload_has_no_dashboard_owned_storage_fields(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="understanding", layer="project_overview")

        self.assertEqual("research-pilot.db", model["source"])
        self.assertNotIn("dashboard_db", model)
        self.assertNotIn("dashboard_state", model)
        self.assertNotIn("mutation", model)

    def test_understanding_question_nodes_do_not_create_question_layer(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="project_overview",
            selected_id="question:Q2",
        )

        self.assertEqual("project_overview", model["layer"])
        self.assertEqual("question_detail", model["inspector"]["kind"])
        self.assertTrue(all(node.get("drill", {}).get("layer") != "question_focus" for node in model["canvas"]["nodes"] if node["entity_type"] == "question"))

    def test_experiment_run_is_terminal_inspector_selection(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="experiment_design_focus",
            focus_id="experiment:EXP3",
            selected_id="run:RUN3",
        )

        run = next(node for node in model["canvas"]["nodes"] if node["id"] == "run:RUN3")
        self.assertIsNone(run.get("drill"))
        self.assertEqual({"selected_id": "run:RUN3"}, run["inspector"])
        self.assertEqual("run_detail", model["inspector"]["kind"])
```

- [ ] **Step 2: Run structural tests**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_payload_has_no_dashboard_owned_storage_fields \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_question_nodes_do_not_create_question_layer \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_experiment_run_is_terminal_inspector_selection \
  -v
```

Expected: PASS if current mode/layer semantics already match PRD. If a test fails, change only `tools/workspace_graph_read_models.py`, not DB schema.

- [ ] **Step 3: Fix only failing layer semantics**

Use these exact rules:

```python
# question nodes stay in project_overview
if kind == "question":
    inspector = {"selected_id": graph_id}
    drill = None

# run nodes are terminal
if entity_type == "run":
    node["drill"] = None
    node["inspector"] = {"selected_id": node["id"]}
```

Do not add a `question_focus` or `run_detail` canvas layer.

- [ ] **Step 4: Run full workspace read-model tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit mode/layer contract**

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "test: lock workspace mode and layer semantics"
```

## Task 4: API Error And Empty-State Contract

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`
- Modify: `tools/research_browser_server.py`
- Modify: `tools/workspace_graph_read_models.py`

- [ ] **Step 1: Add API default and invalid mode tests**

Append:

```python
    def test_workspace_graph_handler_defaults_to_understanding(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance",
        )

        self.assertEqual(HTTPStatus.OK, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("understanding", data["mode"])
        self.assertEqual("project_overview", data["layer"])

    def test_workspace_graph_handler_rejects_invalid_mode(self):
        status, payload = handle_workspace_graph_request(
            self.root,
            "/api/workspace-graph?project=DemoVisualAffordance&mode=madeup",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        data = json.loads(payload.decode("utf-8"))
        self.assertEqual("workspace-graph-error-v1", data["schema_version"])
        self.assertIn("unknown workspace graph mode", data["message"])
```

- [ ] **Step 2: Add missing optional data empty-state test**

Append:

```python
    def test_literature_empty_data_returns_payload_not_crash(self):
        with connect_dataset(self.root) as connection:
            connection.execute("DELETE FROM literature_relations WHERE project_id = ?", (PROJECT_ID,))
            connection.execute("DELETE FROM literature_items WHERE project_id = ?", (PROJECT_ID,))
            connection.execute("DELETE FROM literature_lanes WHERE project_id = ?", (PROJECT_ID,))

        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="literature", layer="literature_overview")

        self.assertEqual("literature_overview", model["layer"])
        self.assertEqual([], model["canvas"]["nodes"])
        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertIsNotNone(model["empty_state"])
        self.assertIn("No literature structure", model["empty_state"]["message"])
```

- [ ] **Step 3: Implement empty-state if missing**

In `_build_literature`, after reading `routes` and `papers`, add before layer-specific logic:

```python
    if not routes and not papers:
        payload["empty_state"] = {
            "title": "No literature structure",
            "message": "No literature lanes or source lineage records exist for this project yet.",
        }
        payload["inspector"] = {
            "kind": "overview",
            "title": "Literature Routes",
            "summary": "No literature structure has been recorded.",
            "sections": [],
            "actions": [],
        }
        return payload
```

- [ ] **Step 4: Run API tests**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_defaults_to_understanding \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_workspace_graph_handler_rejects_invalid_mode \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_literature_empty_data_returns_payload_not_crash \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit API/empty-state contract**

```bash
git add tools/research_browser_server.py tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "feat: harden workspace graph API empty states"
```

## Task 5: Frontend Display-Only Rendering

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add display badge component**

In `WorkspaceIslandApp.jsx`, add above `WorkspaceKnowledgeNode`:

```jsx
function DisplayBadges({ display }) {
  const badges = Array.isArray(display?.badges) ? display.badges : [];
  if (!badges.length) return null;
  return (
    <span className="workspace-node-badges">
      {badges.map((badge) => (
        <small key={`${badge.key || "badge"}:${badge.label}`} data-tone={badge.tone || display?.tone || "unknown"}>
          {badge.label}
        </small>
      ))}
    </span>
  );
}
```

- [ ] **Step 2: Render display badges in knowledge nodes**

In `WorkspaceKnowledgeNode`, replace:

```jsx
      {node.metadata?.role ? <small>{node.metadata.role}</small> : null}
```

with:

```jsx
      <DisplayBadges display={node.display} />
```

- [ ] **Step 3: Render display badges in argument/source nodes**

In `WorkspaceArgumentAtomNode`, after the `<em>` line, add:

```jsx
      <DisplayBadges display={node.display} />
```

In `WorkspacePaperSourceNode`, after the `<em>` line, add:

```jsx
      <DisplayBadges display={node.display} />
```

- [ ] **Step 4: Prefer display tone for minimap color**

Change `entityTone` or `nodeColor` so `display.tone` wins:

```jsx
function displayTone(node) {
  return node?.data?.node?.display?.tone || node?.data?.display?.tone || entityTone(node?.data?.entity_type || node?.data?.node?.entity_type);
}

function nodeColor(node) {
  const tone = displayTone(node);
  return {
    question: "#8ec7ff",
    claim: "#d6a84f",
    evidence: "#70d6a3",
    warrant: "#bea0ff",
    limitation: "#e58b83",
    source: "#68c7d4",
    run: "#9bd7df",
  }[tone] || "#8f98a8";
}
```

- [ ] **Step 5: Add badge CSS**

Append to `workspace-island.css`:

```css
.workspace-node-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.workspace-node-badges small {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0 8px;
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}
```

- [ ] **Step 6: Run frontend source guard**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_renders_display_not_raw_metadata -v
```

Expected: PASS.

- [ ] **Step 7: Build workspace bundle**

Run:

```bash
cd dashboard && npm run build:workspace-island
```

Expected: Vite build PASS and updates `dashboard/workspace-island.bundle.js` plus `dashboard/workspace-island.bundle.css`.

- [ ] **Step 8: Commit frontend display rendering**

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_related_work_lineage_dashboard.py
git commit -m "feat: render workspace display contract only"
```

## Task 6: Workspace Navigation And Compatibility Guardrails

**Files:**
- Modify: `tests/test_related_work_lineage_dashboard.py`
- Modify: `dashboard/app.js`

- [ ] **Step 1: Add route guard test**

Append:

```python
    def test_workspace_navigation_stays_workspace_and_papers_only(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function workspaceUrl(projectId, mode = \"understanding\")", app)
        self.assertIn("function legacyWorkspaceModeForPage", app)
        self.assertIn('if (state.page === "lineage") return "literature";', app)
        self.assertIn('if (state.page === "experiments") return "experiments";', app)
        self.assertIn(">Workspace</a>", app)
        self.assertIn(">Papers</a>", app)
        self.assertNotIn(">Technical Lineage</a>", app)
        self.assertNotIn(">Experiments</a>", app)
```

- [ ] **Step 2: Add lazy-load guard test**

Append:

```python
    def test_workspace_loader_uses_one_mode_layer_request(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("async function loadWorkspaceGraphFromApi", app)
        self.assertIn("search.set(\"mode\", options.mode || \"understanding\")", app)
        self.assertIn("if (options.layer) search.set(\"layer\", options.layer)", app)
        self.assertIn("if (options.focus_id) search.set(\"focus_id\", options.focus_id)", app)
        self.assertIn("if (options.selected_id) search.set(\"selected_id\", options.selected_id)", app)
        self.assertNotIn("Promise.all([loadWorkspaceGraphFromApi", app)
```

- [ ] **Step 3: Run route tests**

Run:

```bash
python3 -m unittest \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_navigation_stays_workspace_and_papers_only \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_loader_uses_one_mode_layer_request \
  -v
```

Expected: PASS. If failing, modify only `dashboard/app.js` route/nav/loading code.

- [ ] **Step 4: Commit route guardrails if changed**

If `dashboard/app.js` changed:

```bash
git add dashboard/app.js tests/test_related_work_lineage_dashboard.py
git commit -m "test: lock workspace navigation guardrails"
```

If no source changed after tests:

```bash
git add tests/test_related_work_lineage_dashboard.py
git commit -m "test: lock workspace navigation guardrails"
```

## Task 7: Demo Visual Affordance Verification

**Files:**
- Modify only if verification exposes a bug from Tasks 1-6.

- [ ] **Step 1: Run backend API smoke against example workspace**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from tools.workspace_graph_read_models import build_workspace_graph_model

root = Path("examples/workspaces")
project = "DemoVisualAffordance"
cases = [
    ("understanding", "project_overview", "", ""),
    ("understanding", "claim_focus", "claim:C2", ""),
    ("understanding", "paper_focus", "claim:C2", "source:paper:do2017-affordancenet"),
    ("literature", "literature_overview", "", ""),
    ("experiments", "evaluation_overview", "", ""),
    ("experiments", "experiment_design_focus", "experiment:EXP3", "run:RUN3"),
]
for mode, layer, focus_id, selected_id in cases:
    model = build_workspace_graph_model(root, project, mode=mode, layer=layer, focus_id=focus_id, selected_id=selected_id)
    assert model["source"] == "research-pilot.db"
    assert model["canvas"]["nodes"], (mode, layer)
    assert all("display" in node for node in model["canvas"]["nodes"]), (mode, layer)
    print(json.dumps({"mode": mode, "layer": layer, "nodes": len(model["canvas"]["nodes"]), "warnings": len(model["warnings"])}))
PY
```

Expected: six JSON lines print. No assertion failure.

- [ ] **Step 2: Start local dashboard server**

Run:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --host 127.0.0.1 --port 8765
```

Expected: prints `Serving Research Browser at http://127.0.0.1:8765/`.

- [ ] **Step 3: In another shell, verify pages load**

Run:

```bash
curl -fsS "http://127.0.0.1:8765/dashboard/workspace.html?project=DemoVisualAffordance&mode=understanding" >/tmp/rp-workspace.html
curl -fsS "http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=understanding&layer=project_overview" >/tmp/rp-workspace-understanding.json
curl -fsS "http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=experiments&layer=evaluation_overview" >/tmp/rp-workspace-experiments.json
rg -n "workspace-island.bundle.js|Research Browser" /tmp/rp-workspace.html
rg -n '"display"|"project_overview"' /tmp/rp-workspace-understanding.json
rg -n '"evaluation_overview"|"evaluation_setting"' /tmp/rp-workspace-experiments.json
```

Expected: all commands exit 0.

- [ ] **Step 4: Stop dashboard server**

Stop the server with `Ctrl-C` in the server shell. Do not leave a running process.

- [ ] **Step 5: Commit verification fixes only if needed**

If source changed during verification:

```bash
git add tools/workspace_graph_read_models.py tools/research_browser_server.py dashboard/app.js dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_workspace_graph_read_models.py tests/test_related_work_lineage_dashboard.py
git commit -m "fix: verify demo workspace island contract"
```

If no source changed, do not create an empty commit.

## Task 8: Full Test And Release Check

**Files:**
- No source edits unless verification fails.

- [ ] **Step 1: Run workspace tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: PASS.

- [ ] **Step 2: Run dashboard source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

- [ ] **Step 3: Run full Python test suite**

Run:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS.

- [ ] **Step 4: Run dashboard build**

Run:

```bash
cd dashboard && npm run build:workspace-island
```

Expected: Vite build PASS.

- [ ] **Step 5: Run release check**

Run:

```bash
bash scripts/release_check.sh
```

Expected: PASS. If it fails because localhost binding is blocked by sandbox, rerun outside sandbox or with approved escalation.

- [ ] **Step 6: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intended source/test/bundle/doc files changed.

- [ ] **Step 7: Final commit**

If verification changes remain uncommitted:

```bash
git add tools/workspace_graph_read_models.py tools/research_browser_server.py dashboard/app.js dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_workspace_graph_read_models.py tests/test_related_work_lineage_dashboard.py docs/superpowers/specs/2026-05-26-unified-research-island-dashboard-prd.md docs/superpowers/plans/2026-05-27-unified-research-island-dashboard-contract-hardening.md
git commit -m "feat: harden workspace island display contract"
```

If commits already exist task-by-task, do not squash unless user asks.

## Plan Self-Review

Spec coverage:

- Workspace primary model: Tasks 3, 6, 7.
- Source of truth in `research-pilot.db`: Tasks 1, 2, 4.
- Read model as display contract: Tasks 1, 2.
- Frontend cannot render arbitrary metadata: Tasks 1, 5.
- Allowed legacy demo roles: Tasks 1, 2.
- Unknown metadata hidden with warnings: Tasks 1, 2.
- Understanding `Project Overview -> Claim Focus -> Paper Focus`: Tasks 3, 7.
- Literature as paper/source lineage: Tasks 3, 7.
- Experiments evaluation substrate: Tasks 3, 7.
- API defaults/errors/empty states: Task 4.
- Lazy mode/layer loading and route compatibility: Task 6.
- Demo Visual Affordance verification: Task 7.
- Full verification: Task 8.

Known implementation boundary:

- This plan does not add DB tables.
- This plan does not add dashboard editing.
- This plan does not redesign the graph visual layout beyond badges/tone rendering required by display governance.
- This plan preserves existing page-specific APIs while moving Workspace to `/api/workspace-graph`.
