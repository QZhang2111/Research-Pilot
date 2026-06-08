# Workspace Island Experiment Arena Three-Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Workspace Island literature route drill and experiment graph layers match the product semantics: whole literature route frames drill down; experiments use Arena -> Arena Detail -> Design Detail, with runs only in Design Detail.

**Architecture:** Keep the existing React Flow island and Python read-model API. Tighten the mapping contract so backend layers own semantic truth, while frontend renderers only choose layout and visual grouping. Avoid broad refactor; edit current files in place.

**Tech Stack:** Python `unittest`, vanilla dashboard JS, Vite React bundle, `@xyflow/react`, CSS.

---

## Current Problems

1. Literature overview uses a small route button inside a large route lane. User expects the whole route frame to hover and drill.
2. Experiment overview cards show too much text and overflow.
3. Arena Detail currently shows `dataset / benchmark / metric`, `experiment designs`, and `runs` together. This collapses two layers.
4. Design Detail exists in backend but frontend does not route to it.
5. Design Detail currently repeats `metric_family`; user expects `dataset / benchmark / metric` only in Arena Detail.

## Target Layer Contract

```text
Layer 1: evaluation_overview
  Nodes: evaluation_arena
  Drill: arena -> evaluation_arena_focus
  Inspector: all arenas

Layer 2: evaluation_arena_focus
  Nodes: dataset, benchmark, metric_family, experiment
  No run nodes
  Drill: experiment -> experiment_design_focus
  Inspector: arena detail, or selected terminal context/design summary

Layer 3: experiment_design_focus
  Nodes: experiment, model, baseline, protocol, ablation, run
  No dataset, benchmark, metric_family nodes
  Drill: none
  Inspector: experiment detail, or selected run detail
```

## Files

- Modify: `tools/workspace_graph_read_models.py`
  - Restore experiment drill from arena to design.
  - Remove runs from arena focus.
  - Remove metric-family support nodes from design focus.
  - Add ablation support nodes from metadata when present.
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
  - Replace small literature route node with full-frame clickable route node.
  - Render `experiment_design_focus`.
  - Split arena focus and design focus layouts.
  - Compress experiment overview cards.
- Modify: `dashboard/workspace-island/src/workspace-island.css`
  - Add route-frame hover/focus styles.
  - Fix arena card typography/overflow.
  - Add design focus stage styles for method and run columns.
- Modify: `tests/test_workspace_graph_read_models.py`
  - Add backend contract tests for three experiment layers.
- Modify: `tests/test_related_work_lineage_dashboard.py`
  - Add frontend source guardrails for route frames and three-layer experiments.
- Generated after build: `dashboard/workspace-island.bundle.js`
- Generated after build: `dashboard/workspace-island.bundle.css`

---

### Task 1: Backend Experiment Layer Contract Tests

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add failing tests for Arena Detail without runs and with design drill**

Add these tests near existing experiment workspace graph tests:

```python
    def test_experiments_arena_focus_contains_context_and_designs_but_no_runs(self):
        overview = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_overview",
        )
        arena_id = next(
            node["id"]
            for node in overview["canvas"]["nodes"]
            if node["entity_type"] == "evaluation_arena"
        )

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_arena_focus",
            focus_id=arena_id,
        )

        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertIn("dataset", entity_types)
        self.assertIn("benchmark", entity_types)
        self.assertIn("metric_family", entity_types)
        self.assertIn("experiment", entity_types)
        self.assertNotIn("run", entity_types)
        experiment_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "experiment"]
        self.assertTrue(experiment_nodes)
        self.assertTrue(
            all(node.get("drill", {}).get("layer") == "experiment_design_focus" for node in experiment_nodes)
        )
        inspector_sections = {section["title"] for section in model["inspector"]["sections"]}
        self.assertIn("Datasets", inspector_sections)
        self.assertIn("Benchmarks / Tasks", inspector_sections)
        self.assertIn("Metric Families", inspector_sections)
        self.assertIn("Experiment Designs", inspector_sections)
        self.assertNotIn("Runs / Results", inspector_sections)
```

- [ ] **Step 2: Add failing test for Design Detail with runs but no arena context**

Add:

```python
    def test_experiments_design_focus_contains_method_plan_and_runs_only(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="experiment_design_focus",
            focus_id="experiment:EXP1",
        )

        self.assertEqual("experiment_design_focus", model["layer"])
        self.assertEqual("experiment_detail", model["inspector"]["kind"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertIn("experiment", entity_types)
        self.assertIn("run", entity_types)
        self.assertTrue({"model", "baseline", "protocol"} & entity_types)
        self.assertNotIn("dataset", entity_types)
        self.assertNotIn("benchmark", entity_types)
        self.assertNotIn("metric_family", entity_types)
        run_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "run"]
        self.assertTrue(run_nodes)
        self.assertTrue(all(not node.get("drill") for node in run_nodes))
        self.assertTrue(all(node.get("inspector") == {"selected_id": node["id"]} for node in run_nodes))
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: failure because arena focus still includes run nodes and experiment nodes do not drill.

- [ ] **Step 4: Commit tests**

```bash
git add tests/test_workspace_graph_read_models.py
git commit -m "test: lock experiment graph layer contract"
```

---

### Task 2: Backend Experiment Read Model Fix

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Restore experiment drill in arena focus**

In `_build_experiments`, inside `if layer == "evaluation_arena_focus":`, change experiment node construction:

```python
                    "drill": {"mode": "experiments", "layer": "experiment_design_focus", "focus_id": graph_id},
                    "inspector": {"selected_id": graph_id},
```

- [ ] **Step 2: Remove run nodes from arena focus canvas**

In the same block, delete `run_nodes = []`, the loop that appends run nodes, and run edge generation.

Set nodes:

```python
        payload["canvas"]["nodes"] = [arena_node, *context_nodes, *experiment_nodes]
```

Set edges to context -> arena and arena -> experiment only:

```python
        payload["canvas"]["edges"] = [
            *[
                {
                    "id": f"arena-context:{focus_id}:{node['id']}",
                    "source": node["id"],
                    "target": focus_id,
                    "relation": "defines",
                    "label": "defines",
                    "metadata": {},
                }
                for node in context_nodes
            ],
            *[
                {
                    "id": f"arena-exp:{focus_id}:{node['id']}",
                    "source": focus_id,
                    "target": node["id"],
                    "relation": "uses",
                    "label": "uses",
                    "metadata": {},
                }
                for node in experiment_nodes
            ],
        ]
```

- [ ] **Step 3: Remove Runs / Results from arena inspector**

In arena default inspector, remove:

```python
                    {"title": "Runs / Results", "kind": "run_list", "items": run_nodes},
```

Keep:

```python
                    {"title": "Experiment Designs", "kind": "experiment_list", "items": experiment_nodes},
```

- [ ] **Step 4: Keep selected experiment inspector valid**

Replace current owned-runs lookup in arena focus selected experiment branch with actual runs:

```python
            owned_runs = [
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
                for run in runs_by_experiment.get(experiment_id, [])
            ]
```

- [ ] **Step 5: Remove metric_family from design focus support nodes**

In `if layer == "experiment_design_focus":`, change support node loop from:

```python
        for kind, values in [
            ("model", _metadata_list(experiment, "models")),
            ("baseline", _metadata_list(experiment, "baselines")),
            ("protocol", experiment.get("protocol") or _metadata_list(experiment, "protocol")),
            ("metric_family", _metadata_list(experiment, "metrics")),
        ]:
```

to:

```python
        for kind, values in [
            ("model", _metadata_list(experiment, "models")),
            ("baseline", _metadata_list(experiment, "baselines")),
            ("protocol", experiment.get("protocol") or _metadata_list(experiment, "protocol")),
            ("ablation", _metadata_list(experiment, "ablations")),
        ]:
```

- [ ] **Step 6: Run backend tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: pass.

- [ ] **Step 7: Commit backend fix**

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "fix: separate experiment arena and design layers"
```

---

### Task 3: Frontend Source Guardrail Tests

**Files:**
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Update literature route test expectations**

In `test_workspace_island_has_literature_route_timeline_layout`, replace route-node assertions:

```python
        self.assertIn("workspaceRouteFrameNode", source)
        self.assertNotIn("workspaceLiteratureRouteNode", source)
        self.assertIn(".workspace-route-frame-node", styles)
        self.assertNotIn(".workspace-literature-route-node", styles)
```

Keep:

```python
        self.assertIn("function buildLiteratureRouteFocusFlowModel", source)
        self.assertIn("workspaceTimelinePaperNode", source)
```

- [ ] **Step 2: Update experiments renderer guardrails**

In `test_workspace_island_has_experiments_specific_layout`, replace design-focus negative assertions with positive assertions:

```python
        self.assertIn("function buildExperimentsDesignFocusFlowModel", source)
        self.assertIn('model?.layer === "experiment_design_focus"', source)
        self.assertIn("workspaceExperimentArenaNode", source)
        self.assertIn("workspaceExperimentEntityNode", source)
        self.assertIn("workspaceRunResultNode", source)
        self.assertIn("Evaluation Context", source)
        self.assertIn("Design Method", source)
        self.assertIn("Runs / Results", source)
```

- [ ] **Step 3: Add guardrail against runs in arena layout**

Add:

```python
    def test_workspace_island_arena_focus_does_not_render_runs_column(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        arena_focus = source.split("function buildExperimentsArenaFocusFlowModel", 1)[1].split(
            "function buildExperimentsDesignFocusFlowModel", 1
        )[0]
        self.assertNotIn('entity_type === "run"', arena_focus)
        self.assertNotIn('title: "Runs / Results"', arena_focus)
```

- [ ] **Step 4: Run frontend source tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: failure because frontend still has `WorkspaceLiteratureRouteNode`, no design-focus renderer, and arena focus still renders runs.

- [ ] **Step 5: Commit tests**

```bash
git add tests/test_related_work_lineage_dashboard.py
git commit -m "test: lock workspace island layer presentation"
```

---

### Task 4: Literature Route Frame Interaction

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Replace small route node component with full route frame node**

In `WorkspaceIslandApp.jsx`, delete `WorkspaceLiteratureRouteNode`. Add:

```jsx
const WorkspaceRouteFrameNode = memo(function WorkspaceRouteFrameNode({ data }) {
  const node = data.node || {};
  return (
    <button
      type="button"
      className={`workspace-route-frame-node tone-${data.tone || "x"}`}
      onClick={() => data.onNodeAction?.(node)}
    >
      <strong>{data.title || shortLabel(node.label || node.local_id || "Route", 84)}</strong>
      {data.subtitle ? <span>{data.subtitle}</span> : null}
    </button>
  );
});
```

Update `workspaceNodeTypes`:

```jsx
  workspaceRouteFrameNode: WorkspaceRouteFrameNode,
```

Remove:

```jsx
  workspaceLiteratureRouteNode: WorkspaceLiteratureRouteNode,
```

- [ ] **Step 2: Use route frame as the whole interactive lane**

In `buildLiteratureOverviewFlowModel`, replace the `frame:${route.id}` node type and data:

```jsx
      type: "workspaceRouteFrameNode",
      data: {
        node: route,
        title: route.label || route.local_id || "Route",
        subtitle: `${routePapers.length} papers`,
        tone,
        onNodeAction: (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      },
```

Delete the `route-node:${route.id}` push block completely.

Keep paper nodes with higher `zIndex: 3` so paper clicks still drill to paper focus.

- [ ] **Step 3: Add route frame CSS**

In `workspace-island.css`, replace `.workspace-literature-route-node` rules with:

```css
.workspace-route-frame-node {
  width: 100%;
  height: 100%;
  border: 1px solid color-mix(in srgb, var(--node-tone, #68c7d4) 44%, transparent);
  border-radius: 8px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone, #68c7d4) 12%, transparent), transparent 45%),
    color-mix(in srgb, var(--workspace-panel-bg) 86%, transparent);
  color: var(--workspace-text);
  text-align: left;
  padding: 18px 20px;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--node-tone, #68c7d4) 10%, transparent);
}

.workspace-route-frame-node strong,
.workspace-route-frame-node span {
  display: block;
  max-width: 220px;
  pointer-events: none;
}

.workspace-route-frame-node strong {
  color: var(--node-tone, #68c7d4);
  font: 800 12px/1.2 var(--workspace-mono);
  text-transform: uppercase;
}

.workspace-route-frame-node span {
  margin-top: 12px;
  color: var(--workspace-muted);
  font: 700 12px/1.2 var(--workspace-mono);
}

.workspace-route-frame-node:hover,
.workspace-route-frame-node:focus-visible {
  border-color: var(--node-tone, #68c7d4);
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone, #68c7d4) 20%, transparent), transparent 48%),
    color-mix(in srgb, var(--workspace-panel-bg) 92%, transparent);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--node-tone, #68c7d4) 44%, transparent),
    0 20px 48px color-mix(in srgb, var(--node-tone, #68c7d4) 14%, transparent);
}
```

Keep tone classes by changing selector prefix:

```css
.workspace-route-frame-node.tone-route-0 { --node-tone: #68c7d4; }
.workspace-route-frame-node.tone-route-1 { --node-tone: #9dc66b; }
.workspace-route-frame-node.tone-route-2 { --node-tone: #d6a84f; }
.workspace-route-frame-node.tone-route-3 { --node-tone: #bea0ff; }
.workspace-route-frame-node.tone-route-4 { --node-tone: #e58b83; }
.workspace-route-frame-node.tone-route-5 { --node-tone: #8ec7ff; }
```

- [ ] **Step 4: Run source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: literature assertions pass; experiment assertions still fail until next tasks.

- [ ] **Step 5: Commit literature frontend fix**

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css tests/test_related_work_lineage_dashboard.py
git commit -m "fix: make literature route frames drillable"
```

---

### Task 5: Frontend Experiment Three-Layer Layout

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Compress arena overview card**

In `WorkspaceExperimentArenaNode`, simplify content:

```jsx
  const content = (
    <>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>{shortLabel(node.label || "Evaluation Arena", 56)}</strong>
      <span>{shortLabel(metadata.metric_families?.join(" / ") || node.subtitle || "", 48)}</span>
      <small>{counts}</small>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </>
  );
```

No summary paragraph in card. Summary belongs to inspector.

- [ ] **Step 2: Make arena overview cards smaller**

In `buildExperimentsArenaOverviewFlowModel`:

```jsx
  const cardWidth = 360;
  const cardHeight = 118;
  const gapX = 76;
  const gapY = 54;
```

Set style:

```jsx
    style: { width: cardWidth, minHeight: cardHeight },
```

- [ ] **Step 3: Remove run rendering from arena focus layout**

In `buildExperimentsArenaFocusFlowModel`, remove:

```jsx
  const runNodes = rawNodes.filter((node) => node.entity_type === "run");
```

Remove the `frame:arena-runs` node.

Remove `runNodes.forEach(...)`.

Use only two frames:

```jsx
    {
      id: "frame:arena-context",
      type: "workspaceLaneFrameNode",
      position: { x: 36, y: -44 },
      style: { width: 470, height: Math.max(330, contextNodes.length * 104 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Evaluation Context", subtitle: "dataset, benchmark, metric", tone: "p" },
    },
    {
      id: "frame:arena-designs",
      type: "workspaceLaneFrameNode",
      position: { x: 590, y: -44 },
      style: { width: 560, height: Math.max(330, experimentNodes.length * 126 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Experiment Designs", subtitle: `${experimentNodes.length} designs`, tone: "e" },
    },
```

- [ ] **Step 4: Place context and design nodes**

In arena focus:

```jsx
  contextNodes.forEach((node, index) => {
    nodes.push(
      toExperimentEntityNode(node, index, model, focusedIds, onNavigate, {
        position: { x: 76, y: 28 + index * 104 },
        width: 390,
        minHeight: 88,
        tone: entityTone(node.entity_type),
      }),
    );
  });
  experimentNodes.forEach((node, index) => {
    nodes.push(
      toExperimentEntityNode(node, index, model, focusedIds, onNavigate, {
        position: { x: 630, y: 28 + index * 126 },
        width: 470,
        minHeight: 100,
        tone: "e",
      }),
    );
  });
```

- [ ] **Step 5: Restore experiment design focus renderer**

Add:

```jsx
function buildExperimentsDesignFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const experiment = rawNodes.find((node) => node.entity_type === "experiment");
  const methodNodes = rawNodes.filter((node) => ["model", "baseline", "protocol", "ablation"].includes(node.entity_type));
  const runNodes = rawNodes.filter((node) => node.entity_type === "run");
  const focusedIds = focusedNodeIds(model);
  const nodes = [
    {
      id: "frame:design-method",
      type: "workspaceLaneFrameNode",
      position: { x: 500, y: -48 },
      style: { width: 430, height: Math.max(330, methodNodes.length * 104 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Design Method", subtitle: "models, baselines, protocol", tone: "p" },
    },
    {
      id: "frame:design-runs",
      type: "workspaceLaneFrameNode",
      position: { x: 980, y: -48 },
      style: { width: 430, height: Math.max(330, runNodes.length * 112 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Runs / Results", subtitle: `${runNodes.length} runs`, tone: "r" },
    },
  ];
  if (experiment) {
    nodes.push(
      toExperimentEntityNode(experiment, 0, model, focusedIds, onNavigate, {
        position: { x: 40, y: 72 },
        width: 400,
        minHeight: 112,
        tone: "e",
      }),
    );
  }
  methodNodes.forEach((node, index) => {
    nodes.push(
      toExperimentEntityNode(node, index, model, focusedIds, onNavigate, {
        position: { x: 540, y: 24 + index * 104 },
        width: 350,
        minHeight: 88,
        tone: entityTone(node.entity_type),
      }),
    );
  });
  runNodes.forEach((node, index) => {
    nodes.push({
      id: node.id,
      type: "workspaceRunResultNode",
      position: { x: 1020, y: 24 + index * 112 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 350, minHeight: 94 },
      zIndex: 4,
      data: { node, tone: "r", onNodeAction: experimentsNodeAction(onNavigate) },
    });
  });
  const visibleIds = new Set(rawNodes.map((node) => node.id));
  return {
    nodes,
    edges: rawEdges
      .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
      .map((edge) => toExperimentEdge(edge)),
  };
}
```

- [ ] **Step 6: Route frontend layer to design focus**

In `buildExperimentsFlowModel`:

```jsx
  if (model?.layer === "experiment_design_focus") return buildExperimentsDesignFocusFlowModel(model, onNavigate);
```

Keep this after arena focus branch.

- [ ] **Step 7: Fix experiment card CSS overflow**

In `workspace-island.css`, update:

```css
.workspace-experiment-arena-node,
.workspace-run-result-node {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-content: start;
  overflow: hidden;
}

.workspace-experiment-arena-node strong,
.workspace-run-result-node strong {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-experiment-arena-node span,
.workspace-experiment-arena-node em,
.workspace-experiment-arena-node small,
.workspace-run-result-node span,
.workspace-run-result-node em,
.workspace-run-result-node small {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

- [ ] **Step 8: Run frontend source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: pass.

- [ ] **Step 9: Commit frontend experiments fix**

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css tests/test_related_work_lineage_dashboard.py
git commit -m "fix: render experiments as arena design run layers"
```

---

### Task 6: Build Bundle And Regression Tests

**Files:**
- Modify generated: `dashboard/workspace-island.bundle.js`
- Modify generated: `dashboard/workspace-island.bundle.css`

- [ ] **Step 1: Build workspace island bundle**

Run:

```bash
npm --prefix dashboard run build:workspace-island
```

Expected:

```text
✓ built
```

- [ ] **Step 2: Run focused regression suite**

Run:

```bash
python3 -m unittest tests.test_research_dataset_read_models tests.test_workspace_graph_read_models tests.test_workspace_scene_contract tests.test_related_work_lineage_dashboard -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Run diff whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Commit generated bundle**

```bash
git add dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css
git commit -m "build: refresh workspace island bundle"
```

---

### Task 7: Manual Browser Smoke

**Files:**
- No source edits expected.

- [ ] **Step 1: Start local dashboard server**

Run:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --host 127.0.0.1 --port 8770
```

Expected: server listens on `http://127.0.0.1:8770`.

- [ ] **Step 2: Open workspace page**

Open:

```text
http://127.0.0.1:8770/dashboard/workspace.html?project=DemoVisualAffordance&mode=experiments&v=english-dashboard-20260603a
```

- [ ] **Step 3: Verify literature behavior**

Switch to Literature:

Expected:
- Whole route frame hover changes border/glow.
- Clicking empty area inside route frame enters `Workspace / Literature / <Route>`.
- Clicking paper card enters shared paper focus.
- No small extra route button exists.

- [ ] **Step 4: Verify experiment behavior**

Switch to Experiments:

Expected:
- Layer 1 shows compact arena cards.
- Clicking arena enters Arena Detail.
- Arena Detail shows `Evaluation Context` and `Experiment Designs`.
- Arena Detail does not show run cards.
- Clicking experiment design enters Design Detail.
- Design Detail shows `Design Method` and `Runs / Results`.
- Design Detail does not show dataset/benchmark/metric cards.
- Clicking run updates inspector only; breadcrumb remains on design layer.

- [ ] **Step 5: Record smoke result in final task report**

Report pass/fail for each browser expectation. Do not edit source during this step.

---

## Done Criteria

- Literature route drill uses whole route frame, not small button.
- Experiment layers match:
  - `evaluation_overview`: arenas only.
  - `evaluation_arena_focus`: context + designs, no runs.
  - `experiment_design_focus`: method + runs, no arena context.
- Run nodes terminal: no drill, inspector-only.
- `npm --prefix dashboard run build:workspace-island` passes.
- Focused Python regression suite passes.
- Browser smoke matches expected behavior.
