---
name: research-pilot-first-run
description: Use when a new user wants to start Research Pilot from scratch, initialize or inspect a workspace, create the first project, or make the first human-gated project graph update.
argument-hint: "[workspace path] [project id]"
---

# Research Pilot First Run

Guide a user from plugin/repo confusion to the first project graph update.

## Goal

Create the minimum working research memory loop:

```text
workspace exists
-> first project exists
-> first question or claim becomes proposed D*
-> dry-run passes
-> human accepts/rejects/parks/revises
-> accepted event updates graph
-> read models rebuild
-> agent offers next move
```

Do not showcase every feature. Do not start paper search first. Do not mutate graph truth without human approval.

## State Detection

First identify where the user is:

- `plugin_repo`: current directory contains `install.sh`, `tools/research_pilot_init.py`, and `skills/research-pilot/SKILL.md`.
- `initialized_workspace`: current directory contains `AGENTS.md`, `wiki/index.md`, `wiki/log.md`, and `.research-pilot/config.example.toml` or `.research-pilot/config.toml`.
- `empty_or_plain_directory`: no Research Pilot workspace markers.
- `unknown`: conflicting markers or missing permissions.

If in `plugin_repo`, explain:

```text
This repo is the plugin source. Your research data belongs in a separate private workspace.
```

Then ask for or infer a workspace path.

## First-Run Flow

### 1. Initialize or confirm workspace

If workspace does not exist, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

If the user is already in a workspace, inspect it and continue.

### 2. Explain the boundary once

Use concise language:

```text
Research Pilot repo = plugin source.
Your workspace = private research memory.
Zotero = paper manager.
Graph events = project-understanding truth.
Dashboard = observer.
Human approval controls graph changes.
```

### 3. Collect minimum project intake

Ask only for missing essentials:

- project name or short id;
- one-sentence research direction;
- first question, uncertainty, or claim;
- Zotero availability: configured / later.

If the user gives enough information in one message, do not ask again.

### 4. Create project skeleton

Create project files only when missing:

```text
wiki/projects/<ProjectId>/overview.md
wiki/projects/<ProjectId>/project-query-pack.md
wiki/projects/<ProjectId>/decisions.md
wiki/projects/<ProjectId>/papers/.gitkeep
wiki/projects/<ProjectId>/experiment-proposals/.gitkeep
```

Use public-safe frontmatter and default `human_review: pending` unless the user explicitly approves content.

### 5. First graph update

Convert the first question or claim into a D* proposal:

- new question -> `operation_type: add_node`, `evolution_type: add`
- new claim -> `operation_type: add_node`, `evolution_type: add`
- refinement of existing project framing -> `operation_type: update_node`, `evolution_type: reframe | refine`

Then:

```text
draft delta JSON
-> dry-run
-> summarize effects
-> stop for human accept/reject/park/revise
```

Only after explicit acceptance:

```text
register/decide or append accepted event through delta tools
-> rebuild graph.db, snapshot, markdown report, dashboard index
```

### 6. Completion response

End with:

```text
Workspace:
Project:
First graph update:
Human gate result:
Generated read models:
Next possible moves:
```

Offer exactly three next moves:

- add or deep-read a paper;
- search for missing evidence;
- propose an experiment for a weak claim.

## Stop Points

Stop for human approval before:

- accepting a graph delta;
- marking a paper project-core or global-core;
- changing research direction;
- interpreting experiment results as evidence;
- writing Zotero status mirrors with `--apply`.
