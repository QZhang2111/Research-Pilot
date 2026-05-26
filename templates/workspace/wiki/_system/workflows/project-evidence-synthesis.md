---
title: "Project Evidence Synthesis Protocol v1"
type: workflow
status: active
human_review: approved
---

# Project Evidence Synthesis Protocol v1

Use this protocol when multiple sources, notes, dossiers, search results, or experiment records must be synthesized into project-level understanding.

The output is project-facing evidence synthesis. Normal output should update project memory / UnderstandingUpdate records. Strict-review D* proposals are optional advanced outputs when formal graph changes are needed.

## Source Boundary

Do not approve sources. Do not mark project-core or global-core. Do not accept strict-review graph changes directly.

Allowed:

- compare sources;
- identify agreement, conflict, missing evidence, and uncertainty;
- update project memory through normal Research Pilot tools;
- propose strict-review graph changes only when needed;
- recommend natural next prompts.

## Required Context

Read:

```text
wiki/projects/<ProjectName>/project-query-pack.md
wiki/projects/<ProjectName>/project-understanding-graph.md if present
wiki/projects/<ProjectName>/papers/<PaperId>/index.md when using dossiers
wiki/graphs/events/<ProjectName>/ if present
```

Query graph state when tools are available:

```bash
python3 tools/graph_query_cli.py summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 tools/graph_query_cli.py open --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Synthesis Units

Use the project graph schema:

- `Question`: project question affected by the evidence.
- `Claim`: contestable project judgment.
- `Evidence`: result, metric, qualitative finding, dataset, or benchmark fact.
- `Warrant`: reason evidence supports claim.
- `Limitation`: boundary, missing proof, or overclaim risk.
- `Reasoning Link`: same-project logic between graph records.
- `Translation Link`: mapping from external/paper claim to project graph.

## Evidence Strength

Label evidence:

| Strength | Meaning |
|---|---|
| direct | directly tests the project claim |
| analogical | supports similar mechanism or setting |
| enabling | provides method/tool/dataset for future proof |
| negative | challenges or bounds a claim |
| weak | indirect, qualitative, or underspecified |

## Required Output

Use this structure:

```markdown
# Project Evidence Synthesis

## Current Project State
Brief current Q/C/E/W/L status.

## Source Set
Papers, dossiers, experiments, or notes considered.

## Agreement and Conflict
What sources jointly support, challenge, or bound.

## Claim/Evidence Table
| Claim | Supporting evidence | Warrant | Limitation | Strength |

## Evidence Pressure
Which Q/C should be refined, split, promoted, demoted, or retired.

## Project Understanding Update
Normal memory / UnderstandingUpdate summary.

## Optional Strict Review
D* proposal summary only when formal graph review is requested or necessary.

## Human Gate
Approvals needed before strict graph accept, project-core/global-core status, direction changes, or confirmed experiment evidence.

## Next Natural Prompts
Natural follow-up prompts for search, deep-read, experiment, or no-op.
```

## Delta Quality Bar

Every proposed D* must answer:

```text
What changed in project understanding?
Why now?
Which source records caused the change?
Which graph records are affected?
What should not be learned?
```

## Stop Point

Stop before accepting strict-review graph changes unless the human explicitly accepts.
