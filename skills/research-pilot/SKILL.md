---
name: research-pilot
description: Use when the user wants to initialize, inspect, or operate a Research Pilot workspace for agent-operated research memory.
argument-hint: "[init <path>|inspect]"
---

# Research Pilot

Research Pilot is the primary router skill for agent-operated research memory.

## Current Capabilities

- Explain plugin vs workspace boundary.
- Initialize a private research workspace.
- Inspect whether the current directory looks like a Research Pilot workspace.
- Validate project graph-event JSONL.
- Build generated graph snapshots.
- Build generated SQLite graph read models.
- Query project graph nodes, links, deltas, open deltas, and summaries.

Zotero paper workflows, dashboard launching, human-gated delta apply, and paper-to-delta automation are extracted in later MVP slices.

## Workspace Detection

A directory is a Research Pilot workspace when it has:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/config.example.toml or .research-pilot/config.toml
```

## Intent Routing

### Initialize Workspace

When the user asks to initialize/create/set up a research workspace:

1. Resolve the requested path. If no path is provided, ask for one concise path.
2. Resolve the plugin root by locating the installed `research-pilot` skill symlink and going two directories up to the Research Pilot repo checkout.
3. Run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

4. Report the workspace path and next steps.

### Inspect Workspace

When the user asks to inspect current Research Pilot status:

1. Check for the workspace detection files.
2. If present, report that the workspace skeleton is initialized.
3. If absent, explain that the user should run initialization first.

### Validate Graph Events

When the user asks to validate graph events:

```bash
python3 "$PLUGIN_ROOT/tools/graph_validate.py" --repo "$WORKSPACE_PATH" --project "$PROJECT_ID"
```

### Build Graph Read Models

When the user asks to rebuild graph read models:

```bash
python3 "$PLUGIN_ROOT/tools/build_graph_snapshot.py" --repo "$WORKSPACE_PATH" --project "$PROJECT_ID"
python3 "$PLUGIN_ROOT/tools/build_graph_db.py" --repo "$WORKSPACE_PATH" --project "$PROJECT_ID"
```

### Query Graph

When the user asks to inspect current project graph state:

```bash
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" summary --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" open --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
```

## Boundaries

Do not claim Zotero workflows, dashboard support, human-gated delta apply, or paper deep-read automation are available until those MVP slices are extracted.

Do not store private research data in the public plugin repo.
