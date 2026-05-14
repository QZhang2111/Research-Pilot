---
name: related-work-lineage
description: Use when the user wants related-work technical routes, a paper-only lineage map, broad direction narrowing into baseline paper candidates, or inspection of project contribution relative to prior work.
argument-hint: "[workspace path] [project id] [round id]"
---

# Related Work Lineage

Build a paper-only related-work lineage map for project-scoped technical route understanding.

## Boundary

This workflow maps papers only. Nodes must be papers. Dataset, benchmark, method, theory, survey, and system are paper roles, not graph nodes.

This is not a citation graph. Do not infer citation edges unless they are explicit cross-route influence/comparison edges needed for route understanding.

Do not append graph events. Do not create D* proposals. Do not require an existing Project Understanding Graph (PUG). Dashboard use is read-only observation.

## Required Context

Read:

```text
$WORKSPACE/wiki/projects/$PROJECT/overview.md
$WORKSPACE/wiki/projects/$PROJECT/project-query-pack.md
$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/
$WORKSPACE/wiki/projects/$PROJECT/papers/
$WORKSPACE/wiki/_system/workflows/related-work-lineage.md
```

If a path is absent, continue with available context and record the missing path in the artifact summary.

## Input Routing

Use baseline paper mode directly when the user provides one or more anchor papers or asks to map lineage around known baseline papers.

For a broad direction, first produce a narrowing menu:

- 3-5 candidate technical routes;
- each route has 1-2 candidate baseline papers;
- each route states why it fits the project;
- each route states why it may be excluded.

Ask the user to choose routes or baseline papers before creating the lineage map.

## Artifact Paths

Write/update artifacts under:

```text
$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/<round>/related-work-lineage.json
$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/<round>/related-work-lineage.md
```

## Commands

Create:

```bash
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" create --repo "$WORKSPACE" --project "$PROJECT" --round "$ROUND" --title "$TITLE" --json
```

Validate:

```bash
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" validate --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --json
```

Render summary:

```bash
python3 "$PLUGIN_ROOT/tools/related_work_lineage_cli.py" render-summary --path "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.json" --output "$WORKSPACE/wiki/projects/$PROJECT/literature-rounds/$ROUND/related-work-lineage.md"
```

## Output Requirements

Artifacts must include:

- max 20 papers;
- every node has `kind: paper`;
- title;
- year;
- route;
- roles;
- source URL;
- source evidence;
- review status;
- inferred date sequence;
- explicit cross-route edges only;
- positioning note for where the project fits relative to prior work.

## Stop Point

Stop after artifact creation or update. Graph updates belong to separate workflow.
