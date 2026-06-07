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

derived:evaluation_setting:<project_id>:<slug>
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
| `experiments` | `evaluation_setting_focus` | `experiments.evaluation_setting_focus` |
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

- evaluation setting: dataset + benchmark/task + metric family
- experiment protocol block: selected protocol fields from `experiments.metadata_json`
- model or baseline block: model/baseline fields from `experiments.metadata_json` or linked artifacts
- planned metric summary: declared metric fields before run results exist
- literature topic anchor: project + literature lanes + project positionings

Contract:

```json
{
  "canonical_id": "derived:evaluation_setting:DemoVisualAffordance:agd20k-kld-sim-nss",
  "display_id": "evaluation_setting:agd20k-kld-sim-nss",
  "entity_type": "evaluation_setting",
  "title": "AGD20K quantitative evaluation / qualitative validation",
  "summary": "AGD20K unseen egocentric objects; UMD categorical masks; saliency/heatmap alignment metrics.",
  "capabilities": ["inspectable", "drillable"],
  "source": {
    "kind": "derived",
    "rule": "dataset + benchmark_task + metric_family from experiment rows",
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
- selected evaluation setting in Evaluation Setting Focus
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
- evaluation setting
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

- Entities: derived evaluation settings only
- Derived entity rule: benchmark/task + dataset + metric family
- Relations: none by default, unless setting dependencies become explicit
- Default inspector: evaluation setting list
- Projected setting interaction: `drill -> experiments.evaluation_setting_focus`

`experiments.evaluation_setting_focus`

- Anchor: selected evaluation setting
- Entities: dataset, benchmark/task, metric family, experiment designs
- Groups: evaluation substrate frame, experiment design frame
- Relations: `uses_dataset`, `uses_benchmark`, `measures_with`, `has_design`
- Projected experiment design interaction: `drill -> experiments.experiment_design_focus`
- Runs do not appear here

`experiments.experiment_design_focus`

- Anchor: selected experiment design
- Entities: derived protocol blocks, derived model/method nodes, derived baseline nodes, derived planned metric summary, DB-backed run nodes
- Groups: Protocol, Models/Baselines, Runs, Interpretation Links
- Relations: `has_run`, `reports_metric`, `impacts`
- Projected run role: `terminal`
- Projected run interaction: `inspect`
- Project Understanding Impact appears in inspector and portals, not as the primary layout driver

Experiment projection rules:

- Evaluation setting nodes are derived substrate entities, not experiment result claims.
- Protocol/model/baseline/planned-metric nodes must carry derived provenance from experiment metadata, metrics, artifacts, or run rows.
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
- Experiments overview shows evaluation settings only
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
