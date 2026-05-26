# Workspace Island Visual Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the workspace island from a generic React Flow diagram into a polished research-map canvas with mode-specific renderers, dark themed graph chrome, readable nodes, and breadcrumb return navigation.

**Architecture:** Keep the existing `/api/workspace-graph` contract and workspace shell. Refactor `WorkspaceIslandApp.jsx` so `WorkspaceIslandApp` owns mode tabs, breadcrumb, inspector, and delegates graph rendering to `UnderstandingGraphRenderer`, `LiteratureGraphRenderer`, and `ExperimentsGraphRenderer`, all backed by a shared styled React Flow renderer. Move visual language into `workspace-island.css`, borrowing proven graph treatment from the old project graph styles and lineage atlas without importing those bundles.

**Tech Stack:** React, `@xyflow/react`, Vite, Python unittest source guards, local `research_browser_server.py`.

---

## Files

- Modify: `tests/test_related_work_lineage_dashboard.py`
  - Add source-level regression guards for renderer split, breadcrumb navigation, dark graph chrome, and literature node readability.
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
  - Add breadcrumb component, controlled active mode synchronization, mode-specific renderers, custom node component, styled edge decoration, and dark React Flow chrome props.
- Modify: `dashboard/workspace-island/src/workspace-island.css`
  - Replace generic node/canvas styling with research-map visual system: textured dark canvas, weak grid, dark controls/minimap, typed node cards, dim/focus states, and wider literature cards.
- Regenerate: `dashboard/workspace-island.bundle.js`
- Regenerate: `dashboard/workspace-island.bundle.css`

Do not modify:

- `tools/workspace_graph_read_models.py`
- `tools/research_browser_server.py`
- `dashboard/app.js`
- `dashboard/project-graph/**`
- `dashboard/lineage-atlas/**`

---

### Task 1: Add Source Guard Tests For Visual Refactor Contract

**Files:**
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add failing renderer split and breadcrumb test**

Insert this method after `test_workspace_island_contains_layer_overview_and_terminal_run_rules`:

```python
    def test_workspace_island_uses_mode_specific_renderers_and_breadcrumb(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function WorkspaceBreadcrumb", source)
        self.assertIn('className="workspace-stage-breadcrumb"', source)
        self.assertIn("onNavigate?.(crumb)", source)
        self.assertIn("function UnderstandingGraphRenderer", source)
        self.assertIn("function LiteratureGraphRenderer", source)
        self.assertIn("function ExperimentsGraphRenderer", source)
        self.assertIn("function WorkspaceGraphRenderer", source)
        self.assertIn("nodeTypes={workspaceNodeTypes}", source)
        self.assertIn("fitViewOptions={{ padding: 0.1, maxZoom: 1.12 }}", source)
        self.assertIn("maskColor=\"var(--workspace-minimap-mask)\"", source)
```

- [ ] **Step 2: Add failing visual style guard test**

Insert this method after the new breadcrumb test:

```python
    def test_workspace_island_visual_style_guardrails(self):
        css = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn(".workspace-knowledge-canvas", css)
        self.assertIn("--workspace-grid-color", css)
        self.assertIn("--workspace-minimap-mask", css)
        self.assertIn(".workspace-stage-breadcrumb", css)
        self.assertIn(".workspace-node-card", css)
        self.assertIn(".workspace-node-card.is-dimmed", css)
        self.assertIn(".workspace-node-card.is-selected", css)
        self.assertIn(".workspace-knowledge-canvas .react-flow__controls-button", css)
        self.assertIn(".workspace-knowledge-canvas .react-flow__minimap", css)
        self.assertIn(".workspace-knowledge-canvas.is-literature .workspace-node-card", css)
        self.assertNotIn("background: var(--surface-2);\\n  cursor: pointer;\\n}", css)
```

- [ ] **Step 3: Run tests to verify red**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_uses_mode_specific_renderers_and_breadcrumb tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_visual_style_guardrails -v
```

Expected: FAIL because `WorkspaceBreadcrumb`, mode-specific renderers, `.workspace-knowledge-canvas`, and dark chrome selectors do not exist yet.

- [ ] **Step 4: Commit red tests**

```bash
git add tests/test_related_work_lineage_dashboard.py
git commit -m "test: define workspace island visual refactor contract"
```

---

### Task 2: Add Breadcrumb Navigation And Controlled Mode State

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`

- [ ] **Step 1: Update imports**

Replace the React import and `@xyflow/react` import block with:

```jsx
import React, { memo, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
```

- [ ] **Step 2: Add breadcrumb helpers before `WorkspaceInspector`**

Add this code before `function WorkspaceInspector`:

```jsx
function normalizeBreadcrumb(model) {
  const crumbs = Array.isArray(model?.breadcrumb) ? model.breadcrumb : [];
  const normalized = crumbs
    .filter((crumb) => crumb && typeof crumb === "object")
    .map((crumb, index) => ({
      label: crumb.label || crumb.layer || crumb.mode || `Layer ${index + 1}`,
      mode: crumb.mode || model?.mode || "understanding",
      layer: crumb.layer || "",
      focus_id: crumb.focus_id || "",
      selected_id: crumb.selected_id || "",
    }));
  if (normalized.length) return normalized;
  return [{
    label: "Workspace",
    mode: model?.mode || "understanding",
    layer: model?.layer || "",
    focus_id: "",
    selected_id: "",
  }];
}

function WorkspaceBreadcrumb({ model, onNavigate }) {
  const crumbs = normalizeBreadcrumb(model);
  return (
    <nav className="workspace-stage-breadcrumb" aria-label="Workspace layer breadcrumb">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;
        return (
          <React.Fragment key={`${crumb.mode}:${crumb.layer}:${crumb.focus_id}:${index}`}>
            {index ? <span className="workspace-breadcrumb-separator">/</span> : null}
            {isLast ? (
              <span className="workspace-breadcrumb-current">{crumb.label}</span>
            ) : (
              <button type="button" onClick={() => onNavigate?.(crumb)}>
                {crumb.label}
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 3: Synchronize active mode with incoming model**

Inside `WorkspaceIslandApp`, keep the existing state but add this effect immediately after it:

```jsx
  useEffect(() => {
    setActiveMode(model?.mode || "understanding");
  }, [model?.mode]);
```

- [ ] **Step 4: Add Escape key back navigation**

Add this effect after the existing `workspace-island-action` effect:

```jsx
  useEffect(() => {
    const handler = (event) => {
      if (event.key !== "Escape") return;
      const crumbs = normalizeBreadcrumb(model);
      if (crumbs.length < 2) return;
      event.preventDefault();
      onNavigate?.(crumbs[crumbs.length - 2]);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [model, onNavigate]);
```

- [ ] **Step 5: Render breadcrumb inside graph stage**

Do not leave breadcrumb in inspector. It belongs over the canvas. Task 3 will place it inside `WorkspaceGraphRenderer`; for now this step is complete when `WorkspaceBreadcrumb` exists and is imported by no other file.

- [ ] **Step 6: Run targeted tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_uses_mode_specific_renderers_and_breadcrumb -v
```

Expected: Still FAIL because renderer functions and `nodeTypes={workspaceNodeTypes}` do not exist yet.

---

### Task 3: Split Mode-Specific Renderers And Add Custom Knowledge Nodes

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`

- [ ] **Step 1: Replace generic node helpers**

Remove `nodeColor`, `toFlowNode`, and `toFlowEdge`. Add this block in their place:

```jsx
function relationClass(value) {
  return String(value || "related").toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "related";
}

function shortLabel(value, limit = 116) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1).trim()}...`;
}

function entityTone(entityType) {
  const type = String(entityType || "").toLowerCase();
  if (type === "question") return "q";
  if (type === "claim" || type === "evaluation_setting") return "c";
  if (type === "evidence" || type === "experiment") return "e";
  if (type === "warrant") return "w";
  if (type === "limitation") return "l";
  if (type === "source" || type === "paper" || type === "literature_lane") return "p";
  if (type === "run") return "r";
  return "x";
}

function nodeColor(node) {
  const tone = entityTone(node?.data?.entity_type || node?.data?.node?.entity_type);
  return {
    q: "#8ec7ff",
    c: "#d6a84f",
    e: "#70d6a3",
    w: "#bea0ff",
    l: "#e58b83",
    p: "#68c7d4",
    r: "#9bd7df",
  }[tone] || "#8f98a8";
}

function workspaceNodePosition(node, index, model) {
  if (node.position) return node.position;
  const type = node.entity_type || "";
  const mode = model?.mode || "understanding";
  const layer = model?.layer || "";
  const sameTypeIndex = (model?.canvas?.nodes || []).filter((item, itemIndex) => itemIndex < index && item.entity_type === type).length;
  if (mode === "understanding" && layer === "project_overview") {
    if (type === "question") return { x: sameTypeIndex * 360, y: -180 };
    if (type === "claim") return { x: sameTypeIndex * 390, y: 80 };
  }
  if (mode === "literature") {
    if (type === "literature_lane") return { x: 0, y: sameTypeIndex * 190 };
    return { x: 360 + (sameTypeIndex % 4) * 340, y: Math.floor(sameTypeIndex / 4) * 170 };
  }
  if (mode === "experiments") {
    if (type === "evaluation_setting") return { x: sameTypeIndex * 410, y: -40 };
    if (type === "experiment") return { x: sameTypeIndex * 380, y: 210 };
    if (type === "run") return { x: sameTypeIndex * 340, y: 430 };
  }
  return { x: (index % 4) * 360, y: Math.floor(index / 4) * 180 };
}

function workspaceNodeWidth(node, model) {
  if (model?.mode === "literature") return node.entity_type === "literature_lane" ? 300 : 330;
  if (model?.mode === "experiments") return node.entity_type === "evaluation_setting" ? 360 : 330;
  return node.entity_type === "claim" ? 360 : 300;
}

function focusedNodeIds(model) {
  const selectedId = model?.selected_id || model?.focus_id || "";
  const ids = new Set([selectedId].filter(Boolean));
  for (const edge of model?.canvas?.edges || []) {
    if (edge.source === selectedId) ids.add(edge.target);
    if (edge.target === selectedId) ids.add(edge.source);
  }
  return ids;
}

function nodeFocusClass(node, focusedIds, hasFocus) {
  if (!hasFocus) return "";
  if (focusedIds.has(node.id)) return node.id === [...focusedIds][0] ? "is-selected" : "is-neighbor";
  return "is-dimmed";
}

function toFlowNode(node, index, model, focusedIds, onNodeAction) {
  const hasFocus = Boolean(model?.selected_id || model?.focus_id);
  const focusClass = nodeFocusClass(node, focusedIds, hasFocus);
  return {
    id: node.id,
    type: "workspaceKnowledgeNode",
    position: workspaceNodePosition(node, index, model),
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    data: {
      node,
      entity_type: node.entity_type,
      tone: entityTone(node.entity_type),
      focusClass,
      onNodeAction,
    },
    style: {
      width: workspaceNodeWidth(node, model),
      minHeight: node.entity_type === "claim" ? 138 : 118,
    },
  };
}

function toFlowEdge(edge, model, focusedIds) {
  const relation = relationClass(edge.relation || edge.label);
  const hasFocus = Boolean(model?.selected_id || model?.focus_id);
  const active = focusedIds.has(edge.source) && focusedIds.has(edge.target);
  const dimmed = hasFocus && !active;
  const color = {
    answers: "#8ec7ff",
    supports: "#d6a84f",
    qualifies: "#68c7d4",
    bounds: "#e58b83",
    cites: "#68c7d4",
    contains: "#8f98a8",
  }[relation] || "#d6a84f";
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: active ? edge.label : undefined,
    type: "smoothstep",
    className: `workspace-edge workspace-edge-${relation} ${active ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""}`.trim(),
    markerEnd: { type: MarkerType.ArrowClosed, color },
    style: {
      stroke: color,
      strokeWidth: active ? 2.4 : 1.2,
      opacity: dimmed ? 0.06 : active ? 0.82 : 0.22,
      strokeDasharray: relation === "bounds" || relation === "cites" ? "7 7" : undefined,
    },
    labelStyle: {
      fill: "var(--text-muted)",
      fontSize: 10,
      fontFamily: "var(--mono)",
      fontWeight: 800,
    },
    labelBgStyle: {
      fill: "var(--surface-1)",
      fillOpacity: 0.82,
    },
    labelBgPadding: [6, 3],
    labelBgBorderRadius: 4,
  };
}
```

- [ ] **Step 2: Add custom node component**

Add this code after the helper block from Step 1:

```jsx
const WorkspaceKnowledgeNode = memo(function WorkspaceKnowledgeNode({ data }) {
  const node = data.node || {};
  const localId = node.local_id || node.subtitle || node.entity_type || "node";
  const canDrill = Boolean(node.drill);
  const className = [
    "workspace-node-card",
    `tone-${data.tone}`,
    data.focusClass,
    canDrill ? "can-drill" : "is-terminal",
  ].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Top} className="workspace-node-handle" />
      <span>{localId}</span>
      <strong>{shortLabel(node.label, 150)}</strong>
      <em>{node.subtitle || node.status || node.entity_type || ""}</em>
      {node.metadata?.role ? <small>{node.metadata.role}</small> : null}
      <Handle type="source" position={Position.Bottom} className="workspace-node-handle" />
    </button>
  );
});

const workspaceNodeTypes = {
  workspaceKnowledgeNode: WorkspaceKnowledgeNode,
};
```

- [ ] **Step 3: Add shared and mode-specific renderers**

Add this code before `function WorkspaceIslandApp`:

```jsx
function WorkspaceGraphRenderer({ model, onNavigate, modeClass }) {
  const focusedIds = useMemo(() => focusedNodeIds(model), [model]);
  const nodes = useMemo(
    () =>
      (model?.canvas?.nodes || []).map((node, index) =>
        toFlowNode(node, index, model, focusedIds, (item) => onNavigate?.(item.drill || item.inspector || { selected_id: item.id })),
      ),
    [model, focusedIds, onNavigate],
  );
  const edges = useMemo(() => (model?.canvas?.edges || []).map((edge) => toFlowEdge(edge, model, focusedIds)), [model, focusedIds]);
  return (
    <div className={`workspace-knowledge-canvas ${modeClass || ""}`} aria-label="Workspace graph canvas">
      <WorkspaceBreadcrumb model={model} onNavigate={onNavigate} />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={workspaceNodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1, maxZoom: 1.12 }}
        minZoom={0.05}
        maxZoom={2.2}
        panOnDrag
        panOnScroll
        zoomOnPinch
        zoomOnScroll
        zoomOnDoubleClick={false}
        nodesDraggable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Lines} gap={42} size={1} color="var(--workspace-grid-color)" />
        <Controls position="top-right" showInteractive={false} />
        <MiniMap
          position="bottom-right"
          nodeColor={nodeColor}
          pannable
          zoomable
          maskColor="var(--workspace-minimap-mask)"
          className="workspace-minimap"
        />
      </ReactFlow>
    </div>
  );
}

function UnderstandingGraphRenderer(props) {
  return <WorkspaceGraphRenderer {...props} modeClass="is-understanding" />;
}

function LiteratureGraphRenderer(props) {
  return <WorkspaceGraphRenderer {...props} modeClass="is-literature" />;
}

function ExperimentsGraphRenderer(props) {
  return <WorkspaceGraphRenderer {...props} modeClass="is-experiments" />;
}

function ModeGraphRenderer({ model, onNavigate }) {
  if (model?.mode === "literature") return <LiteratureGraphRenderer model={model} onNavigate={onNavigate} />;
  if (model?.mode === "experiments") return <ExperimentsGraphRenderer model={model} onNavigate={onNavigate} />;
  return <UnderstandingGraphRenderer model={model} onNavigate={onNavigate} />;
}
```

- [ ] **Step 4: Replace generic canvas render in `WorkspaceIslandApp`**

In the JSX returned by `WorkspaceIslandApp`, replace:

```jsx
          <div className="workspace-canvas" aria-label="Workspace graph canvas">
            <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.05} maxZoom={2} proOptions={{ hideAttribution: true }}>
              <Background variant={BackgroundVariant.Lines} gap={42} size={1} />
              <Controls position="top-right" showInteractive={false} />
              <MiniMap position="bottom-right" nodeColor={nodeColor} pannable zoomable />
            </ReactFlow>
          </div>
```

with:

```jsx
          <ModeGraphRenderer model={model} onNavigate={onNavigate} />
```

Remove the old `nodes` and `edges` `useMemo` declarations from `WorkspaceIslandApp`; `WorkspaceGraphRenderer` now owns them.

- [ ] **Step 5: Run tests to verify renderer contract**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_uses_mode_specific_renderers_and_breadcrumb -v
```

Expected: unittest PASS.

- [ ] **Step 6: Commit renderer split**

```bash
git add dashboard/workspace-island/src/WorkspaceIslandApp.jsx tests/test_related_work_lineage_dashboard.py
git commit -m "feat: add workspace island breadcrumb renderers"
```

---

### Task 4: Replace Generic Island CSS With Research Map Visual System

**Files:**
- Modify: `dashboard/workspace-island/src/workspace-island.css`

- [ ] **Step 1: Replace obsolete canvas and generic node styles**

In `dashboard/workspace-island/src/workspace-island.css`, remove these selector blocks:

```css
.workspace-canvas { ... }
.react-flow__node-default { ... }
.workspace-node-button { ... }
.workspace-node-button span,
.workspace-node-button em { ... }
.workspace-node-button strong { ... }
```

Add this block after `.workspace-island-body`:

```css
.workspace-knowledge-canvas {
  --workspace-grid-color: rgba(255, 255, 255, 0.038);
  --workspace-minimap-mask: rgba(8, 10, 13, 0.72);
  position: relative;
  min-height: calc(100vh - 215px);
  overflow: hidden;
  background:
    radial-gradient(circle at 46% 30%, rgba(214, 168, 79, 0.08), transparent 34%),
    radial-gradient(circle at 78% 62%, rgba(104, 199, 212, 0.045), transparent 26%),
    linear-gradient(180deg, rgba(17, 21, 29, 0.74), rgba(8, 10, 13, 0.84));
}

.workspace-knowledge-canvas::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.24;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.16) 0.7px, transparent 0.8px);
  background-size: 18px 18px;
  mix-blend-mode: screen;
}

.workspace-stage-breadcrumb {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 12;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 3px;
  border: 1px solid rgba(49, 57, 71, 0.78);
  border-radius: 999px;
  background: rgba(8, 10, 13, 0.68);
  color: var(--text-dim);
  font: 800 11px/1 var(--mono);
  backdrop-filter: blur(8px);
}

.workspace-stage-breadcrumb button,
.workspace-stage-breadcrumb span {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-main);
  padding: 8px 10px;
  font: inherit;
}

.workspace-stage-breadcrumb button {
  cursor: pointer;
}

.workspace-stage-breadcrumb button:hover,
.workspace-stage-breadcrumb button:focus-visible {
  background: rgba(214, 168, 79, 0.14);
  color: var(--accent);
  outline: none;
}

.workspace-breadcrumb-separator {
  color: var(--text-muted);
  padding: 0;
}

.workspace-breadcrumb-current {
  background: rgba(255, 255, 255, 0.04);
}

.workspace-node-handle {
  width: 1px;
  height: 1px;
  border: 0;
  background: transparent;
  opacity: 0;
}

.react-flow__node-workspaceKnowledgeNode {
  border: 0;
  padding: 0;
  background: transparent;
}

.workspace-node-card {
  --node-tone: #8f98a8;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 7px 10px;
  align-content: start;
  width: 100%;
  min-height: 100%;
  border: 1px solid color-mix(in srgb, var(--node-tone) 42%, var(--border));
  border-radius: 8px;
  padding: 13px;
  background:
    radial-gradient(circle at 22% 16%, rgba(255, 255, 255, 0.09), transparent 31%),
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone) 14%, transparent), transparent 6px),
    linear-gradient(180deg, rgba(16, 19, 25, 0.94), rgba(8, 10, 13, 0.94));
  color: var(--text-main);
  text-align: left;
  cursor: pointer;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.24), inset 0 1px 0 rgba(255, 255, 255, 0.035);
  transition: opacity 140ms ease, border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
}

.workspace-node-card.tone-q { --node-tone: #8ec7ff; }
.workspace-node-card.tone-c { --node-tone: #d6a84f; }
.workspace-node-card.tone-e { --node-tone: #70d6a3; }
.workspace-node-card.tone-w { --node-tone: #bea0ff; }
.workspace-node-card.tone-l { --node-tone: #e58b83; }
.workspace-node-card.tone-p { --node-tone: #68c7d4; }
.workspace-node-card.tone-r { --node-tone: #9bd7df; }

.workspace-node-card span {
  display: inline-grid;
  place-items: center;
  width: 36px;
  min-width: 36px;
  height: 28px;
  border: 1px solid color-mix(in srgb, var(--node-tone) 52%, transparent);
  border-radius: 6px;
  color: var(--node-tone);
  font: 900 10px/1 var(--mono);
}

.workspace-node-card strong {
  min-width: 0;
  color: var(--text-main);
  font-size: 13px;
  line-height: 1.24;
  overflow-wrap: anywhere;
}

.workspace-node-card em,
.workspace-node-card small {
  grid-column: 2;
  color: var(--text-dim);
  font: 800 10px/1.2 var(--mono);
  font-style: normal;
  text-transform: uppercase;
}

.workspace-node-card small {
  width: fit-content;
  max-width: 100%;
  border: 1px solid color-mix(in srgb, var(--node-tone) 28%, var(--border));
  border-radius: 999px;
  padding: 4px 7px;
  color: var(--node-tone);
  background: rgba(8, 10, 13, 0.44);
}

.workspace-node-card:hover,
.workspace-node-card:focus-visible,
.workspace-node-card.is-selected {
  border-color: color-mix(in srgb, var(--node-tone) 76%, var(--border));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--node-tone) 18%, transparent), 0 22px 52px rgba(0, 0, 0, 0.34);
  outline: none;
  transform: translateY(-1px);
}

.workspace-node-card.is-neighbor {
  opacity: 0.86;
  border-color: color-mix(in srgb, var(--node-tone) 58%, var(--border));
}

.workspace-node-card.is-dimmed {
  opacity: 0.28;
}

.workspace-edge {
  transition: opacity 140ms ease, stroke-width 140ms ease;
}

.workspace-edge.is-dimmed {
  opacity: 0.08;
}
```

- [ ] **Step 2: Add dark React Flow chrome**

Add this block after the node and edge block:

```css
.workspace-knowledge-canvas .react-flow__pane {
  cursor: grab;
}

.workspace-knowledge-canvas .react-flow__pane:active {
  cursor: grabbing;
}

.workspace-knowledge-canvas .react-flow__controls {
  overflow: hidden;
  border: 1px solid rgba(49, 57, 71, 0.88);
  border-radius: 8px;
  background: rgba(8, 10, 13, 0.84);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.34);
}

.workspace-knowledge-canvas .react-flow__controls-button {
  border-bottom: 1px solid rgba(49, 57, 71, 0.88);
  background: rgba(13, 17, 23, 0.92);
  color: var(--text-main);
  fill: currentColor;
}

.workspace-knowledge-canvas .react-flow__controls-button:hover,
.workspace-knowledge-canvas .react-flow__controls-button:focus-visible {
  background: rgba(214, 168, 79, 0.16);
  color: var(--accent);
  outline: 2px solid rgba(214, 168, 79, 0.22);
  outline-offset: -2px;
}

.workspace-knowledge-canvas .react-flow__controls-button svg {
  fill: currentColor;
}

.workspace-knowledge-canvas .react-flow__minimap,
.workspace-minimap {
  overflow: hidden;
  width: 160px;
  height: 118px;
  border: 1px solid rgba(49, 57, 71, 0.88);
  border-radius: 8px;
  background: rgba(8, 10, 13, 0.82);
  opacity: 0.76;
}

.workspace-knowledge-canvas .react-flow__minimap:hover,
.workspace-minimap:hover {
  opacity: 0.95;
}

.workspace-knowledge-canvas .react-flow__edge-textbg {
  fill: rgba(8, 10, 13, 0.84);
}

.workspace-knowledge-canvas .react-flow__edge-text {
  fill: var(--text-muted);
}
```

- [ ] **Step 3: Add mode-specific readability rules**

Add this block after the chrome block:

```css
.workspace-knowledge-canvas.is-understanding .workspace-node-card.tone-q strong {
  font-size: 13px;
}

.workspace-knowledge-canvas.is-understanding .workspace-node-card.tone-c strong {
  font-size: 15px;
}

.workspace-knowledge-canvas.is-literature .workspace-node-card {
  min-height: 126px;
}

.workspace-knowledge-canvas.is-literature .workspace-node-card strong {
  font-size: 14px;
  line-height: 1.28;
}

.workspace-knowledge-canvas.is-experiments .workspace-node-card strong {
  font-size: 14px;
}

:root[data-theme="light"] .workspace-knowledge-canvas {
  --workspace-grid-color: rgba(34, 42, 54, 0.055);
  --workspace-minimap-mask: rgba(244, 240, 232, 0.66);
  background:
    radial-gradient(circle at 46% 30%, rgba(152, 107, 31, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255, 253, 248, 0.72), rgba(244, 240, 232, 0.84));
}

:root[data-theme="light"] .workspace-node-card {
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--node-tone) 12%, transparent), transparent 6px),
    linear-gradient(180deg, rgba(255, 253, 248, 0.96), rgba(244, 240, 232, 0.94));
  box-shadow: 0 16px 34px rgba(85, 74, 56, 0.1);
}

:root[data-theme="light"] .workspace-stage-breadcrumb,
:root[data-theme="light"] .workspace-knowledge-canvas .react-flow__controls,
:root[data-theme="light"] .workspace-knowledge-canvas .react-flow__minimap {
  background: rgba(255, 253, 248, 0.84);
}
```

- [ ] **Step 4: Run style guard test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_workspace_island_visual_style_guardrails -v
```

Expected: PASS.

- [ ] **Step 5: Commit CSS refactor**

```bash
git add dashboard/workspace-island/src/workspace-island.css tests/test_related_work_lineage_dashboard.py
git commit -m "style: restore workspace island research map visuals"
```

---

### Task 5: Build Bundle And Run Dashboard Tests

**Files:**
- Modify: `dashboard/workspace-island.bundle.js`
- Modify: `dashboard/workspace-island.bundle.css`

- [ ] **Step 1: Build workspace island bundle**

Run:

```bash
cd dashboard
npm run build:workspace-island
```

Expected: Vite exits 0 and rewrites `workspace-island.bundle.js` and `workspace-island.bundle.css`.

- [ ] **Step 2: Run dashboard source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: all tests pass.

- [ ] **Step 3: Run workspace graph read model tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models tests.test_research_dataset_read_models -v
```

Expected: all tests pass. This confirms visual refactor did not require backend graph contract changes.

- [ ] **Step 4: Commit generated bundles**

```bash
git add dashboard/workspace-island.bundle.js dashboard/workspace-island.bundle.css
git commit -m "build: refresh workspace island bundle"
```

---

### Task 6: Local Browser Smoke Test

**Files:**
- No source edits expected.

- [ ] **Step 1: Restart dashboard server**

If port `8765` already has a stale server, stop it:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
for pid in $(lsof -tiTCP:8765 -sTCP:LISTEN); do kill "$pid"; done
```

Start server:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --port 8765
```

Expected: `Serving Research Browser at http://127.0.0.1:8765/`

- [ ] **Step 2: Verify API still serves all workspace modes**

Run:

```bash
curl -sS 'http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=understanding' | head
curl -sS 'http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=literature' | head
curl -sS 'http://127.0.0.1:8765/api/workspace-graph?project=DemoVisualAffordance&mode=experiments' | head
```

Expected: each command prints JSON starting with `{` and includes `"schema_version": "workspace-graph-v1"`.

- [ ] **Step 3: Open dashboard and inspect Understanding**

Open:

```bash
open 'http://127.0.0.1:8765/dashboard/index.html?v=english-dashboard-20260523'
```

Click `OpenProject` for `Demo Visual Affordance`.

Expected visual result:

- Canvas grid is subtle, not bright white.
- Minimap and controls are dark in dark mode.
- Nodes look like research cards with type accent strips and badges.
- Overview inspector lists only Questions.
- Clicking a claim drills to claim layer.
- Breadcrumb appears in upper-left canvas and clicking `Workspace` returns to overview.
- Pressing `Esc` returns one breadcrumb level when in a drill layer.

- [ ] **Step 4: Inspect Literature**

Click `Literature`.

Expected visual result:

- Paper and route nodes are wider and readable.
- Route focus does not produce tiny unreadable paper boxes.
- Right inspector remains visible and coherent.

- [ ] **Step 5: Inspect Experiments**

Click `Experiments`.

Expected visual result:

- Experiment overview remains usable.
- Evaluation setting nodes use experiment mode styling.
- No `run_detail` layer appears.

- [ ] **Step 6: Final status check**

Run:

```bash
git status --short
```

Expected: only intentionally untracked PRD/plan docs remain, or no output if docs were committed in this branch.

---

## Self-Review Checklist

- Spec coverage:
  - Dark graph chrome: Task 4.
  - Breadcrumb return: Task 2 and Task 3.
  - Mode-specific renderers: Task 3.
  - Understanding visual restoration: Task 3 and Task 4.
  - Literature readability: Task 3 and Task 4.
  - Backend contract unchanged: Task 5.
  - Browser smoke: Task 6.
- Placeholder scan:
  - No `TBD`.
  - No `TODO`.
  - No unspecified "handle edge cases" step.
  - Every code-edit task includes concrete code.
- Type consistency:
  - `WorkspaceBreadcrumb`, `WorkspaceGraphRenderer`, `UnderstandingGraphRenderer`, `LiteratureGraphRenderer`, `ExperimentsGraphRenderer`, and `workspaceNodeTypes` are introduced before tests assert them.
  - `maskColor="var(--workspace-minimap-mask)"` is present in JSX and `--workspace-minimap-mask` is present in CSS.
  - `className="workspace-stage-breadcrumb"` is present in JSX and styled in CSS.
