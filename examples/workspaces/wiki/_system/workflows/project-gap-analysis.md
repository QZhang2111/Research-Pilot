# Project Gap Analysis

Purpose: detect where the current Project Understanding Graph lacks support, answers, warrant, translation, or limitation-closing evidence.

Gap reports are read models generated from `wiki/graphs/graph.db`. They are not graph truth.

## Command

```bash
python3 tools/project_gap_cli.py detect --repo "$WORKSPACE" --project "$PROJECT" --json
```

Optional cap:

```bash
python3 tools/project_gap_cli.py detect --repo "$WORKSPACE" --project "$PROJECT" --limit 10 --json
```

## Gap Types

- `unsupported_claim`
- `unanswered_question`
- `weak_warrant`
- `overbounded_claim`
- `missing_translation`

## Boundary

Gap analysis must not append events, edit dossiers, approve deltas, or change graph records.

If a gap becomes a graph update, route it through Delta Update Protocol.

