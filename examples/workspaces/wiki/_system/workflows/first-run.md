---
title: "Research Pilot First-Run Protocol"
type: workflow
status: active
human_review: approved
---

# Research Pilot First-Run Protocol

Use this protocol when a new user starts Research Pilot, initializes a private workspace, creates the first project, or asks the agent to begin using project memory.

## Purpose

Guide the user to a status-aware workspace and project shell. Defer the first human-gated project graph update until graph-worthy input exists.

Success is not "all features shown." Success is:

```text
workspace exists
project exists
first question, claim, evidence pressure, paper synthesis, or experiment result has a proposed D*
human gate happens
accepted changes enter append-only graph events
read models can rebuild
agent suggests the next research move
```

If the user only has a venue, broad direction, or baseline-paper need, create a project shell first. Defer the first graph delta until the user provides a real question, claim, evidence pressure, paper synthesis, or experiment result.

## State Detection

Before suggesting next actions, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json
```

Summarize the returned stage in chat. Offer at most two next actions. Do not mutate graph truth during status inspection.

Use returned stage values:

| State | Markers | Action |
|---|---|---|
| plugin_repo | `install.sh`, `tools/research_pilot_init.py`, `skills/research-pilot/SKILL.md` | explain repo vs workspace; ask for workspace path |
| empty_workspace | `AGENTS.md`, `wiki/index.md`, `wiki/log.md`, `.research-pilot/`, no projects | create first project shell |
| project_shell | project overview exists, no graph report | configure Zotero or add baseline anchors |
| read_models_stale | graph events newer than generated views | rebuild read models |
| project_has_graph | project graph exists | inspect current graph and next action |
| plain_directory | no Research Pilot markers | ask whether to initialize here or elsewhere |

In normal installed use, the plugin repo is hidden at `~/.research-pilot/repo`; the optional plugin-root symlink is `~/.research-pilot-plugin`. User-visible research data belongs in the initialized workspace.

## Minimum Project Intake

Ask only for missing essentials:

- project id or short project name;
- one-sentence research direction;
- first question, uncertainty, or claim;
- Zotero status: configured now or later.

Do not force a full project charter before project shell creation.

## Project Skeleton

Create only missing files:

```text
wiki/projects/<ProjectId>/overview.md
wiki/projects/<ProjectId>/project-query-pack.md
wiki/projects/<ProjectId>/decisions.md
wiki/projects/<ProjectId>/papers/.gitkeep
wiki/projects/<ProjectId>/experiment-proposals/.gitkeep
```

Use `human_review: pending` unless the user explicitly approves a decision or graph update.

## First Graph Update

If the user only has a venue, broad direction, or baseline-paper need, stop after project shell creation and explain what input would justify a graph delta.

The first durable graph update should usually be a `Question` node. A `Claim` node is allowed when the user gives a contestable project judgment.

Required flow:

```text
human input
-> D* delta draft
-> dry-run
-> human accept/reject/park/revise
-> append-only graph event if accepted
-> rebuild graph.db, snapshot, markdown report, dashboard index
```

Do not directly edit graph truth from discussion text.

## Human Gate

Human approval is required for:

- graph delta acceptance;
- project-core or global-core promotion;
- research direction decisions;
- experiment result interpretation;
- Zotero write-back with `--apply`.

## Completion Report

End the first-run with:

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
