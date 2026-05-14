---
title: "Demo Visual Affordance Project Understanding Graph"
type: project-understanding-graph
project: DemoVisualAffordance
created: 2026-05-14
updated: 2026-05-14
tags: [demo, graph]
status: active
human_review: approved
confidence: medium
---

# Demo Visual Affordance Project Understanding Graph

## Project Questions

| id | text | status | confidence |
| --- | --- | --- | --- |
| Q1 | What evidence links open-vocabulary visual features to actionable part-level affordance predictions? | accepted | medium |

## Project Claims

| id | text | status | confidence |
| --- | --- | --- | --- |
| C1 | Dataset-grounded affordance labels make interaction regions measurable but narrow vocabulary and scenario coverage. | active | medium |
| C2 | Dense foundation-model descriptors can expose reusable part correspondences that support affordance transfer. | active | medium |

## Evidence

| id | text | status | confidence |
| --- | --- | --- | --- |
| E1 | AGD20K and LOCATE provide public anchors for grounding affordance regions in images. | active | medium |
| E2 | Dense ViT descriptors and later foundation encoders are public anchors for probing visual correspondence. | active | medium |

## Warrants

| id | text | status | confidence |
| --- | --- | --- | --- |
| W1 | If descriptors align semantically similar object parts, they can support affordance transfer across categories. | active | medium |

## Limitations

| id | text | status | confidence |
| --- | --- | --- | --- |
| L1 | Demo evidence is intentionally lightweight and should not be treated as reviewed project truth. | active | medium |

## Reasoning Links

| id | premises | relation | target | warrant | limitations | confidence |
| --- | --- | --- | --- | --- | --- | --- |
| RL1 | E1, E2 | supports | C2 | W1 | L1 | medium |
