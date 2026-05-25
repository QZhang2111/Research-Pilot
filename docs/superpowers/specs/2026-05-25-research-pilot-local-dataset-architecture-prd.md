# Research-Pilot Local Dataset Architecture PRD

Status: draft PRD

Date: 2026-05-25

Related design note: `docs/superpowers/specs/2026-05-25-research-pilot-local-dataset-architecture-design.md`

## 1. Executive Summary

Research-Pilot should be re-architected around a project-centered local research dataset. The product should treat each workspace as a durable local dataset of projects, sources, paper understanding, project understanding, experiments, literature structure, and activity history. Agents should be the primary writers through typed tools. The dashboard should remain a read-only frontend that observes API read models generated from the local dataset. This refactor should preserve the current dashboard and Demo Visual Affordance project behavior while replacing scattered storage paths with a unified `research-pilot.db` primary local store.

## 2. Product Thesis

Research-Pilot is a local-first, project-centered research memory product for agent-assisted research.

The product core is not the dashboard, graph UI, Markdown reports, or workflow commands. The product core is:

```text
a durable local research dataset that records what Research-Pilot understands about each project
```

Primary loop:

```text
human talks with agent
-> agent does research work
-> agent writes structured project dataset through tools
-> dashboard reads project dataset through read models
-> human observes current state and asks better next prompt
```

Core roles:

```text
agent = primary writer / operator
local dataset = product memory
dashboard = read-only observation surface
graph/table/pages = projections over the dataset
```

## 3. Current Problem

The current repository has useful concepts but fragmented storage.

Current durable and generated state is split across:

```text
Markdown project files
paper dossiers
graph event JSONL
graph snapshots
generated graph.db
understanding update JSONL
experiments.json
dashboard index JSON
dashboard-specific read builders
```

This creates product and engineering problems:

- The product center is unclear: graph, dashboard, deltas, paper dossiers, and experiments each look like separate systems.
- Agent writing is not unified around one project dataset model.
- Dashboard read paths have to understand multiple legacy storage formats.
- Experiment records are not cleanly connected to project understanding.
- Paper deep reads and project-level understanding are easy to confuse.
- Existing graph ontology is valuable but lives in a legacy event/read-model path rather than the future dataset core.
- Cloud readiness is difficult because durable IDs, audit events, and portable artifact locators are not consistently modeled.

The refactor should not optimize for preserving old storage shape. It should optimize for the most stable, convenient, and conceptually correct product architecture.

## 4. Target Users

Primary user:

```text
a researcher using an AI agent to understand and develop a research project
```

They ask the agent to:

- start or update a project;
- read papers;
- perform deep paper analysis;
- compare methods;
- map related work;
- import experiment evidence from papers;
- record local experiment results;
- revise claims and limitations;
- inspect the current project state in a dashboard.

Primary pain:

```text
agent work helps in the moment, but project understanding fragments across chats, files, graph artifacts, and dashboard read models
```

Research-Pilot should make agent-generated project memory durable, inspectable, and project-centered.

## 5. Target User Loop

Research-Pilot should support these loops.

### Project Start

```text
User: Use Research-Pilot to track this project.
Agent: creates project brief and initial project understanding.
Dashboard: shows project state.
```

### Source / Paper Intake

```text
User: Read this paper and track what matters.
Agent: records source identity and reading state.
Agent: creates paper-scope understanding nodes.
Agent: translates paper understanding into project understanding when relevant.
Dashboard: shows paper understanding and project contribution.
```

### Project Understanding Update

```text
User: Compare this with our current claim.
Agent: updates project-scope Q/C/E/W/L nodes and reasoning links.
Dashboard: shows current argument structure and recent changes.
```

### Experiment Evidence

```text
User: Use this paper's experiment result as evidence.
Agent: records experiment/run/metrics as imported paper evidence.
Agent: creates project evidence node and reasoning link to claim.
Dashboard: shows experiments and graph evidence without implying local completion.
```

### Local Experiment Result

```text
User: Here are results from my run.
Agent: records local run, metrics, artifacts, and produced project evidence.
Dashboard: distinguishes local result from imported paper evidence.
```

### Literature Structure

```text
User: Map related work around this project.
Agent: records lanes, paper roles, relations, and project positioning.
Dashboard: shows literature structure using existing views/read models.
```

### Human Correction

```text
User: This relation is wrong.
Agent: writes a correction update through typed tools.
Dashboard: reflects corrected state and recent change.
```

## 6. Product Principles

### Project-Centered

Every durable research object should be scoped to a project. Papers, experiments, and literature relations are meaningful because of their role in a project.

### Local-First

The first product version should store the core dataset locally. Research data often includes unpublished ideas, private notes, and early experiment results.

### Cloud-Ready

The local schema should not block future sync, backup, collaboration, or hosted dashboards. Cloud implementation is out of scope for this refactor.

### Agent-Written, Tool-Validated

Agents should not write raw SQL or mutate arbitrary files. Agents should write through typed tools that validate domain rules and record audit history.

### Dashboard Read-Only

The existing dashboard should remain a read-only frontend. Corrections happen through chat, not direct dashboard editing.

### Preserve Existing Graph Semantics

The existing Q/C/E/W/L argument ontology is a core product asset. The refactor should preserve it as the new Project Understanding core, not replace it with a simpler claim/evidence list.

### Read Models Are Not Storage

Dashboard JSON should be generated from the local dataset. It should not define the durable data model.

## 7. Target Architecture

Target layers:

```text
Local Dataset
  research-pilot.db
  normalized project-centered storage

Write Layer
  agent typed tools
  validates and writes DB transactions + audit events

Read Model Layer
  builds page/API-shaped JSON from DB

Dashboard Layer
  existing read-only frontend consumes read models
```

`research-pilot.db` should become the primary local workspace store.

Legacy Markdown, JSONL, JSON, snapshots, and generated dashboard files may remain during transition, but they should not define the future architecture.

## 8. Domain Model

The project-centered dataset has six first-level domains.

```text
Project
├─ Brief
├─ Sources / Papers
├─ Project Understanding
├─ Experiments
├─ Literature Structure
└─ Activity / Updates
```

### Brief

Stable project frame:

```text
title
summary
main_question
working_hypothesis
target_contribution
stage
status
```

Brief should not contain all claims, papers, experiments, or literature review detail.

### Sources / Papers

Source identity and reading state:

```text
source identity
locator
metadata
reading_status
reading_depth
short_summary
```

Deep paper understanding does not live in Source. It lives as `UnderstandingNode(scope=paper, source_id=...)`.

### Project Understanding

Core argument structure, preserving current graph ontology:

```text
Question
Claim
Evidence
Warrant
Limitation
ReasoningLink
TranslationLink
```

Understanding supports scopes:

```text
paper
project
program
```

Interpretation:

```text
scope=paper = paper-level understanding from a source
scope=project = project-level understanding
TranslationLink = paper/program understanding mapped into project understanding
ReasoningLink = argument relation among understanding nodes
```

Reasoning links should preserve:

```text
from_nodes
to_nodes
warrant_nodes
limitation_nodes
relation
confidence
confirmation
source_refs
```

`Gap` should not be introduced as a first-class core node in v1. Many gaps can be derived from limitations, unresolved questions, or missing evidence needs. Add `gap` later only if product usage proves it needs durable first-class storage.

### Experiments

Empirical evidence mechanism:

```text
Experiment
ExperimentRun
ExperimentMetric
ExperimentArtifact
```

Important distinction:

```text
Experiment.status = lifecycle of experiment design
ExperimentRun.origin_type = where the evidence came from
```

Run origins:

```text
local
imported_paper
replication
external
manual
```

Important runs should produce project evidence:

```text
ExperimentRun
-> UnderstandingNode(scope=project, node_type=evidence)
-> ReasoningLink supports/weakens Claim
```

Metrics belong to runs. Metrics do not directly support claims; evidence nodes do.

### Literature Structure

Project-scoped cross-paper research landscape:

```text
LiteratureLane
LiteratureItem
LiteratureRelation
ProjectPositioning
```

It stores:

```text
technical lanes
paper roles
cross-paper relations
project positioning
```

It does not store single-paper deep reading. That is `UnderstandingNode(scope=paper)`.

It does not store project claims. Those are `UnderstandingNode(scope=project, node_type=claim)`.

### Activity / Updates

Change history and provenance:

```text
ActivitySession
Update
AuditEvent
```

Meaning:

```text
ActivitySession = one agent/human work session
Update = human-readable semantic change summary
AuditEvent = machine-readable entity-level change record
```

Audit events should be append-only.

## 9. Conceptual Schema v1

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

`EntityLink` handles non-argument cross-domain relations that are not Q/C/E/W/L reasoning links.

Examples:

```text
Experiment tests Claim
ExperimentRun produces Evidence
LiteratureItem provides baseline for Experiment
LiteratureLane informs Question
```

## 10. Cross-Domain Relationships

Required relationships:

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

Expanded mapping:

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
ActivitySession -> Update -> AuditEvent -> any entity
```

## 11. Agent Write Model

Agents should write through typed tools only.

Required flow:

```text
agent completes meaningful research task
-> agent prepares typed project update
-> write tool validates domain rules
-> DB transaction writes current state
-> Update and AuditEvents are recorded
-> dashboard read models reflect new state
```

Agents should not:

- write raw SQL;
- modify DB without audit;
- write dashboard data directly;
- bypass domain validation;
- mark imported paper evidence as local results.

Write tools should eventually support:

```text
project create/update
source record/update reading state
understanding nodes/links
experiment design/run/metrics/artifacts
literature structure
correction updates
```

## 12. Human Correction Model

Keep v1 simple.

Dashboard remains read-only. User corrections happen through chat.

Important records should carry:

```text
created_by: agent | human | system
confirmation: unconfirmed | confirmed | rejected
confidence: low | medium | high | unknown
```

Meanings:

```text
confidence = evidence/model strength
confirmation = whether the user has confirmed or rejected it
```

Do not implement approval queues, review inboxes, or heavy human-gated delta workflows in this refactor.

All corrections should still create Update and AuditEvent records.

## 13. Read Model Layer

The DB schema and dashboard JSON are separate contracts.

DB schema is optimized for:

```text
long-term correctness
stable relationships
agent writes
validation
auditability
future sync
```

Dashboard read models are optimized for:

```text
fast display
page-shaped JSON
stable frontend consumption
minimal frontend knowledge of storage internals
```

Read model flow:

```text
research-pilot.db
-> read model builders
-> dashboard/API JSON
-> existing read-only dashboard
```

The current dashboard should not need to understand raw DB tables.

Required read models:

```text
project summary
source list
source detail / paper detail
project graph
literature / lineage
experiments
recent updates
```

## 14. Cloud-Ready Boundary

Cloud implementation is out of scope for this architecture refactor.

Non-goals:

```text
cloud auth
hosted dashboard
team permissions
online sync
hosted database
conflict-resolution UI
```

Cloud-ready requirements:

```text
stable text IDs
workspace_id and project_id boundaries
schema versioning and migrations
created_at / updated_at timestamps
created_by / updated_by or actor fields
append-only audit events
portable artifact locators
source/provenance fields
exportable project dataset bundles
```

Preferred future cloud shape:

```text
local research-pilot.db <-> optional cloud sync
```

Not:

```text
cloud-first SaaS as default product shape
```

## 15. Demo Affordance Preservation

Demo Visual Affordance is the golden fixture for this refactor.

The new storage design may replace legacy paths, but must preserve current observable product behavior.

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

Required preservation:

```text
Project:
  Demo Visual Affordance title, summary, main question, stage.

Sources/Papers:
  affordance-related source list and paper identities.

Paper Understanding:
  deep-read paper content can be represented as UnderstandingNode(scope=paper).

Project Understanding:
  Q/C/E/W/L nodes and ReasoningLinks can be represented from DB.

Translation/Contribution:
  paper evidence can map into project evidence and claims.

Literature Structure:
  lanes, paper roles, relations, and project positioning can be represented.

Experiments:
  experiment designs, imported paper runs, metrics, artifacts, and claim impacts can be represented.
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

## 16. Scope

In scope:

```text
research-pilot.db as primary local store
schema migration foundation
project-centered conceptual schema implementation
typed write layer foundation
DB-backed read model builders
dashboard-compatible API outputs
Demo Visual Affordance importer/seed path
tests proving demo preservation
documentation explaining new architecture
```

Out of scope:

```text
dashboard redesign
cloud sync implementation
auth or permissions
review queue / approval inbox
full arbitrary legacy workspace migration polish
rewriting every old CLI in the first pass
deleting legacy files during refactor
```

## 17. Acceptance Criteria

Architecture acceptance:

- `research-pilot.db` exists as the primary local dataset for new architecture path.
- Core domains are represented in DB-backed storage.
- Agent writes go through typed write service or planned tool boundary, not raw dashboard mutation.
- Audit/update history exists for meaningful changes.
- Read APIs can produce dashboard-compatible models from DB.

Demo acceptance:

- Demo Visual Affordance can be imported or seeded into `research-pilot.db`.
- DB-backed project model returns expected project identity.
- DB-backed source model returns non-empty affordance paper/source data.
- DB-backed graph model returns Q/C/E/W/L nodes and reasoning links with warrants/limitations.
- DB-backed literature model returns non-empty lanes/items/relations/positioning.
- DB-backed experiments model returns 4 experiments and 5 imported paper runs.
- AGD20K metrics listed above are preserved.
- Imported paper evidence is not shown as local experiment completion.

Dashboard acceptance:

- Existing dashboard pages still open.
- Existing dashboard can consume DB-backed API models or legacy fallback.
- No dashboard redesign is required for this architecture phase.

Safety acceptance:

- Legacy files are not deleted as part of the architecture refactor.
- Existing demo dashboard behavior remains observable.
- Tests cover DB import/read model path and legacy fallback where needed.

## 18. Implementation Strategy

Use beside-the-old-path architecture:

```text
build DB-backed architecture beside legacy paths
import/seed demo into DB
switch read APIs to prefer DB when available
fallback to legacy readers when DB/project is unavailable
```

Recommended implementation phases:

```text
Phase 1: DB foundation
Phase 2: Demo importer / seed path
Phase 3: DB-backed read model builders
Phase 4: API fallback switch
Phase 5: Core write service
Phase 6: Tests
Phase 7: Docs
```

First vertical slice:

```text
Demo Visual Affordance + Experiments + Understanding graph preservation
```

Rationale:

```text
Experiments are isolated enough to test new storage,
but they connect to sources, understanding evidence, metrics, and dashboard read models.
```

## 19. Risks

### Risk: Overbuilding schema before usage stabilizes

Mitigation:

```text
Use typed core tables plus metadata_json for extension.
Keep rare concepts out of first-class tables until proven.
```

### Risk: Losing existing graph rigor

Mitigation:

```text
Preserve Q/C/E/W/L + ReasoningLink + TranslationLink as core understanding ontology.
```

### Risk: Dashboard breakage

Mitigation:

```text
Do not redesign dashboard in this phase.
Use read model builders and legacy fallback.
Use demo dashboard smoke tests.
```

### Risk: Imported evidence confused with local results

Mitigation:

```text
Use ExperimentRun.origin_type.
Acceptance tests assert imported_paper_runs and local_runs separately.
```

### Risk: DB becomes opaque

Mitigation:

```text
Use stable IDs, audit events, exportable bundles, and read model tests.
```

### Risk: Cloud assumptions overcomplicate v1

Mitigation:

```text
Only make schema cloud-ready.
Do not implement sync/auth/permissions.
```

## 20. Open Questions

1. Should `gap` become a first-class `UnderstandingNode` type later, or stay derived from limitations/questions/missing evidence?
2. Should benchmarks and datasets become first-class entities later, or remain Sources plus experiment fields in v1?
3. Should `EntityLink` remain generic long-term, or should common cross-domain relations become dedicated tables?
4. How much of legacy graph-event terminology should be exposed in developer docs after DB architecture lands?
5. Which old CLIs should be migrated first after DB-backed dashboard read models are stable?

