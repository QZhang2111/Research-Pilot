---
title: "One-Shot Open Affordance Learning with Foundation Models"
type: paper-dossier
project: DemoVisualAffordance
paper_id: paper:li2024-ooal
created: 2026-05-14
updated: 2026-05-14
year: 2024
tags: [demo, affordance, open-vocabulary]
status: summarized
human_review: approved
confidence: medium
---

# One-Shot Open Affordance Learning with Foundation Models

## Source Identity

- Canonical source ref: `li2024-ooal`
- Source title: "One-Shot Open Affordance Learning with Foundation Models"
- Source URL: `https://arxiv.org/pdf/2311.17776`
- Read level: full-text PDF extraction
- Read date: 2026-05-15
- Local read source: project-local paper dossier notes in this file.
- Project role: field core candidate; one-shot open affordance learning and foundation-model transfer anchor.

## Deep Read Notes

### Core Contribution

OOAL studies one-shot open affordance learning: given very limited examples, can a model identify affordances for novel objects and affordance labels? It uses foundation-model knowledge but still builds a task-specific alignment and decoder pipeline.

For the demo, OOAL establishes the field pressure beyond fixed affordance labels. It is relevant because the baseline also addresses open affordance reasoning, but the baseline asks a different question: whether VFM internals already contain geometry and interaction cues.

### Claims Relevant To Demo PUG

- Supports `E7`: fixed affordance labels are insufficient; open affordance transfer is a real field pressure.
- Supports `C3` indirectly: language/action labels create pressure for action-conditioned grounding.
- Contrasts with `C4`: OOAL uses learned alignment, while the baseline demonstrates training-free primitive composition.

### Evidence Relevant To Demo PUG

OOAL evaluates on affordance datasets such as AGD20K and UMD under limited-example/open settings. It uses text prompt learning, multi-layer feature fusion, and a decoder to align visual features with affordance text embeddings. This is field support evidence for open affordance grounding, not baseline experimental evidence.

### Warrants / Assumptions

The warrant is that affordance systems must generalize beyond fixed labels and categories. Foundation models provide useful semantic priors, but fine-grained affordance grounding still needs alignment between language, visual features, and regions.

### Limitations / What Not To Infer

- OOAL is not training-free VFM probing.
- It does not isolate a geometry/interaction decomposition.
- Language/text alignment does not guarantee contact-region grounding.
- Its role in the demo is field pressure and contrast, not central mechanism.

## Teaching-Grade Deep Read

### 1. Paper's real question

The paper asks how to learn open affordances from extremely limited examples. The important shift is from closed affordance classes toward novel objects and novel affordance concepts.

### 2. Background tension

Traditional affordance datasets use fixed labels and enough supervision to learn those labels. Real affordance reasoning must handle new object categories and action words. Foundation models have broad knowledge, but their features do not automatically produce precise affordance masks.

### 3. Author's core hypothesis

The core hypothesis is that foundation-model visual and language knowledge can be adapted to one-shot open affordance grounding if the model learns the right visual-text alignment and combines multi-level visual features.

### 4. Paper structure

The paper defines the one-shot open affordance setting, analyzes foundation-model potential, proposes the OOAL framework, and evaluates generalization to novel objects/affordances.

### 5. Method mechanism

OOAL uses language prompts to represent affordance concepts, fuses visual features from multiple layers, and decodes region-level predictions guided by text-affordance alignment. The mechanism is alignment-and-decoding, not internal mechanism probing.

### 6. Experiment logic

The experiments test whether limited supervision plus foundation-model priors can generalize better than standard supervised affordance models. For the demo, this evidence shows why open affordance grounding matters and why semantics alone still needs visual localization machinery.

### 7. True insight

The true insight is that open affordance is a transfer problem, not just a label expansion problem. The model must connect a new affordance word or example to the correct object region.

### 8. Position for the target project

In `DemoVisualAffordance`, OOAL should support `E7` and provide lineage context for the baseline. It helps explain why the baseline's open affordance reasoning question is field-relevant, while leaving the baseline to supply the mechanistic geometry-interaction account.

### 9. What not to learn

Do not learn that text alignment is enough for affordance reasoning. Also do not treat OOAL as evidence that VFM primitives are already present. It shows transfer pressure and one solution path; the baseline studies internal visual/generative signals.

## Project Relevance

- Recommended project role: field core candidate.
- PUG support: `E7 -> C3`, plus contrast for `C4`.
- Lineage role: open affordance learning branch with foundation models.
- Human review question: whether to keep it as visible support under `C3` or use it mainly as lineage background.

## Project Graph Delta Proposals

No D* block yet. Use `pug-candidate-spec-v1.md` after human review to create accepted graph events.
