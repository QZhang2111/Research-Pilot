---
name: research-pilot-first-run
description: Use when a new user wants to start Research Pilot from scratch, initialize or inspect a workspace, create the first project, or make the first human-gated project graph update.
argument-hint: "[workspace path] [project id]"
---

# Research Pilot First Run

Guide a user from plugin/repo confusion to a status-aware workspace and project shell. Defer the first project graph update until graph-worthy input exists.

Primary command:

```text
/research-init [workspace_path]
```

## Goal

Create the minimum working research memory loop:

```text
workspace exists
-> first project exists
-> first question, claim, evidence pressure, paper synthesis, or experiment result becomes proposed D*
-> dry-run passes
-> human accepts/rejects/parks/revises
-> accepted event updates graph
-> read models rebuild
-> agent offers next move
```

Do not showcase every feature. Do not start paper search first. Do not mutate graph truth without human approval.
If the user only has a venue, broad direction, or baseline-paper need, create a project shell first. Defer the first graph delta until the user provides a real question, claim, evidence pressure, paper synthesis, or experiment result.

## State Detection

Before suggesting next actions, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json
```

Summarize the returned stage in chat. Offer at most two next actions. Do not mutate graph truth during status inspection.

Use returned stage values:

- `plugin_repo`: current directory contains `install.sh`, `tools/research_pilot_init.py`, and `skills/research-pilot/SKILL.md`.
- `plain_directory`: no Research Pilot workspace markers.
- `empty_workspace`: workspace exists without projects.
- `project_shell`: project shell exists without graph truth.
- `read_models_stale`: graph events are newer than generated read models.
- `project_has_graph`: project graph exists.

If in `plugin_repo`, explain:

```text
This repo is the plugin source. Your research data belongs in a separate private workspace.
```

Then ask for or infer a workspace path.

In normal installed use, the plugin repo is hidden at `~/.research-pilot/repo`; the optional plugin-root symlink is `~/.research-pilot-plugin`. User-visible research data belongs in the initialized workspace.

## First-Run Flow

### 1. Initialize or confirm workspace

If workspace does not exist, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

Resolve `PLUGIN_ROOT` in this order:

```text
~/.research-pilot/repo
~/.research-pilot-plugin
current directory, only if it is the plugin repo
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

If the user only has a venue, broad direction, or baseline-paper need, stop after project shell creation and explain what input would justify a graph delta.

Convert the first real question, claim, evidence pressure, paper synthesis, or experiment result into a D* proposal:

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
