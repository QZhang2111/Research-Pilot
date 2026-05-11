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

## Status

Public MVP keeps this protocol as a workflow boundary. Full gap-search tooling is a later extraction slice.

