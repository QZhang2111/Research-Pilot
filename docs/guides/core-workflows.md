# Core Workflows

## Normal chat-first path

Normal Research Pilot use starts with chat:

```text
user asks agent
-> agent uses Research Pilot tools
-> project memory is recorded in the workspace dataset / UnderstandingUpdates
-> dashboard observes read models
```

Users should not need to memorize workflow names or commands.

## Project Status

Agent/internal command examples:

```bash
python3 tools/graph_query_cli.py summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 tools/project_next_action_cli.py suggest --repo "$WORKSPACE" --project "$PROJECT" --json
```

Generate a markdown project graph report:

Agent/internal command examples:

```bash
python3 tools/build_project_graph_report.py --repo "$WORKSPACE" --project "$PROJECT"
```

The generated report is a read model. Graph truth remains append-only JSONL events.

## Ambient Understanding Updates

Normal Research Pilot use starts with chat. After a meaningful research task, the agent records an `UnderstandingUpdate` in `wiki/understanding/events/<project>.jsonl`. This captures what changed in project understanding: sources seen, claims changed, evidence added, gaps found, and next moves suggested.

Graph deltas remain available for advanced review mode. They are not required for every lightweight source note or agent observation.

## Related Work Lineage

Use when a project needs a paper-only technical route map before or alongside Project Understanding Graph work.

Agent/internal command examples:

```bash
python3 tools/related_work_lineage_cli.py create --repo "$WORKSPACE" --project "$PROJECT" --round "$ROUND" --title "$TITLE" --direction "$DIRECTION" --baseline-paper "$PAPER_ID" --json
python3 tools/related_work_lineage_cli.py validate --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
python3 tools/related_work_lineage_cli.py render-summary --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json"
```

The lineage artifact is not graph truth and does not create D* events.

## Advanced graph-derived gap inspection

Agent/internal command examples:

```bash
python3 tools/project_gap_cli.py detect --repo "$WORKSPACE" --project "$PROJECT" --json
```

Gap reports are read-only. If a gap should update ambient/current understanding, append an `UnderstandingUpdate`; if it changes graph-level Q/C/E/W/L/RL/TL truth, use D* delta.

## Project Understanding Update

Use when human discussion, evidence pressure, direction changes, or experiment results should update a project.

Read the workspace protocol:

```text
wiki/_system/workflows/project-understanding-update.md
```

Workflow:

```text
classify input
-> read project context and graph state
-> update safe markdown context when appropriate
-> propose D* for graph-level changes
-> dry-run
-> human accept/reject/park/revise
```

Graph-level question/claim/evidence/warrant/limitation changes must use the delta loop.

## Project Evidence Synthesis

Use when multiple papers, dossiers, or experiment notes need project-level interpretation.

Read the workspace protocol:

```text
wiki/_system/workflows/project-evidence-synthesis.md
```

Required synthesis output:

```text
Current Project State
Source Set
Agreement and Conflict
Claim/Evidence Table
Evidence Pressure
Proposed Project Understanding Delta
Human Decision Queue
Next Action Contract
```

This workflow prepares D* proposals. It does not approve papers or mutate graph truth.

## Source/Paper deep-read note

Agent/internal command examples:

```bash
python3 tools/paper_dossier_cli.py create --repo "$WORKSPACE" --project "$PROJECT" --paper "$PAPER_ID" --title "$TITLE"
python3 tools/paper_dossier_cli.py validate --dossier "$DOSSIER" --json
python3 tools/paper_dossier_cli.py export-deltas --dossier "$DOSSIER" --output-dir "$WORKSPACE/.research-pilot/generated/deltas" --json
```

## Durable Research Jobs

Long paper search, deep-read, evidence-synthesis, and experiment-proposal work should create durable records under `.research-pilot/jobs`.

Valid statuses:

```text
queued
running
needs_review
done
failed
```

Job records are execution state only. They are not graph truth and must not be treated as accepted project understanding.

Normal project-understanding changes use workspace project memory / UnderstandingUpdates. Strict graph review uses D* dry-run, registration, and explicit human acceptance.

## Advanced review mode

Agent/internal command examples:

```bash
python3 tools/graph_delta_cli.py dry-run --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py register --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py decide --repo "$WORKSPACE" --project "$PROJECT" --id "$DELTA_ID" --decision accept --json
```

Human approval is required before graph content changes.
