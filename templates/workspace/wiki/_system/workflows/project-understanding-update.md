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

Project understanding has two paths:

```text
normal path = workspace dataset / UnderstandingUpdate / project memory
strict review = graph events and D* deltas for formal Q/C/E/W/L/RL/TL changes
```

Use the normal path for ordinary agent learning, source notes, uncertainty updates, brief changes, and recent understanding. Use strict review when the user asks for it or when a high-impact formal graph change needs explicit approval.

## Input Types

Classify each update:

| Type | Meaning | Default handling |
|---|---|---|
| observation | New pattern, fact, or state | preserve in project memory |
| intuition | Human hunch or taste | preserve as pending direction |
| question | New/reframed project question | normal update; strict review if formal graph change |
| claim | Contestable project judgment | normal update with status; strict review if high-impact |
| evidence_pressure | Evidence accumulation suggests Q/C change | normal update; strict review if formal graph change |
| limitation_pressure | Caveats bound or weaken current claim | normal update; strict review if formal graph change |
| search_need | Missing literature support | record need; source/literature discovery may follow |
| experiment_need | Missing generated evidence | record planned experiment/design need |
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

## Strict Review Updates

Require Delta Update Protocol only when the user asks for strict review or a formal graph-level Q/C/E/W/L/RL/TL change is being accepted.

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

Evidence pressure should become a normal update first. Use a strict-review D* only when formal graph change is requested or required, never as an automatic change.

## Human Discussion Delta

Human discussion can create strict-review graph deltas directly when the user asks for formal graph change.

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
Project memory:
Strict review:
Human gate:
Next natural prompt:
```
