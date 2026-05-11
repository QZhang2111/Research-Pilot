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
- Dry-run graph deltas.
- Register proposed graph deltas.
- Apply human decisions to registered graph deltas.
- Create and validate project-local paper dossiers.
- Export paper-dossier graph delta JSON proposals.
- Intake source identity with optional Zotero keys and manual fallback.
- Build and serve the optional Research Browser dashboard.

Dashboard is an optional observer. It must not become graph truth.

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

### Human-Gated Delta Loop

When the user asks to preview a graph change:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" dry-run --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --delta "$DELTA_JSON" --json
```

When the user asks to register a proposed graph change:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" register --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --delta "$DELTA_JSON" --json
```

When the human explicitly approves, rejects, parks, or requests revision of a registered delta:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" decide --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --id "$DELTA_ID" --decision accept --json
```

### Paper Dossier Workflow

When the user asks to create a project-local paper dossier:

```bash
python3 "$PLUGIN_ROOT/tools/paper_dossier_cli.py" create --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --json
```

When the user asks to validate a dossier or export its proposed deltas:

```bash
python3 "$PLUGIN_ROOT/tools/paper_dossier_cli.py" validate --dossier "$DOSSIER" --json
python3 "$PLUGIN_ROOT/tools/paper_dossier_cli.py" export-deltas --dossier "$DOSSIER" --output-dir "$WORKSPACE_PATH/.research-pilot/generated/deltas" --json
```

### Source Intake

When the user asks to add a paper/source to a project:

```bash
python3 "$PLUGIN_ROOT/tools/source_intake_cli.py" intake --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --paper "$PAPER_ID" --title "$TITLE" --zotero-key "$ZOTERO_ITEM_KEY" --doi "$DOI" --url "$URL" --json
```

If Zotero credentials are unavailable, continue with DOI, arXiv, URL, or manual source refs.

### Dashboard

When the user asks to build or refresh the dashboard read model:

```bash
python3 "$PLUGIN_ROOT/tools/build_dashboard_index.py" --repo "$WORKSPACE_PATH" --output .dashboard/index.json
```

When the user asks to open the dashboard:

```bash
python3 "$PLUGIN_ROOT/tools/research_browser_server.py" --repo "$WORKSPACE_PATH" --port 8765
```

## Boundaries

Do not claim Zotero API workflows or full paper deep-read automation are available until those MVP slices are extracted.

Do not claim dashboard files are source of truth. Dashboard may only observe generated read models and call explicit graph delta APIs.

Do not store private research data in the public plugin repo.
