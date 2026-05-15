---
title: "LOCATE"
type: paper-dossier
project: DemoVisualAffordance
paper_id: paper:li2023-locate
created: 2026-05-14
updated: 2026-05-14
year: 2023
tags: [demo, affordance, localization]
status: summarized
human_review: approved
confidence: medium
---

# LOCATE: Localize and Transfer Object Parts for Weakly Supervised Affordance Grounding

## Source Identity

- Canonical source ref: `li2023-locate`
- Source title: "LOCATE: Localize and Transfer Object Parts for Weakly Supervised Affordance Grounding"
- Source URL: `https://arxiv.org/pdf/2303.09665`
- Read level: full-text PDF extraction
- Read date: 2026-05-15
- Local read source: `/tmp/rp_deepread/li2023.txt`
- Project role: field core candidate; part localization and transfer bridge between exocentric interaction evidence and VFM dense part priors.

## Deep Read Notes

### Core Contribution

LOCATE addresses weakly supervised affordance grounding by explicitly localizing object parts involved in human-object interactions, then transferring that part evidence to egocentric object images. It is important because it puts "part" at the center of affordance transfer.

For the demo, LOCATE supports the geometry primitive and links AGD20K-style interaction learning to DINO-style dense part representation.

### Claims Relevant To Demo PUG

- Supports `C2`: affordance localization needs object-part structure.
- Supports `E5`: part-level evidence matters beyond object category labels.
- Supports `W2`: if internal representations separate functional parts, they can support transfer beyond fixed categories.

### Evidence Relevant To Demo PUG

The paper uses weak supervision from image-level labels and human-object interaction images. It uses class activation and part/prototype selection to identify interaction-relevant object regions, with DINO-ViT features helping select object-part prototypes. This is field support evidence for the baseline's geometry side.

### Warrants / Assumptions

The paper assumes that affordance transfer depends on discovering the right object part, not merely classifying the object or action. This warrant directly aligns with the baseline's claim that geometric/part structure is a necessary primitive.

### Limitations / What Not To Infer

- LOCATE remains a trained weakly supervised method, not training-free probing.
- DINO features are used as part-aware tools, but the paper does not offer the baseline's full VFM mechanistic decomposition.
- It does not address open vocabulary in the same sense as OOAL or AffordanceLLM.
- It should support the geometry route, not replace the baseline's central claim.

## Teaching-Grade Deep Read

### 1. Paper's real question

The paper asks how to ground affordances when pixel-level affordance labels are expensive but weak interaction evidence is available. More specifically, it asks how to find the object part that matters for an action.

### 2. Background tension

Weakly supervised affordance grounding can learn from image-level labels, but image-level supervision does not say which pixels or parts are functional. Exocentric interaction images show humans using objects, yet the model must distinguish human body regions, background, full object extent, and the actual object part involved in the interaction.

### 3. Author's core hypothesis

The hypothesis is that affordance grounding improves if the model first identifies interaction-relevant object parts and then transfers those parts to target object images. Part localization is treated as the missing bridge between weak labels and region-level affordance maps.

### 4. Paper structure

The paper motivates weak supervision, introduces LOCATE, explains part discovery and transfer, then evaluates against affordance grounding baselines on AGD20K-style settings.

### 5. Method mechanism

LOCATE uses visual activation to identify interaction regions, clusters embeddings into candidate prototypes, and selects object-part prototypes using part-aware features. DINO-ViT matters because its dense representation helps separate object parts. The mechanism is a concrete predecessor to the baseline's idea that DINO-style geometry can expose affordance-relevant structure.

### 6. Experiment logic

The experiments test whether explicit part localization improves weakly supervised affordance grounding. For the demo, the result supports the claim that part-level geometry is not incidental; it is a necessary substrate for transfer.

### 7. True insight

The true insight is that affordance transfer is often part transfer. A model must know not only that an object affords an action, but which structural subregion carries that affordance.

### 8. Position for the target project

In `DemoVisualAffordance`, LOCATE should be a field core candidate for `E5` and `C2`. It also helps explain why the baseline's DINO PCA prototype step is meaningful as a geometry extraction tool.

### 9. What not to learn

Do not learn that DINO part features alone are affordance understanding. LOCATE still uses weak supervision and interaction-derived labels. Also do not treat the method's clustering/prototype details as the demo's route axis; the project-level idea is part-mediated affordance transfer.

## Project Relevance

- Recommended project role: field core candidate.
- PUG support: `E5 -> C2`, with warrant support for `W2`.
- Lineage role: bridge node between exocentric grounding and dense VFM geometry.
- Human review question: whether LOCATE should be shown as direct support under `C2` or as bridge context under lineage only.

## Project Graph Delta Proposals

No D* block yet. Use `pug-candidate-spec-v1.md` after human review to create accepted graph events.
