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
- Detect structural project graph gaps.
- Recommend next workflow action.
- Preserve and update project understanding from human intent, evidence pressure, and direction changes.
- Synthesize paper sets into project-level claim/evidence pressure and D* proposals.
- Generate gap-driven search contracts and project-gap discovery leads.
- Generate read-only experiment proposals for claims.
- Dry-run graph deltas.
- Register proposed graph deltas.
- Apply human decisions to registered graph deltas.
- Create and validate project-local paper dossiers.
- Export paper-dossier graph delta JSON proposals.
- Intake Zotero-first source identity, with manual source-reference capture for setup/dry-run cases.
- Build and serve the Research Browser dashboard.

Dashboard is a required public component and a browser observer. It must not become graph truth.

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

### Detect Graph Gaps

When the user asks what evidence, warrant, answer, or translation is missing:

```bash
python3 "$PLUGIN_ROOT/tools/project_gap_cli.py" detect --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
```

Do not mutate graph state from a gap report. If the gap should change understanding, route through D*.

### Recommend Next Action

When the user asks what to do next:

```bash
python3 "$PLUGIN_ROOT/tools/project_next_action_cli.py" suggest --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
```

This router is read-only. It may recommend another workflow, but it must not run search, deep read, delta apply, Zotero writes, or experiments by itself.

### Project Understanding Update

When human input changes project direction, question framing, claim scope, evidence pressure, or boundaries:

1. Read the workspace protocol:

```text
$WORKSPACE_PATH/wiki/_system/workflows/project-understanding-update.md
```

2. Read current project context and graph state.
3. Classify the input as observation, intuition, question, claim, evidence pressure, limitation pressure, search need, experiment need, boundary, or decision.
4. Preserve safe report/context changes in markdown.
5. Route graph-level changes through D* dry-run, registration, and human decision.

Do not silently promote human discussion into graph truth.

### Project Evidence Synthesis

When a set of papers, dossiers, or experiment notes should affect project understanding:

1. Read the workspace protocol:

```text
$WORKSPACE_PATH/wiki/_system/workflows/project-evidence-synthesis.md
```

2. Compare sources against current Q/C/E/W/L state.
3. Identify agreement, conflict, evidence pressure, and missing proof.
4. Produce Project Understanding Delta proposals and a Human Decision Queue.

Do not approve sources or mutate graph truth without explicit human decision.

### Gap-Driven Search

When the user asks to find papers for a graph gap:

```bash
python3 "$PLUGIN_ROOT/tools/research_gap_discovery_cli.py" run --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --gap "$GAP_TARGET" --source memory --json
```

Use `--source arxiv`, `--source openreview`, or `--source all` only when the user expects external network search. Candidate leads are not Zotero approval and not graph truth.

### Experiment Proposal

When the user asks what experiment could test a claim:

```bash
python3 "$PLUGIN_ROOT/tools/project_experiment_cli.py" suggest --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --target "$CLAIM_ID" --json
```

Experiment proposals are planning artifacts. Completed experiment results still need D* human gate before entering graph truth.

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

Normal paper management is Zotero-first. If Zotero credentials are not configured yet, DOI, arXiv, URL, or manual source refs may be recorded only as source identity capture; do not present this as a replacement paper manager.

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

Do not claim full Zotero API automation beyond extracted source-identity and bridge behavior.

Do not claim dashboard files are source of truth. Dashboard may only observe generated read models and call explicit graph delta APIs.

Do not store private research data in the public plugin repo.
