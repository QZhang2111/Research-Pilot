---
title: "Demo Visual Affordance Project Understanding Graph"
type: project-understanding-graph
project: DemoVisualAffordance
created: 2026-05-14
updated: 2026-05-15
tags: [demo, graph]
status: active
human_review: approved
confidence: medium
---

# Demo Visual Affordance Project Understanding Graph

## Project Questions

| id | text | status | confidence |
| --- | --- | --- | --- |
| Q1 | What mechanistic primitives make visual affordance understanding possible in Visual Foundation Models? | active | medium |
| Q2 | Can affordance reasoning in VFMs be explained as composition of geometric perception and interaction perception? | active | medium |
| Q3 | How can we distinguish genuine affordance-relevant cues from object semantics, part segmentation, or prompt-conditioned localization? | active | medium |

## Project Claims

| id | text | status | confidence |
| --- | --- | --- | --- |
| C0 | Affordance reasoning in VFMs can be decomposed into two composable primitives: geometric perception and interaction perception. | active | medium |
| C2 | Part-level geometric structure in discriminative and self-supervised VFMs provides the spatial substrate for affordance localization. | active | medium |
| C3 | Generative VFMs encode interaction priors that associate actions with plausible object contact regions. | active | medium |
| C4 | Training-free fusion of geometric primitives and interaction priors supports a mechanistic account of affordance reasoning in VFMs. | active | medium |

## Evidence

| id | text | status | confidence |
| --- | --- | --- | --- |
| E1 | Across probed VFMs, stronger geometric awareness aligns with better UMD affordance segmentation under controlled linear probing; depth and normal cues improve weaker geometry models. | active | medium |
| E2 | DINO-family representations expose stable part-level geometric structure; PCA is used as a method tool to isolate compact geometric prototypes. | active | medium |
| E3 | Flux and Flux Kontext verb-conditioned cross-attention localizes plausible interaction or contact regions and remains meaningful even when generation quality is imperfect. | active | medium |
| E4 | DINO geometry prototypes combined with Flux interaction maps yield training-free zero-shot affordance masks competitive with weakly supervised methods on AGD20K. | active | medium |
| E5 | Object-part affordance work shows that affordance prediction depends on localized functional parts rather than object category alone. | active | medium |
| E6 | Exocentric and interaction-grounded affordance work shows that observed action-object interaction can reveal actionable regions. | active | medium |
| E7 | Open affordance and language-conditioned grounding work shows the field pressure beyond fixed labels, while also exposing the risk that language semantics alone may not ground contact regions. | active | medium |
| E8 | Dense descriptor and VFM-prior work shows that frozen visual models can expose dense part or geometry correspondences worth probing. | active | medium |

## Warrants

| id | text | status | confidence |
| --- | --- | --- | --- |
| W1 | If affordance is a relation between agent action and object structure, then an account based only on object semantics or part segmentation is incomplete. | active | medium |
| W2 | If internal visual representations separate functional parts, they can support affordance transfer beyond fixed object categories. | active | medium |
| W3 | If verb-conditioned generative signals consistently localize contact regions, they can function as interaction priors. | active | medium |
| W4 | If independently probed geometry and interaction primitives can be composed without task-specific training to produce affordance maps, that supports a mechanistic account. | active | medium |

## Limitations

| id | text | status | confidence |
| --- | --- | --- | --- |
| L1 | The mechanistic account depends on the quality of extracted primitives: DINO geometry can be entangled with semantics, and Flux attention can be noisy or unstable. | active | medium |
| L2 | The evidence shows usable internal signals and composability, but does not fully prove that VFMs causally understand affordance in the human or embodied sense. | active | medium |
| L3 | UMD and AGD20K provide measurable affordance targets, but their masks or heatmaps only approximate the richer action-object relation. | active | medium |
| L4 | The training-free fusion is deliberately shallow; it demonstrates composability of primitives, not an optimal or complete affordance reasoning system. | active | medium |
| L5 | The paper studies visual grounding of affordance, not closed-loop manipulation, physical success, or policy learning. | active | medium |

## Reasoning Links

| id | premises | relation | target | warrant | limitations | confidence |
| --- | --- | --- | --- | --- | --- | --- |
| RL0 | C0 | answers | Q2 | W1 | L2, L5 | medium |
| RL1 | E1, E2, E5, E8 | supports | C2 | W2 | L1, L3 | medium |
| RL2 | E3, E6, E7 | supports | C3 | W3 | L1, L3 | medium |
| RL3 | E2, E3, E4 | supports | C4 | W4 | L4 | medium |
| RL4 | C2, C3, C4 | supports | C0 | W1 | L2, L5 | medium |
| RL5 | C0 | answers | Q1 | W1 | L2, L5 | medium |
| RL6 | C0 | answers | Q3 | W4 | L1, L2 | medium |
