# Research Pilot Public Plugin Design

Date: 2026-05-11
Status: Draft
Goal: Extract the existing private research-memory system into a public Codex-first agent plugin without redesigning core behavior.

## Core Position

Research Pilot is not a public research-wiki template.

Research Pilot is an agent plugin that helps a user create and operate their own private research wiki workspace.

The public repository contains capabilities:

```text
skills
tools
workflows
templates
dashboard
installer
docs
```

The user workspace contains private research memory:

```text
Zotero-managed paper sources
wiki research understanding
graph events
graph read models
project files
paper dossiers
```

## Extraction Principle

This public version should preserve the currently working system.

Do not use public extraction as a reason to redesign core workflows.

Keep:

- Zotero-first paper management;
- graph-first Project Understanding Graph;
- append-only delta events;
- human gate;
- dashboard as required public component;
- chat/agent as main operating interface;
- existing skills and tools where stable.

Change only what public extraction requires:

- remove private data;
- remove private paths and secrets;
- add install/init docs;
- make workspace location configurable;
- package capabilities as a plugin;
- clarify source boundaries.

## User Model

User installs Research Pilot plugin, then asks agent to initialize a private research workspace.

Expected flow:

```text
install Research Pilot plugin
-> configure Zotero
-> initialize local research wiki workspace
-> agent reads project state
-> agent searches or imports papers through Zotero
-> agent deep-reads paper in project context
-> agent proposes D* graph delta
-> user accepts/rejects/parks/revises
-> graph events and read models update
-> dashboard shows current project state
```

## Product Statement

Research Pilot is an agent-operated research memory plugin for project-centered research.

It helps agents maintain a durable project understanding graph from Zotero papers, paper dossiers, claims, evidence, warrants, limitations, experiment proposals, and human-approved graph updates.

## Non-Goals

MVP is not:

- a rewrite of the existing system;
- a Zotero-free alternate paper manager;
- a generic markdown wiki template;
- a demo-first product;
- a SaaS product;
- an automatic paper approval system;
- an automatic research-direction approval system.

## Source Boundaries

Core truth boundaries stay the same as the private system:

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only Project Understanding Graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = required browser view over read models and wiki state
chat/agent = primary control surface
```

Dashboard can be required without becoming source of truth.

## Required Public Components

Public extraction should include these existing system parts:

```text
.codex/INSTALL.md
install.sh or equivalent installer
Codex plugin metadata when stable
AGENTS.md public template
skills/
tools/
wiki/_system/workflows/
wiki/_system/templates/
dashboard/
README.md
docs/superpowers/
```

The exact public layout can be simplified, but the behavior should remain compatible with the current working private repo.

Codex marketplace/plugin metadata must not block MVP extraction. If the exact plugin manifest format is still unsettled, ship a Codex-compatible install path first:

```text
clone public repo
-> link skills into the user's agent skill directory
-> expose Research Pilot tools and workspace initializer
```

Tests are required before public release, but the `tests/` directory does not need to exist before tools and fixtures exist.

## Required Private Workspace Components

Initialized user workspace should include:

```text
AGENTS.md
wiki/
  index.md
  log.md
  projects/
  graphs/
    events/
  _system/
    workflows/
    templates/
.research-pilot/
  config.toml
dashboard/ or dashboard reference
```

If the workspace is a Git repo, that is for user backup/sync. It is not required to be public.

## Zotero Requirement

Zotero remains first-class and required for normal paper workflows.

Research Pilot does not reimplement citation management.

Public extraction must preserve:

- Zotero as source of truth for paper metadata and PDFs;
- Zotero collection/tag workflow;
- Zotero bridge tooling;
- project paper intake through Zotero;
- paper status mirroring where currently supported.

Public docs must explain required Zotero configuration.

Do not change existing skills only because the system is public. Any skill change should be limited to path/config generalization and removal of private assumptions.

## Dashboard Requirement

Dashboard source is required for public MVP.

Reason:

- it makes the graph visible;
- it makes project state inspectable;
- it helps users trust what the agent is doing;
- it shows papers, deltas, graph state, gaps, and experiment proposals.

Public extraction should carry the existing dashboard behavior forward, with necessary cleanup for portability.

Do not redesign dashboard during extraction unless current code has private-path or public-safety blockers.

MVP does not require dashboard redesign or polished dashboard UX. MVP requires only:

- dashboard source is present;
- dashboard server/index tools can point at an explicit user workspace;
- dashboard opens a freshly initialized workspace or fails with a clear missing-data message;
- dashboard does not require private generated `.dashboard` files.

## Demo Decision

No demo workspace is required for MVP.

Public extraction should focus on:

- plugin install;
- user workspace initialization;
- existing workflow portability;
- dashboard portability;
- Zotero configuration;
- tests.

Demo workspace can be added later.

## Main Skill / Router

`research-pilot` should be the primary user-facing skill.

Subskills remain available, but user onboarding should not require knowing every internal workflow name.

The router should map user intent to existing workflows:

- initialize workspace;
- inspect project;
- detect gap;
- search paper through Zotero workflow;
- deep-read paper;
- propose D* delta;
- apply human decision;
- generate experiment proposal;
- show dashboard.

## Public Safety Requirements

Public repo must not contain:

- private project data;
- real ongoing paper dossiers;
- local PDF files;
- Zotero API keys;
- local Zotero database files;
- absolute maintainer paths;
- personal research taste/program memory unless rewritten as generic examples;
- generated dashboard read-model data from private projects.

## MVP Acceptance

Public acceptance is staged.

### MVP-A: Plugin Shell And Workspace Core

This is the first public extraction target.

1. A fresh clone can install Research Pilot into Codex through a documented install path.
2. Agent can initialize a new private research workspace.
3. Workspace contains generic workflows, templates, graph schema, config example, `wiki/index.md`, and `wiki/log.md`.
4. Core graph tools can run against the initialized workspace.
5. Leak scan finds no private data, private project names, maintainer absolute paths, secrets, PDFs, or generated private read models.

### MVP-B: Graph Workflow Core

1. Agent can query graph state in the new workspace.
2. Agent can dry-run and apply a synthetic D* delta against fixture graph events.
3. Graph DB, snapshot, and project report builders work from fixture events.
4. Tests verify workspace init, graph DB rebuild, graph query, delta dry-run/apply, and no-private-path leakage.

### MVP-C: Zotero Workflow

1. User can configure Zotero.
2. Agent can run existing Zotero-first paper workflow.
3. Zotero bridge is configurable by user and supports dry-run/config validation without real credentials.
4. Zotero tests use mocked or dry-run mode unless explicitly marked integration.

### MVP-D: Dashboard And Docs

1. Dashboard can open the user's workspace or show a clear empty-state.
2. Dashboard does not require private generated `.dashboard` files.
3. README, install guide, workspace initialization guide, Zotero guide, dashboard guide, and source-boundary guide exist.

Full public MVP is acceptable when:

1. A fresh clone can install Research Pilot into Codex.
2. Agent can initialize a new private research workspace.
3. User can configure Zotero.
4. Agent can run existing Zotero-first paper workflow.
5. Agent can run graph query/gap/delta workflows in the new workspace.
6. Dashboard can open the user's workspace.
7. No private data or private local paths are present.
8. Existing tests or extracted tests verify core workflows.

## Deferred

These are not MVP extraction blockers:

- Zotero-free mode;
- fake demo workspace;
- multi-platform plugin support;
- dashboard redesign;
- SaaS hosting;
- team collaboration;
- automatic paper approval;
- automatic experiment execution.
