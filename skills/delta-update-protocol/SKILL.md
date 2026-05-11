---
name: delta-update-protocol
description: Use when a Research Pilot project graph change must be previewed, registered, accepted, rejected, parked, or revised through human-gated D* deltas.
argument-hint: "<project> <delta-json|delta-id>"
---

# Delta Update Protocol

All Q/C/E/W/L/RL/TL changes go through D* deltas.

Preview:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" dry-run --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --delta "$DELTA_JSON" --json
```

Register:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" register --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --delta "$DELTA_JSON" --json
```

Apply explicit human decision:

```bash
python3 "$PLUGIN_ROOT/tools/graph_delta_cli.py" decide --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --id "$DELTA_ID" --decision accept --json
```

Never accept, reject, park, or revise without explicit human instruction.

