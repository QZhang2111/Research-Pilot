# Deep Read To Delta Workflow

Use this workflow after a paper dossier contains project-relevant findings.

## Contract

The agent may propose graph deltas, but the human decides whether to accept, reject, park, or revise them.

## Steps

1. Validate the dossier.

```bash
python3 tools/paper_dossier_cli.py validate --dossier "$DOSSIER" --json
```

2. Export proposed delta JSON files.

```bash
python3 tools/paper_dossier_cli.py export-deltas --dossier "$DOSSIER" --output-dir "$WORKSPACE/.research-pilot/generated/deltas" --json
```

3. Dry-run each exported delta.

```bash
python3 tools/graph_delta_cli.py dry-run --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
```

4. Register valid proposals.

```bash
python3 tools/graph_delta_cli.py register --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
```

5. Apply only explicit human decisions.

```bash
python3 tools/graph_delta_cli.py decide --repo "$WORKSPACE" --project "$PROJECT" --id "$DELTA_ID" --decision accept --json
```
