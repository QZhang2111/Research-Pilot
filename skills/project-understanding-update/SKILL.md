---
name: project-understanding-update
description: Use when a research project needs its current understanding updated from human intent, new questions, new claims, evidence pressure, paper synthesis, experiment results, or direction changes.
argument-hint: "[workspace path] [project id]"
---

# Project Understanding Update

This skill preserves and updates project understanding. It is not a paper search skill and not a graph mutation shortcut.

## Boundary

Human intent is first-class input.

The agent may classify, preserve, compare, and propose. It must not silently convert a human idea into an approved claim, project decision, or graph truth.

Graph-level changes must go through Delta Update Protocol:

```text
human/project input
-> classify meaning
-> propose D* delta with patch_ops
-> dry-run
-> human accept/reject/park/revise
-> append JSONL event
-> rebuild read models
```

## Required Reads

Before changing project understanding, read:

```text
$WORKSPACE/wiki/projects/$PROJECT/project-query-pack.md
$WORKSPACE/wiki/projects/$PROJECT/overview.md
$WORKSPACE/wiki/projects/$PROJECT/project-understanding-graph.md if present
$WORKSPACE/wiki/_system/workflows/project-understanding-update.md
$WORKSPACE/wiki/_system/workflows/delta-update-protocol.md
```

Also query current graph when graph events exist:

```bash
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" open --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Input Classification

Classify the user's input before writing:

- `observation`: project-relevant fact or pattern.
- `intuition`: taste, hunch, or research direction.
- `question`: new or reframed question.
- `claim`: contestable project judgment.
- `evidence_pressure`: accumulated evidence suggests Q/C update.
- `limitation_pressure`: repeated caveat weakens or bounds a claim.
- `search_need`: project now needs papers for a missing support.
- `experiment_need`: project now needs generated evidence.
- `boundary`: do-not-assume or do-not-learn constraint.
- `decision`: human project decision.

## Safe Updates

Direct markdown updates are allowed for workspace memory and reports:

- `overview.md`
- `project-query-pack.md`
- `decisions.md` only for explicit human decisions
- `idea-board.md`
- generated reports/snapshots if rebuilt

Graph truth changes require D*:

- add/refine/split/merge/retire `Question`
- add/refine/split/merge/retire `Claim`
- add `Evidence`, `Warrant`, `Limitation`
- add/update `Reasoning Link` or `Translation Link`
- change lifecycle, lineage, confidence, scope, or human review

## Output

End with:

```text
Update type:
Files touched:
Graph delta:
Human gate:
Next recommended workflow:
```

If no durable update is needed, say so and explain why.
