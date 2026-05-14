---
title: "Demo Visual Affordance Related Work Lineage"
type: related-work-lineage
project: "DemoVisualAffordance"
round: "demo-affordance-lineage"
status: "candidate"
human_review: pending
---

# Demo Visual Affordance Related Work Lineage

## Boundary

This related-work lineage artifact is not Project Understanding Graph truth and does not create D* events.

## Positioning Note

Demo project sits between affordance grounding, dense geometry priors, and open-vocabulary foundation-model probing.

## Technical Routes

### Affordance Datasets And Grounding

Dataset and localization anchors for visual affordance regions.

- 2022. **Learning Affordance Grounding from Exocentric Images** [dataset-anchor, grounding-baseline] - Introduces an exocentric affordance grounding setting and dataset-style evaluation anchor.
- 2023. **LOCATE** [localization-anchor] - Provides a localization-oriented affordance anchor for dataset and grounding comparisons.

### Part And Geometry Priors

Dense descriptors and part correspondences that can support affordance transfer.

- 2022. **Deep ViT Features as Dense Visual Descriptors** [dense-descriptor-anchor, part-correspondence-prior] - Shows that transformer features can serve as dense descriptors for visual correspondence.

### Open Vocabulary Affordance

Methods that broaden affordance prediction beyond fixed labels or heavy supervision.

- 2024. **One-Shot Open Affordance Learning with Foundation Models** [open-vocabulary-anchor, foundation-model-adaptation] - Uses foundation models to adapt affordance prediction with limited examples and broader labels.
- 2024. **AffordanceLLM** [language-guided-affordance, semantic-prior] - Connects language-model affordance knowledge with visual grounding needs.

### Foundation Model Probing

Large visual encoders used as probes for affordance-relevant visual structure.

- 2025. **DINOv3** [foundation-encoder-anchor, feature-probing] - Serves as a public anchor for probing dense signals in modern self-supervised visual encoders.
- 2025. **Perception Encoder** [foundation-encoder-anchor, representation-probing] - Serves as a public anchor for broad visual representation probing.

## Explicit Lineage Edges

- `paper:luo2022-agd20k` influences `paper:li2023-locate`: Both papers anchor affordance localization and grounding evaluation.
- `paper:amir2022-dense-vit-descriptors` influences `paper:li2024-ooal`: Dense feature correspondence motivates foundation-model affordance transfer probes.
- `paper:li2024-ooal` contrasts-with `paper:qian2024-affordancellm`: One route emphasizes visual foundation-model adaptation while the other emphasizes language-guided affordance priors.
- `paper:simeoni2025-dinov3` competes-with `paper:bolya2025-perception-encoder`: Both are foundation-model probing anchors for general visual representations.
