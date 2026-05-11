# Project Next Action

Purpose: give the agent one read-only entry point for deciding which workflow should happen next.

## Command

```bash
python3 tools/project_next_action_cli.py suggest --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Output

The router reports:

- project state;
- open deltas;
- top graph gaps;
- recommended next moves;
- why those moves come first;
- suggested command for the chosen workflow.

## Boundary

This router must not run search, deep read, delta apply, Zotero writes, or experiments. It only recommends.

Human chooses the next move.

