---
title: "AffordanceNet: An End-to-End Deep Learning Approach for Object Affordance Detection"
type: paper-dossier
project: DemoVisualAffordance
paper_id: paper:do2017-affordancenet
created: 2026-05-15
updated: 2026-05-15
year: 2017
tags: [demo, affordance, segmentation, object-part-grounding]
status: summarized
review_status: summarized
summary_status: agent-draft
human_review: pending
confidence: medium
project_core_for: []
global_core: false
---

# AffordanceNet: An End-to-End Deep Learning Approach for Object Affordance Detection

## Source Identity

- Canonical source ref: `do2017-affordancenet`
- Source title: "AffordanceNet: An End-to-End Deep Learning Approach for Object Affordance Detection"
- Source URL: `https://arxiv.org/pdf/1709.07326`
- Read level: full-text PDF extraction
- Read date: 2026-05-15
- Local read source: `/tmp/rp_deepread/do2017.txt`
- Project role: field core candidate; classic 2D object-part affordance segmentation anchor.

## Deep Read Notes

### Core Contribution

AffordanceNet turns object affordance detection into an end-to-end RGB perception task: detect object instances and predict pixel-level affordance masks for each object. It moves the field from object category recognition toward localized functional regions.

For this demo, its value is not that it resembles the baseline method. Its value is historical and conceptual: it establishes that affordance prediction requires object-part localization. This supports the geometry side of the baseline argument.

### Claims Relevant To Demo PUG

- Supports `C2`: affordance localization depends on part-level spatial structure, not object category alone.
- Supports `E5`: classic object-part affordance work treats functional regions as pixel-level outputs.
- Provides contrast for `C4`: supervised closed-label mask prediction is different from training-free VFM primitive composition.

### Evidence Relevant To Demo PUG

AffordanceNet reports object detection plus affordance segmentation on datasets such as IIT-AFF and UMD. The evidence is field support evidence, not baseline experimental evidence. It shows that localized object parts are a stable affordance target before the VFM era.

### Warrants / Assumptions

If affordance labels must be grounded as regions on an object, then a useful model needs spatial/part representation. This is the warrant connecting AffordanceNet to the baseline's geometry primitive.

### Limitations / What Not To Infer

- The method is closed-label and supervised; it does not solve open affordance transfer.
- It does not provide a mechanistic account of VFM internals.
- It does not show interaction priors; action/object relation is represented through annotated affordance classes.
- It should not become a route axis for this demo. It is evidence for the `rgb_object_part_grounding` lane.

## Teaching-Grade Deep Read

### 1. Paper's real question

The paper asks how a vision model can detect not only objects, but the specific regions of objects that afford actions. In 2017, this was a shift from "what object is present?" to "which part of this object is usable for a function?"

### 2. Background tension

Object detection gives boxes and class labels, but affordance needs a more fine-grained output. A knife handle and a knife blade belong to the same object but support different interactions. The paper responds to that gap by treating affordance as instance-level part segmentation.

### 3. Author's core hypothesis

The hypothesis is that object detection and affordance segmentation should be learned jointly. Object context helps infer affordance regions, while pixel-level affordance masks make object understanding more functional.

### 4. Paper structure

The paper defines the task, builds an end-to-end network with detection and mask branches, evaluates on standard affordance datasets, and shows that joint object/affordance modeling can produce usable pixel-level outputs.

### 5. Method mechanism

The method follows the logic of instance-aware segmentation. A detection branch localizes object instances. An affordance branch predicts masks for functional regions inside those instances. The mechanism is supervised learning from annotated affordance masks, not zero-shot inference from foundation-model priors.

### 6. Experiment logic

The experiments test whether joint detection plus mask prediction can recover affordance regions on object-centric datasets. For the demo PUG, the important evidence is that evaluation itself is spatial: success depends on localized mask quality, which supports the need for geometric/part substrate.

### 7. True insight

The durable insight is that affordance is not reducible to object category. It lives in object parts and spatial regions. This is the field-level premise later reused by LOCATE, AGD20K-style grounding, and the baseline's DINO geometry primitive.

### 8. Position for the target project

In `DemoVisualAffordance`, AffordanceNet should be a field core candidate for `C2` and `E5`. It anchors the classic supervised object-part lane, then the baseline moves beyond it by asking whether VFMs already encode part geometry internally.

### 9. What not to learn

Do not learn that the demo should frame affordance as ordinary supervised segmentation. Also do not treat AffordanceNet as evidence for interaction priors or open-vocabulary transfer. Its scope is localized object-part mask prediction under fixed labels.

## Project Relevance

- Recommended project role: field core candidate.
- PUG support: `E5 -> C2` through object-part affordance grounding.
- Lineage role: early anchor for the RGB object-part grounding lane.
- Human review question: likely core enough for demo background, but not central enough to drive the visible thesis.

## Project Graph Delta Proposals

No D* block yet. Use `pug-candidate-spec-v1.md` after human review to create accepted graph events.
