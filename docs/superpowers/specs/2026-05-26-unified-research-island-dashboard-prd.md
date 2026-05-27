# Unified Research Island Dashboard PRD

## 1. Executive Summary

Research Pilot needs a unified dashboard workspace that treats Project Understanding as the primary dashboard visualization model, with Literature and Experiments as supporting evidence surfaces. This PRD defines a new Workspace-first dashboard experience: one graph island shell with three modes, `Understanding`, `Literature`, and `Experiments`, backed by `research-pilot.db` read models, lazy-loaded layers, and mode-specific inspectors. The result should replace scattered project graph sections and weak experiment cards with a graph-native, drillable research browser without changing the local dataset as the primary workspace source.

## 2. Problem Statement

The current dashboard has strong pieces, but the experience is fragmented.

- The project index exposes internal metrics such as candidate counts, projectpaper, paper_count, rounds, and claims. These are low-value for the user.
- The Project page has a useful React graph island, but surrounding sections such as Recent Understanding compete with the graph instead of acting as graph context.
- Papers list/detail are serviceable, but Paper detail exposes read-only state/debug metadata that should not be user-facing.
- Technical Lineage is closest to the desired model: one island plus an inspector, but paper nodes are too small to read comfortably.
- Experiments is the weakest page. It currently presents experiment cards and summary metrics, but it fails to show the actual evaluation substrate: datasets, benchmarks, metrics, protocols, runs, and result interpretation.

The dashboard should help a researcher answer: what is the current understanding, which papers support it, which evaluations/results ground it, and where should the next research move go?

## 3. Product Direction

The dashboard is a read-only observer for a chat-first, local-first research memory. The agent and CLI remain the way users mutate state. The dashboard should not become a workflow command surface or an editor.

The Workspace must express this hierarchy:

- `Understanding` is the primary dashboard model for current project understanding.
- `Literature` maps paper/source evidence that contributes to Understanding.
- `Experiments` maps evaluation settings, experiment designs, runs, and result interpretations that contribute to Understanding.

Literature and Experiments are not peer "reports" beside Understanding. They are supporting evidence modes.

Backend source of truth remains the workspace-local `research-pilot.db`. Graph islands are read-model projections over that dataset, not a new mutation layer or separate dashboard-owned storage.

## 4. Target Users

Primary user: a researcher using Research Pilot to maintain project memory while reading papers, planning experiments, and discussing next moves with an agent.

Primary jobs:

- Inspect current project understanding quickly.
- Drill from project claims into paper support.
- Understand how papers sit in the field lineage.
- Inspect evaluation settings, benchmarks, metrics, experiment designs, and results.
- Jump from evidence surfaces back to relevant Understanding nodes.

## 5. Goals

- Introduce a `Workspace` primary tab that opens directly into the unified research island.
- Keep `Papers` as a separate source library and paper detail surface.
- Use one island shell for graph modes: canvas left, inspector right, mode switch at top.
- Default Workspace mode is `Understanding`.
- Preserve the existing Understanding drill hierarchy: `Project overview -> Claim focus -> Paper focus`.
- Preserve the existing Technical Lineage semantics inside `Literature`.
- Redesign Experiments around evaluation substrate, not claim proof.
- Support contextual jumps across modes, such as claim to related experiments or paper to related Understanding node.
- Use lazy loading by mode/layer so the first Workspace load does not fetch every graph.
- Preserve dark/light theme switching.
- Remove obvious low-value/debug UI.

## 6. Non-Goals

- No dashboard editing or graph mutation.
- No new experiment execution system.
- No requirement to prove every claim from Experiments.
- No conversion of Papers into the graph island.
- No forced single mega-graph containing all nodes from all modes at once.
- No pixel-perfect visual spec in this PRD.
- No new stored `evaluation_settings` table for MVP. Evaluation Settings start as read-model groupings derived from existing experiment, run, and metric records.
- No replacement of existing DB-backed import/write architecture.

## 7. Information Architecture

Top-level dashboard navigation should become:

- `Workspace`
- `Papers`

`Workspace` contains mode switch:

- `Understanding`
- `Literature`
- `Experiments`

Default route:

- Workspace opens `Understanding`.
- No Overview mode.
- No Last Used behavior.

`Papers` remains independent:

- Papers list
- Paper detail
- Paper graph/detail support as needed

## 8. Unified Island Shell

The unified island shell owns layout and interaction chrome:

- Mode switch: `Understanding / Literature / Experiments`
- Breadcrumb
- Canvas viewport
- Inspector panel
- Search/filter controls where relevant
- Cross-mode jump affordances
- Loading/error/empty states

The shell must not force one graph schema. Each mode has its own graph model and renderer/adapter.

Shared interaction rule:

- Layer overview inspector gives lightweight navigation and layer explanation.
- Node detail inspector gives detailed knowledge only after selecting a concrete node.
- Nodes that drill into a deeper layer should show summary plus an entry action.
- Terminal nodes should open detail inspector rather than creating unnecessary canvas layers.

## 9. Understanding Mode

Understanding remains the primary Workspace mode.

Existing drill hierarchy must be preserved:

1. `Project Overview`
   - Canvas shows Questions and Claims.
   - Default inspector lists all Questions only.
   - Question click does not enter a new graph layer.
   - Question click opens Question detail inspector while staying in Project Overview.
   - Claim click enters Claim Focus.

2. `Claim Focus`
   - Canvas centers selected Claim.
   - Shows supporting claims, evidence, warrants, limitations, related claims, and paper sources.
   - Paper source click enters Paper Focus.
   - Inspector summarizes selected claim and offers cross-mode jumps where data exists.

3. `Paper Focus`
   - Canvas shows project claim anchor plus paper argument graph.
   - Paper graph includes paper question, evidence, warrant, claim, limitation, and translation bridge back to project claim.
   - Inspector shows selected paper node or paper-layer overview.

Question handling:

- Question is the top-level organizer in Project Overview.
- Question is not a required drill layer.
- Default inspector should list `Q id`, question text, and claim count.

Recent Understanding:

- Recent Understanding is not primary layout content.
- It may appear as provenance/status in a lower-priority inspector section or collapsed section.

## 10. Literature Mode

Literature inherits the current Technical Lineage semantics.

Purpose:

- Show paper/source lineage, routes, topics, and field positioning.
- Explain how the literature space supports Understanding.
- Remain paper-only lineage, not Project Understanding ground truth.

Default behavior:

- Canvas shows topic/routes/papers.
- Default inspector shows topic/routes overview.
- Route click shows route explanation and associated papers.
- Paper click shows paper summary and navigation to Paper detail or related Understanding nodes.

Required improvement:

- Paper nodes must be readable by default. Increase node size, title space, or default zoom so users can inspect paper labels without excessive zooming.

## 11. Experiments Mode

Experiments must not be claim-first.

Core principle:

> Experiments mode records the evaluation substrate before argument impact. Dataset, benchmark, metric, protocol, and run results are first-class; claim impact is downstream interpretation back into Understanding.

Experiments graph hierarchy:

1. `Evaluation Overview`
   - First layer.
   - Canvas contains Evaluation Setting nodes only.
   - Default inspector lists all Evaluation Settings.
   - Setting node minimum display:
     - name
     - dataset
     - metric family
     - experiment/run counts

2. `Evaluation Setting Focus`
   - Entered by clicking an Evaluation Setting.
   - Canvas shows:
     - selected setting anchor
     - dataset
     - benchmark/task
     - metric family
     - related Experiment Design nodes
   - Does not show runs.
   - Experiment Design nodes may show run count/status summary.
   - Inspector explains what the setting measures and what it does not measure.

3. `Experiment Design Focus`
   - Entered by clicking an Experiment Design.
   - Canvas shows:
     - experiment center
     - models
     - baselines
     - protocol blocks
     - planned metrics summary
     - run nodes
   - Evaluation setting remains breadcrumb/context, not repeated as expanded graph.
   - Inspector shows full design knowledge:
     - question
     - hypothesis
     - expected evidence
     - risks
     - next action
     - linked gaps/claims as downstream interpretation links

4. `Run Detail`
   - Run is terminal.
   - Clicking Run opens inspector detail only.
   - No new Run canvas layer.
   - Inspector order:
     - result summary
     - metric values
     - artifacts
     - interpretation
     - weaknesses
     - origin: imported/local
     - Project Understanding Impact at bottom
   - Project Understanding Impact contains supports/bounds/weakens claim links and contextual jumps to Understanding.

Evaluation Setting identity:

- `Evaluation Setting = benchmark/task + dataset + metric family`

Examples:

- `UMD affordance segmentation / UMD / mIoU`
- `AGD20K zero-shot heatmap / AGD20K / KLD-SIM-NSS`
- `Mug-handle correspondence control / qualitative control scenes / cosine-activation`

## 12. Cross-Mode Jumps

The island should support contextual jumps without collapsing all modes into one graph.

Examples:

- From Understanding claim `C4`: jump to Experiments filtered to runs/results impacting `C4`.
- From Understanding claim source paper: jump to Literature focused on that paper/route.
- From Run detail: jump to Understanding claim impacted by the run.
- From Literature paper: jump to Paper detail or related Understanding nodes.

Cross-mode jumps are preferred where stable IDs exist, but not every node must have one in the first implementation.

## 13. Backend And Read Model Requirements

This initiative should add a new Workspace graph read-model API while reusing existing DB-backed builders internally. The frontend should consume one mode/layer contract instead of composing old page-specific APIs directly.

### 13.1 Current Dataset Facts

`research-pilot.db` already contains enough structure for the first Workspace island:

- `projects`: project brief fields such as title, summary, main question, stage, and status.
- `sources`: source identity for papers, URLs, DOI/arXiv records, notes, Zotero items, and local artifacts.
- `understanding_nodes`: scoped nodes with `scope = project | paper | experiment`, `node_type = question | claim | evidence | warrant | limitation`, status, confidence, source refs, and metadata.
- `understanding_links` plus `understanding_link_endpoints`: project and paper reasoning/translation links.
- `experiments`: experiment designs with question, hypothesis, protocol summary, benchmark, dataset, type, and status.
- `experiment_runs`: imported or local run/result records with method, status, source, completed time, summary, and metadata.
- `experiment_metrics`: metric values by run, including benchmark, dataset, split, direction, numeric value when parseable, and text value.
- `experiment_artifacts`: run artifacts such as local files, URLs, tables, figures, or notes.
- `literature_lanes`, `literature_items`, `literature_relations`, `project_positionings`: paper-only literature structure and field positioning.
- `entity_links`: cross-entity interpretation links, including experiment-run-to-understanding-node relationships.
- `updates`, `activity_sessions`, `audit_events`: recent understanding/update provenance.

### 13.2 Endpoint Contract

Add one read-only endpoint:

```text
GET /api/workspace-graph
  ?project=<project_id>
  &mode=understanding|literature|experiments
  &layer=<layer_id>
  &focus_id=<entity_id>
  &selected_id=<entity_id>
```

Required behavior:

- `project` is required and must pass existing project id validation.
- `mode` defaults to `understanding`.
- `layer` defaults by mode:
  - `understanding`: `project_overview`
  - `literature`: `literature_overview`
  - `experiments`: `evaluation_overview`
- `focus_id` identifies the current drill anchor.
- `selected_id` identifies the inspector selection.
- Missing optional mode data returns a valid empty-state payload, not a hard page failure.
- Invalid project returns `404`.
- Invalid mode/layer/focus returns structured `400` with explanation.

Existing endpoints may remain for compatibility:

- `/api/project-graph`
- `/api/project-understanding`
- `/api/experiments`
- `/api/paper-graph`

The new Workspace frontend should use `/api/workspace-graph` as its primary graph data contract.

### 13.3 Payload Shape

This section proposes a backend contract shape. The backend-focused agent may revise field names or nesting before implementation planning, but the final contract must preserve the same semantics: lazy mode/layer loading, canvas data, inspector data, breadcrumb, drill actions, cross-mode jumps, stable identity, empty states, and warnings.

Proposed mode/layer response shape:

```json
{
  "schema_version": "workspace-graph-v1",
  "source": "research-pilot.db",
  "project_id": "DemoVisualAffordance",
  "mode": "experiments",
  "layer": "evaluation_overview",
  "focus_id": "",
  "selected_id": "",
  "breadcrumb": [
    {
      "label": "Workspace",
      "mode": "understanding",
      "layer": "project_overview",
      "focus_id": ""
    }
  ],
  "canvas": {
    "layout_hint": "island",
    "nodes": [],
    "edges": []
  },
  "inspector": {
    "kind": "overview",
    "title": "Evaluation Overview",
    "summary": "",
    "sections": [],
    "actions": []
  },
  "available_layers": [],
  "cross_mode_jumps": [],
  "empty_state": null,
  "warnings": []
}
```

Canvas node minimum shape:

```json
{
  "id": "claim:C2",
  "entity_type": "claim",
  "db_id": "project:DemoVisualAffordance:C2",
  "local_id": "C2",
  "label": "Short readable label",
  "subtitle": "Status or source context",
  "status": "active",
  "confidence": "medium",
  "display": {
    "tone": "claim",
    "badges": [
      {
        "key": "entity_type",
        "label": "Claim",
        "tone": "claim"
      }
    ],
    "warnings": []
  },
  "drill": {
    "mode": "understanding",
    "layer": "claim_focus",
    "focus_id": "claim:C2"
  },
  "inspector": {
    "selected_id": "claim:C2"
  },
  "metadata": {}
}
```

Canvas edge minimum shape:

```json
{
  "id": "edge:RL1",
  "source": "evidence:E2",
  "target": "claim:C2",
  "source_db_id": "project:DemoVisualAffordance:E2",
  "target_db_id": "project:DemoVisualAffordance:C2",
  "relation": "supports",
  "label": "supports",
  "metadata": {}
}
```

Inspector section minimum shape:

```json
{
  "title": "Metric Values",
  "kind": "table",
  "items": []
}
```

Action shape:

```json
{
  "label": "Open impacted claim",
  "kind": "cross_mode_jump",
  "target": {
    "mode": "understanding",
    "layer": "claim_focus",
    "focus_id": "claim:C2"
  }
}
```

### 13.4 Source Of Truth And Display Governance

The Workspace island must make source-of-truth boundaries explicit. The dashboard should never let freeform agent text become user-facing taxonomy, node badges, graph colors, graph layers, or empty-state behavior.

Source-of-truth rules:

- `research-pilot.db` is the only durable source for project, source, understanding, literature, experiment, update, and link data.
- The dashboard owns no separate storage and must not mutate DB state.
- The read model is the only place that maps DB records into graph/display payloads.
- The frontend renders the read-model contract and should not inspect arbitrary raw DB metadata for visible labels.

Agent write boundary:

- Agents may write structured research data into source tables through approved writers/importers.
- Agents may update conceptual fields such as node text, node type, status, confidence, source refs, links, experiment records, metrics, artifacts, and update summaries.
- Agents must not directly author UI-only labels such as node chip copy, graph lane names, card subtitles, colors, layout hints, button text, or dashboard empty-state text.
- If an agent proposes a new taxonomy or role, it must be recorded as project understanding/provenance first, then promoted into the display contract only through schema/read-model changes.

Read-model display boundary:

- `/api/workspace-graph` must emit explicit `display` fields for user-facing rendering.
- `label`, `subtitle`, `display.tone`, `display.badges`, `display.sections`, and `display.actions` are read-model outputs, not arbitrary frontend fallbacks.
- `metadata` may be included for provenance/debugging, but must be treated as raw data. It is not a display API.
- Unknown metadata keys must not render as badges, subtitles, lanes, graph colors, or inspector facts by default.
- Missing optional data should produce deterministic empty states from the read model, not frontend guesses.

Allowed node display sources for MVP:

- Identity: `id`, `db_id`, `local_id`, `entity_type`.
- Main text: canonical DB text fields such as `understanding_nodes.text`, `sources.title`, `experiments.title`, and `experiment_runs.summary`.
- Status: controlled status/confidence fields from DB columns.
- Source context: source ids, paper titles, benchmark/dataset/metric fields, and explicit `entity_links`.
- Badges: only controlled enums defined in the read-model mapper.

Legacy metadata handling:

- Existing legacy fields such as `metadata.role` may be read only through an explicit allowlist mapper.
- Known legacy roles can become `display.badges` if the PRD or implementation plan names them as approved values.
- Unknown or unsupported legacy roles must be hidden from primary UI and reported in `warnings`.
- The read model should preserve raw legacy metadata for provenance, but frontend components must not render `metadata.role` directly.

Example controlled mapping:

```json
{
  "db_id": "project:DemoVisualAffordance:Q1",
  "entity_type": "question",
  "local_id": "Q1",
  "label": "What mechanistic primitives make visual affordance understanding possible in Visual Foundation Models?",
  "metadata": {
    "role": "framing"
  },
  "display": {
    "tone": "question",
    "badges": [
      {
        "key": "question_role",
        "label": "Framing",
        "tone": "question"
      }
    ],
    "warnings": []
  }
}
```

If `metadata.role = "agent invented role"` and no mapper allows it, the payload should keep the raw metadata but omit the badge:

```json
{
  "metadata": {
    "role": "agent invented role"
  },
  "display": {
    "badges": [],
    "warnings": ["Unsupported metadata.role was not rendered."]
  }
}
```

### 13.5 Stable ID Rules

Workspace graph IDs should be stable, namespaced strings:

```text
project:<project_id>
question:<node_id>
claim:<node_id>
evidence:<node_id>
warrant:<node_id>
limitation:<node_id>
source:<source_id>
paper:<source_id>
literature_lane:<lane_id>
literature_item:<item_id>
literature_relation:<relation_id>
evaluation_setting:<normalized_key>
experiment:<experiment_id>
run:<run_id>
metric:<metric_id>
artifact:<artifact_id>
claim_impact:<entity_link_id>
```

Rules:

- DB primary keys remain the canonical durable ids and must be carried as `db_id` or type-specific raw ids.
- Frontend graph IDs may use readable local IDs such as `claim:C2`, but must not be treated as DB primary keys.
- Understanding nodes must distinguish `id` / `db_id` / `local_id`. Example: `id = claim:C2`, `db_id = project:DemoVisualAffordance:C2`, `local_id = C2`.
- Source-backed nodes must distinguish `id` / `source_id` / `path` where applicable. Avoid ambiguous doubled ids such as `paper:paper:zhang2026...`.
- Cross-mode jumps must carry target `mode`, `layer`, and `focus_id`.
- If a source appears in Understanding, Literature, and Papers, the canonical bridge is `source:<source_id>`.

### 13.6 Mode And Layer Mapping

Understanding mode:

- `project_overview`
  - Source tables: `projects`, `understanding_nodes(scope='project')`, `understanding_links(scope='project')`.
  - Canvas nodes: project questions and claims.
  - Default inspector: question list with claim counts.
- `claim_focus`
  - Source tables: project-scoped understanding nodes/links plus source refs.
  - Canvas nodes: selected claim, related evidence, warrants, limitations, supporting/challenging claims, source/paper anchors.
  - Inspector: selected claim detail and available cross-mode jumps.
- `paper_focus`
  - Source tables: `sources`, `understanding_nodes(scope='paper')`, `understanding_links(scope='paper')`, translations to project nodes.
  - Canvas nodes: paper argument graph plus project claim anchor.
  - Inspector: paper-layer overview or selected paper node.

Literature mode:

- `literature_overview`
  - Source tables: `literature_lanes`, `literature_items`, `literature_relations`, `sources`, `project_positionings`.
  - Canvas nodes: topic, routes/lanes, readable paper/source nodes.
  - Inspector: topic/routes overview.
- `literature_route_focus`
  - Source tables: same as overview, filtered by `lane_id`.
  - Canvas nodes: route anchor, papers, explicit relations where useful.
  - Inspector: route explanation and associated papers.
- `literature_paper_focus`
  - Source tables: `literature_items`, `sources`, optional paper understanding nodes.
  - Canvas nodes: selected paper and its route/local neighbors.
  - Inspector: paper summary, source metadata, jumps to Paper detail and Understanding nodes where available.

Experiments mode:

- `evaluation_overview`
  - Source tables: `experiments`, `experiment_runs`, `experiment_metrics`.
  - Canvas nodes: Evaluation Setting nodes only.
  - Inspector: list of all Evaluation Settings.
- `evaluation_setting_focus`
  - Source tables: experiments/runs/metrics grouped by selected setting.
  - Canvas nodes: setting anchor, dataset, benchmark/task, metric family, related Experiment Design nodes.
  - Inspector: what the setting measures and does not measure.
- `experiment_design_focus`
  - Source tables: `experiments`, `experiment_runs`, `experiment_metrics`, `experiment_artifacts`, `entity_links`.
  - Canvas nodes: experiment design, models/methods, baselines if present in metadata, protocol blocks, planned metrics, run nodes.
  - Inspector: design knowledge, risks, expected evidence, linked gaps/claims.
- Run selection inside `experiment_design_focus`
  - This is an inspector state, not a canvas layer.
  - Request shape should keep `layer = experiment_design_focus`, use `focus_id = experiment:<experiment_id>`, and use `selected_id = run:<run_id>`.
  - Canvas stays on the Experiment Design Focus graph.
  - Inspector displays result summary, metrics, artifacts, interpretation, weaknesses, origin, and Project Understanding Impact.

### 13.7 Evaluation Setting Normalization

For MVP, `EvaluationSetting` is a read-model entity, not a stored table.

Definition:

```text
Evaluation Setting = benchmark/task + dataset + metric family
```

Source fields:

- Benchmark/task:
  - prefer non-empty `experiment_metrics.benchmark_name`
  - else `experiments.benchmark_name`
  - else metadata benchmark/task fields
  - else `Unspecified benchmark`
- Dataset:
  - prefer non-empty `experiment_metrics.dataset_name`
  - else `experiments.dataset_name`
  - else metadata dataset fields
  - else `Unspecified dataset`
- Metric family:
  - derive from evaluation metric names in `experiment_metrics.name`
  - else planned metrics in experiment metadata
  - else `Qualitative`

Normalization rules:

- Ignore blank benchmark/dataset fields and fall back to experiment-level fields.
- Treat long compound benchmark/dataset strings as display labels unless they can be safely split into separate task/dataset values.
- Do not treat all `experiment_metrics` rows as evaluation metrics. Descriptive facts such as training image counts, supervision labels, qualitative localization labels, and evidence-type rows should remain result facts, not metric-family keys.
- Prefer known metric vocabularies for metric-family derivation, such as `mIoU`, `IoU`, `KLD`, `SIM`, `NSS`, `AUC`, `accuracy`, `cosine`, or rubric/human-rating terms.
- If only descriptive result facts exist, use planned metrics from experiment metadata before falling back to `Qualitative`.

Metric family normalization examples:

```text
mIoU, IoU, mask IoU -> segmentation overlap
KLD, SIM, NSS, AUC-Judd -> saliency/heatmap alignment
accuracy, top-1, top-5 -> classification accuracy
cosine, activation similarity -> representation similarity
qualitative, human rating, rubric -> qualitative assessment
```

Stable setting id:

```text
evaluation_setting:<slug(benchmark)>:<slug(dataset)>:<slug(metric_family)>
```

Counts:

- `experiment_count`: number of experiment designs attached to setting.
- `run_count`: number of runs under attached experiments and setting metrics.
- `completed_run_count`: completed runs under setting.
- `imported_evidence_count`: runs with `origin_type = imported_paper`.
- `local_result_count`: runs with `origin_type = local`.

### 13.8 Claim Impact Mapping

Run-to-Understanding impact should come from `entity_links` where possible.

Preferred relations:

```text
from_entity_type = experiment_run
to_entity_type = understanding_node
relation_type = produces
relation_type = claim_impact:supports
relation_type = claim_impact:bounds
relation_type = claim_impact:weakens
relation_type = claim_impact:mentions
```

Rules:

- `produces` links connect run results to experiment-scoped evidence nodes.
- `claim_impact:*` links connect runs to project Understanding nodes.
- If explicit claim impact links are missing, the read model may show "No linked project impact yet" instead of inferring impact.
- The dashboard may display source refs and confidence, but must not upgrade an impact to confirmed project evidence.

### 13.9 Error, Empty, And Cache Rules

Error shape:

```json
{
  "error": "Invalid workspace graph request",
  "message": "Unknown layer: run_canvas",
  "schema_version": "workspace-graph-error-v1"
}
```

Empty state shape:

```json
{
  "title": "No experiment records yet",
  "message": "The workspace has no experiment designs or result records for this project.",
  "suggested_agent_prompt": "Record this experiment design as project experiment data."
}
```

Cache/invalidation:

- MVP can compute read models on request.
- Responses should use `cache: no-store` from the frontend as current dashboard APIs do.
- Later optimization may add file/DB mtime-based in-memory caching.
- Cache must invalidate when `research-pilot.db` changes.

### 13.10 Implementation Boundary

Backend implementation should add read-model builders and endpoint adapters, not mutate existing dataset schema.

Allowed for MVP:

- Add `tools/workspace_graph_read_models.py`.
- Add `/api/workspace-graph` handler in `tools/research_browser_server.py`.
- Reuse existing `build_project_graph_model`, `build_literature_model`, `build_experiments_model`, and `build_paper_graph_model` internally.
- Add tests for each mode/layer payload.
- Add tests proving arbitrary `metadata` fields are not rendered as primary UI labels/badges.

Not allowed for MVP:

- Adding `evaluation_settings` as a stored DB table.
- Changing existing dashboard mutation behavior.
- Replacing current DB import/writer logic.
- Making old page-specific APIs disappear before the new Workspace page is stable.

## 14. Visual And Layout Requirements

- Workspace first viewport should be the island, not a stack of dashboard sections.
- Canvas left, inspector right.
- Inspector fixed width with scrollable content.
- Graph canvas owns pan/zoom/minimap/controls.
- Breadcrumb visible in the island.
- Mode switch visible at island top.
- Theme switching must support both dark and light modes.
- Internal debug/read-only state should not be prominent user-facing UI.
- Cards should not be nested inside cards.
- Text must not overflow buttons, cards, nodes, or inspector sections.
- Graph nodes must be readable at default zoom, especially Literature paper nodes.

## 15. Low-Risk Cleanup

These changes can be implemented alongside the refactor:

- Project index: remove internal metric strip fields such as candidate, projectpaper, paper_count, rounds, claims, and latest status.
- Paper detail: hide `READ-ONLY PAPER STATE` as a main content block.
- Papers list: fix filter layout and obvious width/overflow issues.
- Technical Lineage: increase paper node readability.
- Experiments: remove card-only page once graph mode lands.

## 16. Acceptance Criteria

Workspace:

- `Workspace` tab exists and opens directly to `Understanding`.
- `Papers` remains available and functional.
- Workspace uses one island shell with mode switch, canvas, breadcrumb, and inspector.
- Initial Workspace load does not fetch every mode/layer.

Understanding:

- Project Overview default inspector lists Questions.
- Question click opens Question detail inspector without entering a new graph layer.
- Claim click enters Claim Focus.
- Paper source click enters Paper Focus.
- Existing Project -> Claim -> Paper drill behavior remains intact.

Literature:

- Literature mode preserves Technical Lineage semantics.
- Topic/route/paper inspector behavior remains clear.
- Paper nodes are readable at default zoom.
- Literature remains source lineage, not Understanding truth.

Experiments:

- Default layer is Evaluation Overview.
- Evaluation Overview shows Evaluation Setting nodes only.
- Evaluation Setting Focus shows dataset, benchmark/task, metric family, and related Experiment Designs.
- Experiment Design Focus shows models, baselines, protocol blocks, planned metric summary, and Run nodes.
- Run click opens terminal Run inspector detail.
- Run inspector shows Project Understanding Impact at bottom.
- Claim impact is downstream interpretation, not the graph entry point.

Backend/read model:

- `/api/workspace-graph` exists and returns `workspace-graph-v1` payloads.
- Workspace graph endpoint supports mode/layer lazy loading for Understanding, Literature, and Experiments.
- Evaluation Setting read model exists as a derived grouping, not a new stored DB table.
- Stable namespaced IDs support drill and cross-mode jumps.
- Run-to-claim impact reads from `entity_links` where available and shows an explicit empty state where not available.
- Workspace payloads include explicit `display` fields for visible labels, badges, tones, empty states, and actions.
- Frontend graph components do not render arbitrary `metadata` fields such as `metadata.role` directly.
- Unknown metadata values are hidden from primary UI and surfaced as read-model warnings or inspector provenance only.
- Existing page-specific APIs remain available during migration.

Cleanup:

- Project index no longer exposes low-value internal metrics.
- Paper detail no longer shows read-only state as a primary block.
- Theme switch continues to work in both dark and light modes.

## 17. Open Questions

- Should explicit links be added by agents between run-produced experiment evidence and project-scope evidence nodes when current imported data lacks `entity_links`?
- Which cross-mode jumps are required for first release versus best-effort?
- Should Paper Focus remain inside Understanding mode only, or become reusable when entering from Papers detail?
- Should Evaluation Setting become a stored table after MVP if users begin curating benchmark/task definitions directly?
- Should Workspace graph payloads include layout coordinates from backend, or should frontend layout remain fully client-derived for MVP?
- Which controlled role/badge enums should ship first for question and claim nodes, and which legacy demo roles should be mapped versus hidden?
