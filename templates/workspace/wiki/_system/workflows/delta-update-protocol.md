# Delta Update Protocol

Purpose: define how Project Understanding Graph content changes.

Core rule:

```text
Q/C/E/W/L/RL/TL content changes only through human-gated deltas.
```

Delta is a maintenance object, not a knowledge node. It proposes a graph patch, receives human review, then appends events if accepted.

## Scope

Governed graph records:

- Question
- Claim
- Evidence
- Warrant
- Limitation
- ReasoningLink
- TranslationLink

Not governed:

- Zotero metadata
- PDFs
- dashboard code
- ordinary docs
- non-graph project notes

## Lifecycle

```text
proposed -> accepted
proposed -> rejected
proposed -> parked
proposed -> revised
```

Only `accepted` changes graph content.

## Commands

```bash
python3 tools/graph_delta_cli.py dry-run --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py register --repo "$WORKSPACE" --project "$PROJECT" --delta "$DELTA_JSON" --json
python3 tools/graph_delta_cli.py decide --repo "$WORKSPACE" --project "$PROJECT" --id "$DELTA_ID" --decision accept --json
```

## Human Gate

Agent may propose and dry-run. Human decides accept, reject, park, or revise.

