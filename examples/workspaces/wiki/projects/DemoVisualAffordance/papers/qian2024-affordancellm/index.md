---
title: "AffordanceLLM"
type: paper-dossier
project: DemoVisualAffordance
paper_id: paper:qian2024-affordancellm
created: 2026-05-14
updated: 2026-05-14
year: 2024
tags: [demo, affordance, language-models]
status: summarized
human_review: approved
confidence: medium
---

# AffordanceLLM

## Source Identity

- Canonical source ref: `qian2024-affordancellm`
- Source title: "AffordanceLLM: Grounding Affordance from Vision Language Models"
- Source URL: `https://arxiv.org/pdf/2401.06341`
- Read level: full-text PDF extraction
- Read date: 2026-05-15
- Local read source: project-local paper dossier notes in this file.
- Project role: contrast/core candidate; language/VLM affordance reasoning branch against the baseline's visual-prior cue auditing.

## Deep Read Notes

### Core Contribution

AffordanceLLM grounds affordances using VLM/LLM world knowledge, visual input, and geometry cues. It frames large vision-language models as sources of human-object interaction knowledge and adapts them to produce affordance heatmaps.

For the demo, this paper is important as contrast. It addresses similar open affordance questions, but its explanatory route is language/world-knowledge grounding, while the baseline's route is VFM geometry and interaction cue auditing.

### Claims Relevant To Demo PUG

- Supports `E7`: language-conditioned grounding is a major branch for open affordance reasoning.
- Contrasts with `C3` and `C4`: language/VLM reasoning differs from probing generative visual interaction priors.
- Supports `Q3`: the project must distinguish contact-relevant cues from broad semantic or prompt-conditioned localization.

### Evidence Relevant To Demo PUG

The paper uses a VLM-centered architecture, mask token/decoder style grounding, and geometry/depth information to output affordance heatmaps. It evaluates on AGD20K-style settings, including generalization to unseen or harder examples. This is field support and contrast evidence.

### Warrants / Assumptions

The warrant is that language models encode broad world and human-object interaction knowledge, and that this knowledge can guide visual grounding when paired with image and geometry features. The baseline accepts that this route exists but asks a different mechanistic question: whether visual foundation models themselves contain usable geometry and interaction cues.

### Limitations / What Not To Infer

- VLM world knowledge may hallucinate or over-rely on object semantics.
- Language-guided attention is not automatically contact-grounded.
- The method is supervised/fine-tuned, not pure zero-shot primitive composition.
- It should be used as contrast and field pressure, not as proof of the baseline's mechanism.

## Teaching-Grade Deep Read

### 1. Paper's real question

The paper asks whether the knowledge inside vision-language models can be converted into affordance grounding. It treats affordance as something partly stored in language/world knowledge: what humans do with objects, and where those actions usually apply.

### 2. Background tension

VLMs know many object-action facts but are weak at precise pixel grounding. Affordance requires both semantic knowledge and region-level localization. The paper responds by building a grounding pipeline around VLM knowledge plus visual/geometric decoding.

### 3. Author's core hypothesis

The hypothesis is that VLMs contain useful affordance and interaction knowledge, and that this knowledge can guide a decoder to produce affordance maps when supported by image and geometry features.

### 4. Paper structure

The paper motivates VLM affordance grounding, proposes AffordanceLLM, constructs or adapts evaluation splits, and tests whether language-grounded knowledge improves affordance localization and generalization.

### 5. Method mechanism

The mechanism is semantic reasoning plus visual grounding. A VLM supplies action/object knowledge; special grounding tokens and decoders translate that knowledge into spatial heatmaps. Depth or geometry features help constrain the output.

### 6. Experiment logic

The experiments test whether VLM-guided grounding generalizes across objects and actions. For the demo, the evidence shows that open affordance can be approached through language/world knowledge, but also motivates `Q3`: good semantic knowledge must be separated from true contact-region evidence.

### 7. True insight

The true insight is that open affordance reasoning has a language route and a visual-prior route. AffordanceLLM represents the language route; the baseline represents the visual cue-auditing route. Their contrast clarifies why the demo should not collapse all foundation-model affordance work into one bucket.

### 8. Position for the target project

In `DemoVisualAffordance`, AffordanceLLM should be a contrast/core candidate. It can support `E7` while also strengthening the need for `Q3`: how to tell whether a model grounds action-relevant regions rather than repeating object-action semantics.

### 9. What not to learn

Do not learn that VLM semantic knowledge solves affordance grounding by itself. Also do not use AffordanceLLM as evidence that Flux attention is an interaction prior; it supports the broader field pressure and contrast, not the baseline's internal mechanism.

## Project Relevance

- Recommended project role: contrast/core candidate.
- PUG support: `E7`, `Q3`, contrast against `C4`.
- Lineage role: language-conditioned affordance grounding branch.
- Human review question: classify as core contrast paper or non-core background after human reading.

## Project Graph Delta Proposals

No D* block yet. Use `pug-candidate-spec-v1.md` after human review to create accepted graph events.
