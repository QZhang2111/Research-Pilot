---
name: project-evidence-synthesis
description: Use when a set of papers, dossiers, or graph records must be synthesized into project claims, evidence, limitations, warrants, project deltas, and next actions.
argument-hint: "[workspace path] [project id] [paper ids or dossier paths]"
---

# Project Evidence Synthesis

This skill turns multiple sources into project-level understanding. It is not a literature review for humans. It is an agent-facing synthesis step before delta proposals.

## Boundary

Do not approve papers. Do not mark sources project-core/global-core. Do not mutate graph truth directly.

Allowed:

- compare papers;
- extract agreement/conflict;
- identify evidence pressure;
- propose graph deltas;
- recommend search, deep read, or experiment workflows.

Required human gate for project graph changes:

```text
synthesis -> PD*/D* proposal -> dry-run -> human decision -> append-only graph event
```

## Required Reads

Read:

```text
$WORKSPACE/wiki/projects/$PROJECT/project-query-pack.md
$WORKSPACE/wiki/projects/$PROJECT/project-understanding-graph.md if present
$WORKSPACE/wiki/_system/workflows/project-evidence-synthesis.md
$WORKSPACE/wiki/_system/workflows/delta-update-protocol.md
```

Then query current graph:

```bash
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 "$PLUGIN_ROOT/tools/graph_query_cli.py" open --repo "$WORKSPACE" --project "$PROJECT" --json
```

Use project-local paper dossiers when available:

```text
$WORKSPACE/wiki/projects/$PROJECT/papers/<paper-id>/index.md
```

## Synthesis Model

Separate:

- `Question`: what project question each source affects.
- `Claim`: what project judgment becomes stronger, weaker, narrower, or obsolete.
- `Evidence`: result, benchmark, dataset, metric, qualitative finding, or experimental observation.
- `Warrant`: why the evidence supports the claim.
- `Limitation`: boundary that blocks overclaim.
- `Evidence Need`: missing proof required before the claim should strengthen.
- `Next Action`: search, deep read, experiment, delta, or park.

## Evidence Strength

Use conservative labels:

- `direct`: source directly tests the project claim.
- `analogical`: source supports a similar mechanism or setting.
- `enabling`: source provides method/dataset/tool needed to test.
- `negative`: source challenges or bounds claim.
- `weak`: useful but indirect, qualitative, or under-specified.

## Required Output Sections

```markdown
# Project Evidence Synthesis

## Current Project State
## Source Set
## Agreement and Conflict
## Claim/Evidence Table
## Evidence Pressure
## Proposed Project Understanding Delta
## Human Decision Queue
## Next Action Contract
```

`Proposed Project Understanding Delta` must answer:

```text
What changes in project understanding?
Which current Q/C/E/W/L/RL/TL records are affected?
What new or updated D* should be registered?
What should not be learned from this source set?
```

## Stop Point

Stop before applying changes unless the human explicitly accepts a D* delta.
