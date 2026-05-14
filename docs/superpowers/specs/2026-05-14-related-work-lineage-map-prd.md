# Related Work Lineage Map PRD

Date: 2026-05-14
Status: Draft

## 1. Executive Summary

Research Pilot should add a project-scoped, paper-only related work lineage map that helps a researcher understand the technical development routes around a project and position the project's contribution. The feature should take either baseline papers or a coarse research direction, narrow the scope when needed, discover representative related work, organize papers into time-ordered technical lanes, and render a dashboard read model with route explanations and a paper table. It is not a citation graph, not a generic literature review, and not a Project Understanding Graph update workflow.

## 2. Problem Statement

### Who Has This Problem

The primary user is the researcher operating a Research Pilot project. The agent is a collaborator that searches, organizes, and drafts candidate route maps, but the feature is designed for human understanding.

### What Is The Problem

Research Pilot can maintain project understanding through paper dossiers, graph events, deltas, reports, and dashboard read models, but it does not yet show how the surrounding related work area developed over time. Users can collect papers and ask for evidence synthesis, but they still lack a compact visual answer to:

- what major technical routes exist around this project;
- which papers define each route;
- how those routes evolved over time;
- which route the project is closest to;
- where a project contribution might sit relative to prior work.

### Why It Is Painful

Without a lineage map, early project work can become either too broad or too graph-heavy. A user may only have a coarse direction or one baseline paper, before a Project Understanding Graph exists. For that stage, asking for project evidence synthesis is premature because the user is still trying to understand the field shape and pick the right local scope.

### Evidence From Current System

- Workspace stages explicitly include early `project shell` state before graph maturity; agents should inspect stage before next actions (`docs/guides/workspace.md:32`).
- Existing evidence synthesis is graph-facing and prepares graph deltas, not a human-facing literature map (`templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md:10`, `templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md:12`).
- Dashboard is already a read-model observer and may inspect project markdown/read models without becoming source of truth (`docs/guides/dashboard.md:3`, `docs/guides/dashboard.md:5`).

## 3. Target Users And Personas

### Primary Persona

Researcher using Research Pilot for an early or mid-stage project.

Jobs to be done:

- When I have a rough research direction, help me narrow it into a concrete technical route and baseline paper set.
- When I have one or two baseline papers, show the major related-work routes around them.
- When I inspect a project, show where the project contribution might fit in the surrounding technical lineage.

### Secondary Persona

Agent operating Research Pilot workflows.

Jobs to be done:

- Search for representative papers.
- Group papers into technical lanes.
- Propose candidate route names, paper roles, and key cross-route relationships.
- Preserve source evidence and review status.
- Avoid silently promoting lineage-map content into Project Understanding Graph truth.

## 4. Strategic Context

Research Pilot's value is agent-operated research memory, not a generic note app. Current project memory is strong once questions, claims, evidence, warrants, limitations, and D* deltas exist. The gap is earlier and more exploratory: users need a field-shape artifact that helps them decide which baselines matter before they can cleanly state project claims.

This feature should become the primary user-facing related-work workflow. Existing `project-evidence-synthesis` remains useful as a graph-update bridge, but it should not be treated as the lineage workflow.

## 5. Existing System Alignment

This feature must conform to the current Research Pilot architecture before any implementation plan is written.

### Current Boundaries To Preserve

- Tools execute local workflows but are not research truth (`tools/README.md:3`).
- Append-only Project Understanding Graph truth lives in `wiki/graphs/events/**/*.jsonl` (`tools/README.md:7`).
- `wiki/graphs/graph.db`, snapshots, reports, and `.dashboard/index.json` are rebuildable read models (`tools/README.md:9`).
- Zotero remains the normal paper metadata/PDF source of truth (`tools/README.md:10`).
- Dashboard reads `.dashboard/index.json`, graph snapshots, `wiki/graphs/graph.db`, and project markdown (`docs/guides/dashboard.md:5`).
- Dashboard must remain a read-model observer, not graph truth (`docs/guides/dashboard.md:12`).
- User workspace already has `wiki/projects/`, `wiki/_system/workflows/`, and `.research-pilot/` as established extension points (`docs/guides/workspace.md:5`).

### Existing Patterns To Reuse

- Add a skill under `skills/` for agent routing.
- Add a workspace workflow under `templates/workspace/wiki/_system/workflows/`.
- Add agent-facing CLI helpers under `tools/` when generation or validation needs deterministic behavior.
- Add dashboard read-model building through existing dashboard index/read-model patterns.
- Add tests following existing tool, dashboard, and workflow tests.

### Storage Path Alignment Gate

Before an implementation plan proposes new lineage artifact paths, it must inspect existing project artifact conventions and produce a storage-path alignment section. That section must cite the local files or tests that establish the convention, propose exactly where lineage source artifacts and dashboard read models should live, and explain why those paths fit Research Pilot's current workspace model. Agents must not invent new project directories or read-model locations without this alignment step.

### Structures Not To Invent Casually

- Do not create a parallel graph-truth system.
- Do not store related-work lineage as D* graph events.
- Do not create non-paper nodes for dataset, benchmark, method family, survey, or system in MVP.
- Do not make dashboard mutate lineage data in MVP.
- Do not require an existing Project Understanding Graph.

### Relationship To `project-evidence-synthesis`

`related-work-lineage` is for human field understanding and project positioning.

`project-evidence-synthesis` is for translating a set of papers, dossiers, search results, or experiment notes into project-level understanding and D* proposal pressure (`templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md:67`).

The new skill should not replace the graph-update boundary. Product-level behavior should make `related-work-lineage` the primary user-facing related-work workflow, while preserving `project-evidence-synthesis` as a later bridge from read papers to Project Understanding Graph changes.

## 6. Solution Overview

### Core Concept

Add `related-work-lineage`: a paper-only technical lineage map for one Research Pilot project.

The map shows time-ordered technical lanes. Each node is a paper. A paper can carry attributes such as method paper, dataset paper, benchmark paper, survey paper, theory paper, system paper, milestone, anchor, or baseline. Dataset and benchmark papers remain papers; they are not separate node types.

### Input Modes

1. Baseline paper mode:
   - user provides one or two baseline papers;
   - system uses them as anchors;
   - lineage map generation can start directly.

2. Coarse direction mode:
   - user provides a rough topic or direction;
   - system must not generate a full map directly;
   - system first produces 3 to 5 candidate subfields or technical routes;
   - each candidate route includes 1 to 2 baseline paper candidates;
   - user chooses route/anchor before map generation.

An existing Project Understanding Graph may provide context, but it is optional. A project shell plus user direction must be enough to start.

### Map Shape

- Project-scoped.
- Paper-only nodes.
- Timeline layout.
- Each technical route is a lane.
- Papers are ordered by publication/submission date within their lane.
- Track-internal sequence can be inferred by date.
- Explicit edges are reserved for cross-route influence, branch, convergence, or strong contrast.

### Review Model

Related-work lineage does not use D*. MVP uses local review state inside the lineage artifact:

- paper candidate / approved / rejected;
- route candidate / approved / rejected;
- explicit edge candidate / approved / rejected.

Lineage output must not silently update Project Understanding Graph truth. If the user later wants a lineage insight to become a project claim, evidence, warrant, or limitation, that is handled by the existing graph delta flow.

### Output

MVP output includes:

- dashboard timeline route map;
- route descriptions;
- paper table;
- short project positioning note;
- source evidence for each paper;
- review status for papers, routes, and explicit edges.

MVP does not generate a full literature review draft.

## 7. Success Metrics

### Primary Metric

For a project with a coarse direction or 1 to 2 baseline papers, the user can obtain a project-scoped lineage map of 20 or fewer representative papers that makes the main technical routes understandable.

### Secondary Metrics

- Every paper node has a verifiable identity field such as DOI, arXiv ID, OpenReview ID, ACL Anthology ID, Semantic Scholar ID/URL, or official page URL.
- Every paper node has source evidence.
- No generated map requires an existing Project Understanding Graph.
- Dashboard can render the lineage map as a read model.
- Users can request changes through chat without dashboard editing.

## 8. User Stories And Requirements

### Story 1: Generate From Baseline Papers

As a researcher with one or two baseline papers, I want Research Pilot to generate a project-scoped related-work lineage map so I can understand the surrounding technical routes.

Acceptance criteria:

- User can provide baseline paper titles, URLs, IDs, or dossier/source references.
- System verifies paper identity where possible.
- System builds a map with at most 20 representative papers.
- Map includes technical lanes, paper roles, dates, route descriptions, and a positioning note.
- Map does not create Project Understanding Graph events.

### Story 2: Narrow From Coarse Direction

As a researcher with only a coarse topic, I want Research Pilot to narrow the topic into candidate routes and baseline papers before generating a lineage map.

Acceptance criteria:

- System outputs 3 to 5 candidate technical routes.
- Each route includes 1 to 2 candidate baseline papers.
- System explains why each route is relevant and what it excludes.
- User must choose route/anchor before map generation.
- System must not build a broad map directly from a vague topic.

### Story 3: Inspect In Dashboard

As a researcher, I want to inspect the lineage map in the Research Browser so I can see the time-ordered development routes and paper table.

Acceptance criteria:

- Dashboard renders timeline lanes.
- Dashboard distinguishes inferred track sequence from explicit lineage edges.
- Dashboard shows route descriptions and paper table.
- Dashboard is read-only in MVP.

### Story 4: Revise Through Chat

As a researcher, I want to tell the agent that a paper, route, or edge is wrong so the map can be revised without requiring dashboard editing.

Acceptance criteria:

- User can ask through chat to remove, move, rename, approve, or reject map items.
- Agent updates the lineage artifact.
- Dashboard reflects updated read model after rebuild/refresh.

### Story 5: Preserve Graph Boundary

As a researcher, I want lineage insights to remain separate from project graph truth unless I explicitly decide to convert them into project understanding.

Acceptance criteria:

- Lineage generation never writes D* events.
- Lineage artifacts can be cited later by `project-evidence-synthesis` or a successor graph-update workflow.
- Any graph-level update still requires the existing human-gated delta path.

## 9. Functional Requirements

### Paper Node Requirements

Each paper node must include:

- stable local ID;
- title;
- year and optional month;
- verified identity field when available;
- source URL;
- route/lane;
- paper role attributes;
- review status;
- source evidence;
- optional flags for anchor, baseline, or milestone.

### Explicit Edge Requirements

Explicit edges are optional and limited to important cross-route or non-obvious relationships. They must include:

- source paper;
- target paper;
- relation;
- rationale;
- confidence;
- review status;
- source evidence.

Track-internal chronological sequence should be inferred unless there is a reason to store an explicit relationship.

### Limits

- Default maximum paper count is 20.
- If the topic requires more than 20 papers, the agent must ask the user to narrow scope or split into multiple lineage maps.
- Low-signal follow-ups should be excluded.

### Source Requirements

The PRD does not bind implementation to a specific provider. Acceptable identity/source evidence includes DOI, arXiv ID, OpenReview ID, ACL Anthology ID, Semantic Scholar ID/URL, official project page, venue page, or another stable public source.

## 10. Out Of Scope

- Citation graph visualization.
- Full literature review prose generation.
- Dashboard editing.
- More than 20 papers per MVP map.
- Non-paper nodes.
- Automatic D* generation from lineage output.
- Workspace-level or program-level global maps.
- Claim-only lineage maps.
- Exhaustive survey completeness.

## 11. Dependencies And Risks

### Dependencies

- Existing workspace project shell behavior.
- Existing skill/workflow installation pattern.
- Existing dashboard read-model build and serve path.
- Public paper identity sources.

### Risks

- Coarse topics may stay too broad.
  - Mitigation: require scope narrowing and user anchor selection.

- Agent may invent lineage relationships.
  - Mitigation: require source evidence, confidence, and review status.

- Feature may drift into citation graph.
  - Mitigation: explicit non-goal and relation vocabulary focused on technical development, not citation.

- Feature may duplicate `project-evidence-synthesis`.
  - Mitigation: keep lineage as field-shape artifact; keep evidence synthesis as graph-update bridge.

- Agent may ignore existing architecture.
  - Mitigation: require Existing System Alignment in the implementation design and plan.

## 12. Open Questions

- Exact lineage artifact storage path should be decided only through the required storage-path alignment gate.
- Exact dashboard route/page structure should be decided by matching current dashboard index patterns.
- Whether `project-evidence-synthesis` should later be renamed to a narrower graph-update skill is outside this MVP but should remain open.
- Whether approved lineage papers should integrate with Zotero status mirroring is outside this MVP.
