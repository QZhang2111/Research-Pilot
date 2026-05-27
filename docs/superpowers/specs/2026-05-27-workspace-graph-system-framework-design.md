# Workspace Graph System Framework Design

## 1. Executive Summary

Research Pilot's unified Workspace Island needs a graph system, not more one-off React Flow layout patches. This design defines a layered graph architecture for `Understanding`, `Literature`, and `Experiments`: database truth stays in `research-pilot.db`; backend read models expose semantic scenes with provenance; mode-specific projections decide which entities become anchors, frames, terminals, or portals; React Flow renders that projection through a shared visual grammar.

The goal is to make the dashboard explain research memory quickly and defensibly: what is true in the project, what is supporting evidence, what is experimental substrate, and what is only a view-derived grouping.

## 2. Problem Statement

The current Workspace Island is useful but not yet a finished graph product.

Problems:

- React Flow nodes and edges are built directly from mixed backend payloads and frontend heuristics.
- `Understanding`, `Literature`, and `Experiments` share a shell but not a coherent graph grammar.
- Frames, lanes, groups, terminal nodes, drill nodes, and cross-mode jumps are not defined as first-class concepts.
- Source of truth feels ambiguous because DB facts, derived groups, inspector state, and React Flow projection are mixed in one payload.
- The frontend can accidentally imply false semantics, for example by drawing visual lanes as if they were database facts or making terminal argument atoms behave like deeper layers.

The result is an MVP that can show data, but cannot yet guarantee that graph structure, visual grouping, and source provenance mean what the researcher expects.

## 3. Reference Architecture Lessons

Understand-Anything is a useful reference because it separates concerns cleanly:

- Stored graph data is the fact layer.
- Dashboard store owns navigation, selection, filters, and indexes.
- Containers and clusters are derived visual grouping, not source truth.
- Layout is staged: semantic grouping first, rendering projection second.
- React Flow receives stable custom node and edge types, not raw domain records.
- Visual state overlays such as search, focus, diff, and tour do not mutate graph truth.

Research Pilot should adopt the same separation, but with research-specific entities and modes.

References:

- `https://github.com/Lum1104/Understand-Anything`
- `understand-anything-plugin/packages/dashboard/src/components/GraphView.tsx`
- `understand-anything-plugin/packages/dashboard/src/store.ts`
- `understand-anything-plugin/packages/dashboard/src/utils/containers.ts`
- `understand-anything-plugin/packages/dashboard/src/utils/edgeAggregation.ts`

## 4. Product Direction

Workspace remains a read-only research map.

Mutation still happens through chat, CLI, agents, and human-gated dataset updates. The dashboard explains state and supports navigation. It does not edit claims, papers, experiments, runs, or graph links.

Mode hierarchy:

- `Understanding`: primary project truth surface.
- `Literature`: paper/source landscape that informs Understanding.
- `Experiments`: evaluation substrate and result records that may inform Understanding.

`Literature` and `Experiments` are not peer truth graphs beside `Understanding`; they are supporting modes with their own semantics and portals back to Understanding.

## 5. Goals

- Define a durable source-of-truth model for Workspace graph display.
- Define one shared visual grammar across all Workspace modes.
- Preserve mode-specific research semantics.
- Make derived grouping visibly different from factual relations.
- Make terminal nodes and drill nodes explicit.
- Make cross-mode jumps explicit portals, not accidental links.
- Reduce React Flow components to a rendering adapter.
- Create a contract that backend and frontend agents can implement without re-litigating graph semantics.

## 6. Non-Goals

- No new dashboard editing workflow.
- No replacement of `research-pilot.db`.
- No single mega-graph that merges all modes at once.
- No requirement to use Understand-Anything code directly.
- No new experiment execution system.
- No final pixel-perfect visual theme in this document.
- No immediate implementation plan; this document defines the system contract before implementation planning.

## 7. Layered Architecture

The graph system has four layers.

### 7.1 DB Truth Layer

The only persisted source of truth is `research-pilot.db`.

Primary tables:

- `understanding_nodes`
- `understanding_links`
- `understanding_link_endpoints`
- `sources`
- `literature_lanes`
- `literature_items`
- `literature_relations`
- `experiments`
- `experiment_runs`
- `experiment_metrics`
- `experiment_artifacts`
- `entity_links`
- `updates`, `activity_sessions`, `audit_events`

DB rows are facts or human/agent-recorded memory. The dashboard must not invent DB facts.

### 7.2 Semantic Scene Layer

Backend read models convert DB rows into a mode/layer scene.

A scene describes:

- canonical entities
- factual relations
- derived groups
- allowed interactions
- inspector payloads
- provenance for every entity, relation, and group

The scene does not contain React Flow node types, React Flow positions, CSS class names, or layout dimensions.

### 7.3 Projection Layer

Projection decides how a semantic scene becomes a graph view.

Projection answers:

- Which entity is the anchor?
- Which entities are visible on this layer?
- Which entities are terminal?
- Which entities can drill?
- Which derived groups become frames or containers?
- Which relations should be drawn, aggregated, hidden, or shown only in inspector?
- Which cross-mode portals are available?

Projection may be mode-specific. The projection contract is still shared.

### 7.4 React Flow Adapter Layer

The React Flow adapter converts projected view objects into `@xyflow/react` nodes and edges.

It owns:

- React Flow node type registration
- React Flow edge type registration
- handles
- layout algorithm invocation
- viewport behavior
- minimap / controls / background
- visual overlay state such as selected, hovered, dimmed

It must not decide domain truth.

## 8. Canonical IDs And Provenance

Every scene object must carry a stable canonical id and a source reference.

### 8.1 Canonical Entity IDs

Recommended ids:

```text
understanding:project:<project_id>:question:<local_id>
understanding:project:<project_id>:claim:<local_id>
understanding:project:<project_id>:evidence:<local_id>
understanding:project:<project_id>:warrant:<local_id>
understanding:project:<project_id>:limitation:<local_id>

source:<source_id>
literature:lane:<lane_id>
literature:item:<item_id>
literature:relation:<relation_id>

experiment:design:<experiment_id>
experiment:run:<run_id>
experiment:metric:<metric_id>
experiment:artifact:<artifact_id>

derived:evaluation_setting:<project_id>:<slug>
derived:group:<mode>:<layer>:<slug>
```

Short display ids such as `Q1`, `C2`, `E4`, `P3`, and `EXP1` remain labels, not canonical ids.

### 8.2 Source References

Each entity or relation carries:

```json
{
  "canonical_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "display_id": "C2",
  "source": {
    "kind": "db_row",
    "table": "understanding_nodes",
    "primary_key": "project:DemoVisualAffordance:C2"
  }
}
```

Derived groups carry derivation rules:

```json
{
  "canonical_id": "derived:evaluation_setting:DemoVisualAffordance:agd20k-kld-sim-nss",
  "source": {
    "kind": "derived",
    "rule": "benchmark_task + dataset + metric_family",
    "inputs": [
      {"table": "experiments", "primary_key": "EXP2"},
      {"table": "experiment_runs", "primary_key": "run:exp2:paper"}
    ]
  }
}
```

## 9. Semantic Scene Contract

Each Workspace layer endpoint returns a `WorkspaceScene`.

```ts
type WorkspaceMode = "understanding" | "literature" | "experiments";

type WorkspaceLayer =
  | "understanding.project_overview"
  | "understanding.claim_focus"
  | "understanding.paper_focus"
  | "literature.overview"
  | "literature.route_focus"
  | "literature.paper_focus"
  | "experiments.evaluation_overview"
  | "experiments.evaluation_setting_focus"
  | "experiments.experiment_design_focus";

type SceneObjectKind =
  | "entity"
  | "relation"
  | "derived_group"
  | "portal";
```

Required top-level fields:

```json
{
  "schema_version": "workspace-scene-v2",
  "project_id": "DemoVisualAffordance",
  "mode": "understanding",
  "layer": "understanding.claim_focus",
  "focus_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "source": "research-pilot.db",
  "entities": [],
  "relations": [],
  "groups": [],
  "portals": [],
  "inspector": {},
  "warnings": []
}
```

### 9.1 Entity Contract

```json
{
  "canonical_id": "understanding:project:DemoVisualAffordance:evidence:E1",
  "display_id": "E1",
  "entity_type": "evidence",
  "title": "Across probed VFMs, stronger geometric awareness aligns...",
  "summary": "",
  "status": "accepted",
  "confidence": "medium",
  "interaction": {
    "kind": "terminal",
    "inspector_id": "understanding:project:DemoVisualAffordance:evidence:E1"
  },
  "source": {
    "kind": "db_row",
    "table": "understanding_nodes",
    "primary_key": "project:DemoVisualAffordance:E1"
  },
  "metadata": {}
}
```

Interaction kinds:

- `drill`: enters another canvas layer.
- `inspect`: updates inspector only.
- `terminal`: may show inspector, but cannot create a deeper layer.
- `portal`: jumps to another mode/layer.
- `none`: visual-only label or group member.

### 9.2 Relation Contract

```json
{
  "canonical_id": "relation:project:DemoVisualAffordance:RL4",
  "relation_type": "supports",
  "source_id": "understanding:project:DemoVisualAffordance:evidence:E1",
  "target_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "direction": "forward",
  "weight": 1,
  "source": {
    "kind": "db_row",
    "table": "understanding_links",
    "primary_key": "project:DemoVisualAffordance:RL4"
  }
}
```

Relation types should be limited and mode-aware:

- Understanding: `answers`, `supports`, `qualifies`, `bounds`, `cites`, `translates_to`
- Literature: `route_contains`, `builds_on`, `contrasts`, `extends`, `uses_benchmark`, `positions`
- Experiments: `defines`, `uses_dataset`, `uses_benchmark`, `measures_with`, `has_design`, `has_run`, `reports_metric`, `impacts`
- Cross-mode: `source_of`, `informs`, `evaluates`, `impacts_understanding`

### 9.3 Group Contract

Groups are derived view objects.

```json
{
  "canonical_id": "derived:group:understanding.claim_focus:evidence",
  "group_type": "lane",
  "title": "Evidence / Grounds",
  "member_ids": [
    "understanding:project:DemoVisualAffordance:evidence:E1",
    "understanding:project:DemoVisualAffordance:evidence:E2"
  ],
  "visual_role": "frame",
  "source": {
    "kind": "derived",
    "rule": "entity_type == evidence for focused claim C2",
    "inputs": [
      "understanding:project:DemoVisualAffordance:claim:C2"
    ]
  }
}
```

Groups never become factual edges by themselves.

### 9.4 Portal Contract

```json
{
  "canonical_id": "portal:claim:C2:experiments",
  "title": "View related experiment results",
  "from_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "target": {
    "mode": "experiments",
    "layer": "experiments.evaluation_overview",
    "filter": {
      "impacts": "understanding:project:DemoVisualAffordance:claim:C2"
    }
  },
  "source": {
    "kind": "derived",
    "rule": "entity_links from experiment runs to understanding node"
  }
}
```

## 10. Shared Visual Grammar

The UI needs a common grammar across modes.

### 10.1 Anchor

Anchor is the current focus object.

Examples:

- selected claim in Claim Focus
- selected route in Literature Route Focus
- selected evaluation setting in Evaluation Setting Focus
- selected experiment design in Experiment Design Focus

Rules:

- one primary anchor per focus layer
- largest visual weight
- inspector defaults to anchor detail
- anchor can have portals

### 10.2 Entity Node

Entity node represents a DB-backed or canonical semantic entity.

Examples:

- question
- claim
- paper/source
- literature route
- evaluation setting
- experiment design
- run

Rules:

- can be `drill`, `inspect`, `terminal`, or `portal`
- must show display id and title
- should show status only if status affects research interpretation

### 10.3 Terminal Atom

Terminal atom is the last graph-level knowledge unit in the current hierarchy.

Examples:

- evidence
- warrant
- limitation
- metric value
- artifact
- run in first MVP

Rules:

- no new canvas layer
- no fake breadcrumb
- optional inspector
- visually lower weight than anchor

### 10.4 Frame / Lane / Container

Frame is visual grouping.

Examples:

- Questions frame
- Claims frame
- Evidence lane
- Warrants lane
- Limitations lane
- Dataset / Benchmark / Metric frame

Rules:

- derived object only
- not clickable by default
- no factual relation implied
- must have `source.kind = derived`

### 10.5 Portal Node / Portal Action

Portal is explicit cross-mode navigation.

Examples:

- claim to experiments
- source paper to literature paper focus
- run result to impacted Understanding claim
- literature paper to Paper detail page

Rules:

- portal should look different from factual entity
- target must be typed
- missing target should not render as active portal

### 10.6 Edge

Edges represent factual or interpreted relations, not layout grouping.

Rules:

- relation type controls color and dash style
- edge labels should be sparse
- dense edges should aggregate
- frame membership should not be drawn as edges unless the membership itself is a semantic relation

## 11. Mode And Layer Registry

Each mode/layer must declare its expected objects.

### 11.1 Understanding

`understanding.project_overview`

- Entities: questions, claims
- Groups: Questions frame, Claims frame
- Relations: `answers`, claim-to-claim `supports` if useful
- Default inspector: question list
- Question interaction: `inspect`
- Claim interaction: `drill -> understanding.claim_focus`

`understanding.claim_focus`

- Anchor: one claim
- Entity nodes: source papers
- Terminal atoms: evidence, warrant, limitation
- Optional inspector-only entities: supporting claims, related claims
- Groups: Evidence lane, Warrants lane, Limitations lane, Source Papers lane
- Relations: `supports`, `qualifies`, `bounds`, `cites`
- Source paper interaction: `drill -> understanding.paper_focus` or `portal -> literature.paper_focus`, depending available data

`understanding.paper_focus`

- Anchor: project claim
- Entities: paper nodes with paper-scope question/claim/evidence/warrant/limitation
- Groups: paper argument lanes and translation bridge
- Relations: paper argument links, translation links
- Inspector: paper node detail or paper overview

### 11.2 Literature

`literature.overview`

- Anchor: topic/project literature map
- Entities: literature lanes/routes, readable paper/source nodes
- Groups: route lanes or field-position clusters
- Relations: paper lineage relations
- Route interaction: `drill -> literature.route_focus`
- Paper interaction: `drill -> literature.paper_focus`

`literature.route_focus`

- Anchor: selected route
- Entities: route papers
- Groups: timeline or method-family grouping
- Relations: route sequence and explicit literature relations
- Inspector: route explanation and papers

`literature.paper_focus`

- Anchor: selected source paper
- Entities: source metadata, optional paper understanding nodes
- Groups: optional paper argument group
- Portals: Paper detail page, Understanding nodes if linked

### 11.3 Experiments

`experiments.evaluation_overview`

- Entities: evaluation settings only
- Derived group rule: benchmark/task + dataset + metric family
- Relations: none by default, unless setting dependencies become explicit
- Default inspector: evaluation setting list
- Setting interaction: `drill -> experiments.evaluation_setting_focus`

`experiments.evaluation_setting_focus`

- Anchor: selected evaluation setting
- Entities: dataset, benchmark/task, metric family, experiment designs
- Groups: evaluation substrate frame, experiment design frame
- Relations: `uses_dataset`, `uses_benchmark`, `measures_with`, `has_design`
- Experiment design interaction: `drill -> experiments.experiment_design_focus`
- Runs do not appear here

`experiments.experiment_design_focus`

- Anchor: selected experiment design
- Entities: protocol blocks, model/method nodes, baseline nodes, planned metric summary, run nodes
- Groups: Protocol, Models/Baselines, Runs, Interpretation Links
- Relations: `has_run`, `reports_metric`, `impacts`
- Run interaction: `terminal inspect`
- Project Understanding Impact appears in inspector and portals, not as the primary layout driver

## 12. Inspector Contract

Inspector is not a dump of raw DB state.

Each inspector should declare:

```json
{
  "kind": "claim_detail",
  "subject_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "title": "C2",
  "summary": "Part-level geometric structure...",
  "sections": [],
  "portals": []
}
```

Section rules:

- Overview inspectors stay light.
- Detail inspectors contain rich knowledge.
- Terminal inspectors can be rich, but do not create breadcrumbs.
- Debug state such as raw review status belongs in collapsible provenance only, not primary copy.
- Long inspector content must scroll independently from canvas.

## 13. Frontend Architecture

Recommended module split:

```text
dashboard/workspace-island/src/
  WorkspaceIslandApp.jsx
  graph-system/
    sceneTypes.js
    modeRegistry.js
    projection/
      understandingProjection.js
      literatureProjection.js
      experimentsProjection.js
    render/
      ReactFlowCanvas.jsx
      nodeTypes.jsx
      edgeTypes.jsx
      visualGrammar.js
      layout.js
    inspector/
      WorkspaceInspector.jsx
```

Responsibilities:

- `WorkspaceIslandApp`: shell only.
- `modeRegistry`: legal modes/layers and interaction rules.
- `projection/*`: scene to projected graph.
- `render/*`: projected graph to React Flow.
- `visualGrammar`: color, shape, weight, edge style tokens.
- `inspector/*`: inspector rendering.

React Flow rules:

- import from `@xyflow/react`
- stable `nodeTypes` and `edgeTypes`
- explicit canvas height
- custom nodes for all graph objects
- hidden handles use opacity/visibility, not `display: none`
- terminal nodes cannot call layer navigation
- scrollable inspector uses `nowheel` where embedded inside React Flow; external inspector uses normal scroll

## 14. Backend Architecture

Recommended module split:

```text
tools/
  workspace_graph_read_models.py
  workspace_scene_contract.py
  workspace_scene_builders/
    understanding_scene.py
    literature_scene.py
    experiments_scene.py
    provenance.py
```

Responsibilities:

- read DB rows
- normalize canonical ids
- emit scene entities/relations/groups/portals
- include provenance
- avoid React Flow layout details
- keep existing `/api/workspace-graph` as compatibility wrapper during migration

Compatibility path:

1. Add `workspace-scene-v2` endpoint or optional response flag.
2. Keep current `workspace-graph-v1` until frontend migration.
3. Add tests that compare v2 scene provenance to DB rows.
4. Retire v1 only after all modes render from v2.

## 15. Source Of Truth Rules

Hard rules:

- DB rows are facts.
- Derived groups must say they are derived.
- React Flow nodes are render objects, not source objects.
- Inspector summaries may synthesize, but must carry subject ids and provenance.
- Cross-mode portals are navigation affordances, not evidence claims.
- Experiments do not prove claims by default; they record substrate and results, then link interpreted impact separately.
- Literature remains paper/source lineage, not project truth.
- Understanding remains current project truth.

## 16. Testing Strategy

Backend tests:

- canonical ids are stable and typed
- every entity has provenance
- every relation endpoint exists in scene or is intentionally external
- every derived group has rule and inputs
- mode/layer registry rejects invalid layer
- terminal objects do not return drill targets

Frontend source tests:

- React Flow adapter does not inspect DB fields directly
- terminal node component cannot call `onNavigate`
- mode projections are separate modules
- frame nodes are non-draggable, non-selectable by default
- top-level mode breadcrumbs remain siblings

Browser tests:

- Understanding overview shows question/claim frames
- Claim focus shows one claim anchor and E/W/L/source lanes
- Literature overview readable paper nodes
- Experiments overview shows evaluation settings only
- Inspector scroll does not resize canvas
- Run click updates inspector, no breadcrumb layer

## 17. Migration Plan Shape

This is not the implementation plan, but expected sequence:

1. Add scene contract types and backend scene builders beside current read model.
2. Add frontend projection modules that consume v2 scenes.
3. Move current Understanding projection into `understandingProjection`.
4. Move Literature and Experiments into their own projection modules.
5. Replace generic node/edge fallback with shared visual grammar.
6. Add provenance-aware inspector.
7. Deprecate v1 payload once all mode screenshots match or improve current behavior.

## 18. Open Questions

- Whether `/api/workspace-graph` should become v2 by default or expose `?schema=scene-v2`.
- Whether canonical ids should include `project_id` for all source objects or keep `source:<source_id>` globally stable.
- Whether `entity_links` is sufficient for cross-mode impact links, or backend needs a dedicated read-model helper.
- Whether paper focus belongs under Understanding only, or should be accessible as a shared source/paper scene.
- Whether frontend state should stay local React state or move to a small Zustand store like Understand-Anything.

## 19. Acceptance Criteria

The system framework is ready for implementation when:

- Product, backend, and frontend agents agree on scene object meanings.
- A frontend node frame cannot be confused with a DB fact.
- Every visible entity can trace back to DB or a derived rule.
- Every drill/terminal/portal interaction is explicit in data.
- Understanding, Literature, and Experiments each have declared mode/layer object contracts.
- React Flow adapter can be replaced without changing semantic scene builders.

