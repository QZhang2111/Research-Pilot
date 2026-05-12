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
- Guide first-run setup from plugin source or empty directory to a project shell, then a human-gated graph update when real graph-worthy input exists.
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
- Create durable execution-state records for long search, deep-read, synthesis, and experiment-proposal jobs.

Dashboard is a required public component and a browser observer. It must not become graph truth.
Durable job records are execution state only. They must not become graph truth.

## Durable Research Jobs

For long paper-search, deep-read, evidence-synthesis, or experiment-proposal work, create a durable record under `.research-pilot/jobs`. Job records track execution state only. They do not change graph truth. Any graph change from job output still requires D* dry-run, D* registration, and explicit human decision in the main agent/user conversation before acceptance.

## Workspace Detection

A directory is a Research Pilot workspace when it has:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/config.example.toml or .research-pilot/config.toml
```

## Intent Routing

### Command Aliases

Treat these as equivalent initialization intents:

```text
/research-init
research-init
init research memory
initialize Research Pilot
create a Research Pilot workspace
```

Treat these as equivalent dashboard intents:

```text
/research-dashboard
research-dashboard
open Research Pilot dashboard
open research browser
show dashboard
```

### Initialize Workspace

When the user asks to initialize/create/set up a research workspace:

1. Resolve the requested path. If no path is provided, ask for one concise path.
2. Resolve the plugin root by locating the installed `research-pilot` skill symlink and going two directories up to the Research Pilot repo checkout.
3. Run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

4. Report the workspace path and next steps.

### First Run

When the user asks to start from scratch, create the first project, initialize a new research memory, or is confused about repo/plugin/workspace boundaries:

1. Use the `research-pilot-first-run` skill.
2. If already inside a workspace, read:

```text
$WORKSPACE_PATH/wiki/_system/workflows/first-run.md
```

3. Before suggesting next actions, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json
```

Summarize the returned stage in chat. Offer at most two next actions. Do not mutate graph truth during status inspection.

4. Create or confirm a private workspace.
5. Collect only minimum project intake: project id/name, one-sentence direction, first question/claim, Zotero now/later.
6. If the user only has a venue, broad direction, or baseline-paper need, create a project shell first. Defer the first graph delta until the user provides a real question, claim, evidence pressure, paper synthesis, or experiment result.
7. Route the first graph-level question or claim through D* dry-run and human gate.

Do not start paper search or dashboard work before a first project question or claim exists.

### Inspect Workspace

When the user asks to inspect current Research Pilot status:

Before suggesting next actions, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json
```

Summarize the returned stage in chat. Offer at most two next actions. Do not mutate graph truth during status inspection.

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

Create a durable job record in `.research-pilot/jobs` for long-running evidence-synthesis work.

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

Create a durable job record in `.research-pilot/jobs` for long-running search work. The record tracks execution state only; it is not graph truth. Human gating still happens in the main agent/user conversation before any graph delta is accepted.

```bash
python3 "$PLUGIN_ROOT/tools/research_gap_discovery_cli.py" run --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --gap "$GAP_TARGET" --source memory --json
```

Use `--source arxiv`, `--source openreview`, or `--source all` only when the user expects external network search. Candidate leads are not Zotero approval and not graph truth.

### Experiment Proposal

When the user asks what experiment could test a claim:

Create a durable job record in `.research-pilot/jobs` for long-running experiment-proposal work. The record tracks execution state only; it is not graph truth. Human gating still happens in the main agent/user conversation before any graph delta is accepted.

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

Create a durable job record in `.research-pilot/jobs` for long-running deep-read work.

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

For Zotero setup, use the agent-facing helper:

```bash
python3 "$PLUGIN_ROOT/tools/zotero_setup.py" prepare-env --repo "$WORKSPACE_PATH" --json
python3 "$PLUGIN_ROOT/tools/zotero_setup.py" status --repo "$WORKSPACE_PATH" --json
```

Do not print API keys. Do not mention Zotero MCP as part of the normal user flow.

### Dashboard

When the user invokes `/research-dashboard`, read `commands/research-dashboard.md` and follow it.

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
