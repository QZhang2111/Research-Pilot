---
title: "Related Work Lineage Protocol v1"
type: workflow
status: active
human_review: approved
---

# Related Work Lineage Protocol v1

Use this protocol to build a paper-only route map for related-work understanding, baseline selection, or positioning a project contribution relative to prior work. Output is not PUG truth.

Boundary: this workflow must not append graph events, create D*, mutate Zotero, mark project-core/global-core approval, or treat output as Project Understanding Graph truth.

Dashboard views are read-only observers. They may display lineage artifacts but must not become source of truth.

## Required Context

Read:

```text
wiki/projects/<ProjectName>/overview.md
wiki/projects/<ProjectName>/project-query-pack.md
wiki/projects/<ProjectName>/literature-rounds/
wiki/projects/<ProjectName>/papers/
wiki/_system/workflows/related-work-lineage.md
```

Missing paths must be recorded in the lineage summary.

## Input Modes

Baseline paper mode:

- use directly when anchor papers are supplied;
- map technical routes around the anchor set;
- keep nodes limited to papers.

Broad direction mode:

- first produce 3-5 candidate technical routes;
- include 1-2 candidate baseline papers for each route;
- state why each route fits the project;
- state why each route may be excluded;
- ask the user to choose routes or baseline papers before map creation.

If the topic needs more than 20 papers, stop and ask the user to narrow or split maps by route, time window, method family, venue, or project contribution target. Exclude low-signal follow-ups instead of expanding the map.

## Artifact Location

Store lineage artifacts under:

```text
wiki/projects/<ProjectName>/literature-rounds/<round>/related-work-lineage.json
wiki/projects/<ProjectName>/literature-rounds/<round>/related-work-lineage.md
```

## Quality Bar

- Max 20 papers.
- If topic needs more than 20 papers, ask the user to narrow or split maps and exclude low-signal follow-ups.
- Every node is a paper with `kind: paper`.
- Roles are not nodes; dataset, benchmark, method, theory, survey, and system are roles attached to paper nodes.
- Route lanes are explicit.
- Date ordering is present and marked inferred when necessary.
- Cross-route edges are explicit only; no citation graph expansion.
- Source URL and source evidence exist for each paper.
- Review status exists for each paper.
- Positioning note explains where the project fits relative to prior work.
- Dashboard is read-only.

## Stop Point

Stop after artifact creation, validation, or summary rendering. Any project graph update requires separate human-gated workflow.
