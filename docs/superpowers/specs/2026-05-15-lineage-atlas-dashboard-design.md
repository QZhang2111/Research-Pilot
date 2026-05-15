# Lineage Atlas Dashboard Design

Date: 2026-05-15
Status: Draft

## Context

Research Pilot has a related-work lineage artifact under each literature round:

```text
wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json
wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.md
```

The JSON artifact is paper-only related-work structure, not Project Understanding Graph truth. The dashboard currently renders it as a long page: summary facts, a swimlane timeline, route cards, edge list, and a paper table. This is accurate but too report-like and visually noisy. Future users will bring their own related-work organization, so the page should feel like a general-purpose literature atlas, not a visual-affordance-specific report.

## Goal

Replace the current lineage page with a single interactive React island that presents a topic-centered related-work atlas.

The first view should communicate the field map in one screen:

- one central topic node;
- one layer of route branches;
- paper nodes attached to route branches;
- a right inspector that explains the selected paper, route, or map;
- compact controls for search, filtering, edge visibility, and fit/reset.

## Non-Goals

- Do not write lineage data into the Project Understanding Graph.
- Do not add approve/edit/mutation controls to the dashboard.
- Do not reuse Toulmin/GSN graph semantics for lineage papers.
- Do not keep the current long report layout as the primary experience.
- Do not make the demo-specific visual affordance taxonomy a hard-coded renderer behavior.
- Do not require every lineage map to have a baseline paper.

## Product Shape

### Page Model

The lineage page becomes a full-screen atlas surface:

```text
top control bar
  search
  route filter
  status filter
  edge toggle
  fit/reset

main canvas
  center topic node
  route branches
  paper nodes
  optional explicit edges

right inspector
  selected route / selected paper / map overview
```

The existing tab navigation remains. The lineage page content area should be one island, not several stacked dashboard sections.

### Center Topic

The center should be the field/topic name, not a project graph node.

Data priority:

1. `map.topic_name`
2. `map.display.topic_name`
3. cleaned map title
4. project title

The demo lineage should add:

```json
"topic_name": "Visual Affordance Grounding"
```

Future users can set topic names explicitly. If absent, the dashboard should still render.

### Route Branches

Each route becomes one branch from the center.

Routes are one layer only:

```text
Topic -> Route -> Papers
```

No nested argument layers. No premise/warrant/evidence layout. Route branches should be visually distinct with stable colors and labels.

Route placement:

- distribute routes around the center in a radial or organic layout;
- keep route labels outside the center collision zone;
- sort routes in artifact order, not alphabetically;
- cap visible routes gracefully for dense maps by shrinking label emphasis rather than hiding data.

### Paper Nodes

Paper nodes attach to their route branch and are ordered by date.

Node display:

- short title;
- year or year-month;
- optional role/status marker;
- baseline node visually emphasized if `roles` includes `baseline`.

Long text does not appear on the canvas. It belongs in the inspector.

### Inspector

Right inspector states:

Map overview:

- topic name;
- title;
- status;
- route count, paper count, edge count;
- baseline paper if present;
- boundary: paper-only, not graph truth.

Route selected:

- route label;
- route description;
- review status;
- paper count;
- representative paper list.

Paper selected:

- title;
- year/month;
- route;
- roles;
- 2-3 line summary;
- source URL;
- source evidence collapsed by default.

Edge selected, if edge interaction is implemented:

- source paper;
- target paper;
- relation;
- rationale;
- confidence.

### Controls

MVP controls:

- search by paper title, route label, role, summary;
- route filter;
- status filter;
- show/hide explicit edges;
- fit/reset viewport.

Optional later controls:

- year range;
- artifact type filter;
- export image.

## Architecture

### React Island

Create a dedicated lineage island instead of extending the project graph island:

```text
dashboard/lineage-atlas.bundle.js
window.ResearchBrowserLineageAtlas.mount(container, { map, project })
```

`dashboard/app.js` remains responsible for:

- loading `.dashboard/index.json`;
- selecting the project and lineage map;
- passing map payload to the island;
- rendering a small fallback if the island bundle fails.

The island owns:

- layout model;
- canvas render;
- selection state;
- controls;
- inspector.

### Why Not Reuse GSN/Toulmin Internals

Project graph rendering and lineage atlas rendering can share implementation ideas, but not the same semantic model.

Project graph:

- question / claim / evidence / warrant / limitation;
- graph truth and delta maintenance context;
- multi-layer reasoning drilldown.

Lineage atlas:

- topic / route / paper / edge;
- paper-only related-work artifact;
- one-layer field map.

Reusing Toulmin internals would make the page harder to reason about and easier to mislabel as graph truth.

### Renderer Choice

Preferred MVP renderer: React Flow.

Reasons:

- the project page already ships a React Flow island pattern, so dashboard integration risk is lower;
- zoom, pan, fit-view, minimap, node focus, and edge rendering are solved product patterns;
- lineage can reuse the existing island infrastructure without reusing the GSN/Toulmin data model;
- a simpler lineage graph model can still render as React Flow nodes and edges.

The design should reuse React Flow as the canvas/runtime, but keep lineage semantics shallow:

```text
topic node
route nodes
paper nodes
explicit relationship edges
```

Do not import the project graph's argument-layer builders. Build a separate lineage model that outputs ordinary React Flow nodes and edges.

### Data Flow

```text
related-work-lineage.json
  -> tools/build_dashboard_index.py
  -> .dashboard/index.json lineage_maps[]
  -> dashboard/app.js selectedMap
  -> ResearchBrowserLineageAtlas.mount()
  -> atlas layout + inspector
```

`build_dashboard_index.py` should pass through:

- `topic_name`;
- `baseline_paper_field_scope`;
- `axis_candidates`;
- `survey_catalog`;
- `major_trends`;
- `notable_forks`;
- `timeline_tracks`;
- `search_log`;
- `display`, if present.

The current index only passes routes, papers, explicit edges, and positioning note. The atlas needs enough metadata for map overview and inspector.

## Layout Algorithm

MVP deterministic layout:

1. Place topic node at center.
2. Split route nodes around the topic in a broad radial layout.
3. Sort route papers by `year`, `month`, title.
4. Place paper nodes outward from each route node, one shallow branch per route.
5. Create light route edges from topic to routes and route-to-paper edges.
6. Draw explicit paper-to-paper edges only when the edge toggle is enabled.
7. Use React Flow fit-view after mount and after filter changes.

The algorithm must be deterministic so screenshots and tests are stable.

Dense maps:

- max paper count already validates at 20 for lineage artifacts;
- route count can fit 4-8 branches;
- if paper labels collide, shrink paper cards and leave full title in tooltip/inspector.

## Visual Direction

Use an atlas / research map visual language.

Default dark dashboard shell remains. The atlas canvas can be a high-contrast dark map or a light paper-canvas panel depending on theme. The first implementation should fit the current dashboard without redesigning the whole product.

Design rules:

- route colors are muted and stable;
- center topic is visually dominant;
- selected node has clear outline and inspector sync;
- labels do not overlap controls or inspector;
- long summaries never appear directly on the canvas;
- table-like source audit is hidden behind inspector or collapsible panel.

## Accessibility

The island must support:

- keyboard focus for paper and route nodes;
- visible focus state;
- inspector updates announced through normal DOM text;
- text alternatives for node labels;
- controls as real buttons/inputs.

The canvas can be SVG, but interactive elements should be reachable.

## Error Handling

If no lineage map exists:

- show the existing empty lineage message.

If the island bundle fails:

- render compact fallback with route list and paper list.

If map validation fails:

- show validation errors before the atlas.

If topic name is missing:

- use cleaned title fallback.

If a paper lacks route:

- render under an `Unassigned` branch.

## Testing

Add or update tests for:

- lineage page loads island bundle hook;
- `app.js` calls `ResearchBrowserLineageAtlas.mount` when available;
- fallback renders when island is unavailable;
- dashboard index passes through `topic_name` and field-scope metadata;
- atlas model creates deterministic one-layer React Flow nodes and edges;
- lineage atlas does not import or call GSN/Toulmin project graph model builders;
- old route table/page sections are not the primary lineage render;
- demo lineage validates and includes `topic_name`;
- no-store fetch remains for `.dashboard/index.json`.

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_cli tests.test_related_work_lineage_dashboard -v
python3 tools/related_work_lineage_cli.py validate --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --json
```

If bundling uses Node tooling, add the relevant build/test command to the implementation plan.

## Rollout

1. Add `topic_name` to demo lineage JSON.
2. Pass more lineage metadata through dashboard index.
3. Add lineage atlas island bundle and mount hook.
4. Replace current lineage body with island mount + fallback.
5. Add tests.
6. Rebuild demo dashboard index.
7. Verify in browser at the active local dashboard port.

## Open Decisions

1. Whether to use custom SVG or React Flow.

Decision: use React Flow for MVP because the project already has an island implementation path and the lineage model can remain shallow.

2. Whether the atlas canvas should be dark or light by default.

Recommended: match dashboard theme first; add polished light paper-canvas later if needed.

3. Whether source audit should remain visible.

Recommended: move source audit into inspector/collapsible details, not primary page.

4. Whether explicit edges are shown by default.

Recommended: hidden by default; user toggles on.
