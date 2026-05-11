# Core Workflows

## Project Status

```bash
python3 tools/graph_query_cli.py summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 tools/project_next_action_cli.py suggest --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Gap Detection

```bash
python3 tools/project_gap_cli.py detect --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Paper Dossier

```bash
python3 tools/paper_dossier_cli.py create --repo "$WORKSPACE" --project "$PROJECT" --paper "$PAPER_ID" --title "$TITLE"
python3 tools/paper_dossier_cli.py validate --dossier "$DOSSIER" --json
python3 tools/paper_dossier_cli.py export-deltas --dossier "$DOSSIER" --output-dir "$WORKSPACE/.research-pilot/generated/deltas" --json
```

## Delta Update

```bash
python3 tools/graph_delta_cli.py dry-run --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py register --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py decide --repo "$WORKSPACE" --project "$PROJECT" --id "$DELTA_ID" --decision accept --json
```

Human approval is required before graph content changes.

