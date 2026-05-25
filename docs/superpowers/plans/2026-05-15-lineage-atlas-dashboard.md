# Lineage Atlas Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the related-work lineage report page with a single React Flow atlas island centered on `topic_name`, with one layer of route branches and paper nodes plus a right inspector.

**Architecture:** Keep `related-work-lineage.json` as the source of truth, pass richer lineage metadata through `.dashboard/index.json`, and mount a new `ResearchBrowserLineageAtlas` React island from `dashboard/app.js`. Reuse React Flow as the canvas runtime, but build a separate shallow lineage model instead of importing project graph GSN/Toulmin model builders.

**Tech Stack:** Python `unittest`, dashboard static JS, React 19, `@xyflow/react`, Vite, generated dashboard read-model JSON.

---

## File Structure

- Modify `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json`
  - Add `topic_name`.
- Modify `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md`
  - Re-render from JSON after validation.
- Modify `tools/build_dashboard_index.py`
  - Pass lineage metadata needed by the atlas.
- Modify `dashboard/package.json`
  - Add `build:lineage-atlas`.
- Create `dashboard/lineage-atlas/vite.config.mjs`
  - Build a standalone `lineage-atlas.bundle.js` and `lineage-atlas.bundle.css`.
- Create `dashboard/lineage-atlas/src/LineageAtlasApp.jsx`
  - React Flow island, layout model, controls, inspector, mount API.
- Create `dashboard/lineage-atlas/src/lineage-atlas.css`
  - Island-specific canvas, node, control, and inspector styles.
- Modify `dashboard/lineage.html`
  - Load the new bundle and CSS.
- Modify `dashboard/app.js`
  - Mount the island and provide compact fallback.
- Modify `tests/test_related_work_lineage_dashboard.py`
  - Cover island hooks, metadata pass-through, fallback, and cache behavior.
- Modify `tests/test_related_work_lineage_cli.py`
  - Cover optional `topic_name` preservation only if validation policy is extended.

---

## Task 1: Add Topic Metadata To Demo Lineage

**Files:**
- Modify: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json`
- Modify: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md`

- [ ] **Step 1: Add the topic field**

In `related-work-lineage.json`, add `topic_name` immediately after `title`:

```json
  "title": "Visual Affordance Field Lineage from VFM Probing Baseline",
  "topic_name": "Visual Affordance Grounding",
  "status": "approved",
```

- [ ] **Step 2: Validate the lineage artifact**

Run:

```bash
python3 tools/related_work_lineage_cli.py validate --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --json
```

Expected:

```json
{
  "edge_count": 15,
  "errors": [],
  "paper_count": 18,
  "route_count": 4,
  "valid": true
}
```

- [ ] **Step 3: Re-render the Markdown summary**

Run:

```bash
python3 tools/related_work_lineage_cli.py render-summary --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --output examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md --json
```

Expected:

```json
{
  "output": "$REPO_ROOT/examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md",
  "valid": true
}
```

- [ ] **Step 4: Restore approved Markdown frontmatter**

The renderer writes `human_review: pending`. Change it back:

```yaml
status: "approved"
human_review: approved
```

- [ ] **Step 5: Commit**

```bash
git add examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md
git commit -m "demo: add lineage atlas topic name"
```

---

## Task 2: Pass Atlas Metadata Through Dashboard Index

**Files:**
- Modify: `tools/build_dashboard_index.py`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing test for metadata pass-through**

Add this test to `RelatedWorkLineageDashboardTest`:

```python
    def test_dashboard_index_passes_lineage_atlas_metadata(self):
        script = textwrap.dedent(
            """
            const assert = require("assert");
            const fs = require("fs");

            const index = JSON.parse(fs.readFileSync("examples/workspaces/demo-visual-affordance/.dashboard/index.json", "utf8"));
            const map = index.lineage_maps.find((item) => item.id === "DemoVisualAffordance/demo-affordance-lineage");

            assert(map, "demo lineage map missing");
            assert.equal(map.topic_name, "Visual Affordance Grounding");
            assert(map.baseline_paper_field_scope, "baseline scope missing");
            assert(Array.isArray(map.axis_candidates), "axis candidates missing");
            assert(Array.isArray(map.major_trends), "major trends missing");
            assert(Array.isArray(map.notable_forks), "notable forks missing");
            assert(Array.isArray(map.search_log), "search log missing");
            """
        )
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_dashboard_index_passes_lineage_atlas_metadata -v
```

Expected: FAIL because `topic_name` and metadata are not present in `.dashboard/index.json` yet.

- [ ] **Step 3: Implement metadata pass-through**

In `tools/build_dashboard_index.py`, inside `collect_lineage_maps`, extend the appended map object:

```python
                "topic_name": str(payload.get("topic_name") or "").strip() if isinstance(payload, dict) else "",
                "display": payload.get("display", {}) if isinstance(payload, dict) else {},
                "baseline_paper_field_scope": payload.get("baseline_paper_field_scope", {}) if isinstance(payload, dict) else {},
                "axis_candidates": list_field(payload, "axis_candidates", MAX_LINEAGE_DASHBOARD_ITEMS),
                "survey_catalog": list_field(payload, "survey_catalog", MAX_LINEAGE_DASHBOARD_ITEMS),
                "timeline_tracks": list_field(payload, "timeline_tracks", MAX_LINEAGE_DASHBOARD_ITEMS),
                "major_trends": list_field(payload, "major_trends", MAX_LINEAGE_DASHBOARD_ITEMS),
                "notable_forks": list_field(payload, "notable_forks", MAX_LINEAGE_DASHBOARD_ITEMS),
                "search_log": list_field(payload, "search_log", MAX_LINEAGE_DASHBOARD_ITEMS),
```

Place these fields near existing `route_narrowing`, `routes`, `papers`, and `positioning_note`.

- [ ] **Step 4: Rebuild demo dashboard index**

Run:

```bash
python3 tools/build_dashboard_index.py --repo examples/workspaces/demo-visual-affordance
```

Expected:

```text
Wrote .dashboard/index.json
Projects: 1 Papers: 7 Rounds: 1 Claims: 0 Lineage maps: 1
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_dashboard_index_passes_lineage_atlas_metadata -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/build_dashboard_index.py tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: pass lineage atlas metadata"
```

---

## Task 3: Add Lineage Atlas Build Target

**Files:**
- Modify: `dashboard/package.json`
- Create: `dashboard/lineage-atlas/vite.config.mjs`
- Create: `dashboard/lineage-atlas/src/LineageAtlasApp.jsx`
- Create: `dashboard/lineage-atlas/src/lineage-atlas.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing tests for bundle source and script**

Add this test:

```python
    def test_lineage_atlas_source_and_build_script_exist(self):
        package_json = (ROOT / "dashboard" / "package.json").read_text(encoding="utf-8")
        vite_config = ROOT / "dashboard" / "lineage-atlas" / "vite.config.mjs"
        source = ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx"
        css = ROOT / "dashboard" / "lineage-atlas" / "src" / "lineage-atlas.css"

        self.assertIn('"build:lineage-atlas"', package_json)
        self.assertTrue(vite_config.exists())
        self.assertTrue(source.exists())
        self.assertTrue(css.exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_source_and_build_script_exist -v
```

Expected: FAIL because files and script do not exist.

- [ ] **Step 3: Add npm build script**

Update `dashboard/package.json` scripts:

```json
  "scripts": {
    "build:project-graph": "vite build --config project-graph/vite.config.mjs",
    "build:lineage-atlas": "vite build --config lineage-atlas/vite.config.mjs"
  },
```

- [ ] **Step 4: Create Vite config**

Create `dashboard/lineage-atlas/vite.config.mjs`:

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  root: resolve(import.meta.dirname),
  build: {
    outDir: resolve(import.meta.dirname, ".."),
    emptyOutDir: false,
    sourcemap: false,
    rollupOptions: {
      input: resolve(import.meta.dirname, "src/LineageAtlasApp.jsx"),
      output: {
        entryFileNames: "lineage-atlas.bundle.js",
        assetFileNames: "lineage-atlas.bundle.[ext]",
        chunkFileNames: "lineage-atlas.[hash].js",
        inlineDynamicImports: true,
      },
    },
  },
});
```

- [ ] **Step 5: Create minimal React island source**

Create `dashboard/lineage-atlas/src/LineageAtlasApp.jsx`:

```jsx
import React from "react";
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
import "./lineage-atlas.css";

const mountedRoots = new WeakMap();

export function lineageTopicName(map = {}, project = {}) {
  const direct = String(map.topic_name || "").trim();
  if (direct) return direct;
  const displayTopic = String(map.display?.topic_name || "").trim();
  if (displayTopic) return displayTopic;
  const title = String(map.title || "").replace(/\b(Lineage|Related Work|from VFM Probing Baseline)\b/gi, " ").replace(/\s+/g, " ").trim();
  if (title) return title;
  return String(project.title || project.id || "Related Work").trim();
}

export function buildLineageAtlasModel(map = {}, project = {}) {
  const topic = lineageTopicName(map, project);
  return {
    topic,
    nodes: [
      {
        id: "topic",
        type: "default",
        position: { x: 0, y: 0 },
        data: { label: topic, kind: "topic" },
      },
    ],
    edges: [],
  };
}

function LineageAtlasApp({ map = {}, project = {} }) {
  const model = buildLineageAtlasModel(map, project);
  return (
    <ReactFlowProvider>
      <div className="lineage-atlas-shell">
        <section className="lineage-atlas-flow" aria-label="Related work lineage atlas">
          <ReactFlow
            nodes={model.nodes}
            edges={model.edges}
            fitView
            fitViewOptions={{ padding: 0.22, maxZoom: 1.05 }}
            minZoom={0.2}
            maxZoom={1.8}
            nodesDraggable={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="var(--graph-grid-color)" />
            <Controls position="bottom-left" showInteractive={false} />
            <MiniMap position="bottom-right" pannable zoomable className="lineage-atlas-minimap" />
          </ReactFlow>
        </section>
        <aside className="lineage-atlas-inspector">
          <p className="eyebrow">Topic</p>
          <h2>{model.topic}</h2>
          <p>{map.positioning_note || "Paper-only related-work atlas."}</p>
        </aside>
      </div>
    </ReactFlowProvider>
  );
}

function mount(root, props) {
  if (!root) return null;
  const previous = mountedRoots.get(root);
  if (previous) previous.unmount();
  const reactRoot = createRoot(root);
  reactRoot.render(<LineageAtlasApp {...props} />);
  mountedRoots.set(root, reactRoot);
  return reactRoot;
}

window.ResearchBrowserLineageAtlas = {
  mount,
  LineageAtlasApp,
  buildLineageAtlasModel,
  lineageTopicName,
};
```

- [ ] **Step 6: Create minimal CSS**

Create `dashboard/lineage-atlas/src/lineage-atlas.css`:

```css
.lineage-atlas-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  min-height: calc(100vh - 128px);
  border: 1px solid var(--border);
  border-radius: 18px;
  overflow: hidden;
  background: var(--panel);
}

.lineage-atlas-flow {
  min-height: 680px;
  background:
    radial-gradient(circle at center, rgba(214, 168, 79, 0.12), transparent 34%),
    var(--bg);
}

.lineage-atlas-inspector {
  border-left: 1px solid var(--border);
  padding: 24px;
  background: color-mix(in srgb, var(--panel) 92%, #000 8%);
}

.lineage-atlas-inspector h2 {
  margin: 8px 0 12px;
  font-size: 1.5rem;
}

.lineage-atlas-inspector p {
  color: var(--muted);
  line-height: 1.6;
}

.lineage-atlas-minimap {
  background: color-mix(in srgb, var(--panel) 88%, #000 12%);
  border: 1px solid var(--border);
}
```

- [ ] **Step 7: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_source_and_build_script_exist -v
```

Expected: PASS.

- [ ] **Step 8: Build the bundle**

Run:

```bash
cd dashboard && npm run build:lineage-atlas
```

Expected: Vite writes `dashboard/lineage-atlas.bundle.js` and `dashboard/lineage-atlas.bundle.css`.

- [ ] **Step 9: Commit**

```bash
git add dashboard/package.json dashboard/lineage-atlas/vite.config.mjs dashboard/lineage-atlas/src/LineageAtlasApp.jsx dashboard/lineage-atlas/src/lineage-atlas.css dashboard/lineage-atlas.bundle.js dashboard/lineage-atlas.bundle.css tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: add lineage atlas island"
```

---

## Task 4: Build The Shallow React Flow Lineage Model

**Files:**
- Modify: `dashboard/lineage-atlas/src/LineageAtlasApp.jsx`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing static/model tests**

Add this test:

```python
    def test_lineage_atlas_uses_shallow_model_not_project_graph_builders(self):
        source = (ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx").read_text(encoding="utf-8")

        self.assertIn("function buildLineageAtlasModel", source)
        self.assertIn("routeNode", source)
        self.assertIn("paperNode", source)
        self.assertNotIn("buildProjectGraphFlowModel", source)
        self.assertNotIn("buildClaimFocusFlowModel", source)
        self.assertNotIn("paperArgumentNode", source)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_uses_shallow_model_not_project_graph_builders -v
```

Expected: FAIL because route and paper node types do not exist yet.

- [ ] **Step 3: Add node components and route colors**

In `LineageAtlasApp.jsx`, update the existing `@xyflow/react` import to include `Handle`, `MarkerType`, and `Position`:

```jsx
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  MarkerType,
  Position,
} from "@xyflow/react";
```

Then add these helpers above `buildLineageAtlasModel`:

```jsx

const ROUTE_COLORS = ["#d6a84f", "#70d6a3", "#8ec7ff", "#d2a6ff", "#e58b83", "#68c7d4", "#f2a6c7", "#a8d66d"];

function flowSafeId(value) {
  return String(value || "node").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "node";
}

function shortLabel(value, limit = 54) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1).trim()}...`;
}

function sortedPapers(papers = []) {
  return [...papers].sort((a, b) => {
    const yearA = Number(a.year || 9999);
    const yearB = Number(b.year || 9999);
    if (yearA !== yearB) return yearA - yearB;
    const monthA = Number(a.month || 99);
    const monthB = Number(b.month || 99);
    if (monthA !== monthB) return monthA - monthB;
    return String(a.title || "").localeCompare(String(b.title || ""));
  });
}

function LineageTopicNode({ data }) {
  return (
    <button type="button" className="lineage-atlas-topic-node" onClick={() => data.onSelect?.({ type: "map" })}>
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
      <span>Topic</span>
      <strong>{data.label}</strong>
      <em>{data.subtitle}</em>
    </button>
  );
}

function LineageRouteNode({ data }) {
  return (
    <button
      type="button"
      className={`lineage-atlas-route-node ${data.selected ? "is-selected" : ""}`}
      style={{ "--route-color": data.color }}
      onClick={() => data.onSelect?.({ type: "route", route: data.route })}
    >
      <Handle type="target" position={Position.Left} className="lineage-atlas-handle" />
      <span>{data.reviewStatus || "candidate"}</span>
      <strong>{data.label}</strong>
      <em>{data.paperCount} papers</em>
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
    </button>
  );
}

function LineagePaperNode({ data }) {
  return (
    <button
      type="button"
      className={`lineage-atlas-paper-node ${data.isBaseline ? "is-baseline" : ""} ${data.selected ? "is-selected" : ""}`}
      style={{ "--route-color": data.color }}
      onClick={() => data.onSelect?.({ type: "paper", paper: data.paper })}
    >
      <Handle type="target" position={Position.Left} className="lineage-atlas-handle" />
      <span>{data.date || "n.d."}</span>
      <strong>{data.label}</strong>
      <em>{data.roles}</em>
      <Handle type="source" position={Position.Right} className="lineage-atlas-handle" />
    </button>
  );
}

const nodeTypes = {
  topicNode: LineageTopicNode,
  routeNode: LineageRouteNode,
  paperNode: LineagePaperNode,
};
```

- [ ] **Step 4: Replace model builder with deterministic route/paper layout**

Replace `buildLineageAtlasModel`:

```jsx
export function buildLineageAtlasModel(map = {}, project = {}, options = {}) {
  const topic = lineageTopicName(map, project);
  const selected = options.selected || { type: "map" };
  const onSelect = options.onSelect || (() => {});
  const showEdges = Boolean(options.showEdges);
  const routeFilter = String(options.routeFilter || "");
  const statusFilter = String(options.statusFilter || "");
  const query = String(options.query || "").trim().toLowerCase();
  const routes = Array.isArray(map.routes) ? map.routes : [];
  const papers = Array.isArray(map.papers) ? map.papers : [];
  const routeIds = routes.map((route) => route.id);
  const routeMap = new Map(routes.map((route, index) => [route.id, { ...route, color: ROUTE_COLORS[index % ROUTE_COLORS.length] }]));
  const nodes = [
    {
      id: "topic",
      type: "topicNode",
      position: { x: 0, y: 0 },
      data: {
        label: topic,
        subtitle: `${routes.length} routes / ${papers.length} papers`,
        onSelect,
      },
    },
  ];
  const edges = [];
  const visibleRouteIds = routeIds.filter((routeId) => !routeFilter || routeId === routeFilter);
  const radiusX = 420;
  const radiusY = 260;
  const startAngle = -Math.PI * 0.78;
  const endAngle = Math.PI * 0.78;
  const angleStep = visibleRouteIds.length > 1 ? (endAngle - startAngle) / (visibleRouteIds.length - 1) : 0;

  visibleRouteIds.forEach((routeId, routeIndex) => {
    const route = routeMap.get(routeId);
    const angle = visibleRouteIds.length === 1 ? 0 : startAngle + angleStep * routeIndex;
    const routeX = Math.cos(angle) * radiusX;
    const routeY = Math.sin(angle) * radiusY;
    const color = route.color;
    const routePapers = sortedPapers(papers.filter((paper) => {
      if ((paper.route || "unassigned") !== routeId) return false;
      if (statusFilter && String(paper.review_status || "candidate") !== statusFilter) return false;
      if (!query) return true;
      return [paper.title, paper.summary, paper.source_evidence, ...(paper.roles || [])].join(" ").toLowerCase().includes(query);
    }));

    nodes.push({
      id: `route:${flowSafeId(routeId)}`,
      type: "routeNode",
      position: { x: routeX, y: routeY },
      data: {
        route,
        label: route.label || route.id,
        reviewStatus: route.review_status || "candidate",
        paperCount: routePapers.length,
        color,
        selected: selected.type === "route" && selected.route?.id === route.id,
        onSelect,
      },
    });
    edges.push({
      id: `topic-route:${flowSafeId(routeId)}`,
      source: "topic",
      target: `route:${flowSafeId(routeId)}`,
      type: "smoothstep",
      className: "lineage-atlas-route-edge",
      style: { stroke: color, strokeWidth: 3 },
    });

    const directionX = Math.cos(angle);
    const directionY = Math.sin(angle);
    const tangentX = -directionY;
    const tangentY = directionX;
    routePapers.forEach((paper, paperIndex) => {
      const distance = 260 + paperIndex * 170;
      const alternate = paperIndex % 2 === 0 ? -1 : 1;
      const offset = alternate * 52;
      const paperId = `paper:${flowSafeId(paper.id)}`;
      const date = [paper.year, paper.month].filter(Boolean).join("-");
      const isBaseline = (paper.roles || []).includes("baseline");
      nodes.push({
        id: paperId,
        type: "paperNode",
        position: {
          x: routeX + directionX * distance + tangentX * offset,
          y: routeY + directionY * distance + tangentY * offset,
        },
        data: {
          paper,
          label: shortLabel(paper.title || paper.id, 46),
          date,
          roles: (paper.roles || []).slice(0, 2).join(", "),
          isBaseline,
          color,
          selected: selected.type === "paper" && selected.paper?.id === paper.id,
          onSelect,
        },
      });
      edges.push({
        id: `route-paper:${flowSafeId(routeId)}:${flowSafeId(paper.id)}`,
        source: `route:${flowSafeId(routeId)}`,
        target: paperId,
        type: "smoothstep",
        className: "lineage-atlas-paper-edge",
        style: { stroke: color, strokeWidth: isBaseline ? 2.8 : 1.6 },
      });
    });
  });

  if (showEdges) {
    for (const edge of Array.isArray(map.explicit_edges) ? map.explicit_edges : []) {
      edges.push({
        id: `explicit:${flowSafeId(edge.source)}:${flowSafeId(edge.target)}:${flowSafeId(edge.relation)}`,
        source: `paper:${flowSafeId(edge.source)}`,
        target: `paper:${flowSafeId(edge.target)}`,
        type: "smoothstep",
        label: edge.relation || "related",
        className: "lineage-atlas-explicit-edge",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#d6a84f" },
        data: { edge },
      });
    }
  }

  return { topic, nodes, edges, routes, papers };
}
```

- [ ] **Step 5: Pass nodeTypes into ReactFlow**

In `LineageAtlasApp`, update `<ReactFlow>`:

```jsx
          <ReactFlow
            nodes={model.nodes}
            edges={model.edges}
            nodeTypes={nodeTypes}
            fitView
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_uses_shallow_model_not_project_graph_builders -v
```

Expected: PASS.

- [ ] **Step 7: Build the bundle**

Run:

```bash
cd dashboard && npm run build:lineage-atlas
```

Expected: build succeeds and bundle contains `ResearchBrowserLineageAtlas`.

- [ ] **Step 8: Commit**

```bash
git add dashboard/lineage-atlas/src/LineageAtlasApp.jsx dashboard/lineage-atlas.bundle.js tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: build shallow lineage atlas model"
```

---

## Task 5: Add Controls And Inspector

**Files:**
- Modify: `dashboard/lineage-atlas/src/LineageAtlasApp.jsx`
- Modify: `dashboard/lineage-atlas/src/lineage-atlas.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing static test**

Add:

```python
    def test_lineage_atlas_has_controls_and_inspector_states(self):
        source = (ROOT / "dashboard" / "lineage-atlas" / "src" / "LineageAtlasApp.jsx").read_text(encoding="utf-8")

        self.assertIn("lineage-atlas-controlbar", source)
        self.assertIn("Show edges", source)
        self.assertIn("Search papers and routes", source)
        self.assertIn("LineageInspector", source)
        self.assertIn("source evidence", source.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_has_controls_and_inspector_states -v
```

Expected: FAIL because controls and inspector do not exist yet.

- [ ] **Step 3: Add inspector component**

Add this before `LineageAtlasApp`:

```jsx
function LineageInspector({ map, project, selected, model }) {
  if (selected?.type === "paper" && selected.paper) {
    const paper = selected.paper;
    return (
      <aside className="lineage-atlas-inspector" aria-live="polite">
        <p className="eyebrow">Paper</p>
        <h2>{paper.title || paper.id}</h2>
        <dl>
          <div><dt>Date</dt><dd>{[paper.year, paper.month].filter(Boolean).join("-") || "n.d."}</dd></div>
          <div><dt>Route</dt><dd>{paper.route || "unassigned"}</dd></div>
          <div><dt>Status</dt><dd>{paper.review_status || "candidate"}</dd></div>
        </dl>
        <p>{paper.summary || "No summary."}</p>
        <div className="lineage-atlas-tagrow">
          {(paper.roles || []).map((role) => <span key={role}>{role}</span>)}
        </div>
        {paper.source_url ? <a className="lineage-atlas-source-link" href={paper.source_url} target="_blank" rel="noopener noreferrer">Open source</a> : null}
        <details>
          <summary>source evidence</summary>
          <p>{paper.source_evidence || "No source evidence."}</p>
        </details>
      </aside>
    );
  }
  if (selected?.type === "route" && selected.route) {
    const route = selected.route;
    const routePapers = model.papers.filter((paper) => (paper.route || "unassigned") === route.id);
    return (
      <aside className="lineage-atlas-inspector" aria-live="polite">
        <p className="eyebrow">Route</p>
        <h2>{route.label || route.id}</h2>
        <dl>
          <div><dt>Status</dt><dd>{route.review_status || "candidate"}</dd></div>
          <div><dt>Papers</dt><dd>{routePapers.length}</dd></div>
        </dl>
        <p>{route.description || "No route description."}</p>
        <ol>
          {sortedPapers(routePapers).slice(0, 8).map((paper) => <li key={paper.id}>{paper.title || paper.id}</li>)}
        </ol>
      </aside>
    );
  }
  const baseline = model.papers.find((paper) => (paper.roles || []).includes("baseline"));
  return (
    <aside className="lineage-atlas-inspector" aria-live="polite">
      <p className="eyebrow">Topic</p>
      <h2>{model.topic}</h2>
      <dl>
        <div><dt>Status</dt><dd>{map.status || "candidate"}</dd></div>
        <div><dt>Routes</dt><dd>{model.routes.length}</dd></div>
        <div><dt>Papers</dt><dd>{model.papers.length}</dd></div>
      </dl>
      {baseline ? <p><strong>Baseline:</strong> {baseline.title}</p> : null}
      <p>{map.positioning_note || "Paper-only related-work atlas."}</p>
      <p className="lineage-atlas-boundary">Paper-only lineage. Not Project Understanding Graph truth.</p>
    </aside>
  );
}
```

- [ ] **Step 4: Add state and controls in `LineageAtlasApp`**

Replace the component body with:

```jsx
function LineageAtlasApp({ map = {}, project = {} }) {
  const [selected, setSelected] = React.useState({ type: "map" });
  const [query, setQuery] = React.useState("");
  const [routeFilter, setRouteFilter] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("");
  const [showEdges, setShowEdges] = React.useState(false);
  const model = buildLineageAtlasModel(map, project, {
    selected,
    onSelect: setSelected,
    query,
    routeFilter,
    statusFilter,
    showEdges,
  });
  const routeOptions = Array.isArray(map.routes) ? map.routes : [];
  const statuses = Array.from(new Set((map.papers || []).map((paper) => paper.review_status || "candidate")));

  return (
    <ReactFlowProvider>
      <div className="lineage-atlas-shell">
        <section className="lineage-atlas-main">
          <div className="lineage-atlas-controlbar">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search papers and routes"
              aria-label="Search papers and routes"
            />
            <select value={routeFilter} onChange={(event) => setRouteFilter(event.target.value)} aria-label="Filter route">
              <option value="">All routes</option>
              {routeOptions.map((route) => <option key={route.id} value={route.id}>{route.label || route.id}</option>)}
            </select>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter paper status">
              <option value="">All statuses</option>
              {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
            <label>
              <input type="checkbox" checked={showEdges} onChange={(event) => setShowEdges(event.target.checked)} />
              Show edges
            </label>
            <button type="button" onClick={() => setSelected({ type: "map" })}>Overview</button>
          </div>
          <div className="lineage-atlas-flow" aria-label="Related work lineage atlas">
            <ReactFlow
              nodes={model.nodes}
              edges={model.edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.22, maxZoom: 1.05 }}
              minZoom={0.08}
              maxZoom={1.8}
              panOnDrag
              panOnScroll
              zoomOnPinch
              zoomOnScroll
              zoomOnDoubleClick={false}
              nodesDraggable={false}
              elementsSelectable
              proOptions={{ hideAttribution: true }}
            >
              <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="var(--graph-grid-color)" />
              <Controls position="bottom-left" showInteractive={false} />
              <MiniMap position="bottom-right" pannable zoomable className="lineage-atlas-minimap" />
            </ReactFlow>
          </div>
        </section>
        <LineageInspector map={map} project={project} selected={selected} model={model} />
      </div>
    </ReactFlowProvider>
  );
}
```

- [ ] **Step 5: Add control and inspector CSS**

Append to `lineage-atlas.css`:

```css
.lineage-atlas-main {
  min-width: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.lineage-atlas-controlbar {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--panel) 94%, #000 6%);
}

.lineage-atlas-controlbar input,
.lineage-atlas-controlbar select,
.lineage-atlas-controlbar button {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  color: var(--text);
  padding: 9px 11px;
}

.lineage-atlas-controlbar input {
  flex: 1;
  min-width: 220px;
}

.lineage-atlas-controlbar label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 0.84rem;
}

.lineage-atlas-inspector dl {
  display: grid;
  gap: 8px;
  margin: 16px 0;
}

.lineage-atlas-inspector dl div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 72%, transparent);
  padding-bottom: 8px;
}

.lineage-atlas-inspector dt {
  color: var(--muted);
}

.lineage-atlas-inspector dd {
  margin: 0;
  color: var(--text);
}

.lineage-atlas-tagrow {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 14px 0;
}

.lineage-atlas-tagrow span {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 8px;
  color: var(--muted);
}

.lineage-atlas-source-link {
  display: inline-flex;
  margin: 8px 0 12px;
  color: var(--accent);
}

.lineage-atlas-boundary {
  border-top: 1px solid var(--border);
  padding-top: 12px;
  font-size: 0.82rem;
}
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_atlas_has_controls_and_inspector_states -v
```

Expected: PASS.

- [ ] **Step 7: Build bundle**

Run:

```bash
cd dashboard && npm run build:lineage-atlas
```

Expected: build succeeds.

- [ ] **Step 8: Commit**

```bash
git add dashboard/lineage-atlas/src/LineageAtlasApp.jsx dashboard/lineage-atlas/src/lineage-atlas.css dashboard/lineage-atlas.bundle.js dashboard/lineage-atlas.bundle.css tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: add lineage atlas controls and inspector"
```

---

## Task 6: Mount Atlas Island From The Lineage Page

**Files:**
- Modify: `dashboard/lineage.html`
- Modify: `dashboard/app.js`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing tests for bundle loading and mount hook**

Update `test_app_contains_lineage_page_hooks`:

```python
        self.assertIn("function renderLineageAtlasFallback(map)", app)
        self.assertIn("ResearchBrowserLineageAtlas.mount", app)
        self.assertIn("lineage-atlas-root", app)
```

Add this assertion to `test_lineage_page_exists_with_page_marker`:

```python
        self.assertIn("lineage-atlas.bundle.js", html)
        self.assertIn("lineage-atlas.bundle.css", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_app_contains_lineage_page_hooks tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_page_exists_with_page_marker -v
```

Expected: FAIL because page and app do not load/mount the island yet.

- [ ] **Step 3: Load atlas CSS and JS**

In `dashboard/lineage.html`, add CSS after `styles.css`:

```html
    <link rel="stylesheet" href="./lineage-atlas.bundle.css" />
```

Add script before `app.js`:

```html
    <script src="./lineage-atlas.bundle.js" defer></script>
    <script src="./app.js" defer></script>
```

- [ ] **Step 4: Add fallback renderer in `dashboard/app.js`**

Add above `renderLineagePage`:

```js
function renderLineageAtlasFallback(map) {
  const routes = Array.isArray(map?.routes) ? map.routes : [];
  const papers = Array.isArray(map?.papers) ? map.papers : [];
  return `
    <section class="lineage-atlas-fallback">
      <div class="section-head">
        <div>
          <p class="eyebrow">Lineage Atlas</p>
          <h2>${escapeHtml(map?.topic_name || map?.title || "Related Work")}</h2>
          <p class="section-note">Interactive atlas bundle unavailable. Showing compact route list.</p>
        </div>
      </div>
      <div class="lineage-lanes">
        ${routes.map((route) => {
          const routePapers = papers.filter((paper) => (paper.route || "unassigned") === route.id);
          return `
            <section class="lineage-lane">
              <header>
                <div>
                  <span>${escapeHtml(route.review_status || "candidate")}</span>
                  <h3>${escapeHtml(route.label || route.id || "Unnamed route")}</h3>
                </div>
                <small>${routePapers.length} papers</small>
              </header>
              <p>${escapeHtml(route.description || "No route description.")}</p>
            </section>
          `;
        }).join("")}
      </div>
    </section>
  `;
}
```

- [ ] **Step 5: Replace lineage body with island mount root**

In `renderLineagePage`, replace the long primary body after selected map with:

```js
  el.content.innerHTML = `
    <section class="section-block lineage-map-shell">
      <div id="lineage-atlas-root" class="lineage-atlas-root"></div>
    </section>
  `;
  const root = document.getElementById("lineage-atlas-root");
  if (window.ResearchBrowserLineageAtlas?.mount) {
    window.ResearchBrowserLineageAtlas.mount(root, { map: selectedMap, project });
  } else if (root) {
    root.innerHTML = renderLineageAtlasFallback(selectedMap);
  }
```

Keep `renderLineageGraph`, `renderLineageLanes`, `renderLineagePaperTable`, and safety helpers in `app.js` for fallback/tests until a later cleanup task removes or rewires tests.

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_app_contains_lineage_page_hooks tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_lineage_page_exists_with_page_marker -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add dashboard/lineage.html dashboard/app.js tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: mount lineage atlas island"
```

---

## Task 7: Polish Atlas Styling And Remove Report Feel

**Files:**
- Modify: `dashboard/lineage-atlas/src/lineage-atlas.css`
- Modify: `dashboard/styles.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing style tests**

Replace `test_styles_contain_lineage_selectors` with:

```python
    def test_styles_contain_lineage_atlas_selectors(self):
        atlas_css = (ROOT / "dashboard" / "lineage-atlas" / "src" / "lineage-atlas.css").read_text(encoding="utf-8")

        self.assertIn(".lineage-atlas-shell", atlas_css)
        self.assertIn(".lineage-atlas-topic-node", atlas_css)
        self.assertIn(".lineage-atlas-route-node", atlas_css)
        self.assertIn(".lineage-atlas-paper-node", atlas_css)
        self.assertIn(".lineage-atlas-inspector", atlas_css)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_styles_contain_lineage_atlas_selectors -v
```

Expected: FAIL until node styles are added.

- [ ] **Step 3: Add node and edge styles**

Append:

```css
.lineage-atlas-topic-node,
.lineage-atlas-route-node,
.lineage-atlas-paper-node {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--panel) 88%, #000 12%);
  color: var(--text);
  text-align: left;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.24);
}

.lineage-atlas-topic-node {
  width: 280px;
  padding: 22px;
  border-color: color-mix(in srgb, var(--accent) 64%, var(--border));
}

.lineage-atlas-topic-node span,
.lineage-atlas-route-node span,
.lineage-atlas-paper-node span {
  display: block;
  color: var(--muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.lineage-atlas-topic-node strong {
  display: block;
  margin-top: 6px;
  font-size: 1.45rem;
}

.lineage-atlas-topic-node em,
.lineage-atlas-route-node em,
.lineage-atlas-paper-node em {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-style: normal;
}

.lineage-atlas-route-node {
  width: 220px;
  padding: 16px;
  border-color: color-mix(in srgb, var(--route-color) 60%, var(--border));
}

.lineage-atlas-route-node strong {
  display: block;
  margin-top: 5px;
  font-size: 1rem;
}

.lineage-atlas-paper-node {
  width: 230px;
  padding: 13px;
  border-color: color-mix(in srgb, var(--route-color) 38%, var(--border));
}

.lineage-atlas-paper-node strong {
  display: block;
  margin-top: 5px;
  font-size: 0.92rem;
  line-height: 1.25;
}

.lineage-atlas-paper-node.is-baseline {
  border-width: 2px;
  border-color: var(--accent);
}

.lineage-atlas-route-node.is-selected,
.lineage-atlas-paper-node.is-selected {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.lineage-atlas-handle {
  opacity: 0;
}

.lineage-atlas-route-edge,
.lineage-atlas-paper-edge {
  opacity: 0.78;
}

.lineage-atlas-explicit-edge {
  stroke: var(--accent);
  stroke-width: 1.8;
  stroke-dasharray: 6 6;
}

.lineage-atlas-root {
  min-height: calc(100vh - 150px);
}
```

- [ ] **Step 4: Ensure old report sections do not dominate**

In `dashboard/styles.css`, keep existing `.lineage-*` fallback styles. Add a wrapper tweak:

```css
.lineage-map-shell:has(.lineage-atlas-root) {
  padding: 0;
  overflow: hidden;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_styles_contain_lineage_atlas_selectors -v
```

Expected: PASS.

- [ ] **Step 6: Build bundle**

Run:

```bash
cd dashboard && npm run build:lineage-atlas
```

Expected: build succeeds and CSS bundle updates.

- [ ] **Step 7: Commit**

```bash
git add dashboard/lineage-atlas/src/lineage-atlas.css dashboard/lineage-atlas.bundle.css dashboard/styles.css tests/test_related_work_lineage_dashboard.py
git commit -m "dashboard: style lineage atlas"
```

---

## Task 8: Verify End-To-End And Rebuild Demo Read Model

**Files:**
- Generated/ignored: `examples/workspaces/demo-visual-affordance/.dashboard/index.json`

- [ ] **Step 1: Rebuild demo dashboard index**

Run:

```bash
python3 tools/build_dashboard_index.py --repo examples/workspaces/demo-visual-affordance
```

Expected:

```text
Wrote .dashboard/index.json
Projects: 1 Papers: 7 Rounds: 1 Claims: 0 Lineage maps: 1
```

- [ ] **Step 2: Validate lineage artifact**

Run:

```bash
python3 tools/related_work_lineage_cli.py validate --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --json
```

Expected:

```json
{
  "edge_count": 15,
  "errors": [],
  "paper_count": 18,
  "route_count": 4,
  "valid": true
}
```

- [ ] **Step 3: Run dashboard lineage tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_cli tests.test_related_work_lineage_dashboard -v
```

Expected: all tests pass.

- [ ] **Step 4: Build lineage atlas bundle**

Run:

```bash
cd dashboard && npm run build:lineage-atlas
```

Expected: Vite build succeeds with no errors.

- [ ] **Step 5: Start current-source dashboard server**

Run:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces/demo-visual-affordance --host 127.0.0.1 --port 8767
```

Expected:

```text
Serving Research Browser at http://127.0.0.1:8767/
```

- [ ] **Step 6: Verify served index and JS**

Run:

```bash
curl -fsS http://127.0.0.1:8767/.dashboard/index.json | rg 'topic_name|route_count|paper_count|edge_count|rgb_object_part_grounding'
curl -fsS http://127.0.0.1:8767/dashboard/app.js | rg 'cache: "no-store"|ResearchBrowserLineageAtlas'
curl -fsS http://127.0.0.1:8767/dashboard/lineage-atlas.bundle.js | rg 'ResearchBrowserLineageAtlas|buildLineageAtlasModel'
```

Expected:

```text
"topic_name": "Visual Affordance Grounding"
"route_count": 4
"paper_count": 18
"edge_count": 15
rgb_object_part_grounding
cache: "no-store"
ResearchBrowserLineageAtlas
buildLineageAtlasModel
```

- [ ] **Step 7: Manual browser check**

Open:

```text
http://127.0.0.1:8767/dashboard/lineage.html?project=DemoVisualAffordance&round=demo-affordance-lineage
```

Expected:

- one atlas island fills the lineage page;
- center reads `Visual Affordance Grounding`;
- route and paper nodes render around center;
- right inspector shows topic overview by default;
- clicking a paper changes inspector to paper title and summary;
- old long report sections are absent from the primary page.

- [ ] **Step 8: Commit final verification updates if any source changed**

```bash
git status --short
git add dashboard/lineage-atlas.bundle.js dashboard/lineage-atlas.bundle.css
git commit -m "dashboard: build lineage atlas assets"
```

Skip the commit if the assets were already committed in prior tasks and no tracked files changed.

---

## Self-Review

Spec coverage:

- Topic-centered atlas: Task 1 and Task 4.
- Single React island page: Task 3 and Task 6.
- React Flow renderer: Task 3 and Task 4.
- Shallow model only: Task 4.
- Inspector: Task 5.
- Controls: Task 5.
- Metadata pass-through: Task 2.
- Fallback/error path: Task 6.
- Tests and validation: Tasks 2 through 8.

Intentional deferrals:

- Year range filter: optional later control from spec.
- Export image: optional later control from spec.
- Edge inspector: only explicit edge rendering is in MVP; right inspector can add edge selection later.

Placeholder scan:

- No `TBD`, `TODO`, or incomplete implementation steps are used.

Type consistency:

- Global mount object is `window.ResearchBrowserLineageAtlas`.
- Model builder is `buildLineageAtlasModel`.
- Node types are `topicNode`, `routeNode`, and `paperNode`.
- Demo topic field is `topic_name`.
