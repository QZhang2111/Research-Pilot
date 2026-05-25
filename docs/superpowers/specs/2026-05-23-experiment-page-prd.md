# Experiment Page PRD

Date: 2026-05-23
Status: Draft v0.1

## 1. Summary

Research-Pilot should replace the current `Experiment Proposals` dashboard concept with a read-only `Experiments` page. The page should show both planned experiment design and completed experimental evidence for a research project.

The user still works through agent chat and local files. The dashboard observes: what experiment is planned, what benchmark and dataset define it, what runs have completed, what results exist, and how those results affect project claims, gaps, and next moves.

## 2. Product Thesis

The experiment page is not a task planner and not a proposal inbox. It is an evidence board for project-owned experiments.

```text
Agent designs or reviews experiment
-> Research-Pilot records experiment design / result
-> read-only dashboard shows experiment state
-> user sees what evidence exists and what remains weak
-> user asks agent the next better experiment or interpretation prompt
```

## 3. Problem

The existing dashboard page is framed around `Experiment Proposals`. That is too narrow for the new Research-Pilot direction.

It can show suggested experiments, but it cannot clearly answer:

- What benchmark/dataset defines the actual experiment?
- What protocol will be run?
- Which model variants or baselines are involved?
- What has already completed?
- What metrics or artifacts exist?
- Which claims are supported, weakened, or still uncertain?

This makes experiments feel like optional planning notes instead of durable project evidence.

## 4. Product Goal

Build a read-only experiment page that answers:

```text
What experiment are we planning?
What evidence has this project already produced?
What claim/gap does each experiment address?
What remains uncertain?
What should the agent do next?
```

## 5. Target User

Primary user:

A researcher using an AI agent to design, run, inspect, or interpret experiments for an ongoing project.

They need a stable place to observe:

- experiment intent
- benchmark and dataset choices
- protocol details
- completed runs
- result interpretation
- claim impact
- remaining uncertainty

Non-target user:

A user who wants the dashboard to run experiments, edit records, schedule jobs, or replace experiment tracking tools.

## 6. Product Principles

### Read-only observation

The website does not create, edit, approve, or execute experiments. It renders local project state produced by agent/CLI work.

### Design and evidence together

Planned design and completed evidence must live on the same page. A user should not need to open one page for proposals and another for results.

### Claim-linked

Every useful experiment should connect to at least one claim, gap, limitation, or project question when possible.

### Artifact-aware

Completed evidence should point to artifacts: result files, logs, tables, figures, notebooks, reports, or experiment notes.

### Lightweight before rigorous

The first version should support simple local Markdown/JSON records. It should not require a full ML experiment tracking system.

## 7. Non-Goals

This improvement does not include:

- dashboard editing
- running experiments from the browser
- job queue management
- notebook execution
- MLflow/W&B integration
- mandatory graph delta approval
- replacing graph evidence logic
- statistical audit tooling
- automatic metric validation
- full paper-writing output

## 8. Page Concept

Rename:

```text
Experiment Proposals -> Experiments
```

The page should have four read-only sections, ordered by user usefulness rather than internal data shape.

### 8.1 Experiment Evidence Summary

Purpose:

Give a compact view of the project experiment landscape.

Fields:

- total experiments
- planned
- running
- completed
- blocked
- strongest current evidence
- highest-priority unresolved experiment

### 8.2 Active Experiment Designs

Purpose:

Show planned or active experiment protocols.

Fields:

- experiment id
- title
- status
- research question
- hypothesis
- linked claims/gaps
- benchmark
- dataset
- model variants / baselines
- metrics
- protocol summary
- expected evidence
- risk or weakness
- next action

Recommended statuses:

```text
planned
ready
running
blocked
completed
superseded
```

### 8.3 Results / Evidence

Purpose:

Show completed or partial runs.

Fields:

- run id
- parent experiment id
- run status
- completed date
- metrics
- result summary
- interpretation
- artifacts
- claim impact
- remaining weakness

Recommended run statuses:

```text
not_started
running
completed
failed
inconclusive
```

Recommended claim impact labels:

```text
supports
weakens
contests
inconclusive
needs_replication
```

### 8.4 Next Experiment Moves

Purpose:

Show what the agent recommends doing next.

Move types:

```text
design
run
compare
ablate
validate
replicate
interpret
revise_claim
```

Each next move should include:

- rationale
- suggested prompt
- linked experiment or claim

## 9. Public Object Model

Expose these objects to the dashboard:

```text
Experiment
ExperimentRun
ExperimentArtifact
ExperimentMetric
ExperimentImpact
ExperimentNextMove
```

### Experiment

```text
id
title
status
question
hypothesis
linked_claims
linked_gaps
benchmark
dataset
models
baselines
metrics
protocol
expected_evidence
risks
next_action
```

### ExperimentRun

```text
id
experiment_id
status
evidence_type
completed_at
summary
metrics
artifacts
interpretation
claim_impacts
weaknesses
```

Recommended evidence types:

```text
imported_paper_evidence
local_experiment_result
external_result
replication_result
```

### ExperimentArtifact

```text
type
path_or_url
label
description
```

## 10. Data Location

Recommended durable project files:

```text
wiki/projects/<ProjectId>/experiments/
  experiments.json
  artifacts/
```

MVP should use one JSON file:

```text
wiki/projects/<ProjectId>/experiments/experiments.json
```

That file contains:

```text
experiments[]
runs[]
next_moves[]
```

Legacy proposal files may remain under:

```text
wiki/projects/<ProjectId>/experiment-proposals/
```

Do not migrate legacy proposal files in the MVP. The new page should read the new `experiments/experiments.json` model. If legacy proposal artifacts exist but no experiment records exist, the dashboard may show a read-only note such as `Legacy proposals found`, but it should not silently convert them into completed evidence.

## 11. Demo Affordance Example

The demo project should include one planned experiment and one completed/partial evidence example.

### Planned Experiment

Title:

```text
Geometry-interaction ablation on affordance grounding
```

Purpose:

Test whether affordance grounding improves when geometric part cues and interaction priors are composed, compared with each signal alone.

Benchmark / dataset:

```text
AGD20K or UMD affordance segmentation
```

Protocol:

- run geometry-only baseline
- run interaction-prior-only baseline
- run fused geometry + interaction method
- compare spatial mask quality
- inspect failure cases where object semantics may dominate

Metrics:

```text
mIoU
F1
pointing accuracy
qualitative contact-region consistency
```

Linked claims:

```text
C2: geometric structure supports affordance localization
C3: interaction priors localize plausible contact regions
C4: fusion supports mechanistic affordance reasoning
```

### Completed / Partial Evidence

Use demo baseline paper evidence as read-only imported evidence:

```text
Zhang 2026 reports that geometry-aware VFM features correlate with better affordance probes, verb-conditioned generative attention localizes plausible interaction regions, and fused signals produce competitive zero-shot affordance maps.
```

Claim impact:

```text
C4: supports, but weak / needs replication
```

Remaining weakness:

```text
Evidence is imported from the baseline paper, not reproduced in this local workspace.
```

Evidence type:

```text
imported_paper_evidence
```

## 12. Dashboard Requirements

P0:

- Rename nav/page title from `Experiment Proposals` to `Experiments`.
- Remove proposal-first copy from normal dashboard UX.
- Show planned experiment designs and completed result evidence on one page.
- Add empty state that explains no experiments are recorded yet.
- Add demo affordance experiment data.
- Distinguish imported paper evidence from local experiment results.
- Keep page read-only.

P1:

- Show a legacy proposal note when old `experiment-proposals/` artifacts exist and no new experiment records exist.
- Show claim/gap links where IDs match project graph nodes.
- Show artifact links when local files exist.
- Add status counts.

P2:

- Add richer run comparison tables.
- Add result trend or metric visualization.
- Add optional advanced review status for turning result evidence into graph deltas.

## 13. Acceptance Criteria

MVP is successful when:

1. User opens Demo Visual Affordance.
2. User opens `Experiments`.
3. Page shows at least one planned experiment design.
4. Page shows at least one completed or partial evidence record.
5. Page shows benchmark/dataset, metrics, protocol, linked claims, and weaknesses.
6. Page does not use `Experiment Proposals` as the main framing.
7. Page is read-only.
8. Dashboard does not require graph/delta terminology to understand experiment state.
9. Imported evidence is visually distinct from locally completed experiment runs.

## 14. Risks

### Risk: Page becomes fake evidence

Mitigation:

Use explicit statuses and labels:

```text
planned
completed
imported evidence
local result
needs replication
inconclusive
```

### Risk: Page becomes a workflow manager

Mitigation:

No browser editing, no run buttons, no queue state beyond read-only status.

### Risk: Data model grows too heavy

Mitigation:

Use one compact experiment JSON model first. Avoid external tracking integrations.

### Risk: Confusion with graph evidence

Mitigation:

Say experiment results can inform claims, but graph acceptance remains advanced/internal.

## 15. Recommended Implementation Direction

Use a small read model/API:

```text
GET /api/experiments?project=<ProjectId>
```

It should read project-local experiment records and return:

```text
{
  "schema_version": "experiments-v1",
  "project_id": "...",
  "summary": {},
  "experiments": [],
  "runs": [],
  "next_moves": []
}
```

Keep legacy endpoint support temporarily:

```text
/api/experiment-proposals
```

But new dashboard code should prefer:

```text
/api/experiments
```

## 16. Open Questions

1. Should future local experiment results be appended through `UnderstandingUpdate`, a separate experiment update event, or both?
2. Should `Experiments` link directly into `Recent Understanding` when a result changes project claims?
