---
title: "Related Work Lineage Protocol v2"
type: workflow
status: active
human_review: approved
---

# Related Work Lineage Protocol v2

Build a paper-only route map for related-work understanding. Output is not PUG truth.

Boundary: output must not append graph events, create D*, mutate Zotero, mark sources project-core/global-core, or treat output as Project Understanding Graph truth. Dashboard views are read-only observers.

## Baseline-Paper Rule

When an anchor/baseline paper is supplied, use it to infer **field scope**:

- primary problem;
- input/output;
- benchmarks and datasets;
- evaluation setting;
- method/evaluation setting;
- broader field structure and adjacent problem settings;
- exclusion rules.

Do not turn the paper's internal method components into route lanes unless the user explicitly asks for method motivation lineage.

## Field Ontology First

Choose route lanes from the field's natural ontology before using the baseline paper's novelty claim.

Ask what kinds of problems, target settings, outputs, benchmarks, or paper traditions organize the field if the baseline paper is removed. Do not begin by turning the baseline's components, cues, modules, backbones, losses, or fusion steps into route lanes.

Prefer candidate lane axes in this order:

1. object of study or target setting;
2. task formulation or output/evaluation object;
3. benchmark/dataset community;
4. application or deployment context;
5. field tradition/problem-position;
6. method/evidence source, only when papers in the field are actually organized that way;
7. baseline method components, forbidden unless the user explicitly asks for method motivation.

If a candidate lane axis mostly restates the baseline's claimed novelty, demote it to a non-lane axis unless the user asks for method motivation.

## Required Context

Read:

```text
wiki/projects/<ProjectName>/overview.md
wiki/projects/<ProjectName>/project-query-pack.md
wiki/projects/<ProjectName>/literature-rounds/
wiki/projects/<ProjectName>/papers/
wiki/_system/workflows/related-work-lineage.md
```

Missing paths must be recorded in the lineage artifact.

## Search Standard

For baseline-paper field surveys, first derive 3-6 taxonomy axes from the baseline paper:

```text
related-work categories named by the paper
comparison-method groups
datasets, benchmarks, and metrics
input/output variants
field positions or adjacent problem settings
explicit limitations and gaps
```

Before artifact creation, create 3-6 candidate lane axes. For each candidate, record:

- axis name;
- candidate lanes;
- source in baseline paper, project context, or exploratory search;
- why it is field-native rather than baseline-method-native;
- weakness or risk;
- checks for baseline-removal, neighbor-paper fit, project-intent fit, and non-component status;
- decision: selected or rejected.

Select the lane axis that best matches project intent, captures field ontology, organizes neighboring papers without forcing them, remains meaningful without the baseline paper, and does not merely restate the baseline contribution. If ambiguous, ask the user to choose before writing the artifact.

Then run enough field-first searches to cover the derived axes:

- field/problem definition and benchmark query;
- one query per derived taxonomy axis;
- benchmark/latest query for each major dataset or benchmark;
- survey/SOTA calibration query;
- adjacent-branch queries only when the baseline paper or field boundary supports them.

Do not hard-code domain-specific axes such as supervision, openness, modality, or architecture family unless the baseline paper itself supports that taxonomy.

## Artifact Location

Store artifacts under:

```text
wiki/projects/<ProjectName>/literature-rounds/<round>/related-work-lineage.json
wiki/projects/<ProjectName>/literature-rounds/<round>/related-work-lineage.md
```

## Quality Bar

- Max 20 papers per artifact; split if larger.
- If the map would exceed 20 papers, ask the user to narrow or split maps before expanding scope.
- Always exclude low-signal follow-ups that only restate the same method or benchmark position without changing the field structure.
- Every node is a paper with `kind: paper`.
- Baseline-paper mode requires `baseline_paper_field_scope`.
- `baseline_paper_field_scope` must include non-empty `derived_taxonomy` and `field_structure`.
- Baseline-paper mode requires non-empty `axis_candidates` with one selected candidate matching `field_structure.lane_axis.name`.
- Papers in baseline-paper mode require `field_position`, `method_setting`, and `artifact_type`.
- Routes are field-structure/problem-position lanes, not method-internal component lanes.
- Dates use arXiv/release date when available; venue date only if no release date is available.
- Source URL and source evidence exist for each paper.
- Search log records `derived_from` for dynamic query planning.
- Written output includes chronological catalog, major trends, notable forks, and baseline positioning.
- Dashboard is read-only.

## Stop Point

Stop after artifact creation, validation, or summary rendering. Any project graph update requires separate human-gated workflow.
