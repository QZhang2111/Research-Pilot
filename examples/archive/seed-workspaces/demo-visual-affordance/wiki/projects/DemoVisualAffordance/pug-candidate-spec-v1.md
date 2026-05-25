---
title: "Demo Visual Affordance PUG Candidate Spec v1"
type: pug-candidate-spec
project: DemoVisualAffordance
status: candidate
human_review: pending
created: 2026-05-15
updated: 2026-05-15
source_boundary: human_review_draft_not_graph_truth
tags: [demo, affordance, pug-candidate]
---

# Demo Visual Affordance PUG Candidate Spec v1

## Boundary

This document is a human-review draft for rebuilding the DemoVisualAffordance Project Understanding Graph from the baseline paper understanding. It is not graph truth and does not append graph events.

Existing placeholder PUG content should be ignored for this draft. This spec starts from the baseline paper, the approved lineage map, and the human discussion on 2026-05-15.

## Source Frame

- Baseline paper: `zhang2026-geometry-interaction-vfm`
- Baseline title: "Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models"
- Lineage source: `demo-affordance-lineage/related-work-lineage`
- Demo purpose: reconstruct paper understanding, not reproduce the original research process.

## Candidate Questions

| id | question | role | note |
| --- | --- | --- | --- |
| Q1 | What mechanistic primitives make visual affordance understanding possible in Visual Foundation Models? | framing | Broad framing question for the demo project. |
| Q2 | Can affordance reasoning in VFMs be explained as composition of geometric perception and interaction perception? | primary | Main question aligned with the baseline paper thesis. |
| Q3 | How can we distinguish genuine affordance-relevant cues from object semantics, part segmentation, or prompt-conditioned localization? | validation | Critical question that guards against over-reading probes or attention maps. |

## Dashboard Projection Plan

The project dashboard renders a GSN / Toulmin argument map as a claim-centered view:

- Question cards define project questions and map to claims.
- Claim nodes form the visible argument backbone.
- Evidence, Warrant, and Limitation nodes are placed inside each selected claim's Toulmin detail.
- ReasoningLink records decide which Evidence, Warrant, and Limitation belong to each Claim.

For this demo, use `C0` as the primary claim so the dashboard places it at the center of the argument backbone.

| display role | graph id | content |
| --- | --- | --- |
| primary question | Q2 | Can affordance reasoning in VFMs be explained as composition of geometric perception and interaction perception? |
| framing question | Q1 | What mechanistic primitives make visual affordance understanding possible in Visual Foundation Models? |
| validation question | Q3 | How can we distinguish genuine affordance-relevant cues from object semantics, part segmentation, or prompt-conditioned localization? |
| primary claim | C0 | Affordance reasoning in VFMs can be decomposed into two composable primitives: geometric perception and interaction perception. |
| supporting claim | C2 | Part-level geometric structure in discriminative and self-supervised VFMs provides the spatial substrate for affordance localization. |
| supporting claim | C3 | Generative VFMs encode interaction priors that associate actions with plausible object contact regions. |
| supporting claim | C4 | Training-free fusion of geometric primitives and interaction priors supports a mechanistic account of affordance reasoning in VFMs. |

## Candidate Claims

| id | claim | source_refs | note |
| --- | --- | --- | --- |
| C0 | Affordance reasoning in VFMs can be decomposed into two composable primitives: geometric perception and interaction perception. | `zhang2026-geometry-interaction-vfm` | Primary dashboard claim and central thesis. |
| C2 | Part-level geometric structure in discriminative and self-supervised VFMs provides the spatial substrate for affordance localization. | `zhang2026-geometry-interaction-vfm`, `do2017-affordancenet`, `li2023-locate`, `amir2021-dense-vit-descriptors`, `oquab2023-dinov2`, `simeoni2025-dinov3` | Geometry primitive claim. |
| C3 | Generative VFMs encode interaction priors that associate actions with plausible object contact regions. | `zhang2026-geometry-interaction-vfm`, `luo2022-agd20k`, `qian2024-affordancellm` | Interaction primitive claim. |
| C4 | Training-free fusion of geometric primitives and interaction priors supports a mechanistic account of affordance reasoning in VFMs. | `zhang2026-geometry-interaction-vfm` | Composition claim. |

## Candidate Evidence

| id | evidence | source_type | source_refs | supports |
| --- | --- | --- | --- | --- |
| E1 | Across probed VFMs, stronger geometric awareness aligns with better UMD affordance segmentation under controlled linear probing; depth and normal cues improve weaker geometry models. | baseline experimental evidence | `zhang2026-geometry-interaction-vfm` | C2 |
| E2 | DINO-family representations expose stable part-level geometric structure; PCA is used as a method tool to isolate compact geometric prototypes. | baseline experimental evidence | `zhang2026-geometry-interaction-vfm` | C2, C4 |
| E3 | Flux and Flux Kontext verb-conditioned cross-attention localizes plausible interaction or contact regions and remains meaningful even when generation quality is imperfect. | baseline experimental evidence | `zhang2026-geometry-interaction-vfm` | C3, C4 |
| E4 | DINO geometry prototypes combined with Flux interaction maps yield training-free zero-shot affordance masks competitive with weakly supervised methods on AGD20K. | baseline experimental evidence | `zhang2026-geometry-interaction-vfm` | C4 |
| E5 | Object-part affordance work shows that affordance prediction depends on localized functional parts rather than object category alone. | field support evidence | `do2017-affordancenet`, `li2023-locate` | C2 |
| E6 | Exocentric and interaction-grounded affordance work shows that observed action-object interaction can reveal actionable regions. | field support evidence | `luo2022-agd20k` | C3 |
| E7 | Open affordance and language-conditioned grounding work shows the field pressure beyond fixed labels, while also exposing the risk that language semantics alone may not ground contact regions. | field support evidence | `li2024-ooal`, `qian2024-affordancellm` | C3 |
| E8 | Dense descriptor and VFM-prior work shows that frozen visual models can expose dense part or geometry correspondences worth probing. | field support evidence | `amir2021-dense-vit-descriptors`, `oquab2023-dinov2`, `simeoni2025-dinov3` | C2 |

## Candidate Warrants

| id | warrant | supports_reasoning |
| --- | --- | --- |
| W1 | If affordance is a relation between agent action and object structure, then an account based only on object semantics or part segmentation is incomplete. | C2 + C3 + C4 -> C0 |
| W2 | If internal visual representations separate functional parts, they can support affordance transfer beyond fixed object categories. | E1 + E2 + E5 + E8 -> C2 |
| W3 | If verb-conditioned generative signals consistently localize contact regions, they can function as interaction priors. | E3 + E6 + E7 -> C3 |
| W4 | If independently probed geometry and interaction primitives can be composed without task-specific training to produce affordance maps, that supports a mechanistic account. | E2 + E3 + E4 -> C4 |

## Candidate Limitations

| id | limitation | bounds |
| --- | --- | --- |
| L1 | The mechanistic account depends on the quality of extracted primitives: DINO geometry can be entangled with semantics, and Flux attention can be noisy or unstable. | C2, C3, C4 |
| L2 | The evidence shows usable internal signals and composability, but does not fully prove that VFMs causally understand affordance in the human or embodied sense. | C0 |
| L3 | UMD and AGD20K provide measurable affordance targets, but their masks or heatmaps only approximate the richer action-object relation. | C2, C4 |
| L4 | The training-free fusion is deliberately shallow; it demonstrates composability of primitives, not an optimal or complete affordance reasoning system. | C4 |
| L5 | The paper studies visual grounding of affordance, not closed-loop manipulation, physical success, or policy learning. | C0, C4 |

## Candidate Reasoning Links

| id | from | relation | to | warrants | limitations | confidence |
| --- | --- | --- | --- | --- | --- | --- |
| RL0 | Q2 | frames | C0 |  |  | medium |
| RL1 | E1, E2, E5, E8 | supports | C2 | W2 | L1, L3 | medium |
| RL2 | E3, E6, E7 | supports | C3 | W3 | L1, L3 | medium |
| RL3 | E2, E3, E4 | supports | C4 | W4 | L4 | medium |
| RL4 | C2, C3, C4 | supports | C0 | W1 | L2, L5 | medium |

## Claim-Centered Toulmin Detail

| claim | supporting claims | evidence / grounds | warrant / bridge | limitations / rebuttal |
| --- | --- | --- | --- | --- |
| C0 | C2, C3, C4 |  | W1 | L2, L5 |
| C2 |  | E1, E2, E5, E8 | W2 | L1, L3 |
| C3 |  | E3, E6, E7 | W3 | L1, L3 |
| C4 |  | E2, E3, E4 | W4 | L4 |

## Core Paper Candidates

| paper | proposed_role | why |
| --- | --- | --- |
| `zhang2026-geometry-interaction-vfm` | baseline core | Supplies the main thesis, experimental evidence, composition evidence, and method pipeline. |
| `do2017-affordancenet` | field core candidate | Anchors classic object-part affordance segmentation. |
| `luo2022-agd20k` | field core candidate | Anchors exocentric affordance grounding and interaction-region supervision. |
| `li2023-locate` | field core candidate | Connects part localization and transfer to weakly supervised affordance grounding. |
| `li2024-ooal` | field core candidate | Anchors one-shot open affordance learning with foundation models. |
| `qian2024-affordancellm` | contrast/core candidate | Contrasts language or VLM affordance reasoning with visual-prior cue auditing. |
| `amir2021-dense-vit-descriptors` | warrant support candidate | Supports the dense visual descriptor premise behind VFM geometry probing. |
| `oquab2023-dinov2` | warrant support candidate | Supports self-supervised VFM dense visual priors. |
| `simeoni2025-dinov3` | warrant support candidate | Supports recent VFM dense-prior lineage used around the baseline. |

## Human Review Queue

- Confirm whether Q1 should enter the graph or remain page-level framing context.
- Confirm whether Q3 should enter the graph in this first draft or remain a validation note.
- Confirm whether E7 should remain evidence for C3 or be treated only as contrast/background.
- Decide whether `qian2024-affordancellm` is core, contrast, or context.
- Decide whether 3D spatial affordance papers should enter this first PUG draft or remain lineage-only for now.
- After review, convert accepted parts into a D* graph delta; do not append graph events from this draft directly.
