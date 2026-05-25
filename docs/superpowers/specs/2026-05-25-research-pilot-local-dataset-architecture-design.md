# Research-Pilot Local Dataset Architecture Design

Status: discussion design, not PRD, not implementation plan.

Date: 2026-05-25

## Product Frame

Research-Pilot is a local-first, project-centered research memory product.

The product core is not the dashboard, graph UI, Markdown reports, or a workflow system. The product core is a durable local research dataset that records what Research-Pilot understands about each project.

Primary interaction surface:

```text
human talks with agent
-> agent writes project dataset through tools
-> dashboard reads project dataset
-> human observes current project state and asks better next prompt
```

Core roles:

```text
agent = primary writer / operator
local dataset = product memory
dashboard = read-only observation surface
graph/table/pages = projections over the dataset
```

## Local First, Cloud Ready

The first implementation should be local-first because research data often contains unpublished ideas, private notes, experiment results, and sensitive project direction.

The design should remain cloud-ready by using:

- stable IDs;
- workspace and project IDs;
- schema versions;
- created/updated timestamps;
- actor fields;
- provenance;
- append-only update/audit history;
- attachment locators rather than hard-coded machine paths.

Future cloud use cases may include sync, backup, team collaboration, hosted dashboard, long-running agent jobs, and cross-project search. Cloud should not drive the first storage design.

Cloud implementation is out of scope for the first architecture refactor.

Non-goals:

```text
cloud auth
hosted dashboard
team permissions
online sync
hosted database
conflict-resolution UI
```

The first architecture should still avoid choices that block later cloud support.

Cloud-ready requirements:

```text
stable text IDs for all durable entities
workspace_id and project_id boundaries
schema versioning and migrations
created_at / updated_at timestamps
created_by / updated_by or actor fields
append-only audit events
portable artifact locators
source/provenance fields
exportable project dataset bundles
```

Artifact paths should not depend on absolute machine paths. Store locators in a portable shape:

```text
locator_type = local_path | cloud_uri | zotero_attachment | url
locator = artifacts/EXP3/run1/table.csv
```

The preferred long-term cloud shape is local-first sync, not cloud-first SaaS:

```text
local research-pilot.db <-> optional cloud sync
```

This matches the privacy expectations of unpublished research while preserving future backup, collaboration, and hosted-view possibilities.

## Workspace Model

A Research-Pilot workspace is a local research dataset.

It contains multiple projects. Each project owns its own sources, understanding, experiments, literature structure, and activity history.

The architecture should be project-centered:

```text
Workspace
└── Projects
    ├── Brief
    ├── Sources / Papers
    ├── Project Understanding
    ├── Experiments
    ├── Literature Structure
    └── Activity / Updates
```

Every core entity should be scoped by `project_id`.

## Domain Model

### 1. Brief

Stable project frame.

Purpose:

```text
Define what the project is, why it exists, and its current high-level direction.
```

Typical fields:

```text
project_id
title
slug
summary
main_question
working_hypothesis
target_contribution
stage
status
created_at
updated_at
```

Brief should not contain all claims, papers, experiments, or literature review detail.

### 2. Sources / Papers

Source identity and reading state.

Purpose:

```text
Record what material the project has seen, read, used, rejected, or archived.
```

Source examples:

```text
paper
pdf
url
note
dataset
benchmark
experiment_result
manual_reference
zotero_item
```

Source stores identity and reading state only. Deep paper understanding should not live inside the Source object.

Important correction:

```text
paper deep-read content belongs to Project Understanding as scope=paper nodes.
```

### 3. Project Understanding

Core project argument structure.

This should preserve the existing graph ontology instead of replacing it with a simpler claim/evidence model.

Core ontology:

```text
Question
Claim
Evidence
Warrant
Limitation
ReasoningLink
TranslationLink
```

Understanding nodes support multiple scopes:

```text
paper
project
program
```

Interpretation:

```text
UnderstandingNode(scope=paper) = paper-level understanding from a source.
UnderstandingNode(scope=project) = project-level understanding.
TranslationLink = paper/program understanding mapped into project understanding.
ReasoningLink = argument relation among understanding nodes.
```

Reasoning links should preserve the current expressive structure:

```text
from_nodes -> to_nodes
with warrant_nodes
with limitation_nodes
relation
confidence
human_review
source_refs
```

Gap is not part of the core ontology yet. Many gaps can be derived from limitations, unresolved questions, or missing evidence needs. Add a `gap` node type only after stronger evidence that it needs first-class storage.

### 4. Experiments

Empirical evidence mechanism for project understanding.

Purpose:

```text
Record planned empirical validation and completed/imported/local/replication results.
```

Core objects:

```text
Experiment
ExperimentRun
ExperimentMetric
ExperimentArtifact
```

Important distinction:

```text
Experiment.status = lifecycle of the experiment design.
ExperimentRun.origin_type = where the evidence came from.
```

Example origins:

```text
local
imported_paper
replication
external
manual
```

Experiment results should not remain isolated. Important runs should produce project-level evidence:

```text
ExperimentRun
-> UnderstandingNode(scope=project, node_type=evidence)
-> ReasoningLink supports/weakens Claim
```

Metrics belong to runs. Metrics do not directly support claims; evidence nodes do.

### 5. Literature Structure

Project-scoped cross-paper research landscape.

Purpose:

```text
Organize how sources/papers relate to one another and how the project is positioned in the surrounding research area.
```

Core objects:

```text
LiteratureLane
LiteratureItem
LiteratureRelation
ProjectPositioning
```

Literature Structure does not store single-paper deep reading. That is `UnderstandingNode(scope=paper)`.

Literature Structure does not store project claims. Those are `UnderstandingNode(scope=project, node_type=claim)`.

It stores:

```text
technical lanes
paper roles
cross-paper relations
project positioning in the research landscape
```

Examples:

```text
AGD20K = benchmark_provider
LOCATE = baseline
Zhang 2026 = anchor
Zhang 2026 uses_benchmark_from AGD20K
Zhang 2026 compares_with LOCATE
```

### 6. Activity / Updates

Change history and provenance.

Purpose:

```text
Record who/what changed the project dataset, why, and what entities changed.
```

Core objects:

```text
ActivitySession
Update
AuditEvent
```

Meaning:

```text
ActivitySession = one agent/human work session.
Update = human-readable semantic change summary.
AuditEvent = machine-readable entity-level change record.
```

This replaces the idea of standalone UnderstandingUpdate as a separate architecture concept. UnderstandingUpdate becomes one kind of Update in the broader Activity model.

Audit events should be append-only.

## Cross-Domain Relationships

Most important relationships:

```text
Project has Source
Source has paper-scope UnderstandingNode
paper-scope UnderstandingNode translates_to project-scope UnderstandingNode
project-scope UnderstandingNodes connect via ReasoningLink
Experiment tests UnderstandingNode
ExperimentRun produces Evidence UnderstandingNode
LiteratureItem represents Source
ActivitySession -> Update -> AuditEvent records changes to any entity
```

Detailed relationships:

```text
Source -> UnderstandingNode(scope=paper)
UnderstandingNode(scope=paper) -> TranslationLink -> UnderstandingNode(scope=project)
UnderstandingNode(scope=project) -> ReasoningLink -> UnderstandingNode(scope=project)
Experiment -> tests -> UnderstandingNode(question/claim/limitation)
ExperimentRun -> produces -> UnderstandingNode(evidence)
ExperimentRun -> has -> ExperimentMetric
ExperimentRun -> has -> ExperimentArtifact
LiteratureItem -> represents -> Source
LiteratureLane -> has -> LiteratureItem
LiteratureRelation -> connects -> LiteratureItem
LiteratureItem/Lane/Relation -> can inform -> UnderstandingNode
ActivitySession -> Update -> AuditEvent -> any entity
```

## Conceptual Schema v1

Core entities:

```text
Project
Source
UnderstandingNode
UnderstandingLink
UnderstandingLinkEndpoint
Experiment
ExperimentRun
ExperimentMetric
ExperimentArtifact
LiteratureLane
LiteratureItem
LiteratureRelation
ProjectPositioning
ActivitySession
Update
AuditEvent
EntityLink
```

`EntityLink` is a generic non-argument relationship table for cross-domain links that are not Q/C/E/W/L reasoning links.

Examples:

```text
Experiment tests Claim
ExperimentRun produces Evidence
LiteratureItem provides baseline for Experiment
LiteratureLane informs Question
```

## Dashboard Position

Dashboard is a global read-only frontend application.

It should not own durable state. It should read API view models produced from the local dataset.

Examples:

```text
Project page = Brief + active project understanding + recent updates
Paper page = Source + paper-scope understanding + translation links
Experiments page = experiments + runs + metrics + produced evidence + linked claims
Literature page = lanes + items + relations + positioning
Graph page = understanding nodes + understanding links
```

## Read Model Layer

The DB schema and dashboard JSON should not be the same contract.

The local DB is the normalized storage model. Its job is long-term correctness, stable relationships, validation, auditability, and future sync.

Dashboard pages need page-shaped data. Their job is fast reading and clear display. They should not know the internal table layout or reproduce backend joins.

Therefore Research-Pilot should use a read model layer:

```text
research-pilot.db
-> read model builders
-> dashboard/API JSON
-> existing read-only dashboard
```

Read models are not durable project state. They are runtime projections or rebuildable JSON responses produced from the DB.

This lets the project redesign storage without forcing a dashboard rewrite.

Examples:

```text
Experiments page read model
  combines experiments, runs, metrics, artifacts, produced evidence, linked claims, and sources.

Project graph read model
  combines understanding_nodes, understanding_links, endpoints, and source metadata into graph nodes/edges.

Paper detail read model
  combines source identity, paper-scope understanding nodes, and translation links into project contributions.
```

Principle:

```text
DB schema = truth/storage model.
Read model = dashboard consumption model.
Dashboard = read-only frontend over read models.
```

## Storage Direction

Target direction:

```text
research-pilot.db as the primary local workspace store
```

Existing Markdown, JSONL, JSON, snapshots, and dashboard files should not be deleted during the transition.

Migration should be staged:

```text
legacy workspace files
-> importer
-> research-pilot.db
-> read APIs
-> dashboard views
```

Use a strangler migration:

```text
new DB-backed APIs wrap old data gradually
old files remain readable
dashboard and demo affordance content are preserved
```

## Open Questions

1. Should `gap` become a first-class `UnderstandingNode` type, or remain derived from limitations, missing evidence, and unresolved questions?
2. Should benchmarks and datasets remain Sources in v1, or become first-class entities?
3. Should `EntityLink` be generic, or should some cross-domain links become dedicated tables immediately?
4. How much of current `graph-event-v1` should be preserved as-is versus migrated into DB tables?
5. What is the first vertical slice for migration: Experiments, Project Understanding, or Sources/Papers?

## Current Recommendation

Use Experiments as the first vertical slice because it is currently isolated enough to test the new architecture without breaking Project Graph.

Target slice:

```text
legacy experiments.json + demo paper evidence
-> research-pilot.db experiment tables
-> DB-backed /api/experiments
-> improved read-only Experiments dashboard
```

This slice must preserve Demo Visual Affordance data and current dashboard behavior until the new path is verified.

## Demo Visual Affordance Preservation

The Demo Visual Affordance project should be treated as a golden fixture for the architecture refactor.

The new storage design may replace legacy storage paths, but it must preserve the current demo's product capabilities and content.

The demo currently exercises:

```text
project brief
sources/papers
deep paper dossiers
project understanding graph
literature / technical lineage
experiments and imported evidence
recent understanding updates
dashboard pages
```

Required preservation targets:

```text
Project:
  Demo Visual Affordance title, summary, main question, stage.

Sources/Papers:
  affordance-related source list and paper identities.

Paper Understanding:
  deep-read paper content must be representable as UnderstandingNode(scope=paper).

Project Understanding:
  Q/C/E/W/L nodes and ReasoningLinks must be representable from the DB-backed model.

Translation/Contribution:
  paper evidence must be mappable into project evidence and project claims.

Literature Structure:
  lanes, paper roles, relations, and project positioning must be representable.

Experiments:
  experiment designs, imported paper runs, metrics, artifacts, and claim impacts must be representable.
```

Experiment fixture expectations:

```text
total_experiments = 4
total_runs = 5
imported_paper_runs = 5
local_runs = 0

Only Interaction:
  KLD = 1.825
  SIM = 0.271
  NSS = 1.050

Interaction x Geometry:
  KLD = 1.493
  SIM = 0.326
  NSS = 1.090
```

Dashboard preservation expectations:

```text
Project page opens with project state.
Sources/Papers page opens with non-empty source data.
Project graph page opens with Q/C/E/W/L graph data.
Literature/lineage page opens with non-empty literature structure.
Experiments page opens with experiment designs, runs, and metrics.
```

Acceptance direction:

```text
legacy demo files
-> importer
-> research-pilot.db
-> DB-backed read models
-> existing dashboard-compatible APIs
```

The refactor should not depend on preserving legacy files as the long-term storage model, but it must preserve the demo as observable product behavior.
