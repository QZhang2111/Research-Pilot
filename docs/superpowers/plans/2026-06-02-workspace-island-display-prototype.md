# Workspace Island Display Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also use `react-flow` before editing `dashboard/workspace-island/src/WorkspaceIslandApp.jsx` or `dashboard/workspace-island/src/workspace-island.css`.

**Goal:** Build a DemoVisualAffordance-first workspace display prototype that makes Understanding, Literature, Paper Focus, and Experiments read as one coherent research island.

**Architecture:** Keep `research-pilot.db` and existing v1 API as the durable backing. Change only read-model projection and React Flow presentation: Literature gains a route focus layer, Paper Focus becomes one shared deep-read destination, and Experiments changes from automatic evaluation settings to `Evaluation Arena -> Experiment Design -> Run / Result`. The display prototype intentionally precedes final backend mapping contract hardening.

**Tech Stack:** Python stdlib, SQLite, `unittest`, React 19, `@xyflow/react`, Vite, existing static dashboard server.

---

## Product Decisions Locked By This Plan

- `Understanding`, `Literature`, and `Experiments` are sibling workspace modes.
- `Understanding` overview and claim focus are mostly stable; this plan only avoids regressions.
- `Literature` overview shows routes and papers; route frames are clickable.
- `Literature` route focus shows one literature line and papers inside that line.
- `Paper Focus` is shared. Clicking a paper from Understanding or Literature reaches the same paper argument layer and the same paper brief.
- `Paper Focus` default inspector must show deep-read paper brief before raw paper nodes.
- `Experiments` overview uses `Evaluation Arena`, not `Evaluation Setting`.
- `Evaluation Arena` groups experiments by research evaluation purpose, not by exact `benchmark + dataset + metric` strings.
- `Experiment Design` is a plan.
- `Run` is evidence.
- `Metric`, `artifact`, `interpretation`, `weakness`, and `claim impact` hang from `Run`.
- `imported_paper`, `local`, `replication`, and `external` origins must be visible.

## Non-Goals

- Do not change `tools/research_dataset.py` schema.
- Do not rewrite scene-v2 builders for all modes in this plan.
- Do not add mutation APIs.
- Do not add a new graph layout library.
- Do not remove the legacy `/api/experiments` page.

## File Map

Modify:

- `tests/test_research_dataset_read_models.py`
  - Add guard that DB-backed experiment read model preserves narrative summary and next moves from the legacy experiment JSON.

- `tests/test_workspace_graph_read_models.py`
  - Replace `evaluation_setting` expectations with `evaluation_arena`.
  - Add route focus, shared paper focus, experiment arena focus, and run-detail contract tests.

- `tests/test_related_work_lineage_dashboard.py`
  - Add source guards for React Flow renderers, node types, CSS classes, and labels.

- `tools/research_dataset_read_models.py`
  - Add `narrative_summary` and `next_moves` to `build_experiments_model`.

- `tools/workspace_graph_read_models.py`
  - Add paper brief extraction from project-local paper dossiers.
  - Rename experiment display entity from `evaluation_setting` to `evaluation_arena`.
  - Add `evaluation_arena_focus` while keeping `evaluation_setting_focus` as an alias.
  - Build experiment arenas from experiments, runs, metrics, artifacts, and claim impacts.

- `tools/workspace_scene_contract.py`
  - Add `evaluation_arena_focus` normalization and keep old setting focus alias.

- `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
  - Add paper focus card/inspector semantics.
  - Add arena overview/focus/design/run experiment renderers.
  - Keep `nodeTypes` stable outside component bodies.

- `dashboard/workspace-island/src/workspace-island.css`
  - Add arena/design/run visual rules.
  - Keep island body fixed-height; inspector scrolls independently.

Regenerate:

- `dashboard/workspace-island.bundle.js`
- `dashboard/workspace-island.bundle.css`

---

### Task 1: Add Backend Contract Tests For Display Semantics

**Files:**
- Modify: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Replace the experiments overview setting test**

Replace `test_experiments_evaluation_overview_uses_settings_not_claims` with:

```python
    def test_experiments_evaluation_overview_uses_arenas_not_settings(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("experiments", model["mode"])
        self.assertEqual("evaluation_overview", model["layer"])
        self.assertEqual("Evaluation Arenas", model["inspector"]["title"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertEqual({"evaluation_arena"}, entity_types)
        labels = {node["label"] for node in model["canvas"]["nodes"]}
        self.assertEqual(
            {
                "AGD20K Affordance Localization",
                "UMD Geometry / Segmentation Probe",
                "Semantic Assimilation Control",
            },
            labels,
        )
        agd20k = next(node for node in model["canvas"]["nodes"] if node["label"] == "AGD20K Affordance Localization")
        self.assertEqual("2 experiments / 3 runs", agd20k["subtitle"])
        self.assertEqual(
            {"mode": "experiments", "layer": "evaluation_arena_focus", "focus_id": agd20k["id"]},
            agd20k["drill"],
        )
        self.assertNotIn("evaluation_setting", " ".join(node["id"] for node in model["canvas"]["nodes"]))
```

- [ ] **Step 2: Replace the experiments overview inspector test**

Replace `test_experiments_overview_inspector_uses_human_readable_setting_items` with:

```python
    def test_experiments_overview_inspector_surfaces_summary_and_next_moves(self):
        model = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")

        self.assertEqual("overview", model["inspector"]["kind"])
        self.assertIn("AGD20K evidence", model["inspector"]["summary"])
        section_kinds = [section["kind"] for section in model["inspector"]["sections"]]
        self.assertIn("evaluation_arena_list", section_kinds)
        self.assertIn("next_move_list", section_kinds)
        next_moves = next(section for section in model["inspector"]["sections"] if section["kind"] == "next_move_list")
        self.assertTrue(any(item.get("linked_experiment") == "EXP3" for item in next_moves["items"]))
```

- [ ] **Step 3: Replace the setting-focus test with arena-focus test**

Replace `test_experiments_setting_focus_excludes_run_nodes` with:

```python
    def test_experiments_arena_focus_shows_context_designs_and_runs(self):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        arena_id = next(node["id"] for node in overview["canvas"]["nodes"] if node["label"] == "AGD20K Affordance Localization")

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_arena_focus",
            focus_id=arena_id,
        )

        self.assertEqual("evaluation_arena_focus", model["layer"])
        entity_types = {node["entity_type"] for node in model["canvas"]["nodes"]}
        self.assertGreaterEqual(entity_types, {"evaluation_arena", "dataset", "benchmark", "metric_family", "experiment", "run"})
        self.assertEqual("arena_detail", model["inspector"]["kind"])
        self.assertEqual("AGD20K Affordance Localization", model["inspector"]["title"])
        run_nodes = [node for node in model["canvas"]["nodes"] if node["entity_type"] == "run"]
        self.assertEqual({"run:RUN2", "run:RUN3", "run:RUN4"}, {node["id"] for node in run_nodes})
        self.assertTrue(all(node["metadata"].get("origin_type") == "imported_paper" for node in run_nodes))
        self.assertEqual("Workspace", model["breadcrumb"][0]["label"])
        self.assertEqual("Experiments", model["breadcrumb"][1]["label"])
        self.assertEqual("evaluation_overview", model["breadcrumb"][1]["layer"])
```

- [ ] **Step 4: Add old-layer alias test**

Insert after the arena-focus test:

```python
    def test_experiments_old_setting_focus_aliases_to_arena_focus(self):
        overview = build_workspace_graph_model(self.root, PROJECT_ID, mode="experiments", layer="evaluation_overview")
        arena_id = next(node["id"] for node in overview["canvas"]["nodes"] if node["label"] == "AGD20K Affordance Localization")

        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="experiments",
            layer="evaluation_setting_focus",
            focus_id=arena_id,
        )

        self.assertEqual("evaluation_arena_focus", model["layer"])
        self.assertEqual(arena_id, model["focus_id"])
```

- [ ] **Step 5: Strengthen design focus test**

Append these assertions to `test_experiments_design_focus_and_run_selection`:

```python
        run3 = next(node for node in model["canvas"]["nodes"] if node["id"] == "run:RUN3")
        self.assertEqual("imported_paper", run3["metadata"]["origin_type"])
        metric_values = {metric["name"]: metric["value"] for metric in run3["metadata"]["metrics"]}
        self.assertEqual("1.493", metric_values["KLD"])
        self.assertEqual("0.326", metric_values["SIM"])
        self.assertEqual("1.090", metric_values["NSS"])
```

- [ ] **Step 6: Add shared paper focus brief test**

Insert after `test_literature_paper_focus_reuses_deep_read_paper_graph`:

```python
    def test_shared_paper_focus_uses_deep_read_brief_before_raw_nodes(self):
        model = build_workspace_graph_model(
            self.root,
            PROJECT_ID,
            mode="literature",
            layer="literature_paper_focus",
            focus_id="source:paper:li2024-ooal",
        )

        self.assertEqual("paper_focus", model["inspector"]["kind"])
        self.assertEqual("One-Shot Open Affordance Learning with Foundation Models", model["inspector"]["title"])
        section_titles = [section["title"] for section in model["inspector"]["sections"]]
        self.assertEqual("Paper Brief", section_titles[0])
        self.assertIn("Paper Argument Nodes", section_titles)
        brief = model["inspector"]["sections"][0]
        brief_labels = [item["label"] for item in brief["items"]]
        self.assertIn("Core Contribution", brief_labels)
        self.assertIn("Evidence Boundary", brief_labels)
        self.assertIn("What Not To Overlearn", brief_labels)
        self.assertTrue(any("not training-free VFM probing" in item["text"] for item in brief["items"]))
```

- [ ] **Step 7: Run targeted tests to verify failures**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models -v
```

Expected: FAIL. Current code returns `evaluation_setting`, lacks `evaluation_arena_focus`, and inspector kind remains `paper_layer`.

---

### Task 2: Preserve Experiment Narrative Summary And Next Moves

**Files:**
- Modify: `tests/test_research_dataset_read_models.py`
- Modify: `tools/research_dataset_read_models.py`

- [ ] **Step 1: Add failing read-model test**

Append to `test_experiments_model_preserves_imported_origin_and_metrics`:

```python
        self.assertIn("narrative_summary", model)
        self.assertIn("strongest_current_evidence", model["narrative_summary"])
        self.assertIn("AGD20K evidence", model["narrative_summary"]["strongest_current_evidence"])
        self.assertTrue(model["next_moves"])
        self.assertTrue(any(move["type"] == "replicate" and move["linked_experiment"] == "EXP3" for move in model["next_moves"]))
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_research_dataset_read_models.ResearchDatasetReadModelsTest.test_experiments_model_preserves_imported_origin_and_metrics -v
```

Expected: FAIL because `narrative_summary` is missing and `next_moves` is empty.

- [ ] **Step 3: Import legacy experiment loader**

In `tools/research_dataset_read_models.py`, replace:

```python
from tools.experiment_store import _legacy_proposals
```

with:

```python
from tools.experiment_store import _legacy_proposals, build_project_experiments
```

- [ ] **Step 4: Merge legacy narrative in `build_experiments_model`**

Replace the return block in `build_experiments_model` with:

```python
    legacy_model = build_project_experiments(Path(root), project_id)
    return {
        "schema_version": "experiments-v1",
        "project_id": project_id,
        "source_boundary": "project_experiments_from_research_dataset",
        "mutating": False,
        "summary": _experiment_summary(experiments, runs),
        "narrative_summary": legacy_model.get("summary") or {},
        "experiments": experiments,
        "runs": runs,
        "next_moves": legacy_model.get("next_moves") or [],
        "legacy_proposals": _legacy_proposals(Path(root), project_id),
    }
```

- [ ] **Step 5: Run dataset read-model tests**

Run:

```bash
python3 -m unittest tests.test_research_dataset_read_models -v
```

Expected: PASS.

---

### Task 3: Build Experiment Arenas In Workspace Read Model

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Modify: `tools/workspace_scene_contract.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add display entity and layer alias**

In `tools/workspace_graph_read_models.py`, add `evaluation_arena` to `ENTITY_DISPLAY`:

```python
    "evaluation_arena": {"tone": "claim", "label": "Evaluation Arena"},
```

Change `VALID_LAYERS["experiments"]` to:

```python
    "experiments": {"evaluation_overview", "evaluation_arena_focus", "evaluation_setting_focus", "experiment_design_focus"},
```

In `build_workspace_graph_model`, after layer validation and before dispatch, add:

```python
    if mode == "experiments" and layer == "evaluation_setting_focus":
        layer = "evaluation_arena_focus"
```

- [ ] **Step 2: Update scene contract layer aliases**

In `tools/workspace_scene_contract.py`, add:

```python
    ("experiments", "evaluation_arena_focus"): "experiments.evaluation_arena_focus",
```

Change the old setting mapping to:

```python
    ("experiments", "evaluation_setting_focus"): "experiments.evaluation_arena_focus",
```

Expected result: both v1 layer names normalize to the arena layer.

- [ ] **Step 3: Add arena helper functions**

Insert before `_experiments_by_id`:

```python
def _experiment_metric_families(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    names = [str(metric.get("name") or "") for run in runs for metric in run.get("metrics", [])]
    family = _metric_family_from_names(names) or _planned_metric_family(experiment)
    return [item.strip() for item in family.split("+") if item.strip()]


def _experiment_arena_key(experiment: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            experiment.get("id", ""),
            experiment.get("title", ""),
            experiment.get("benchmark", ""),
            experiment.get("dataset", ""),
            " ".join(_experiment_metric_families(experiment, runs)),
        ]
    ).lower()
    if "mug-handle" in text or "semantic assimilation" in text:
        return "semantic_assimilation_control"
    if "agd20k" in text or "heatmap" in text or "flux" in text:
        return "agd20k_affordance_localization"
    if "umd" in text or "segmentation" in text or "miou" in text or "linear probe" in text:
        return "umd_geometry_segmentation_probe"
    return "other_experiment_arena"


ARENA_DISPLAY = {
    "agd20k_affordance_localization": {
        "label": "AGD20K Affordance Localization",
        "summary": "Verb-conditioned attention, geometry fusion, heatmap metrics, and qualitative localization evidence.",
    },
    "umd_geometry_segmentation_probe": {
        "label": "UMD Geometry / Segmentation Probe",
        "summary": "Geometry-aware VFM representations tested against object-part affordance segmentation evidence.",
    },
    "semantic_assimilation_control": {
        "label": "Semantic Assimilation Control",
        "summary": "Controls that bound whether apparent geometry evidence is pure shape or entangled with object semantics.",
    },
    "other_experiment_arena": {
        "label": "Other Experiment Arena",
        "summary": "Experiment designs not assigned to the primary demo arenas.",
    },
}


def _experiment_arenas(model: dict[str, Any]) -> list[dict[str, Any]]:
    runs_by_experiment = _runs_by_experiment(model)
    arenas: dict[str, dict[str, Any]] = {}
    for experiment in model.get("experiments", []):
        experiment_runs = runs_by_experiment.get(experiment.get("id"), [])
        arena_key = _experiment_arena_key(experiment, experiment_runs)
        display = ARENA_DISPLAY[arena_key]
        current = arenas.setdefault(
            arena_key,
            {
                "id": f"evaluation_arena:{arena_key}",
                "entity_type": "evaluation_arena",
                "key": arena_key,
                "label": display["label"],
                "summary": display["summary"],
                "experiment_ids": [],
                "run_ids": [],
                "datasets": set(),
                "benchmarks": set(),
                "metric_families": set(),
                "origin_types": set(),
            },
        )
        current["experiment_ids"].append(experiment["id"])
        if experiment.get("dataset"):
            current["datasets"].add(experiment["dataset"])
        if experiment.get("benchmark"):
            current["benchmarks"].add(experiment["benchmark"])
        for family in _experiment_metric_families(experiment, experiment_runs):
            current["metric_families"].add(family)
        for run in experiment_runs:
            current["run_ids"].append(run["id"])
            if run.get("origin_type"):
                current["origin_types"].add(run["origin_type"])
    result = []
    order = ["agd20k_affordance_localization", "umd_geometry_segmentation_probe", "semantic_assimilation_control", "other_experiment_arena"]
    for key in order:
        arena = arenas.get(key)
        if not arena:
            continue
        arena["experiment_ids"] = sorted(set(arena["experiment_ids"]))
        arena["run_ids"] = sorted(set(arena["run_ids"]))
        arena["datasets"] = sorted(arena["datasets"])
        arena["benchmarks"] = sorted(arena["benchmarks"])
        arena["metric_families"] = sorted(arena["metric_families"])
        arena["origin_types"] = sorted(arena["origin_types"])
        arena["experiment_count"] = len(arena["experiment_ids"])
        arena["run_count"] = len(arena["run_ids"])
        result.append(arena)
    return result
```

- [ ] **Step 4: Replace experiments overview branch**

In `_build_experiments`, compute:

```python
    arenas = _experiment_arenas(model)
```

Replace the `if layer == "evaluation_overview":` body with arena nodes:

```python
    if layer == "evaluation_overview":
        payload["canvas"]["nodes"] = [
            {
                "id": arena["id"],
                "entity_type": "evaluation_arena",
                "label": arena["label"],
                "subtitle": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
                "status": "",
                "confidence": "",
                "drill": {"mode": "experiments", "layer": "evaluation_arena_focus", "focus_id": arena["id"]},
                "inspector": {"selected_id": arena["id"]},
                "metadata": arena,
            }
            for arena in arenas
        ]
        narrative = model.get("narrative_summary") or {}
        payload["inspector"] = {
            "kind": "overview",
            "title": "Evaluation Arenas",
            "summary": narrative.get("strongest_current_evidence") or "Evaluation arenas organize experiments before claim impact.",
            "sections": [
                {
                    "title": "Evaluation Arenas",
                    "kind": "evaluation_arena_list",
                    "items": [
                        {
                            "id": arena["id"],
                            "label": arena["label"],
                            "subtitle": ", ".join(arena["metric_families"]) or "mixed metrics",
                            "impact": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
                        }
                        for arena in arenas
                    ],
                },
                {"title": "Next Moves", "kind": "next_move_list", "items": model.get("next_moves") or []},
            ],
            "actions": [],
        }
        return payload
```

- [ ] **Step 5: Replace setting focus branch with arena focus branch**

Replace `if layer == "evaluation_setting_focus":` with:

```python
    if layer == "evaluation_arena_focus":
        arena = next((item for item in arenas if item["id"] == focus_id), None)
        if not arena:
            raise ValueError(f"unknown evaluation arena: {focus_id}")
        payload["focus_id"] = focus_id
        payload["breadcrumb"] = _experiments_breadcrumb(
            {
                "label": arena["label"],
                "mode": "experiments",
                "layer": "evaluation_arena_focus",
                "focus_id": focus_id,
                "selected_id": "",
            }
        )
        experiment_nodes = []
        run_nodes = []
        for experiment_id in arena["experiment_ids"]:
            experiment = experiments.get(experiment_id)
            if not experiment:
                continue
            runs = runs_by_experiment.get(experiment_id, [])
            graph_id = _experiment_graph_id(experiment_id)
            experiment_nodes.append(
                {
                    "id": graph_id,
                    "entity_type": "experiment",
                    "db_id": experiment_id,
                    "local_id": experiment_id,
                    "label": experiment.get("title") or experiment_id,
                    "subtitle": f"{len(runs)} runs / {experiment.get('status', '')}",
                    "status": experiment.get("status") or "",
                    "confidence": "",
                    "drill": {"mode": "experiments", "layer": "experiment_design_focus", "focus_id": graph_id},
                    "inspector": {"selected_id": graph_id},
                    "metadata": experiment,
                }
            )
            for run in runs:
                run_nodes.append(
                    {
                        "id": _run_graph_id(run["id"]),
                        "entity_type": "run",
                        "db_id": run["id"],
                        "local_id": run["id"],
                        "label": run.get("run_label") or run.get("id"),
                        "subtitle": f"{run.get('origin_type', '')} / {run.get('status', '')}",
                        "status": run.get("status") or "",
                        "confidence": "",
                        "drill": None,
                        "inspector": {"selected_id": _run_graph_id(run["id"])},
                        "metadata": run,
                    }
                )
        context_nodes = [
            {
                "id": f"dataset:{_slug(value)}",
                "entity_type": "dataset",
                "label": value,
                "subtitle": "dataset",
                "status": "",
                "confidence": "",
                "metadata": {"arena_id": focus_id, "value": value},
                "drill": None,
                "inspector": {"selected_id": f"dataset:{_slug(value)}"},
            }
            for value in arena["datasets"]
        ] + [
            {
                "id": f"benchmark:{_slug(value)}",
                "entity_type": "benchmark",
                "label": value,
                "subtitle": "benchmark/task",
                "status": "",
                "confidence": "",
                "metadata": {"arena_id": focus_id, "value": value},
                "drill": None,
                "inspector": {"selected_id": f"benchmark:{_slug(value)}"},
            }
            for value in arena["benchmarks"]
        ] + [
            {
                "id": f"metric_family:{_slug(value)}",
                "entity_type": "metric_family",
                "label": value,
                "subtitle": "metric family",
                "status": "",
                "confidence": "",
                "metadata": {"arena_id": focus_id, "value": value},
                "drill": None,
                "inspector": {"selected_id": f"metric_family:{_slug(value)}"},
            }
            for value in arena["metric_families"]
        ]
        arena_node = {
            "id": arena["id"],
            "entity_type": "evaluation_arena",
            "label": arena["label"],
            "subtitle": f"{arena['experiment_count']} experiments / {arena['run_count']} runs",
            "status": "",
            "confidence": "",
            "drill": None,
            "inspector": {"selected_id": arena["id"]},
            "metadata": arena,
        }
        payload["canvas"]["nodes"] = [arena_node, *context_nodes, *experiment_nodes, *run_nodes]
        payload["canvas"]["edges"] = [
            *[
                {"id": f"arena-context:{focus_id}:{node['id']}", "source": node["id"], "target": focus_id, "relation": "defines", "label": "defines", "metadata": {}}
                for node in context_nodes
            ],
            *[
                {"id": f"arena-exp:{focus_id}:{node['id']}", "source": focus_id, "target": node["id"], "relation": "uses", "label": "uses", "metadata": {}}
                for node in experiment_nodes
            ],
            *[
                {"id": f"arena-run:{focus_id}:{node['id']}", "source": node["metadata"]["experiment_id"], "target": node["id"], "relation": "produces", "label": "produces", "metadata": {}}
                for node in run_nodes
            ],
        ]
        if selected_id.startswith("run:"):
            payload["inspector"] = _run_inspector(root, project_id, selected_id, model.get("runs", []))
        else:
            payload["inspector"] = {
                "kind": "arena_detail",
                "title": arena["label"],
                "summary": arena["summary"],
                "sections": [
                    {"title": "Datasets", "kind": "dataset", "items": [{"label": item} for item in arena["datasets"]]},
                    {"title": "Benchmarks / Tasks", "kind": "benchmark", "items": [{"label": item} for item in arena["benchmarks"]]},
                    {"title": "Metric Families", "kind": "metric_family", "items": [{"label": item} for item in arena["metric_families"]]},
                    {"title": "Experiment Designs", "kind": "experiment_list", "items": experiment_nodes},
                    {"title": "Runs / Results", "kind": "run_list", "items": run_nodes},
                ],
                "actions": [],
            }
        return payload
```

- [ ] **Step 6: Fix arena-run edge source**

Before building arena edges, add:

```python
        run_owner = {run["id"]: run.get("experiment_id", "") for run in model.get("runs", [])}
```

Then use:

```python
"source": _experiment_graph_id(run_owner.get(node["local_id"], "")),
```

in `arena-run` edge objects.

- [ ] **Step 7: Run backend tests**

Run:

```bash
python3 -m unittest tests.test_workspace_graph_read_models tests.test_workspace_scene_contract -v
```

Expected: PASS.

---

### Task 4: Add Shared Paper Focus Brief Extraction

**Files:**
- Modify: `tools/workspace_graph_read_models.py`
- Test: `tests/test_workspace_graph_read_models.py`

- [ ] **Step 1: Add markdown section parser helpers**

Insert before `_paper_layer_inspector`:

```python
PAPER_BRIEF_SECTION_MAP = {
    "core contribution": "Core Contribution",
    "evidence relevant to demo pug": "Evidence Boundary",
    "limitations / what not to infer": "What Not To Overlearn",
    "5. method mechanism": "Method View",
    "6. experiment logic": "Experiment Logic",
    "8. position for the target project": "Project Consequence",
    "9. what not to learn": "What Not To Overlearn",
}


def _markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("### "):
            current = line[4:].strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items() if "\n".join(value).strip()}


def _paper_dossier_brief(root: Path, source: dict[str, Any]) -> list[dict[str, str]]:
    locator = source.get("locator") or source.get("path") or ""
    if not locator:
        return []
    path = root / locator
    if not path.exists():
        return []
    sections = _markdown_sections(path.read_text(encoding="utf-8"))
    brief = []
    seen_labels: set[str] = set()
    for source_heading, label in PAPER_BRIEF_SECTION_MAP.items():
        text = sections.get(source_heading, "")
        if not text or label in seen_labels:
            continue
        seen_labels.add(label)
        brief.append({"label": label, "text": text})
    return brief
```

- [ ] **Step 2: Change `_paper_layer_inspector` signature**

Replace:

```python
def _paper_layer_inspector(
    paper_graph: dict[str, Any],
    source: dict[str, Any],
    source_id: str,
    summary: str,
    extra_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
```

with:

```python
def _paper_layer_inspector(
    root: Path,
    paper_graph: dict[str, Any],
    source: dict[str, Any],
    source_id: str,
    summary: str,
    extra_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 3: Replace `_paper_layer_inspector` body**

Use:

```python
    brief_items = _paper_dossier_brief(root, source)
    sections = []
    if brief_items:
        sections.append({"title": "Paper Brief", "kind": "paper_brief", "items": brief_items})
    sections.extend(extra_sections or [])
    sections.extend(
        [
            {"title": "Paper Argument Nodes", "kind": "paper_node_list", "items": paper_graph.get("nodes", [])},
            {"title": "Translation Bridge", "kind": "translation_bridge", "items": paper_graph.get("translations", [])},
        ]
    )
    return {
        "kind": "paper_focus",
        "title": paper_graph.get("title") or source.get("title") or source_id,
        "summary": summary,
        "sections": sections,
        "actions": [],
    }
```

- [ ] **Step 4: Update call sites**

In `_build_understanding`, call:

```python
        payload["inspector"] = _paper_layer_inspector(
            root,
            paper_graph,
            source,
            source_id,
            "Paper argument layer projected beside the selected project claim.",
        )
```

In `_build_literature`, call:

```python
            payload["inspector"] = _paper_layer_inspector(
                root,
                paper_graph,
                source,
                source_key,
                "Paper argument layer reused from the deep-read source record.",
                [{"title": "Literature Context", "kind": "source_metadata", "items": [paper]}],
            )
```

- [ ] **Step 5: Update existing paper-focus tests**

In tests that currently expect `paper_layer`, change:

```python
self.assertEqual("paper_layer", model["inspector"]["kind"])
```

to:

```python
self.assertEqual("paper_focus", model["inspector"]["kind"])
```

- [ ] **Step 6: Run paper focus tests**

Run:

```bash
python3 -m unittest \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_understanding_paper_focus_contract \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_literature_paper_focus_reuses_deep_read_paper_graph \
  tests.test_workspace_graph_read_models.WorkspaceGraphReadModelsTest.test_shared_paper_focus_uses_deep_read_brief_before_raw_nodes \
  -v
```

Expected: PASS.

---

### Task 5: Update Frontend Source Guards

**Files:**
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add source guard for experiment arena renderer names**

Append to `test_workspace_island_contains_layer_overview_and_terminal_run_rules`:

```python
        self.assertIn("WorkspaceExperimentArenaNode", source)
        self.assertIn("buildExperimentsArenaOverviewFlowModel", source)
        self.assertIn("buildExperimentsArenaFocusFlowModel", source)
        self.assertIn("evaluation_arena", source)
        self.assertIn("Evaluation Arena", source)
```

- [ ] **Step 2: Add source guard for shared paper focus labels**

Insert after `test_workspace_island_uses_mode_specific_renderers_and_breadcrumb`:

```python
    def test_workspace_island_shared_paper_focus_and_experiment_arena_copy(self):
        source = (ROOT / "dashboard" / "workspace-island" / "src" / "WorkspaceIslandApp.jsx").read_text(encoding="utf-8")
        css = (ROOT / "dashboard" / "workspace-island" / "src" / "workspace-island.css").read_text(encoding="utf-8")

        self.assertIn("Paper Brief", source)
        self.assertIn("Paper Argument Nodes", source)
        self.assertIn("Evaluation Arena", source)
        self.assertIn("Runs / Results", source)
        self.assertIn("Imported Paper", source)
        self.assertIn("workspace-experiment-arena-node", css)
        self.assertIn("workspace-run-result-node", css)
        self.assertIn("overflow-y: auto;", css)
```

- [ ] **Step 3: Run source tests to verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: FAIL until frontend code and CSS are updated.

---

### Task 6: Implement React Flow Experiment Arena Presentation

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Update tone mapping**

In `entityTone`, change:

```javascript
  if (type === "claim" || type === "evaluation_setting") return "c";
```

to:

```javascript
  if (type === "claim" || type === "evaluation_arena" || type === "evaluation_setting") return "c";
```

- [ ] **Step 2: Add origin label helper**

Insert before `WorkspaceExperimentSettingNode`:

```javascript
function experimentOriginLabel(value) {
  return {
    imported_paper: "Imported Paper",
    local: "Local",
    replication: "Replication",
    external: "External",
  }[value] || shortLabel(value || "Run", 36);
}
```

- [ ] **Step 3: Add `WorkspaceExperimentArenaNode`**

Insert before `WorkspaceExperimentSettingNode`:

```javascript
const WorkspaceExperimentArenaNode = memo(function WorkspaceExperimentArenaNode({ data }) {
  const node = data.node || {};
  const metadata = node.metadata || {};
  const metric = (metadata.metric_families || []).slice(0, 2).join(" + ");
  const counts = node.subtitle || `${metadata.experiment_count || 0} experiments / ${metadata.run_count || 0} runs`;
  const content = (
    <>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <strong>{shortLabel(node.label, 96)}</strong>
      <span>{shortLabel(node.metadata?.summary || node.summary || "", 110)}</span>
      {metric ? <em>{shortLabel(metric, 70)}</em> : null}
      <small>{counts}</small>
      <Handle type="source" position={Position.Right} className="workspace-node-handle" />
    </>
  );
  return (
    <button type="button" className="workspace-experiment-arena-node" onClick={() => data.onNodeAction?.(node)}>
      {content}
    </button>
  );
});
```

- [ ] **Step 4: Add `WorkspaceRunResultNode`**

Insert after `WorkspaceExperimentArenaNode`:

```javascript
const WorkspaceRunResultNode = memo(function WorkspaceRunResultNode({ data }) {
  const node = data.node || {};
  const origin = experimentOriginLabel(node.metadata?.origin_type);
  const metricText = (node.metadata?.metrics || []).slice(0, 3).map((metric) => `${metric.name} ${metric.value}`).join(" / ");
  return (
    <button type="button" className={`workspace-run-result-node tone-${data.tone || "r"}`} onClick={() => data.onNodeAction?.(node)}>
      <Handle type="target" position={Position.Left} className="workspace-node-handle" />
      <span>{node.local_id || node.entity_type}</span>
      <strong>{shortLabel(node.label, 72)}</strong>
      <em>{shortLabel(metricText || node.subtitle || "", 92)}</em>
      <small>{origin}</small>
    </button>
  );
});
```

- [ ] **Step 5: Register node types**

Add to `workspaceNodeTypes`:

```javascript
  workspaceExperimentArenaNode: WorkspaceExperimentArenaNode,
  workspaceRunResultNode: WorkspaceRunResultNode,
```

- [ ] **Step 6: Rename overview builder and use arena node**

Replace `buildExperimentsOverviewFlowModel` with `buildExperimentsArenaOverviewFlowModel`:

```javascript
function buildExperimentsArenaOverviewFlowModel(model, onNavigate) {
  const arenas = model?.canvas?.nodes || [];
  const cardWidth = 500;
  const cardHeight = 172;
  const gapX = 80;
  const gapY = 64;
  const nodes = arenas.map((node, index) => ({
    id: node.id,
    type: "workspaceExperimentArenaNode",
    position: { x: (index % 2) * (cardWidth + gapX), y: Math.floor(index / 2) * (cardHeight + gapY) },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: { width: cardWidth, minHeight: cardHeight },
    zIndex: 3,
    data: {
      node,
      onNodeAction: experimentsNodeAction(onNavigate),
    },
  }));
  return { nodes, edges: [] };
}
```

- [ ] **Step 7: Add arena focus builder**

Replace `buildExperimentsSettingFocusFlowModel` with `buildExperimentsArenaFocusFlowModel`. It must group raw nodes by `evaluation_arena`, context facets, experiments, and runs:

```javascript
function buildExperimentsArenaFocusFlowModel(model, onNavigate) {
  const rawNodes = model?.canvas?.nodes || [];
  const rawEdges = model?.canvas?.edges || [];
  const arena = rawNodes.find((node) => node.entity_type === "evaluation_arena");
  const contextNodes = rawNodes.filter((node) => ["dataset", "benchmark", "metric_family"].includes(node.entity_type));
  const experimentNodes = rawNodes.filter((node) => node.entity_type === "experiment");
  const runNodes = rawNodes.filter((node) => node.entity_type === "run");
  const focusedIds = focusedNodeIds(model);
  const nodes = [
    {
      id: "frame:arena-context",
      type: "workspaceLaneFrameNode",
      position: { x: 36, y: -60 },
      style: { width: 430, height: Math.max(300, contextNodes.length * 104 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Dataset / Benchmark / Metric", subtitle: `${contextNodes.length} context records`, tone: "p" },
    },
    {
      id: "frame:arena-designs",
      type: "workspaceLaneFrameNode",
      position: { x: 520, y: -60 },
      style: { width: 430, height: Math.max(300, experimentNodes.length * 124 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Experiment Designs", subtitle: `${experimentNodes.length} designs`, tone: "e" },
    },
    {
      id: "frame:arena-runs",
      type: "workspaceLaneFrameNode",
      position: { x: 1000, y: -60 },
      style: { width: 430, height: Math.max(300, runNodes.length * 112 + 92) },
      draggable: false,
      selectable: false,
      zIndex: 0,
      data: { title: "Runs / Results", subtitle: `${runNodes.length} runs`, tone: "r" },
    },
  ];
  if (arena) {
    nodes.push({
      id: arena.id,
      type: "workspaceExperimentArenaNode",
      position: { x: 520, y: -230 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 430, minHeight: 148 },
      zIndex: 4,
      data: { node: arena, onNodeAction: experimentsNodeAction(onNavigate) },
    });
  }
  contextNodes.forEach((node, index) => {
    nodes.push(toExperimentEntityNode(node, index, model, focusedIds, onNavigate, { position: { x: 76, y: 16 + index * 104 }, width: 350, minHeight: 88, tone: entityTone(node.entity_type) }));
  });
  experimentNodes.forEach((node, index) => {
    nodes.push(toExperimentEntityNode(node, index, model, focusedIds, onNavigate, { position: { x: 560, y: 16 + index * 124 }, width: 350, minHeight: 98, tone: "e" }));
  });
  runNodes.forEach((node, index) => {
    nodes.push({
      id: node.id,
      type: "workspaceRunResultNode",
      position: { x: 1040, y: 16 + index * 112 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 350, minHeight: 94 },
      zIndex: 4,
      data: { node, tone: "r", onNodeAction: experimentsNodeAction(onNavigate) },
    });
  });
  const visibleIds = new Set(rawNodes.map((node) => node.id));
  return {
    nodes,
    edges: rawEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)).map((edge) => toExperimentEdge(edge)),
  };
}
```

- [ ] **Step 8: Use new builders**

Change `buildExperimentsFlowModel` to:

```javascript
function buildExperimentsFlowModel(model, onNavigate) {
  if (model?.layer === "evaluation_overview") return buildExperimentsArenaOverviewFlowModel(model, onNavigate);
  if (model?.layer === "evaluation_arena_focus" || model?.layer === "evaluation_setting_focus") return buildExperimentsArenaFocusFlowModel(model, onNavigate);
  if (model?.layer === "experiment_design_focus") return buildExperimentsDesignFocusFlowModel(model, onNavigate);
  return { nodes: [], edges: [] };
}
```

- [ ] **Step 9: Use run node in design focus**

In `buildExperimentsDesignFocusFlowModel`, replace run node creation inside `runNodes.forEach` with:

```javascript
    nodes.push({
      id: node.id,
      type: "workspaceRunResultNode",
      position: { x: 84, y: 486 + index * 106 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: { width: 296, minHeight: 88 },
      zIndex: 4,
      data: { node, tone: "r", onNodeAction: experimentsNodeAction(onNavigate) },
    });
```

- [ ] **Step 10: Add CSS classes**

Append to `dashboard/workspace-island/src/workspace-island.css`:

```css
.workspace-experiment-arena-node,
.workspace-run-result-node {
  width: 100%;
  min-height: inherit;
  border: 1px solid color-mix(in srgb, var(--node-tone, #d6a84f) 72%, var(--border));
  border-radius: 8px;
  background:
    radial-gradient(circle at 12% 10%, color-mix(in srgb, var(--node-tone, #d6a84f) 18%, transparent), transparent 38%),
    linear-gradient(180deg, color-mix(in srgb, var(--surface-2) 86%, transparent), color-mix(in srgb, #020409 80%, transparent));
  color: var(--text);
  display: grid;
  gap: 10px;
  padding: 22px 24px;
  text-align: left;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.24);
}

.workspace-experiment-arena-node {
  --node-tone: #d6a84f;
}

.workspace-run-result-node {
  --node-tone: #9bd7df;
}

.workspace-experiment-arena-node strong,
.workspace-run-result-node strong {
  font-size: 18px;
  line-height: 1.16;
}

.workspace-experiment-arena-node span,
.workspace-experiment-arena-node em,
.workspace-experiment-arena-node small,
.workspace-run-result-node span,
.workspace-run-result-node em,
.workspace-run-result-node small {
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.35;
  text-transform: uppercase;
}

.workspace-run-result-node small {
  color: var(--accent);
}
```

- [ ] **Step 11: Run source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

---

### Task 7: Tighten Shared Paper Focus Frontend Presentation

**Files:**
- Modify: `dashboard/workspace-island/src/WorkspaceIslandApp.jsx`
- Modify: `dashboard/workspace-island/src/workspace-island.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add inspector section rendering for paper brief**

Find `WorkspaceInspector` section rendering. Add a branch for `paper_brief` items:

```javascript
  if (section.kind === "paper_brief") {
    return (
      <section key={`${section.title}-${index}`} className="workspace-inspector-section workspace-paper-brief-section">
        <h3>{section.title}</h3>
        {(section.items || []).map((item) => (
          <article key={item.label} className="workspace-paper-brief-item">
            <strong>{item.label}</strong>
            <p>{item.text}</p>
          </article>
        ))}
      </section>
    );
  }
```

If `WorkspaceInspector` already uses generic section rendering, keep that rendering and add class names based on `section.kind`.

- [ ] **Step 2: Add CSS for paper brief**

Append:

```css
.workspace-paper-brief-section {
  display: grid;
  gap: 12px;
}

.workspace-paper-brief-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-2) 82%, transparent);
  padding: 14px 16px;
}

.workspace-paper-brief-item strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text);
  font-size: 14px;
}

.workspace-paper-brief-item p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}
```

- [ ] **Step 3: Ensure inspector scroll isolation**

Find the `.workspace-inspector` rule in `dashboard/workspace-island/src/workspace-island.css` and ensure it has:

```css
overflow-y: auto;
min-height: 0;
```

If missing, add it to the inspector container rule.

- [ ] **Step 4: Run source tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
```

Expected: PASS.

---

### Task 8: Regenerate Workspace Island Bundle And Verify

**Files:**
- Regenerate: `dashboard/workspace-island.bundle.js`
- Regenerate: `dashboard/workspace-island.bundle.css`
- Verify: backend tests, frontend source tests, build output

- [ ] **Step 1: Build workspace island**

Run:

```bash
npm --prefix dashboard run build:workspace-island
```

Expected: Vite build succeeds and updates `dashboard/workspace-island.bundle.js` plus `dashboard/workspace-island.bundle.css`.

- [ ] **Step 2: Run targeted Python tests**

Run:

```bash
python3 -m unittest \
  tests.test_research_dataset_read_models \
  tests.test_workspace_graph_read_models \
  tests.test_workspace_scene_contract \
  tests.test_related_work_lineage_dashboard \
  -v
```

Expected: PASS.

- [ ] **Step 3: Start example dashboard server**

Run:

```bash
python3 tools/research_browser_server.py --repo examples/workspaces --host 127.0.0.1 --port 8765
```

Expected: server prints `Serving Research Browser at http://127.0.0.1:8765/`.

- [ ] **Step 4: Manual browser checks**

Open:

```text
http://127.0.0.1:8765/dashboard/workspace.html?v=workspace-display-prototype-20260602&project=DemoVisualAffordance&mode=understanding
http://127.0.0.1:8765/dashboard/workspace.html?v=workspace-display-prototype-20260602&project=DemoVisualAffordance&mode=literature
http://127.0.0.1:8765/dashboard/workspace.html?v=workspace-display-prototype-20260602&project=DemoVisualAffordance&mode=experiments
```

Expected:

- Understanding overview still shows questions and claims.
- Literature overview shows route frames and paper cards.
- Clicking a literature route opens one route focus layer.
- Clicking a paper opens shared Paper Focus with Paper Brief first.
- Experiments overview shows three Evaluation Arena cards.
- AGD20K arena focus shows context, designs, and runs.
- EXP3 design focus shows plan groups and RUN3/RUN4.
- RUN3 inspector shows KLD/SIM/NSS, artifacts, weaknesses, and claim impact.
- Inspector scrolls without changing island height.

- [ ] **Step 5: Commit implementation**

Run:

```bash
git add \
  tests/test_research_dataset_read_models.py \
  tests/test_workspace_graph_read_models.py \
  tests/test_related_work_lineage_dashboard.py \
  tools/research_dataset_read_models.py \
  tools/workspace_graph_read_models.py \
  tools/workspace_scene_contract.py \
  dashboard/workspace-island/src/WorkspaceIslandApp.jsx \
  dashboard/workspace-island/src/workspace-island.css \
  dashboard/workspace-island.bundle.js \
  dashboard/workspace-island.bundle.css
git commit -m "feat: prototype workspace island display mapping"
```

---

## Self-Review Checklist

- [ ] No DB schema changes.
- [ ] Understanding behavior unchanged except shared paper focus inspector kind.
- [ ] Literature route focus remains one route, not all literature.
- [ ] Paper focus default inspector begins with deep-read brief.
- [ ] Experiments overview uses `evaluation_arena`.
- [ ] `evaluation_setting_focus` remains accepted as an alias.
- [ ] Run nodes remain terminal.
- [ ] Imported/local/replication origin visible in run nodes or inspector.
- [ ] Inspector height independent from canvas height.
- [ ] Bundles regenerated after source edits.
