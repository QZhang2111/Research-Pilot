# Project Gap Discovery

Purpose: expose a user-facing path from graph gap to papers worth human deep-read decision.

Expected flow:

```text
graph gap -> evidence need -> search -> lead scoring -> human chooses deep-read
```

## Boundary

Project Gap Discovery must not add papers to Zotero, approve candidates, or append graph events.

If a found paper later changes project understanding:

```text
single-paper deep read -> PD* -> D* -> dry-run -> human gate
```

## Tooling

Use `tools/project_gap_cli.py`, `tools/gap_search_cli.py`, and `tools/research_gap_discovery_cli.py` when command-line support is useful. Tool output remains candidate guidance until the human chooses a deep-read target.
