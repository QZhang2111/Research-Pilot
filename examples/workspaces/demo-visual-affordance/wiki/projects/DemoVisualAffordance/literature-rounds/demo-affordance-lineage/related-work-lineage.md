---
title: "Geometry-Interaction Affordance Reasoning Lineage"
type: related-work-lineage
project: "DemoVisualAffordance"
round: "demo-affordance-lineage"
status: "candidate"
human_review: pending
---

# Geometry-Interaction Affordance Reasoning Lineage

## Boundary

This related-work lineage artifact is not Project Understanding Graph truth and does not create D* events.

## Positioning Note

Starting from arXiv:2602.20501, the field shape is not a simple citation chain. The baseline paper sits at a convergence of four paper routes: AGD20K/LOCATE define affordance grounding as localized action-region transfer; Amir-DINOv2-DINOv3 provide dense part/geometry priors; OOAL/AffordanceLLM test open and language-guided affordance generalization; FLUX.1 Kontext supplies the generative model family whose instruction-conditioned spatial behavior can be reinterpreted as interaction cues. The project contribution is the bridge: treat geometry and interaction as separable VFM capacities, then compose them in a training-free affordance estimator.

## Technical Routes

### Affordance Grounding Benchmarks

Papers that define visual affordance grounding as localization and establish exocentric-to-egocentric evaluation anchors.

- 2022.03 **Learning Affordance Grounding from Exocentric Images** [dataset, task-anchor, weak-supervision-baseline] - Establishes the core visual affordance grounding task and AGD20K benchmark that later project papers use as the main localization/evaluation frame.
- 2023.03 **LOCATE: Localize and Transfer Object Parts for Weakly Supervised Affordance Grounding** [part-transfer, weak-supervision-method, grounding-baseline] - Moves the grounding route from dataset/task framing toward explicit object-part transfer, making parts a central affordance localization mechanism.

### Part And Dense Geometry Priors

Papers showing that self-supervised visual features expose object parts, dense correspondences, and reusable geometry priors.

- 2021.12 **Deep ViT Features as Dense Visual Descriptors** [dense-descriptor, part-correspondence-prior, geometry-anchor] - Provides the early dense-feature premise: frozen self-supervised ViT features can expose object parts and correspondences without task-specific affordance training.
- 2023.04 **DINOv2: Learning Robust Visual Features without Supervision** [self-supervised-vfm, dense-feature-scale-up, geometry-prior] - Scales the dense self-supervised feature route from DINO-ViT descriptors into a general-purpose VFM backbone used by later affordance work.
- 2025.08 **DINOv3** [self-supervised-vfm, dense-feature-milestone, geometry-prior] - Supplies the latest dense-feature geometry backbone in the baseline paper's DINO-side argument.

### Open And Language-Guided Affordance

Papers that use foundation models or language knowledge to generalize affordance grounding beyond fixed closed-set supervision.

- 2024.01 **AffordanceLLM: Grounding Affordance from Vision Language Models** [vlm-knowledge, language-guided-grounding, semantic-prior] - Represents the language/world-knowledge route: use VLM priors to expand affordance grounding beyond narrow supervised labels.
- 2024.06 **One-Shot Open Affordance Learning with Foundation Models** [open-affordance, one-shot-learning, foundation-model-adaptation] - Shows that open-vocabulary affordance is not solved by generic VLM semantics; fine-grained affordance grounding still needs visual-part alignment.

### Generative Interaction Cues

Papers that make generative models relevant as action- or instruction-conditioned spatial priors rather than pure recognition encoders.

- 2025.06 **FLUX.1 Kontext: Flow Matching for In-Context Image Generation and Editing in Latent Space** [generative-model, instruction-conditioned-prior, interaction-cue-source] - Not an affordance method by itself, but supplies the generative, instruction-conditioned model family whose attention maps the baseline treats as interaction priors.

### VFM Probing And Bridging

Papers that probe what visual foundation models encode, then bridge geometry and interaction cues into an affordance reasoning account.

- 2024.04 **Probing the 3D Awareness of Visual Foundation Models** [vfm-probe, geometry-boundary, representation-analysis] - Adds the probing methodology and boundary language needed before claiming that VFM representations encode affordance-relevant geometry.
- 2025.04 **Perception Encoder: The best visual embeddings are not at the output of the network** [intermediate-feature-analysis, spatial-alignment, vfm-probe] - Strengthens the representation-probing route: affordance-relevant spatial signals may live in intermediate VFM layers rather than final global embeddings.
- 2026.02 **Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models** [baseline, project-anchor, synthesis, training-free-fusion] - Sits at the convergence point: converts grounding, dense geometry, VLM/open-affordance, and generative interaction cues into a probe-and-bridge account.

## Explicit Lineage Edges

- `paper:luo2022-agd20k` extends-method `paper:li2023-locate`: LOCATE keeps the exocentric-to-egocentric affordance grounding setup but shifts the mechanism toward object-part localization and transfer.
- `paper:amir2021-dense-vit-descriptors` extends-method `paper:oquab2023-dinov2`: DINOv2 scales the self-supervised ViT feature route from dense descriptors into robust all-purpose visual features at image and pixel levels.
- `paper:oquab2023-dinov2` extends-method `paper:simeoni2025-dinov3`: DINOv3 extends the DINO self-supervised route with stronger dense features and larger-scale foundation-model behavior.
- `paper:li2024-ooal` contrasts-with `paper:qian2024-affordancellm`: OOAL emphasizes visual-feature/text-embedding alignment under one-shot supervision, while AffordanceLLM emphasizes world and human-object-interaction knowledge from VLMs.
- `paper:flux2025-kontext` adapts-to-domain `paper:zhang2026-geometry-interaction-affordance`: The baseline adapts Flux-style instruction-conditioned generative behavior from image generation/editing into affordance interaction priors.
- `paper:simeoni2025-dinov3` adapts-to-domain `paper:zhang2026-geometry-interaction-affordance`: The baseline adapts DINO dense geometry into affordance-region estimation by fusing geometric prototypes with interaction maps.
- `paper:banani2024-probe3d` influences `paper:zhang2026-geometry-interaction-affordance`: Both use probing to ask what VFMs internally encode, but the baseline narrows the probe to affordance-relevant geometry and interaction cues.
