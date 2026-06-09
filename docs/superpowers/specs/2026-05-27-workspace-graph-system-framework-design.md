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
- semantic capabilities
- inspector payloads
- provenance for every entity, relation, group, and portal

The scene does not contain React Flow node types, React Flow positions, CSS class names, or layout dimensions.

The scene also does not decide concrete click behavior. It may say an entity is capable of inspection, drill, portal navigation, or no interaction. The projection layer decides which capability is active in a specific mode/layer.

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
- Which concrete interaction each projected object receives?

Projection may be mode-specific. The projection contract is still shared.

Projection is the boundary between domain meaning and UI behavior. It consumes scene capabilities and mode registry rules, then emits concrete projected interactions such as `inspect`, `drill`, `portal`, or `none`.

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

Required id shapes:

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

derived:evaluation_arena:<project_id>:<slug>
derived:group:<mode>:<layer>:<slug>
```

Short display ids such as `Q1`, `C2`, `E4`, `P3`, and `EXP1` remain labels, not canonical ids.

Source papers use `source:<source_id>` globally.

Reason: `sources.source_id` is already the canonical paper/source identity in `research-pilot.db`. Project-specific meaning belongs in links, positionings, summaries, and inspector context, not in the source id itself.

Examples:

```text
source:zhang2026-geometry-interaction-vfm
source:do2017-affordancenet
```

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
  "canonical_id": "derived:evaluation_arena:DemoVisualAffordance:agd20k-kld-sim-nss",
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
  | "experiments.evaluation_arena_focus"
  | "experiments.experiment_design_focus";

type SceneObjectKind =
  | "entity"
  | "relation"
  | "derived_group"
  | "portal";
```

`entity` may be DB-backed or derived. Derivation is expressed in `source.kind`, not by inventing a separate untyped frontend object.

### 9.1 Layer Name Compatibility

The v2 layer names are semantic names. The current v1 endpoint uses shorter names. During migration, the compatibility wrapper must map them explicitly.

| v1 mode | v1 layer | v2 layer |
| --- | --- | --- |
| `understanding` | `project_overview` | `understanding.project_overview` |
| `understanding` | `claim_focus` | `understanding.claim_focus` |
| `understanding` | `paper_focus` | `understanding.paper_focus` |
| `literature` | `literature_overview` | `literature.overview` |
| `literature` | `literature_route_focus` | `literature.route_focus` |
| `literature` | `literature_paper_focus` | `literature.paper_focus` |
| `experiments` | `evaluation_overview` | `experiments.evaluation_overview` |
| `experiments` | `evaluation_arena_focus` | `experiments.evaluation_arena_focus` |
| `experiments` | `evaluation_setting_focus` | `experiments.evaluation_arena_focus` |
| `experiments` | `experiment_design_focus` | `experiments.experiment_design_focus` |

Compatibility rule: the UI may keep URL/query names while the new internal graph system uses v2 names. The adapter owns the mapping. Scene builders should emit v2 names only.

Source id compatibility:

| v1 source id | v2 canonical id |
| --- | --- |
| `source:paper:<source_id>` | `source:<source_id>` |

The adapter must normalize old `source:paper:*` ids before comparing focus ids, relation endpoints, or inspector subjects.

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

### 9.2 Entity Contract

```json
{
  "canonical_id": "understanding:project:DemoVisualAffordance:evidence:E1",
  "display_id": "E1",
  "entity_type": "evidence",
  "title": "Across probed VFMs, stronger geometric awareness aligns...",
  "summary": "",
  "status": "accepted",
  "confidence": "medium",
  "capabilities": ["inspectable"],
  "source": {
    "kind": "db_row",
    "table": "understanding_nodes",
    "primary_key": "project:DemoVisualAffordance:E1"
  },
  "metadata": {}
}
```

Capability kinds:

- `inspectable`: scene has enough detail for inspector.
- `drillable`: scene can support a deeper semantic layer.
- `portalable`: scene can support a cross-mode or page target.
- `none`: visual-only label or group member.

Capabilities are semantic permissions, not concrete UI behavior. Projection maps them into projected interactions.

### 9.3 Relation Contract

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

Scene relations are semantic relations. They are not layout lines. If several relations become one visible line, that aggregation happens in the projection layer and must retain member relation ids.

### 9.4 Group Contract

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

### 9.5 Derived Entity Contract

Some visible objects are not single DB rows but still need stable ids and provenance. They must be emitted as derived entities, not as untyped frontend cards.

Examples:

- evaluation arena: coherent evaluation objective from dataset, benchmark/task, metric family, and experiment rows
- experiment protocol block: selected protocol fields from `experiments.metadata_json`
- model or baseline block: model/baseline fields from `experiments.metadata_json` or linked artifacts
- planned metric summary: declared metric fields before run results exist
- literature topic anchor: project + literature lanes + project positionings

Contract:

```json
{
  "canonical_id": "derived:evaluation_arena:DemoVisualAffordance:agd20k-affordance-localization",
  "display_id": "evaluation_arena:agd20k_affordance_localization",
  "entity_type": "evaluation_arena",
  "title": "AGD20K Affordance Localization",
  "summary": "Verb-conditioned attention, geometry fusion, heatmap metrics, and qualitative localization evidence.",
  "capabilities": ["inspectable", "drillable"],
  "source": {
    "kind": "derived",
    "rule": "coherent evaluation objective from experiment metadata, datasets, benchmark tasks, metric families, and runs",
    "inputs": [
      {"table": "experiments", "primary_key": "EXP1"},
      {"table": "experiment_runs", "primary_key": "run:exp1:paper"},
      {"table": "experiment_metrics", "primary_key": "metric:exp1:umd-miou"}
    ]
  },
  "metadata": {
    "derived_from": "experiment_substrate"
  }
}
```

Derived entities must not pretend to be DB rows. Inspector copy must label them as derived when provenance is shown.

### 9.6 Portal Contract

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

## 10. Projected Graph Contract

Projection consumes `WorkspaceScene` plus `modeRegistry`, then emits `ProjectedGraph`.

`ProjectedGraph` is the only data shape the React Flow adapter may render.

```ts
type ProjectedGraph = {
  schema_version: "workspace-projection-v1";
  project_id: string;
  mode: WorkspaceMode;
  layer: WorkspaceLayer;
  focus_id?: string;
  breadcrumb: ProjectedBreadcrumbItem[];
  nodes: ProjectedNode[];
  edges: ProjectedEdge[];
  frames: ProjectedFrame[];
  portals: ProjectedPortal[];
  inspector_default_id?: string;
  layout: ProjectedLayoutSpec;
  warnings: string[];
};

type ProjectedNodeRole =
  | "anchor"
  | "entity"
  | "terminal"
  | "portal";

type ProjectedInteractionKind =
  | "none"
  | "inspect"
  | "drill"
  | "portal";
```

### 10.1 Projected Node

```json
{
  "projected_id": "node:understanding:claim:C2:evidence:E1",
  "semantic_id": "understanding:project:DemoVisualAffordance:evidence:E1",
  "role": "terminal",
  "visual_kind": "evidence",
  "title": "Across probed VFMs, stronger geometric awareness aligns...",
  "display_id": "E1",
  "interaction": {
    "kind": "inspect",
    "inspector_id": "understanding:project:DemoVisualAffordance:evidence:E1"
  },
  "source": {
    "kind": "db_row",
    "table": "understanding_nodes",
    "primary_key": "project:DemoVisualAffordance:E1"
  },
  "layout_hints": {
    "lane": "evidence",
    "rank": 1
  }
}
```

Rules:

- `terminal` is a node role, not an interaction kind.
- `inspect` means click changes inspector only.
- `drill` means click enters another canvas layer.
- `portal` means click jumps mode/page through a typed target.
- terminal nodes may use `inspect` or `none`; terminal nodes must not use `drill`.
- projected nodes carry source/provenance copied from the scene object or derived rule.

### 10.2 Projected Edge

```json
{
  "projected_id": "edge:aggregate:C2:evidence",
  "relation_type": "supports",
  "source_id": "understanding:project:DemoVisualAffordance:evidence:E1",
  "target_id": "understanding:project:DemoVisualAffordance:claim:C2",
  "label": "3 supports",
  "member_relation_ids": [
    "relation:project:DemoVisualAffordance:RL4",
    "relation:project:DemoVisualAffordance:RL5",
    "relation:project:DemoVisualAffordance:RL6"
  ],
  "aggregation": {
    "kind": "same_relation_type_same_target",
    "count": 3,
    "relation_types": ["supports"]
  },
  "source": {
    "kind": "derived",
    "rule": "aggregate supports edges from evidence lane to focused claim",
    "inputs": [
      "relation:project:DemoVisualAffordance:RL4",
      "relation:project:DemoVisualAffordance:RL5",
      "relation:project:DemoVisualAffordance:RL6"
    ]
  }
}
```

Rules:

- Factual one-to-one projected edges keep exactly one `member_relation_id`.
- Aggregated projected edges must include all member relation ids and an aggregation rule.
- Frame membership is not a projected edge unless the underlying scene relation is semantic.
- Layout helper lines must use a non-semantic `visual_connector` type and must not enter inspector as evidence.

### 10.3 Projected Frame

```json
{
  "projected_id": "frame:understanding.claim_focus:evidence",
  "semantic_id": "derived:group:understanding.claim_focus:evidence",
  "frame_kind": "lane",
  "title": "Evidence / Grounds",
  "member_node_ids": [
    "node:understanding:claim:C2:evidence:E1",
    "node:understanding:claim:C2:evidence:E2"
  ],
  "interaction": {"kind": "none"},
  "source": {
    "kind": "derived",
    "rule": "entity_type == evidence for focused claim C2"
  }
}
```

Frame kinds:

- `frame`: static visual boundary around related nodes.
- `lane`: ordered visual bucket with semantic type ordering.
- `container`: collapsible/nestable grouping for dense scenes.

Rules:

- frames are projected view objects, not DB facts.
- frames default to non-clickable.
- containers may collapse/expand in frontend state without mutating scene truth.
- lanes define reading order; lanes do not imply factual relation.

### 10.4 Projected Portal

```json
{
  "projected_id": "portal:claim:C2:experiments",
  "from_node_id": "node:understanding:claim:C2",
  "label": "View related experiment results",
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

Portals are navigation affordances. They do not assert support, proof, or contradiction unless a separate semantic relation exists.

## 11. Shared Visual Grammar

The UI needs a common grammar across modes.

### 11.1 Anchor

Anchor is the current focus object.

Examples:

- selected claim in Claim Focus
- selected route in Literature Route Focus
- selected evaluation arena in Evaluation Arena Focus
- selected experiment design in Experiment Design Focus

Rules:

- one primary anchor per focus layer
- largest visual weight
- inspector defaults to anchor detail
- anchor can have portals

### 11.2 Entity Node

Entity node represents a DB-backed or canonical semantic entity.

Examples:

- question
- claim
- paper/source
- literature route
- evaluation arena
- experiment design
- run

Rules:

- projected interaction can be `drill`, `inspect`, `portal`, or `none`
- must show display id and title
- should show status only if status affects research interpretation

### 11.3 Terminal Atom

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

### 11.4 Frame / Lane / Container

Frame, lane, and container are related but distinct projected view objects.

Examples:

- Questions frame
- Claims frame
- Evidence lane
- Warrants lane
- Limitations lane
- Dataset / Benchmark / Metric frame

Rules:

- Frame: static visual boundary around related nodes.
- Lane: ordered visual bucket with semantic type ordering.
- Container: collapsible or nested grouping for dense scenes.
- All three are derived objects only.
- All three are non-clickable by default.
- None implies a factual relation.
- All three must have `source.kind = derived`.

### 11.5 Portal Node / Portal Action

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

### 11.6 Edge

Edges represent factual or interpreted relations, not layout grouping.

Rules:

- relation type controls color and dash style
- edge labels should be sparse
- dense edges should aggregate
- frame membership should not be drawn as edges unless the membership itself is a semantic relation

## 12. Mode And Layer Registry

Each mode/layer must declare its expected objects.

### 12.1 Understanding

`understanding.project_overview`

- Entities: questions, claims
- Groups: Questions frame, Claims frame
- Relations: `answers`, claim-to-claim `supports` if useful
- Default inspector: question list
- Projected question interaction: `inspect`
- Projected claim interaction: `drill -> understanding.claim_focus`

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph shows only project question nodes and project claim nodes.
- Question and claim nodes live in separate visual frames.
- Inspector shows only the project question list.
- Inspector does not show Recent Understanding, raw IDs, debug metrics, or paper/experiment detail.
- Clicking a question does not leave Understanding mode.
- Clicking a question updates the canvas focus to that question and its linked claims.
- Clicking a question updates inspector to the selected question and linked claims.
- Question focus remains a shallow inspection state, not a new deep drill layer.
- Claim evidence, warrants, limitations, papers, and experiments stay hidden until claim focus or paper focus.

`understanding.claim_focus`

- Anchor: one claim
- Entity nodes: source papers
- Terminal atoms: evidence, warrant, limitation
- Optional inspector-only entities: supporting claims, related claims
- Groups: Evidence lane, Warrants lane, Limitations lane, Source Papers lane
- Relations: `supports`, `qualifies`, `bounds`, `cites`
- Projected source paper interaction: `drill -> understanding.paper_focus` or `portal -> literature.paper_focus`, depending available data

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph centers one selected project claim as anchor.
- Graph does not show unrelated project claims as active content.
- Evidence, warrants, limitations, and source papers are separated into visible frames.
- Evidence/grounds frame contains evidence atoms.
- Warrants/bridges frame contains warrant atoms.
- Limitations/boundaries frame contains limitation atoms.
- Source papers frame contains paper/source terminal or portal nodes.
- Edge density is acceptable when it explains how atom/source relations support, qualify, bound, or cite the selected claim.
- Default claim inspector shows rich claim detail and all surrounding evidence, warrants, limitations, and source papers.
- Clicking an evidence, warrant, or limitation atom updates inspector only.
- Atom click does not create another breadcrumb layer and does not drill deeper.
- Atom inspector can show atom text, source refs, and related source papers.
- Evidence, warrant, and limitation atoms are terminal nodes unless they point to a concrete paper/source portal.

`understanding.paper_focus`

- Anchor: project claim
- Entities: paper nodes with paper-scope question/claim/evidence/warrant/limitation
- Groups: paper argument lanes and translation bridge
- Relations: paper argument links, translation links
- Inspector: paper node detail or paper overview

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph uses a fixed paper argument template beside the selected project claim.
- Fixed lanes are Paper Questions, Paper Claims, Paper Evidence, Paper Warrants, and Paper Limitations.
- Lane presence and lane height are data-driven.
- Adding paper evidence adds cards inside Paper Evidence.
- Adding paper limitations adds cards inside Paper Limitations.
- Adding paper questions, claims, or warrants follows the same lane rule.
- Empty lanes may be hidden.
- Paper argument nodes are terminal inspect nodes by default.
- Paper argument nodes do not create deeper breadcrumb layers.
- Inspector shows paper focus detail, including paper brief, argument nodes, and translation bridge.
- This layer represents the selected paper's internal argument projected beside the selected project claim.
- This layer does not replace the project claim focus graph and does not show the project's complete evidence graph.

Understanding mode frontend is locked:

- `understanding.project_overview`, `understanding.claim_focus`, and `understanding.paper_focus` are accepted as the frontend display contract.
- Future changes should preserve these graph frames, inspector roles, and drill/inspect boundaries unless this document is revised.

### 12.2 Literature

`literature.overview`

- Anchor: topic/project literature map
- Entities: literature lanes/routes, readable paper/source nodes
- Groups: route lanes or field-position clusters
- Relations: paper lineage relations
- Projected route interaction: `drill -> literature.route_focus`
- Projected paper interaction: `drill -> literature.paper_focus`

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph shows literature routes as large colored route frames.
- Each route frame contains readable paper/source cards.
- Route frame color separates literature lines.
- Paper/source cards show paper title and year when available.
- Inspector shows route list only.
- Inspector does not show project Understanding detail, experiment detail, raw debug state, or paper argument detail.
- Clicking a route frame drills to `literature.route_focus`.
- Clicking a paper/source card drills to `literature.paper_focus`.
- Literature overview is a paper-only lineage surface that supports but does not replace Project Understanding.

`literature.route_focus`

- Anchor: selected route
- Entities: route papers
- Groups: timeline or method-family grouping
- Relations: route sequence and explicit literature relations
- Inspector: route explanation and papers

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph shows one selected literature route frame.
- Graph shows only papers inside that selected route.
- Route focus preserves the same route color and visual style from literature overview.
- Inspector shows route detail, route explanation, and papers in the route.
- Clicking a paper/source card drills to `literature.paper_focus`.
- Route focus does not show unrelated literature routes.
- Route focus does not show project claim evidence/warrant/limitation frames.

`literature.paper_focus`

- Anchor: selected source paper
- Entities: source metadata, optional paper understanding nodes
- Groups: optional paper argument group
- Portals: Paper detail page, Understanding nodes if linked

Locked display contract, accepted from DemoVisualAffordance dashboard review:

- Graph reuses the fixed paper argument template.
- Fixed lanes are Paper Questions, Paper Claims, Paper Evidence, Paper Warrants, and Paper Limitations.
- Lane presence and lane height are data-driven.
- Paper argument nodes are terminal inspect nodes by default.
- Paper argument nodes do not create deeper breadcrumb layers.
- Inspector shows paper focus detail and paper brief.
- Literature paper focus and Understanding paper focus share the same paper argument visual grammar.
- Literature paper focus is reached from a literature route or paper card, not from a selected project claim.
- This layer represents one source paper's internal argument, not the whole literature route.

Literature mode frontend is locked:

- `literature.overview`, `literature.route_focus`, and `literature.paper_focus` are accepted as the frontend display contract.
- Future changes should preserve these route frames, paper card roles, paper focus grammar, inspector roles, and drill/inspect boundaries unless this document is revised.

### 12.3 Experiments

`experiments.evaluation_overview`

- Entities: derived evaluation arenas only
- Derived entity rule: coherent evaluation objective from experiment rows, run metrics, and experiment metadata
- Relations: none by default, unless arena dependencies become explicit
- Default inspector: evaluation arena list
- Projected arena interaction: `drill -> experiments.evaluation_arena_focus`

`experiments.evaluation_arena_focus`

- Anchor: selected evaluation arena
- Entities: compact evaluation context summary, experiment designs
- Groups: evaluation context frame, experiment design frame
- Relations: `defines`, `has_design`
- Projected experiment design interaction: `drill -> experiments.experiment_design_focus`
- Runs do not appear here

`experiments.experiment_design_focus`

- Anchor: selected experiment design
- Entities: derived design method summary, DB-backed run nodes
- Groups: Design Method, Runs / Results
- Relations: `has_run`, `reports_metric`, `impacts`
- Projected run role: `terminal`
- Projected run interaction: `inspect`
- Projected design method group interaction: `inspect`
- Project Understanding Impact appears in inspector and portals, not as the primary layout driver

Experiment projection rules:

- Evaluation arena nodes are derived substrate entities, not experiment result claims.
- Evaluation arena means a coherent evaluation context: datasets, benchmarks/tasks, and metric families used to compare a set of experiment designs.
- Dataset, benchmark, and metric records are not separate top-level graph nodes in arena focus; they are summarized into the Evaluation Context panel and detailed in inspector.
- Protocol/model/baseline/planned-metric values inside Design Method must carry derived provenance from experiment metadata, metrics, artifacts, or run rows.
- If metadata is absent, the node must not be fabricated. Use inspector warning instead.
- `impacts` links describe recorded interpretation links. They do not mean the experiment proved the target claim.

## 13. Inspector Contract

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

## 14. Frontend Architecture

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

## 15. Backend Architecture

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

## 16. Source Of Truth Rules

Hard rules:

- DB rows are facts.
- Source papers use `source:<source_id>` as global canonical ids.
- Derived groups must say they are derived.
- Derived entities must say which DB rows or metadata fields produced them.
- React Flow nodes are render objects, not source objects.
- Projected graph objects are render contracts, not source truth.
- Inspector summaries may synthesize, but must carry subject ids and provenance.
- Cross-mode portals are navigation affordances, not evidence claims.
- Experiments do not prove claims by default; they record substrate and results, then link interpreted impact separately.
- Literature remains paper/source lineage, not project truth.
- Understanding remains current project truth.

## 17. Testing Strategy

Backend tests:

- canonical ids are stable and typed
- every entity has provenance
- every relation endpoint exists in scene or is intentionally external
- every derived group has rule and inputs
- every derived entity has rule and inputs
- v1 layer names map to v2 layer names
- v1 `source:paper:*` ids map to v2 `source:*` ids
- mode/layer registry rejects invalid layer
- scene capabilities do not include unsupported drill targets

Frontend source tests:

- projected graph schema validates before React Flow rendering
- React Flow adapter does not inspect DB fields directly
- terminal node component cannot call `onNavigate`
- terminal projected nodes never receive `interaction.kind = drill`
- aggregated projected edges retain `member_relation_ids`
- mode projections are separate modules
- frame nodes are non-draggable, non-selectable by default
- top-level mode breadcrumbs remain siblings

Browser tests:

- Understanding overview shows question/claim frames
- Claim focus shows one claim anchor and E/W/L/source lanes
- Literature overview readable paper nodes
- Experiments overview shows evaluation arenas only
- Inspector scroll does not resize canvas
- Run click updates inspector, no breadcrumb layer

## 18. Migration Plan Shape

This is not the implementation plan, but expected sequence:

1. Add scene contract types and backend scene builders beside current read model.
2. Add frontend projection modules that consume v2 scenes.
3. Move current Understanding projection into `understandingProjection`.
4. Move Literature and Experiments into their own projection modules.
5. Replace generic node/edge fallback with shared visual grammar.
6. Add provenance-aware inspector.
7. Deprecate v1 payload once all mode screenshots match or improve current behavior.

## 19. Open Questions

- Whether `/api/workspace-graph` should become v2 by default or expose `?schema=scene-v2`.
- Whether `entity_links` is sufficient for cross-mode impact links, or backend needs a dedicated read-model helper.
- Whether paper focus belongs under Understanding only, or should be accessible as a shared source/paper scene.
- Whether frontend state should stay local React state or move to a small Zustand store like Understand-Anything.

## 20. Acceptance Criteria

The system framework is ready for implementation when:

- Product, backend, and frontend agents agree on scene object meanings.
- A frontend node frame cannot be confused with a DB fact.
- Every visible entity can trace back to DB or a derived rule.
- Every `drill`, `inspect`, and `portal` interaction is explicit in projection data.
- Every terminal node role is explicit in projection data.
- Understanding, Literature, and Experiments each have declared mode/layer object contracts.
- React Flow adapter can be replaced without changing semantic scene builders.

## 21. Concrete Projection Map Contract

This section fixes the current dashboard display as the target projection contract. It is the map from `research-pilot.db` and project-local paper records into the visible Workspace Island.

Projection pipeline:

```text
DB truth / paper dossier
  -> WorkspaceScene entity / relation / derived_group / portal
  -> ProjectedGraph node / edge / frame / portal / interaction
  -> React Flow adapter node / edge / viewport
  -> Inspector subject / sections / actions
```

The projection map is mode/layer-specific. It must not depend on per-project hard-coded labels, DemoVisualAffordance-only ids, or frontend fallback guesses.

### 21.1 Global Projection Rules

- Display title comes from canonical content fields, never raw ids.
- Source paper title fallback order: paper dossier title, `sources.title`, source metadata title, short source id as debug-only fallback.
- Raw ids such as `source:paper:*`, `paper:<project>:*`, `literature_lane:*`, and `evaluation_arena:*` may appear in debug/provenance text, not primary card titles.
- `drill` changes layer and breadcrumb.
- `inspect` changes inspector only and keeps breadcrumb unchanged.
- Terminal nodes may use `inspect` or `none`; terminal nodes must not drill.
- Derived groups become frames only when declared by projection map.
- Frames are visual grouping, not DB facts.
- Cross-mode jumps are portals. They are not evidence links unless backed by `entity_links` or a declared relation.
- Inspector is layer-aware. Overview inspectors describe the layer broadly; terminal inspectors show detailed node knowledge.
- React Flow layout may move nodes, resize frames, or aggregate edges, but cannot change entity role, interaction, title source, or provenance.

### 21.2 Required Source Tables And Fields

Understanding projection reads:

- `understanding_nodes`: project id, local id, node type, title/text, status, confidence, metadata.
- `understanding_links`: relation id, relation type, status, metadata.
- `understanding_link_endpoints`: relation endpoints, endpoint roles, ordering.
- `sources`: source id, title, year, authors, url/locator metadata.
- `entity_links`: optional cross-mode references from claims/atoms to sources, experiments, or runs.

Literature projection reads:

- `literature_lanes`: lane id, title, summary, order, status, metadata.
- `literature_items`: item id, lane id, source id, summary, metadata, order/sort hints.
- `literature_relations`: source-to-source or lane-to-lane relation type and endpoints.
- `sources`: title/year/authors/url fallback for every literature item.
- project-local paper dossiers: paper argument nodes and paper brief when present.

Experiments projection reads:

- `experiments`: experiment id, title, question, hypothesis, expected evidence, risks, status, metadata.
- `experiment_runs`: run id, experiment id, label, origin, status, summary, results metadata.
- `experiment_metrics`: metric family/name/value/direction/context.
- `experiment_artifacts`: artifact labels, paths, source refs.
- `entity_links`: optional links from experiments/runs/metrics to understanding claims or paper sources.

### 21.3 Understanding Projection Map

| Layer | DB truth input | Scene objects | Projection output | Inspector output | Forbidden |
| --- | --- | --- | --- | --- | --- |
| `understanding.project_overview` | Project questions and project claims from `understanding_nodes`; `answers`/claim-support links from `understanding_links` | `question`, `claim`, `answers`, optional claim support relations, question and claim groups | Questions frame, Claims frame; question nodes inspect; claim nodes drill to `understanding.claim_focus` | Default question list; selected question detail with linked claims | Recent Understanding panel, papers, experiment results, raw counts, unrelated debug fields |
| `understanding.claim_focus` | Focused claim, direct E/W/L/source neighbors, relevant relations | One anchor `claim`; terminal `evidence`, `warrant`, `limitation`; source paper nodes; E/W/L/source frames | Selected claim anchor; Evidence/Grounds frame; Warrants/Bridges frame; Limitations/Boundaries frame; Source Papers frame; atom nodes inspect; source nodes drill/portal to paper focus | Default rich claim detail; selected atom/source detail with source refs and related source papers | Unrelated active claims; deeper E/W/L layers; treating limitation/evidence/warrant as drillable |
| `understanding.paper_focus` | Selected paper/source plus paper dossier argument records and optional selected project claim context | `project_claim_anchor`; paper question/claim/evidence/warrant/limitation entities; translation relations when present | Fixed paper argument template: Paper Questions, Paper Claims, Paper Evidence, Paper Warrants, Paper Limitations; paper atoms inspect | Paper focus detail; paper brief; argument node detail; translation bridge | Full project claim graph; full literature route graph; raw paper state dump |

Understanding paper focus and Literature paper focus share the same paper argument projection. Only breadcrumb and contextual inspector copy differ.

### 21.4 Literature Projection Map

| Layer | DB truth input | Scene objects | Projection output | Inspector output | Forbidden |
| --- | --- | --- | --- | --- | --- |
| `literature.overview` | All literature lanes/items/relations for the project plus source metadata | `literature_lane`, source paper entities, optional literature relations, route frames | Large colored route frames; each route contains readable paper cards; route frame drills to route focus; paper card drills to paper focus | Route list only | Project claim graph, experiment graph, paper argument detail, raw lane ids as card titles |
| `literature.route_focus` | Selected lane, lane items, lane relations, source metadata | One selected `literature_lane`, source paper entities, route frame | One route frame only; papers inside route; paper card drills to paper focus | Route detail, route explanation, paper list | Unrelated routes; Understanding E/W/L frames; experiment results |
| `literature.paper_focus` | Selected source, paper dossier/read model, optional route context | Paper argument entities and optional route context | Same fixed paper argument template as Understanding paper focus | Paper focus detail and paper brief | Whole route overview; project claim focus graph unless entered through Understanding context |

Literature route identity is not a paper fact. It is a derived organizing lane from `literature_lanes` plus `literature_items`.

### 21.5 Experiments Projection Map

| Layer | DB truth input | Scene objects | Projection output | Inspector output | Forbidden |
| --- | --- | --- | --- | --- | --- |
| `experiments.evaluation_overview` | Experiments, runs, metrics, metadata-derived arena grouping | Derived `evaluation_arena` entities | Arena cards only; concise metric-family summary and experiment/run counts; arena drills to arena focus | Arena list plus next moves | Dataset/benchmark/metric nodes as top-level scatter; claim proof language |
| `experiments.evaluation_arena_focus` | Selected arena, experiments assigned to arena, summarized datasets/benchmarks/metrics | Anchor `evaluation_arena`, derived compact `evaluation_context`, experiment design entities | Evaluation Context frame with one compact summary panel; Experiment Designs frame with design cards; design drills to design focus; selected context/design inspects only | Arena detail; datasets, benchmarks/tasks, metric families; experiment designs | Run nodes; long dataset/benchmark/metric lists as graph nodes; duplicated context groups |
| `experiments.experiment_design_focus` | Selected experiment row, experiment metadata, runs, metrics, artifacts, interpretation links | Anchor experiment; derived `experiment_method`; run nodes; optional portals/impact links | Experiment anchor; Design Method frame with clickable model/baseline/protocol/ablation groups; Runs / Results frame; run nodes inspect only | Default experiment detail; method group detail; selected run detail; expected evidence and risks | Separate long model/baseline/protocol node lists; extra drill layer under run/method; claiming proof of Understanding claim |

Evaluation Arena definition:

- Arena is a derived evaluation context, not a DB table row unless backend later adds one.
- Arena groups experiment designs that share a coherent evaluation objective.
- Dataset, benchmark/task, and metric family belong to arena context.
- Runs belong only to experiment design focus.
- Experiment designs are research plans or completed designs inside an arena.

### 21.6 Paper Focus Projection Map

Paper focus is shared by two entry paths:

- `understanding.claim_focus -> source paper -> understanding.paper_focus`
- `literature.route_focus|literature.overview -> paper -> literature.paper_focus`

Shared graph:

- Paper Questions lane
- Paper Claims lane
- Paper Evidence lane
- Paper Warrants lane
- Paper Limitations lane

Shared rules:

- Lanes are fixed categories.
- Lane membership is data-driven.
- Empty lanes may be hidden.
- Paper argument atoms are terminal inspect nodes.
- More atoms increase cards inside the lane; they do not create a new graph layer.

Context differences:

- Understanding entry may show a selected project claim anchor and translation bridge.
- Literature entry may show route context in breadcrumb/inspector.
- Both entries must use the same paper title, paper brief, and paper argument records.

### 21.7 Inspector Projection Map

| Inspector kind | Subject | Trigger | Required content |
| --- | --- | --- | --- |
| `overview` | Current layer | Layer default | Short layer explanation and list of drillable top-level objects |
| `question_detail` | Question | Inspect question | Question text, role, linked claims |
| `claim_detail` | Claim | Claim focus default or selected claim | Claim text, supporting claims, evidence, warrants, limitations, source papers |
| `argument_atom_detail` | Evidence/warrant/limitation | Inspect terminal atom | Atom text, source refs, related source papers |
| `paper_focus` | Source paper | Paper focus default | Paper brief, core contribution, evidence boundary, argument records, project/route context |
| `route_detail` | Literature lane | Route focus default | Route explanation, papers, position in literature map |
| `arena_detail` | Evaluation arena | Arena focus default | Datasets, benchmarks/tasks, metric families, designs |
| `experiment_detail` | Experiment design | Design focus default or selected design | Question, hypothesis, expected evidence, risks, run summary |
| `experiment_method_detail` | Method group | Inspect method group | Models, baselines, protocol, ablations, provenance |
| `run_detail` | Experiment run | Inspect run | Origin, status, metric values, artifacts, result notes |

Inspector content may summarize, but must keep subject id and provenance. Inspector scroll must not resize the island canvas.

### 21.8 Validation Rules

Backend scene/projection validation should fail or warn when:

- A visible node has no provenance.
- A derived group lacks `source.kind = derived`, rule, or inputs.
- A projected terminal node has `interaction.kind = drill`.
- A node title falls back to a raw id while a source title exists.
- A literature item references a source id missing from `sources`.
- A relation endpoint is absent from the scene without an explicit external reference rule.
- A layer emits an entity type outside its projection map.
- Breadcrumb adds a segment for inspect-only selection.
- `evaluation_setting_focus` appears as emitted semantic layer instead of compatibility input mapped to `evaluation_arena_focus`.

Frontend source validation should fail or warn when:

- React Flow adapter reads DB table-shaped fields directly.
- React Flow component decides drill/inspect behavior from entity type instead of projected `interaction`.
- A mode renders a layer not declared in this contract.
- Card title renders raw canonical id in normal display.
- Inspector height changes canvas height.

### 21.9 Current Migration State

Current implementation state:

- `/api/workspace-graph` without `schema` returns `workspace-graph-v1` compatibility payload.
- `?schema=scene-v2` returns semantic scene objects.
- `?schema=projection-v1` returns projected graph objects.
- Current frontend still renders mostly from `workspace-graph-v1`.

Target implementation state:

- Frontend renders `workspace-projection-v1`.
- React Flow adapter only receives projected nodes, edges, frames, portals, and interactions.
- `workspace-graph-v1` remains compatibility-only until the projection path matches locked screenshots for all accepted layers.
