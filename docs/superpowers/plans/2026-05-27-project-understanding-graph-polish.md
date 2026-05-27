# Project Understanding Graph Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also use `react-flow` before editing `dashboard/workspace-island/src/WorkspaceIslandApp.jsx` or React Flow CSS.

**Goal:** Make the Unified Workspace Island's Project Understanding graph read like a structured research argument map instead of a generic graph.

**Architecture:** Keep `/api/workspace-graph` and the unified workspace shell. Tighten the Understanding read model so claim focus exposes only one claim on the canvas and treats evidence, warrants, and limitations as terminal argument material. Add an Understanding-specific React Flow projection with lane frames for overview and claim focus, while Literature and Experiments continue using the shared generic renderer.

**Tech Stack:** Python unittest, Research Pilot read models, React, `@xyflow/react`, Vite, CSS.

---

## Current Problems

- Top-level mode breadcrumbs imply `Literature` and `Experiments` are child layers of `Workspace`; they are sibling modes.
- Inspector content can stretch the island row, which makes the React Flow canvas height unstable.
- Understanding overview does not communicate two distinct regions: project questions and project claims.
- Claim focus includes unrelated/supporting claims on the canvas, plus dimmed nodes and edges whose meaning is unclear.
- Evidence, warrant, and limitation nodes behave like selectable layers because the frontend falls back to `selected_id` navigation.

## Files

- Modify: `tests/test_workspace_graph_read_models.py`
  - Add backend contract tests for claim-focus canvas scope and terminal E/W/L nodes.
- Modify: `tests/test_related_work_lineage_dashboard.py`
  - Add source-level guards for breadcrumb semantics, fixed viewport CSS, Understanding-specific renderer, lane frame node, and terminal node click behavior.
- Modify: `tools/workspace_graph_read_models.py`
  - Stop adding generic inspector targets to terminal Understanding nodes.
  - Keep supporting claims in the inspector, but remove non-focused claim nodes from claim-focus canvas.
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
  - Add terminal-aware node action handling.
  - Fix breadcrumb semantics.
  - Add Understanding-specific React Flow nodes and layout helpers.
  - Keep shared renderer for Literature and Experiments.
- Modify: `dashboard/workspace-island/src/workspace-island.css`
  - Add fixed island viewport rules.
  - Add lane frame styling and typed Understanding node styling.
- Regenerate: `dashboard/workspace-island.bundle.js`
- Regenerate: `dashboard/workspace-island.bundle.css`

Do not modify:

- `dashboard/project-graph/**`
- `dashboard/lineage-atlas/**`
- Literature data projection in `tools/workspace_graph_read_models.py`
- Experiment data projection beyond tests proving it remains unaffected

---

### Task 1: Add Backend Contract Tests For Claim-Focus Scope

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add failing test for single-claim canvas**

Insert after `test_understanding_claim_focus_contract`:

```python
    def test_understanding_claim_focus_canvas_contains_only_focused_claim(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        claim_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "claim"]
        self.assertEqual(["claim:C2"], [node["id"] for node in claim_nodes])

        supporting_claims = next(
            section for section in model["inspector"]["sections"] if section["kind"] == "claim"
        )
        self.assertTrue(any(item["id"] == "claim:C0" for item in supporting_claims["items"]))
```

- [ ] **Step 2: Add failing test for terminal E/W/L nodes**

Insert after the new single-claim test:

```python
    def test_understanding_claim_focus_argument_atoms_are_terminal(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="understanding",
            layer="claim_focus",
            focus_id="claim:C2",
        )

        terminal_nodes = [
            node for node in model["canvas"]["nodes"]
            if node["entity_type"] in {"evidence", "warrant", "limitation"}
        ]
        self.assertTrue(terminal_nodes)
        self.assertTrue(all(not node.get("drill") for node in terminal_nodes))
        self.assertTrue(all(not node.get("inspector") for node in terminal_nodes))
```

- [ ] **Step 3: Run targeted tests to verify failure**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_claim_focus_canvas_contains_only_focused_claim \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_claim_focus_argument_atoms_are_terminal \
  -v
```

Expected: FAIL. Current claim-focus canvas includes `claim:C0`, and `_understanding_node` gives every project node an `inspector` fallback.

- [ ] **Step 4: Commit red tests**

Run:

```bash
git add tests/test_workspace_graph_read_models.py
git commit -m "test: define understanding claim focus canvas contract"
```

---

### Task 2: Tighten Understanding Read Model Semantics

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Make `_understanding_node` terminal-aware**

Replace the tail of `_understanding_node` with this structure:

```python
    inspector = {"selected_id": graph_id} if kind == "question" else None
    result = {
        "id": graph_id,
        "entity_type": kind,
        "db_id": node.get("id", ""),
        "local_id": local_id,
        "label": node.get("label") or node.get("text") or local_id,
        "subtitle": node.get("subtitle") or node.get("status") or "",
        "status": node.get("status") or "",
        "confidence": node.get("confidence") or "",
        "drill": drill,
        "selected": graph_id == selected_id,
        "metadata": node.get("metadata") or {},
    }
    if inspector:
        result["inspector"] = inspector
    return result
```

Keep the existing `drill` logic above it:

```python
    drill = None
    if kind == "claim":
        drill = {"mode": "understanding", "layer": "claim_focus", "focus_id": graph_id}
```

- [ ] **Step 2: Filter claim-focus canvas nodes**

In `_build_understanding`, inside `if layer == "claim_focus":`, replace the `payload["canvas"]["nodes"] = [...]` assignment with:

```python
        canvas_related_nodes = [node for node in related_nodes if node.get("kind") != "claim"]
        payload["canvas"]["nodes"] = [
            _understanding_node(claim, selected_id=claim_id),
            *[_understanding_node(node, selected_id=selected_id) for node in canvas_related_nodes],
            *source_nodes,
        ]
```

Do not change `_claim_detail`; supporting claims must remain in the inspector.

- [ ] **Step 3: Keep only edges whose endpoints remain on canvas**

Keep the current edge filter after `related_ids`:

```python
        related_ids = {node["id"] for node in payload["canvas"]["nodes"]}
        payload["canvas"]["edges"] = [edge for edge in _understanding_edges(graph) if edge["source"] in related_ids and edge["target"] in related_ids]
```

This removes `claim:C2 -> claim:C0` from the canvas because `claim:C0` is no longer a canvas node.

- [ ] **Step 4: Run backend tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: PASS.

- [ ] **Step 5: Commit read model fix**

Run:

```bash
git add tools/workspace_graph_read_models.py tests/test_workspace_graph_read_models.py
git commit -m "fix: scope understanding claim focus canvas"
```

---

### Task 3: Add Frontend Source Guards For Breadcrumb, Viewport, And Understanding Renderer

**Files:**
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add breadcrumb semantics guard**

Insert after `test_workspace_island_synthesizes_current_breadcrumb_layer`:

```python
    def test_workspace_island_breadcrumb_treats_modes_as_siblings(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function isTopLevelWorkspaceLayer", source)
        self.assertIn('layer === "project_overview"', source)
        self.assertIn('layer === "literature_overview"', source)
        self.assertIn('layer === "evaluation_overview"', source)
        self.assertIn("if (isTopLevelWorkspaceLayer(layer) && !focus_id) return null", source)
```

- [ ] **Step 2: Add terminal click guard**

Insert after the breadcrumb semantics guard:

```python
    def test_workspace_island_terminal_argument_nodes_do_not_navigate(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function nodeNavigationTarget", source)
        self.assertIn("if (!target) return", source)
        self.assertNotIn("item.drill || item.inspector || { selected_id: item.id }", source)
```

- [ ] **Step 3: Add Understanding renderer guard**

Insert after the terminal click guard:

```python
    def test_workspace_island_has_understanding_specific_layout(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function WorkspaceLaneFrameNode", source)
        self.assertIn("function buildUnderstandingFlowModel", source)
        self.assertIn("function buildUnderstandingOverviewFlowModel", source)
        self.assertIn("function buildUnderstandingClaimFocusFlowModel", source)
        self.assertIn("workspaceLaneFrameNode", source)
        self.assertIn("workspaceArgumentAtomNode", source)
        self.assertIn("workspacePaperSourceNode", source)
        self.assertIn("model?.mode === \"understanding\"", source)
```

- [ ] **Step 4: Add fixed viewport CSS guard**

Append these assertions to `test_workspace_island_visual_style_guardrails`:

```python
        self.assertIn("height: calc(100vh - 215px)", css)
        self.assertIn("min-height: 0", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn(".workspace-lane-frame", css)
        self.assertIn(".workspace-argument-atom", css)
        self.assertIn(".workspace-paper-source-node", css)
```

- [ ] **Step 5: Run targeted tests to verify failure**

Run:

```bash
python3 -m unittest \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_breadcrumb_treats_modes_as_siblings \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_terminal_argument_nodes_do_not_navigate \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_has_understanding_specific_layout \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_visual_style_guardrails \
  -v
```

Expected: FAIL because the new frontend contract is not implemented yet.

- [ ] **Step 6: Commit red frontend guards**

Run:

```bash
git add tests/test_related_work_lineage_dashboard.py
git commit -m "test: define understanding graph polish contract"
```

---

### Task 4: Fix Breadcrumb Semantics And Terminal Navigation

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add top-level layer helper**

Add before `breadcrumbLabelForTarget`:

```jsx
function isTopLevelWorkspaceLayer(layer) {
  return (
    layer === "project_overview" ||
    layer === "literature_overview" ||
    layer === "evaluation_overview"
  );
}
```

- [ ] **Step 2: Update `currentBreadcrumbTarget`**

Replace `currentBreadcrumbTarget` with:

```jsx
function currentBreadcrumbTarget(model) {
  const layer = model?.layer || "";
  const focus_id = model?.focus_id || "";
  const selected_id = model?.selected_id || "";
  if (!layer && !focus_id && !selected_id) return null;
  if (isTopLevelWorkspaceLayer(layer) && !focus_id) return null;
  if (!focus_id && selected_id) return null;
  const target = {
    label: "",
    mode: model?.mode || "understanding",
    layer,
    focus_id,
    selected_id: model?.selected_id || "",
  };
  target.label = breadcrumbLabelForTarget(target);
  return target;
}
```

This makes top-level `Understanding`, `Literature`, and `Experiments` all display `Workspace` only.

- [ ] **Step 3: Add terminal-aware navigation target helper**

Add before `WorkspaceGraphRenderer`:

```jsx
function nodeNavigationTarget(node) {
  if (node?.drill) return node.drill;
  if (node?.inspector) return node.inspector;
  return null;
}
```

- [ ] **Step 4: Use `nodeNavigationTarget` in shared renderer**

In `WorkspaceGraphRenderer`, replace the `toFlowNode` callback argument:

```jsx
        toFlowNode(node, index, model, focusedIds, (item) => onNavigate?.(item.drill || item.inspector || { selected_id: item.id })),
```

with:

```jsx
        toFlowNode(node, index, model, focusedIds, (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        }),
```

- [ ] **Step 5: Render terminal generic cards as non-buttons**

Replace `WorkspaceKnowledgeNode` return block with:

```jsx
  const content = (
    <>
      <Handle type="target" position={Position.Top} className="workspace-node-handle" />
      <span>{localId}</span>
      <strong>{shortLabel(node.label, 150)}</strong>
      <em>{node.subtitle || node.status || node.entity_type || ""}</em>
      {node.metadata?.role ? <small>{node.metadata.role}</small> : null}
      <Handle type="source" position={Position.Bottom} className="workspace-node-handle" />
    </>
  );
  if (!canDrill && !node.inspector) {
    return <article className={className}>{content}</article>;
  }
  return (
    <button type="button" className={className} onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
```

- [ ] **Step 6: Run frontend source tests**

Run:

```bash
python3 -m unittest \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_breadcrumb_treats_modes_as_siblings \
  tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_terminal_argument_nodes_do_not_navigate \
  -v
```

Expected: PASS.

- [ ] **Step 7: Commit breadcrumb and navigation fix**

Run:

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx tests/test_related_work_lineage_dashboard.py
git commit -m "fix: clarify workspace breadcrumb and terminal nodes"
```

---

### Task 5: Add Understanding-Specific React Flow Projection

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add lane frame node**

Add after `WorkspaceKnowledgeNode`:

```jsx
const WorkspaceLaneFrameNode = memo(function WorkspaceLaneFrameNode({ data }) {
  return (
    <section className={`workspace-lane-frame tone-${data.tone || "x"}`}>
      <strong>{data.title}</strong>
      {data.subtitle ? <span>{data.subtitle}</span> : null}
    </section>
  );
});
```

- [ ] **Step 2: Add terminal argument atom node**

Add after `WorkspaceLaneFrameNode`:

```jsx
const WorkspaceArgumentAtomNode = memo(function WorkspaceArgumentAtomNode({ data }) {
  const node = data.node || {};
  return (
    <article className={`workspace-argument-atom tone-${data.tone || "x"}`}>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
      <span>{node.local_id || node.subtitle || node.entity_type}</span>
      <strong>{shortLabel(node.label, 128)}</strong>
      <em>{node.subtitle || node.entity_type}</em>
    </article>
  );
});
```

- [ ] **Step 3: Add paper source node**

Add after `WorkspaceArgumentAtomNode`:

```jsx
const WorkspacePaperSourceNode = memo(function WorkspacePaperSourceNode({ data }) {
  const node = data.node || {};
  return (
    <button type="button" className="workspace-paper-source-node" onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <span>{node.local_id || node.source_id || "paper"}</span>
      <strong>{shortLabel(node.label, 96)}</strong>
      <em>{node.subtitle || "paper/source"}</em>
    </button>
  );
});
```

- [ ] **Step 4: Register node types**

Replace `workspaceNodeTypes` with:

```jsx
const workspaceNodeTypes = {
  workspaceKnowledgeNode: WorkspaceKnowledgeNode,
  workspaceLaneFrameNode: WorkspaceLaneFrameNode,
  workspaceArgumentAtomNode: WorkspaceArgumentAtomNode,
  workspacePaperSourceNode: WorkspacePaperSourceNode,
};
```

- [ ] **Step 5: Add Understanding overview flow builder**

Add before `WorkspaceGraphRenderer`:

```jsx
function buildUnderstandingOverviewFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const questions = rawNodes.filter((node) => node.entity_type === "question");
  const claims = rawNodes.filter((node) => node.entity_type === "claim");
  const questionWidth = 300;
  const claimWidth = 360;
  const gap = 36;
  const questionFrameWidth = Math.max(questions.length * (questionWidth + gap) + 70, 720);
  const claimFrameWidth = Math.max(claims.length * (claimWidth + gap) + 70, 980);
  const focusedIds = focusedNodeIds(model);

  const nodes = [
    {
      id: "frame:questions",
      type: "workspaceLaneFrameNode",
      position: { x: -40, y: -250 },
      style: { width: questionFrameWidth, height: 220 },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Questions", subtitle: `${questions.length} project questions`, tone: "q" },
    },
    {
      id: "frame:claims",
      type: "workspaceLaneFrameNode",
      position: { x: -40, y: 20 },
      style: { width: claimFrameWidth, height: 260 },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Claims", subtitle: `${claims.length} project claims`, tone: "c" },
    },
    ...questions.map((node, index) =>
      toFlowNode(
        { ...node, position: { x: index * (questionWidth + gap), y: -180 } },
        index,
        model,
        focusedIds,
        (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      ),
    ),
    ...claims.map((node, index) =>
      toFlowNode(
        { ...node, position: { x: index * (claimWidth + gap), y: 90 } },
        index,
        model,
        focusedIds,
        (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        },
      ),
    ),
  ];

  const visibleIds = new Set(rawNodes.map((node) => node.id));
  const edgeFocusIds = focusedIds.size ? focusedIds : visibleIds;
  const edges = rawEdges
    .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
    .map((edge) => toFlowEdge(edge, model, edgeFocusIds));

  return { nodes, edges };
}
```

- [ ] **Step 6: Add Claim focus flow builder**

Add after `buildUnderstandingOverviewFlowModel`:

```jsx
function buildUnderstandingClaimFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const focusId = model?.focus_id || rawNodes.find((node) => node.entity_type === "claim")?.id || "";
  const claim = rawNodes.find((node) => node.id === focusId) || rawNodes.find((node) => node.entity_type === "claim");
  if (!claim) return { nodes: [], edges: [] };

  const laneConfig = [
    { key: "evidence", title: "Evidence / Grounds", tone: "e", x: 720, y: 20, relation: "supports" },
    { key: "warrant", title: "Warrants / Bridges", tone: "w", x: 720, y: 310, relation: "qualifies" },
    { key: "limitation", title: "Limitations / Boundaries", tone: "l", x: 1120, y: 165, relation: "bounds" },
    { key: "source", title: "Source Papers", tone: "p", x: 1540, y: 20, relation: "cites" },
  ];

  const nodes = [
    {
      ...toFlowNode(
        { ...claim, position: { x: 160, y: 190 } },
        0,
        model,
        new Set([claim.id]),
        () => {},
      ),
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 420, minHeight: 160 },
      zIndex: 4,
    },
  ];
  const edges = [];

  laneConfig.forEach((lane) => {
    const items = rawNodes.filter((node) => node.entity_type === lane.key);
    const frameHeight = Math.max(190, items.length * 130 + 92);
    nodes.push({
      id: `frame:${lane.key}`,
      type: "workspaceLaneFrameNode",
      position: { x: lane.x - 28, y: lane.y - 52 },
      style: { width: lane.key === "source" ? 340 : 360, height: frameHeight },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: lane.title, subtitle: `${items.length} records`, tone: lane.tone },
    });
    items.forEach((node, index) => {
      const nodeId = node.id;
      if (lane.key === "source") {
        nodes.push({
          id: nodeId,
          type: "workspacePaperSourceNode",
          position: { x: lane.x, y: lane.y + index * 126 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: { width: 286, minHeight: 96 },
          zIndex: 3,
          data: {
            node,
            tone: lane.tone,
            onNodeAction: (item) => {
              const target = nodeNavigationTarget(item);
              if (!target) return;
              onNavigate?.(target);
            },
          },
        });
        edges.push({
          id: `claim-focus:${claim.id}:${nodeId}`,
          source: claim.id,
          target: nodeId,
          relation: lane.relation,
          label: lane.relation,
        });
        return;
      }
      nodes.push({
        id: nodeId,
        type: "workspaceArgumentAtomNode",
        position: { x: lane.x, y: lane.y + index * 126 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: { width: 310, minHeight: 104 },
        zIndex: 3,
        data: { node, tone: lane.tone },
      });
      edges.push({
        id: `claim-focus:${nodeId}:${claim.id}`,
        source: nodeId,
        target: claim.id,
        relation: lane.relation,
        label: lane.relation,
      });
    });
  });

  return {
    nodes,
    edges: edges.map((edge) => toFlowEdge(edge, model, new Set([edge.source, edge.target, claim.id]))),
  };
}
```

- [ ] **Step 7: Add Understanding dispatcher**

Add after `buildUnderstandingClaimFocusFlowModel`:

```jsx
function buildUnderstandingFlowModel(model, onNavigate) {
  if (model?.layer === "claim_focus") {
    return buildUnderstandingClaimFocusFlowModel(model, onNavigate);
  }
  return buildUnderstandingOverviewFlowModel(model, onNavigate);
}
```

- [ ] **Step 8: Route Understanding renderer to dedicated builder**

Replace `UnderstandingGraphRenderer` with:

```jsx
function UnderstandingGraphRenderer({ model, onNavigate }) {
  const { nodes, edges } = useMemo(() => buildUnderstandingFlowModel(model, onNavigate), [model, onNavigate]);
  return (
    <WorkspaceGraphRenderer
      model={model}
      onNavigate={onNavigate}
      modeClass="is-understanding"
      providedNodes={nodes}
      providedEdges={edges}
    />
  );
}
```

Update `WorkspaceGraphRenderer` signature:

```jsx
function WorkspaceGraphRenderer({ model, onNavigate, modeClass, providedNodes = null, providedEdges = null }) {
```

Update its `nodes` and `edges` memo blocks:

```jsx
  const nodes = useMemo(
    () =>
      providedNodes ||
      (model?.canvas?.nodes || []).map((node, index) =>
        toFlowNode(node, index, model, focusedIds, (item) => {
          const target = nodeNavigationTarget(item);
          if (!target) return;
          onNavigate?.(target);
        }),
      ),
    [model, focusedIds, onNavigate, providedNodes],
  );
  const edges = useMemo(
    () => providedEdges || (model?.canvas?.edges || []).map((edge) => toFlowEdge(edge, model, focusedIds)),
    [model, focusedIds, providedEdges],
  );
```

- [ ] **Step 9: Run source guard**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_has_understanding_specific_layout -v
```

Expected: PASS.

- [ ] **Step 10: Commit renderer split**

Run:

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx tests/test_related_work_lineage_dashboard.py
git commit -m "feat: add understanding graph lane projection"
```

---

### Task 6: Style Lane Frames, Terminal Atoms, And Fixed Viewport

**Files:**
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Stabilize shell height**

Replace the top shell/body/canvas rules with:

```css
.workspace-island-shell {
  height: calc(100vh - 150px);
  min-height: 620px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-1);
  overflow: hidden;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.workspace-island-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 390px);
  min-height: 0;
  height: 100%;
}

.workspace-knowledge-canvas {
  --workspace-grid-color: rgba(255, 255, 255, 0.038);
  --workspace-minimap-mask: rgba(8, 10, 13, 0.72);
  position: relative;
  min-height: 0;
  height: calc(100vh - 215px);
  overflow: hidden;
  background:
    radial-gradient(circle at 46% 30%, rgba(214, 168, 79, 0.08), transparent 34%),
    radial-gradient(circle at 78% 62%, rgba(104, 199, 212, 0.045), transparent 26%),
    linear-gradient(180deg, rgba(17, 21, 29, 0.74), rgba(8, 10, 13, 0.84));
}
```

- [ ] **Step 2: Make inspector independently scroll**

Replace `.workspace-inspector` with:

```css
.workspace-inspector {
  min-height: 0;
  height: 100%;
  border-left: 1px solid var(--border);
  padding: 18px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--surface-1);
}
```

- [ ] **Step 3: Add lane frame styles**

Add before `.workspace-node-card`:

```css
.react-flow__node-workspaceLaneFrameNode {
  pointer-events: none;
  z-index: -1 !important;
}

.workspace-lane-frame {
  --node-tone: #8f98a8;
  width: 100%;
  height: 100%;
  border: 1px solid color-mix(in srgb, var(--node-tone) 34%, transparent);
  border-radius: 12px;
  padding: 14px 16px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone) 8%, transparent), transparent 42%),
    rgba(8, 10, 13, 0.22);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.workspace-lane-frame.tone-q { --node-tone: #8ec7ff; }
.workspace-lane-frame.tone-c { --node-tone: #d6a84f; }
.workspace-lane-frame.tone-e { --node-tone: #70d6a3; }
.workspace-lane-frame.tone-w { --node-tone: #bea0ff; }
.workspace-lane-frame.tone-l { --node-tone: #e58b83; }
.workspace-lane-frame.tone-p { --node-tone: #68c7d4; }

.workspace-lane-frame strong {
  display: block;
  color: color-mix(in srgb, var(--node-tone) 78%, var(--text-main));
  font: 900 12px/1 var(--mono);
  text-transform: uppercase;
}

.workspace-lane-frame span {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font: 800 11px/1.2 var(--mono);
}
```

- [ ] **Step 4: Add argument atom and paper source styles**

Add after `.workspace-node-card` styles:

```css
.workspace-argument-atom,
.workspace-paper-source-node {
  --node-tone: #8f98a8;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 7px 10px;
  align-content: start;
  width: 100%;
  height: 100%;
  border: 1px solid color-mix(in srgb, var(--node-tone) 42%, var(--border));
  border-radius: 8px;
  padding: 12px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone) 16%, transparent), transparent 5px),
    linear-gradient(180deg, rgba(13, 18, 25, 0.94), rgba(7, 10, 14, 0.93));
  color: var(--text-main);
  text-align: left;
}

.workspace-argument-atom.tone-e { --node-tone: #70d6a3; }
.workspace-argument-atom.tone-w { --node-tone: #bea0ff; }
.workspace-argument-atom.tone-l { --node-tone: #e58b83; }

.workspace-paper-source-node {
  --node-tone: #68c7d4;
  border-style: dashed;
  cursor: pointer;
}

.workspace-argument-atom span,
.workspace-paper-source-node span {
  display: inline-grid;
  place-items: center;
  width: 36px;
  min-width: 36px;
  height: 26px;
  border: 1px solid color-mix(in srgb, var(--node-tone) 48%, transparent);
  border-radius: 6px;
  color: var(--node-tone);
  font: 900 10px/1 var(--mono);
}

.workspace-argument-atom strong,
.workspace-paper-source-node strong {
  min-width: 0;
  color: var(--text-main);
  font-size: 12px;
  line-height: 1.24;
}

.workspace-argument-atom em,
.workspace-paper-source-node em {
  grid-column: 2;
  color: var(--text-dim);
  font: 800 10px/1.2 var(--mono);
  font-style: normal;
  text-transform: uppercase;
}

.workspace-paper-source-node:hover,
.workspace-paper-source-node:focus-visible {
  border-color: color-mix(in srgb, var(--node-tone) 72%, var(--border));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--node-tone) 16%, transparent), 0 18px 38px rgba(0, 0, 0, 0.24);
  outline: none;
  transform: translateY(-1px);
}
```

- [ ] **Step 5: Add React Flow node reset selectors**

Add after `.react-flow__node-workspaceKnowledgeNode`:

```css
.react-flow__node-workspaceArgumentAtomNode,
.react-flow__node-workspacePaperSourceNode {
  border: 0;
  padding: 0;
  background: transparent;
}
```

- [ ] **Step 6: Run CSS source guard**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_visual_style_guardrails -v
```

Expected: PASS.

- [ ] **Step 7: Commit CSS polish**

Run:

```bash
git add dashboard/workspace-island/src/workspace-island.css tests/test_related_work_lineage_dashboard.py
git commit -m "style: polish understanding graph lanes"
```

---

### Task 7: Build Bundle And Verify Regressions

**Files:**
- Regenerate: `dashboard/workspace-island.bundle.js`
- Regenerate: `dashboard/workspace-island.bundle.css`

- [ ] **Step 1: Run backend read-model tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: PASS.

- [ ] **Step 2: Run dashboard source guards**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

- [ ] **Step 3: Build workspace island bundle**

Run:

```bash
cd dashboard && npm run build:workspace-island
```

Expected: PASS and update:

```text
dashboard/workspace-island.bundle.js
dashboard/workspace-island.bundle.css
```

- [ ] **Step 4: Smoke API responses**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from tools.workspace_graph_read_models import build_workspace_graph_model

root = Path("examples/workspaces")
project = "DemoVisualAffordance"
cases = [
    ("understanding", "project_overview", "", ""),
    ("understanding", "claim_focus", "claim:C2", ""),
    ("literature", "literature_overview", "", ""),
    ("experiments", "evaluation_overview", "", ""),
]
for mode, layer, focus_id, selected_id in cases:
    model = build_workspace_graph_model(root, project, mode=mode, layer=layer, focus_id=focus_id, selected_id=selected_id)
    print(mode, layer, len(model["canvas"]["nodes"]), len(model["canvas"]["edges"]), model["inspector"]["kind"])
PY
```

Expected output includes four lines and no exception:

```text
understanding project_overview
understanding claim_focus
literature literature_overview
experiments evaluation_overview
```

- [ ] **Step 5: Commit regenerated bundle**

Run:

```bash
git add dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css
git commit -m "build: refresh workspace island graph bundle"
```

---

### Task 8: Browser Verification

**Files:**
- No source changes unless verification reveals a defect.

- [ ] **Step 1: Start or reuse dashboard server**

Run if no server is listening on port 8765:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --port 8765
```

Expected: server listens on `http://127.0.0.1:8765`.

- [ ] **Step 2: Open Understanding overview**

Open:

```text
http://127.0.0.1:8765/dashboard/workspace.html?project=DemoVisualAffordance&mode=understanding&v=english-dashboard-20260523
```

Expected:

- Breadcrumb shows `Workspace`, not `Workspace / project overview`.
- Canvas height stays fixed when inspector content grows.
- Questions sit inside a blue `Questions` lane frame.
- Claims sit inside a gold `Claims` lane frame.
- Only question and claim nodes appear.

- [ ] **Step 3: Click claim `C2`**

Expected:

- Breadcrumb shows `Workspace / C2`.
- Canvas shows one claim node for `C2`.
- Evidence, warrants, limitations, and source papers are separated into colored lane frames.
- No non-focused claim node appears on the canvas.
- Evidence, warrant, and limitation cards are not clickable buttons.
- Source paper cards remain clickable into paper focus.

- [ ] **Step 4: Switch Literature and Experiments**

Expected:

- Breadcrumb returns to `Workspace` at each top-level mode.
- Existing Literature and Experiments graphs still render.
- Right inspector scrolls independently from the canvas.

- [ ] **Step 5: Commit verification-only fixes if needed**

If browser verification exposes a defect, fix the smallest scoped issue, rerun Tasks 7.1-7.3, and commit:

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx dashboard/workspace-island/src/workspace-island.css dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css tests/test_related_work_lineage_dashboard.py tests/test_workspace_graph_read_models.py
git commit -m "fix: verify understanding graph polish"
```

If no defect appears, do not create a commit.

---

## Final Verification

Run all commands before reporting complete:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
python3 -m unittest tests.test_related_work_lineage_dashboard -v
cd dashboard && npm run build:workspace-island
git status --short
```

Expected:

- Tests pass.
- Bundle build passes.
- `git status --short` only shows intentional files before final commit, then clean after commit.

## Execution Notes

- Use the installed `react-flow` skill before editing React Flow layout or custom nodes.
- Keep React Flow imports from `@xyflow/react`.
- Keep `nodeTypes` stable outside component bodies.
- Keep React Flow parent containers with explicit height.
- Hide handles with opacity, not `display: none`.
- Do not use a force graph or generic auto layout for Understanding claim focus.
- Do not make Evidence, Warrant, or Limitation a drill layer.
