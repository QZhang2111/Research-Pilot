---
title: "Project Understanding Update Protocol v1"
type: workflow
status: active
human_review: approved
---

# Project Understanding Update Protocol v1

Use this protocol when human input, paper synthesis, evidence pressure, experiment results, or direction changes should update a project.

The goal is durable project understanding, not chat transcript storage.

## Core Rule

Project understanding has two layers:

```text
markdown workspace memory = readable reports, decisions, context
graph events = append-only truth for project Q/C/E/W/L/RL/TL changes
```

Markdown can preserve context. Graph changes require D* delta.

## Input Types

Classify each update:

| Type | Meaning | Default handling |
|---|---|---|
| observation | New pattern, fact, or state | preserve in project memory |
| intuition | Human hunch or taste | preserve as pending direction |
| question | New/reframed project question | D* if graph-level |
| claim | Contestable project judgment | D* if graph-level |
| evidence_pressure | Evidence accumulation suggests Q/C change | D* |
| limitation_pressure | Caveats bound or weaken current claim | D* |
| search_need | Missing literature support | create search contract |
| experiment_need | Missing generated evidence | create experiment proposal |
| boundary | Do-not-assume constraint | preserve and enforce |
| decision | Explicit human decision | record in decisions/report |

## Required Context

Read:

```text
wiki/projects/<ProjectName>/project-query-pack.md
wiki/projects/<ProjectName>/overview.md
wiki/projects/<ProjectName>/project-understanding-graph.md if present
wiki/graphs/events/<ProjectName>/ if present
```

Use graph query tools when available:

```bash
python3 tools/graph_query_cli.py summary --repo "$WORKSPACE" --project "$PROJECT" --json
python3 tools/graph_query_cli.py open --repo "$WORKSPACE" --project "$PROJECT" --json
```

## Safe Markdown Updates

Allowed without D* when content is report/context only:

- update project overview;
- update project query pack;
- record explicit decisions;
- preserve human intuitions;
- add search or experiment planning artifacts;
- regenerate reports from graph state.

## Graph Updates

Require Delta Update Protocol:

- add/refine/split/merge/retire project questions;
- add/refine/split/merge/retire project claims;
- add evidence, warrant, or limitation;
- add reasoning links or translation links;
- change lifecycle, status, scope, confidence, or lineage.

Each graph update must include:

```yaml
evolution_type: refine | split | merge | promote | demote | reframe | decompose | retire | add | support | challenge | bound | clarify_translation
operation_type: add_node | update_node | retire_node | add_link | update_link | retire_link | split_node | merge_nodes
before: {}
after: {}
rationale: ""
caused_by: []
patch_ops: []
human_review: pending
```

## Evidence Pressure

Evidence pressure exists when multiple sources or results repeatedly point at the same graph weakness.

Examples:

- multiple evidence nodes support a narrower version of a claim;
- limitations repeatedly block a broad claim;
- warrants support a new sub-question;
- translation links show a paper-level claim should become project-level.

Evidence pressure should become a proposed D*, not an automatic change.

## Human Discussion Delta

Human discussion can create graph deltas directly.

Examples:

- "Add a question: does the model encode interaction knowledge?"
- "This claim is too broad; split it."
- "Retire this question; it is not my direction."

The agent should:

1. identify the intended graph object;
2. draft D* with clear patch_ops;
3. dry-run;
4. ask for accept/reject/park/revise;
5. append event only after explicit acceptance.

## Output Format

End every update with:

```text
Update type:
Project files changed:
Graph delta status:
Human gate:
Next action:
```
