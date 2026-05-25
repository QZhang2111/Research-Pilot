---
title: "Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models"
type: paper-dossier
project: DemoVisualAffordance
paper_id: paper:zhang2026-geometry-interaction-vfm
created: 2026-05-15
updated: 2026-05-15
year: 2026
tags: [demo, affordance, vfm, mechanistic-account]
status: summarized
review_status: summarized
summary_status: agent-draft
human_review: pending
confidence: medium
project_core_for: []
global_core: false
---

# Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models

## Source Identity

- Canonical source ref: `zhang2026-geometry-interaction-vfm`
- Source title: "Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models"
- Source type: baseline paper for `DemoVisualAffordance`
- Source URL: `https://arxiv.org/pdf/2602.20501`
- Read level: full-text PDF extraction
- Read date: 2026-05-15
- Local read source: project-local paper dossier notes in this file.
- Project role: baseline core; supplies central question, paper thesis, baseline experimental evidence, and method pipeline for the demo.

## Deep Read Notes

### Core Contribution

This paper should not be read as a conventional affordance segmentation method. Its real contribution is to decompose VFM affordance reasoning into inspectable mechanism questions: whether the model already contains enough `geometric perception`, whether it exposes usable `interaction perception`, and whether those two signals can compose into an affordance map.

The core thesis is that affordance reasoning in VFMs can be explained as a composition of two primitives. One primitive is an object-part / spatial-layout / geometry cue. The other is an action-conditioned interaction cue. DINO PCA prototypes and Flux attention are tools for observing and bridging these primitives, not the final theory itself.

### Claims Relevant To Demo PUG

- Supports `C0`: affordance reasoning in VFMs can be decomposed into geometric perception and interaction perception.
- Supports `C2`: DINO-family and related VFMs contain part-level geometric structure that can serve as spatial substrate for affordance localization.
- Supports `C3`: Flux / Flux Kontext verb-conditioned attention can act as an interaction prior over plausible contact regions.
- Supports `C4`: training-free composition of geometry prototype and interaction prior gives a mechanistic account, not merely another supervised mask predictor.

### Evidence Relevant To Demo PUG

- `E1`: geometry-aware VFMs perform better under UMD-style linear probing; weaker geometry models benefit from depth or normal augmentation.
- `E2`: DINO-family internal representations expose stable part-level structure; PCA is used to isolate compact geometric prototypes.
- `E3`: Flux-family verb-conditioned cross-attention localizes plausible interaction/contact regions, even when image generation is imperfect.
- `E4`: combining DINO geometry prototypes with Flux interaction maps yields training-free zero-shot affordance masks competitive with weakly supervised AGD20K methods.

### Warrants / Assumptions

The paper relies on a relational definition of affordance: an affordance is not an object label alone and not a part mask alone, but a relation between action and object structure. This justifies separating geometry from interaction, then asking whether they can be recombined.

The mechanistic warrant is stronger than ordinary performance reporting: if independently probed geometry and interaction signals can be composed without task-specific training and still produce meaningful affordance maps, then those signals are plausible internal primitives for VFM affordance reasoning.

### Limitations / What Not To Infer

- Do not infer that VFM has human-like or embodied affordance understanding.
- Do not infer causal mechanism solely from attention maps or PCA maps.
- Do not treat DINO PCA as the thesis; it is an instrument for extracting geometry evidence.
- Do not treat Flux attention as ground truth contact; it is a noisy interaction prior.
- Do not treat AGD20K/UMD masks as full physical affordance truth.
- Do not claim policy learning, closed-loop manipulation, or execution success.

## Teaching-Grade Deep Read

### 1. Paper's real question

The real question is: what must already be present inside a Visual Foundation Model for visual affordance reasoning to be possible? The paper narrows this to a mechanistic account. Instead of asking only whether a model can output a good affordance mask, it asks whether the model contains separable geometry and interaction signals that explain how such a mask could arise.

### 2. Background tension

Affordance grounding work traditionally learns masks from affordance labels or human-object interaction data. Foundation-model work often assumes that large visual or generative models already contain rich semantic and spatial knowledge. The tension is that affordance needs both: object structure tells where action could happen, while action-conditioned interaction tells which part matters for the requested verb. Semantics alone can name a chair; it does not identify the sit-able surface under a particular action.

### 3. Author's core hypothesis

The core hypothesis is that affordance reasoning in VFMs can be decomposed into two composable primitives: geometric perception and interaction perception. Geometry supplies part-level spatial candidates. Interaction supplies action-conditioned contact likelihood. If the two signals exist and can be bridged, affordance grounding becomes explainable as composition rather than opaque end-task supervision.

### 4. Paper structure

The argument has three moves. First, probe geometry in different VFMs and test whether geometry awareness correlates with affordance localization. Second, probe interaction signals in generative VFMs, especially verb-conditioned attention in Flux-family models. Third, bridge the two signals in a training-free pipeline and test whether their composition produces useful affordance maps.

### 5. Method mechanism

The geometry side uses internal visual features and PCA-like prototype extraction to expose part-level structure. This mechanism tests whether discriminative/self-supervised VFMs encode the spatial substrate needed for affordance. The interaction side uses verb-conditioned cross-attention from generative models as an interaction prior. The bridge aligns the two: geometry constrains where plausible object parts are, interaction selects which of those parts are action-relevant.

### 6. Experiment logic

The geometry experiments support `E1` and `E2`: if geometry matters, then better geometric representations should correlate with better affordance probes, and part prototypes should be visible in internal features. The interaction experiments support `E3`: if generative models encode action-object relations, verb prompts should highlight plausible contact regions. The zero-shot fusion experiments support `E4`: if the two primitives are composable, their fusion should work without task-specific training.

### 7. True insight

The lasting insight is not "DINO plus Flux works." The lasting insight is that affordance reasoning can be made legible as a decomposition into geometry and interaction. This gives the demo a clean Toulmin structure: claim is decomposition, grounds are geometry/interaction/fusion evidence, warrants are relational affordance assumptions, and limitations bound what probing can prove.

### 8. Position for the target project

For `DemoVisualAffordance`, this is the baseline convergence node. It should sit at the center of the PUG and dashboard argument map. Earlier papers justify why part-level masks, exocentric interaction cues, open affordance transfer, and dense VFM priors matter. This paper reinterprets those threads as evidence for a mechanistic account.

### 9. What not to learn

Do not build the demo around internal modules such as DINO PCA, Flux attention, or a specific loss as if they were separate research routes. The right abstraction is task/mechanism level: geometry primitive, interaction prior, and compositional bridge. Also do not overclaim that the model "understands" affordance in an embodied sense; the paper studies visual grounding evidence.

## Project Relevance

- Recommended project role: baseline core.
- Primary PUG impact: anchors `Q2`, `C0`, `C2`, `C3`, `C4`, and baseline evidence `E1`-`E4`.
- Dashboard impact: should be the center node in the claim-centered GSN / Toulmin view.
- Lineage impact: convergence node that reinterprets object-part grounding, interaction grounding, open affordance, and dense VFM priors.
- Human review question: whether to phrase the central claim as "mechanistic account" or "decomposition hypothesis" in the visible dashboard.

## Project Graph Delta Proposals

No D* block yet. Use `pug-candidate-spec-v1.md` after human review to create accepted graph events.
