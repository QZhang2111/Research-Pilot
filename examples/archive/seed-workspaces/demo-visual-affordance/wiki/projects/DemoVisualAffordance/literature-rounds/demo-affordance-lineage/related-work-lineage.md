---
title: "Visual Affordance Field Lineage from VFM Probing Baseline"
type: related-work-lineage
project: "DemoVisualAffordance"
round: "demo-affordance-lineage"
status: "approved"
human_review: approved
---

# Visual Affordance Field Lineage from VFM Probing Baseline

## Boundary

This related-work lineage artifact is not Project Understanding Graph truth and does not create D* events.

## Positioning Note

The baseline paper, Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models, sits as a convergence node rather than a starting point. Earlier work defines object-part affordance masks, exocentric grounding benchmarks, one-shot/open transfer, 3D spatial affordance labels, and dense VFM priors. The baseline asks whether modern visual foundation models already carry the geometry and interaction cues needed for affordance reasoning, then bridges those cues for the task. It should be read as a field-scope detector for affordance grounding plus VFM evidence, not as a prompt to make DINO/Flux/loss components the lineage routes.

## Baseline Paper Field Scope

- Primary problem: Localize object regions or parts that support a requested action, especially when action/object labels, viewpoints, or categories differ from the training setting.
- Input/output: Inputs are RGB images, object-centric crops, language/action prompts, support examples, 3D point clouds, or frozen visual foundation model activations. Outputs are affordance masks, keypoints, part/region labels, point-wise affordance scores, or diagnostic maps.
- Evaluation setting: Affordance localization and segmentation are measured with pixel, part, or point-level overlap and ranking metrics, plus cross-category, one-shot, zero-shot, and prompt-conditioned transfer settings where available.
- Survey boundary: Paper-only map for visual affordance grounding, open-text affordance reasoning, 3D/spatial affordance grounding, and foundation-model evidence used to explain or transfer affordance predictions.
- Lane axis: task setting and output object
- Selected lanes: rgb_object_part_grounding, open_text_affordance_grounding, spatial_3d_affordance_grounding, vfm_affordance_auditing
- Benchmarks/datasets: IIT-AFF, UMD, PAD, PADv2, AGD20K, 3D AffordanceNet, PIAD, PIADv2
- Exclusion rules: Exclude pure grasp-planning or robot-control papers unless visual affordance grounding is an explicit evaluated output.; Exclude general VLM/VFM papers unless they are used as dense correspondence, perception prior, or affordance evidence for this field.; Exclude dataset-only listings without an accompanying paper.; Do not treat baseline internal components, losses, or fusion stages as routes.

## Search Log

- field_scope_problem_benchmark: visual affordance grounding dataset AGD20K exocentric images arxiv
- survey_calibration: visual affordance grounding dataset part interaction labels survey
- language_conditioned_branch: open vocabulary affordance grounding foundation model arxiv
- object_part_segmentation_branch: AffordanceNet end-to-end deep learning object affordance detection ICRA 2018
- one_shot_transfer_branch: One-Shot Object Affordance Detection in the Wild arxiv PADv2
- spatial_3d_branch: 3D AffordanceNet benchmark point cloud affordance grounding arxiv
- spatial_3d_language_branch: GREAT Geometry-Intention Collaborative Inference open vocabulary 3D object affordance grounding arxiv
- vfm_prior_branch: Deep ViT Features as Dense Visual Descriptors arxiv 2022 Amir
- vfm_recent_calibration: DINOv3 arxiv dense features 2025 visual descriptors
- baseline_metadata_check: Probing and Bridging Geometry-Interaction Cues affordance DINO Flux arxiv 2602.20501

## Axis Candidates

- selected: task setting and output object (rgb_object_part_grounding, open_text_affordance_grounding, spatial_3d_affordance_grounding, vfm_affordance_auditing) - Best field-level axis for a baseline-paper survey around visual affordance grounding.
- rejected: benchmark community (IIT-AFF/UMD, PAD/PADv2, AGD20K, 3D AffordanceNet/PIAD) - Useful metadata, weaker as primary lineage axis.
- rejected: generalization pressure (supervised known categories, one-shot transfer, open-text transfer, zero-shot frozen-model evidence) - Recorded as method_setting rather than route axis.
- rejected: evidence source (pixel labels, human-object interaction, language knowledge, 3D geometry, self-supervised visual priors) - Demoted to non-lane axis to satisfy baseline-paper field-scope rule.
- rejected: application or deployment context (robot manipulation, human-object interaction understanding, scene assistance, foundation-model diagnostics) - Good background axis, not best for this project map.

## Technical Routes

### RGB Object-Part Grounding

Papers that predict affordance regions, parts, keypoints, or masks from RGB object/scene images with dataset-defined affordance labels.

- 2016.02 **Detecting Object Affordances with Convolutional Neural Networks** [early-deep-learning, rgbd-affordance] - Early CNN approach to object affordance detection from visual input, before large-scale affordance grounding benchmarks.
- 2017.09 **AffordanceNet: An End-to-End Deep Learning Approach for Object Affordance Detection** [object-detection, affordance-segmentation] - Turns affordance prediction into object detection plus pixel-level affordance mask estimation.
- 2018.07 **Visual Affordance and Function Understanding: A Survey** [survey, field-boundary] - Broad survey that names affordance detection, object function, and interaction understanding as connected visual recognition problems.
- 2021.08 **One-Shot Object Affordance Detection in the Wild** [one-shot, benchmark] - Extends affordance detection from closed labels toward support-image transfer in natural scenes.
- 2022.03 **Learning Affordance Grounding from Exocentric Images** [dataset, exocentric-grounding] - Defines a large exocentric affordance grounding dataset and task where interaction examples supervise object-region predictions.
- 2023.03 **LOCATE: Localize and Transfer Object Parts for Weakly Supervised Affordance Grounding** [part-transfer, weak-supervision] - Uses part localization and transfer to reduce direct pixel-level affordance supervision.

### Text-Conditioned Affordance Grounding

Papers that use action names, instructions, large language models, or support examples to move beyond a closed affordance label set.

- 2023.11 **One-Shot Open Affordance Learning with Foundation Models** [one-shot, foundation-model] - Moves affordance learning toward open labels and limited examples by using foundation-model knowledge.
- 2024.01 **AffordanceLLM: Grounding Affordance from Vision Language Models** [vlm, language-grounding] - Uses VLM/LLM knowledge to connect textual affordance concepts with visual regions.
- 2024.09 **INTRA: Interaction Relationship-aware Weakly Supervised Affordance Grounding** [interaction-relation, weak-supervision] - Uses interaction relationships to guide weakly supervised affordance grounding.

### 3D Spatial Affordance Grounding

Papers that ground affordances on point clouds, 3D object parts, or geometry-aware object representations.

- 2021.03 **3D AffordanceNet: A Benchmark for Visual Object Affordance Understanding** [3d-benchmark, point-wise-grounding] - Defines point-cloud affordance prediction as a benchmarked visual understanding task.
- 2023.03 **Grounding 3D Object Affordance from 2D Interactions in Images** [2d-to-3d-transfer, interaction-cues] - Transfers interaction evidence from 2D images into 3D affordance grounding.
- 2024.11 **GREAT: Geometry-Intention Collaborative Inference for Open-Vocabulary 3D Object Affordance Grounding** [open-text-3d, geometry-intention] - Extends 3D affordance grounding toward open text intent and geometry-aware inference.
- 2026.03 **Part-Aware Open-Vocabulary 3D Affordance Grounding via Prototypical Semantic and Geometric Alignment** [part-aware, recent-3d-open] - Recent 3D affordance work that combines part structure, open vocabulary, and interaction priors.

### VFM Affordance Auditing

Papers that test whether frozen visual foundation models carry part, geometry, or action-relevant cues that can support affordance grounding.

- 2021.12 **Deep ViT Features as Dense Visual Descriptors** [dense-correspondence, visual-prior] - Demonstrates dense semantic correspondence from frozen transformer activations.
- 2023.04 **DINOv2: Learning Robust Visual Features without Supervision** [self-supervised-vision, dense-prior] - Large-scale self-supervised visual model used as a general visual prior for dense downstream tasks.
- 2025.04 **Perception Encoder: The Best Visual Embeddings Are Not at the Output of the Network** [embedding-analysis, visual-prior] - Analyzes internal visual embeddings and strengthens the case for inspecting frozen model signals before task-specific training.
- 2025.08 **DINOv3** [recent-vfm, dense-prior] - Recent self-supervised visual foundation model that updates the dense-prior side of affordance analysis.
- 2026.02 **Probing and Bridging Geometry-Interaction Cues for Affordance Reasoning in Vision Foundation Models** [baseline, zero-shot-vfm-audit] - Baseline for this map: uses VFM evidence to test and bridge geometry-interaction cues for affordance reasoning.

## Explicit Lineage Edges

- `nguyen2016-affordance-cnn` influences `do2017-affordancenet`: AffordanceNet extends early CNN affordance detection into object detection plus affordance segmentation.
- `do2017-affordancenet` contrasts-with `zhai2021-osad-pad-v2`: OSAD/PADv2 shifts the evaluation pressure from closed supervised affordance categories to one-shot transfer in the wild.
- `zhai2021-osad-pad-v2` influences `li2024-ooal`: OOAL inherits the transfer problem and moves it toward open affordance labels and foundation models.
- `luo2022-agd20k` influences `li2023-locate`: LOCATE builds on affordance grounding pressure from exocentric datasets while emphasizing part localization and transfer.
- `luo2022-agd20k` influences `jang2024-intra`: INTRA keeps human-object interaction relationships as affordance evidence while changing the weak-supervision mechanism.
- `deng2021-3d-affordancenet` extends-method `yang2023-iagnet`: IAGNet extends 3D affordance grounding by using 2D interaction evidence to infer point-level affordance.
- `yang2023-iagnet` branches-from `shao2024-great`: GREAT branches toward open-text 3D affordance grounding while retaining geometry as central evidence.
- `shao2024-great` influences `gou2026-part-aware-ov3d`: Recent 3D open affordance papers move from geometry-intention inference toward part-aware open vocabulary grounding with interaction priors.
- `amir2021-dense-vit-descriptors` influences `oquab2023-dinov2`: Dense ViT descriptors made frozen-transformer correspondence visible; DINOv2 scales self-supervised visual priors used for dense tasks.
- `oquab2023-dinov2` extends-method `simeoni2025-dinov3`: DINOv3 is a successor-style self-supervised visual foundation model lineage node after DINOv2.
- `oquab2023-dinov2` influences `zhang2026-geometry-interaction-vfm`: The baseline sits in the line of using self-supervised visual models as dense priors for affordance grounding.
- `simeoni2025-dinov3` influences `zhang2026-geometry-interaction-vfm`: The baseline uses recent VFM evidence to inspect geometry and interaction cues for open affordance grounding.
- `li2024-ooal` influences `zhang2026-geometry-interaction-vfm`: OOAL frames open affordance learning with foundation models; the baseline narrows to VFM cue auditing and bridging.
- `li2023-locate` influences `zhang2026-geometry-interaction-vfm`: LOCATE's part transfer problem becomes part of the baseline's geometry-interaction cue framing.
- `qian2024-affordancellm` contrasts-with `zhang2026-geometry-interaction-vfm`: AffordanceLLM emphasizes language/VLM reasoning, while the baseline tests visual foundation model geometry-interaction cues.

## Chronological Catalog

- 2016.02 `nguyen2016-affordance-cnn`: Early CNN object affordance detection from visual input.
  Task relevance: Shows pre-benchmark deep affordance detection baseline.
- 2017.09 `do2017-affordancenet`: Object detection plus affordance segmentation as an end-to-end task.
  Task relevance: Classic 2D part-mask affordance anchor.
- 2018.07 `hassanin2018-visual-affordance-survey`: Survey-level field boundary across visual affordance and function understanding.
  Task relevance: Calibrates what belongs in the map.
- 2021.03 `deng2021-3d-affordancenet`: Point-wise 3D affordance benchmark.
  Task relevance: Starts the spatial 3D lane.
- 2021.08 `zhai2021-osad-pad-v2`: One-shot object affordance detection and PADv2.
  Task relevance: Introduces support-example transfer pressure.
- 2021.12 `amir2021-dense-vit-descriptors`: Frozen ViT activations as dense correspondence descriptors.
  Task relevance: Visual prior for part transfer and VFM affordance auditing.
- 2022.03 `luo2022-agd20k`: AGD20K and exocentric affordance grounding.
  Task relevance: Large-scale 2D grounding benchmark for action-object evidence.
- 2023.03 `li2023-locate`: Part localization and transfer for weakly supervised affordance grounding.
  Task relevance: Connects part evidence to visual affordance transfer.
- 2023.03 `yang2023-iagnet`: Grounds 3D affordance from 2D interactions.
  Task relevance: Bridges exocentric interaction cues and 3D geometry.
- 2023.04 `oquab2023-dinov2`: Robust self-supervised visual model.
  Task relevance: Dense visual prior for later affordance maps.
- 2023.11 `li2024-ooal`: One-shot open affordance learning with foundation models.
  Task relevance: Open affordance transfer branch.
- 2024.01 `qian2024-affordancellm`: Vision-language model grounding of affordance.
  Task relevance: Language-guided affordance reasoning branch.
- 2024.09 `jang2024-intra`: Interaction relationship-aware weakly supervised affordance grounding.
  Task relevance: Refines interaction evidence for image affordance grounding.
- 2024.11 `shao2024-great`: Open-text 3D affordance grounding with geometry-intention inference.
  Task relevance: Hybrid open text and 3D spatial lane.
- 2025.04 `bolya2025-perception-encoder`: Visual embedding analysis inside perception networks.
  Task relevance: General VFM audit support.
- 2025.08 `simeoni2025-dinov3`: Recent self-supervised visual foundation model.
  Task relevance: Recent dense prior used around the baseline.
- 2026.02 `zhang2026-geometry-interaction-vfm`: Probes and bridges geometry-interaction cues for affordance reasoning in VFMs.
  Task relevance: Baseline convergence node.
- 2026.03 `gou2026-part-aware-ov3d`: Part-aware open-text 3D affordance grounding with interaction priors.
  Task relevance: Post-baseline adjacent hybrid branch.

## Major Trends

- From closed labels to transfer pressure: The line moves from supervised affordance masks toward one-shot, weakly supervised, and open-text settings. Evidence: do2017-affordancenet, zhai2021-osad-pad-v2, li2024-ooal, zhang2026-geometry-interaction-vfm.
- Part and geometry become central evidence: Part localization and 3D point-level grounding turn affordance from label recognition into spatial/actionable region prediction. Evidence: li2023-locate, deng2021-3d-affordancenet, yang2023-iagnet, gou2026-part-aware-ov3d.
- Human-object interaction cues bridge image and action: Exocentric and interaction-aware papers use observed interactions to identify the object regions that afford actions. Evidence: luo2022-agd20k, jang2024-intra, yang2023-iagnet.
- Frozen visual models become objects of study: Dense correspondence and self-supervised VFMs are no longer only backbones; papers test whether they already encode useful part and geometry cues. Evidence: amir2021-dense-vit-descriptors, oquab2023-dinov2, bolya2025-perception-encoder, zhang2026-geometry-interaction-vfm.

## Notable Forks

- Dataset-grounded masks vs open-text affordance grounding (AffordanceNet/AGD20K style fixed labels vs OOAL/AffordanceLLM/baseline style open labels): The fork changes the core failure mode from mask quality under known labels to semantic-action transfer under new labels.
- 2D interaction evidence vs 3D spatial grounding (exocentric image evidence vs point-cloud and part-level geometry): IAGNet and later 3D open-text papers try to bridge interaction cues and spatial object structure.
- Language knowledge vs visual prior evidence (VLM/LLM affordance reasoning vs frozen VFM cue auditing): AffordanceLLM and the 2026 baseline address similar open affordance questions but stress different evidence sources.
