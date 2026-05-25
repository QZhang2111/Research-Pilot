# Experiment Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the proposal-first experiment dashboard with a read-only Experiments page that shows planned experiment design and completed/partial evidence.

**Architecture:** Add a small `experiments-v1` read model stored at `wiki/projects/<ProjectId>/experiments/experiments.json`, expose it through `GET /api/experiments`, and render it on a renamed `Experiments` dashboard page. Keep the legacy `/api/experiment-proposals` endpoint and `experiment-proposals.html` page as compatibility aliases; do not migrate old proposal artifacts in this implementation.

**Tech Stack:** Python standard library HTTP server and unittest, JSON project artifacts, vanilla dashboard JavaScript/CSS, existing Research-Pilot demo workspace.

---

## File Structure

- Create `tools/experiment_store.py`: focused loader/normalizer for `experiments/experiments.json`.
- Modify `tools/research_browser_server.py`: add `handle_experiments_request` and route `/api/experiments`.
- Create `dashboard/experiments.html`: canonical dashboard page for experiments.
- Modify `dashboard/experiment-proposals.html`: compatibility shell that loads the same app but uses `data-page="experiments"`.
- Modify `dashboard/app.js`: rename nav and render the new read-only experiment sections.
- Modify `dashboard/styles.css`: reuse existing card styles where possible, add only missing selectors for experiment evidence layout.
- Create `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/experiments/experiments.json`: demo experiment data.
- Modify `tests/test_dashboard_public.py`: API and invalid-project tests.
- Modify `tests/test_demo_project.py`: demo artifact contract tests.
- Modify `tests/test_related_work_lineage_dashboard.py`: dashboard source and route copy tests.
- Modify docs after implementation only if behavior differs from current PRD.

## Task 1: Experiment Read Model Loader

**Files:**
- Create: `tools/experiment_store.py`
- Test: `tests/test_dashboard_public.py`

- [ ] **Step 1: Write failing loader/API tests**

Add imports:

```python
from tools.experiment_store import build_project_experiments
from tools.research_browser_server import handle_experiments_request
```

Add tests near existing API tests in `DashboardPublicTest`:

```python
    def test_project_experiments_api_serves_designs_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = root / "wiki" / "projects" / "DemoProject" / "experiments" / "experiments.json"
            experiment_path.parent.mkdir(parents=True)
            experiment_path.write_text(
                json.dumps(
                    {
                        "schema_version": "experiments-v1",
                        "project_id": "DemoProject",
                        "summary": {
                            "strongest_current_evidence": "Imported baseline result supports fusion, but local replication is missing.",
                            "highest_priority_unresolved": "Run local ablation on held-out affordance masks.",
                        },
                        "experiments": [
                            {
                                "id": "EXP1",
                                "title": "Geometry-interaction ablation",
                                "status": "planned",
                                "question": "Does fusion beat each signal alone?",
                                "hypothesis": "Fusion improves affordance localization.",
                                "linked_claims": ["C4"],
                                "linked_gaps": ["G1"],
                                "benchmark": "AGD20K",
                                "dataset": "AGD20K affordance masks",
                                "models": ["DINO", "Flux"],
                                "baselines": ["geometry-only", "interaction-only"],
                                "metrics": ["mIoU", "F1"],
                                "protocol": ["Run geometry-only baseline.", "Run fused method."],
                                "expected_evidence": "Fusion should improve localization.",
                                "risks": ["Imported evidence may not replicate locally."],
                                "next_action": "Prepare local evaluation split.",
                            }
                        ],
                        "runs": [
                            {
                                "id": "RUN1",
                                "experiment_id": "EXP1",
                                "status": "completed",
                                "evidence_type": "imported_paper_evidence",
                                "completed_at": "2026-05-15",
                                "summary": "Baseline paper reports competitive zero-shot affordance maps.",
                                "metrics": [{"name": "mIoU", "value": "reported in source paper"}],
                                "artifacts": [{"type": "paper", "path_or_url": "wiki/projects/DemoProject/papers/source/index.md", "label": "source paper"}],
                                "interpretation": "Supports fusion as a plausible mechanism but needs local replication.",
                                "claim_impacts": [{"claim": "C4", "impact": "supports", "strength": "weak"}],
                                "weaknesses": ["Not reproduced in local workspace."],
                            }
                        ],
                        "next_moves": [
                            {
                                "type": "run",
                                "rationale": "Imported evidence needs local replication.",
                                "suggested_prompt": "Run the geometry-interaction ablation locally.",
                                "linked_experiment": "EXP1",
                                "linked_claim": "C4",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status, payload = handle_experiments_request(root, "/api/experiments?project=DemoProject")

        self.assertEqual(status, 200)
        model = json.loads(payload.decode("utf-8"))
        self.assertEqual(model["schema_version"], "experiments-v1")
        self.assertEqual(model["project_id"], "DemoProject")
        self.assertEqual(model["summary"]["total_experiments"], 1)
        self.assertEqual(model["summary"]["planned"], 1)
        self.assertEqual(model["summary"]["completed_runs"], 1)
        self.assertEqual(model["runs"][0]["evidence_type"], "imported_paper_evidence")
        self.assertFalse(model["mutating"])
```

Add invalid project test:

```python
    def test_project_experiments_api_rejects_nested_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload = handle_experiments_request(Path(tmp), "/api/experiments?project=../DemoProject")

        self.assertEqual(status, 404)
        self.assertEqual(json.loads(payload.decode("utf-8"))["error"], "Not Found")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_dashboard_public.DashboardPublicTest.test_project_experiments_api_serves_designs_and_runs tests.test_dashboard_public.DashboardPublicTest.test_project_experiments_api_rejects_nested_project_id -v
```

Expected: import failure for `tools.experiment_store` or missing `handle_experiments_request`.

- [ ] **Step 3: Implement experiment loader**

Create `tools/experiment_store.py`:

```python
"""Read-only experiment read model loader."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.research_browser_server import valid_project_id


EXPERIMENT_SCHEMA_VERSION = "experiments-v1"
VALID_EXPERIMENT_STATUSES = {"planned", "ready", "running", "blocked", "completed", "superseded"}
VALID_RUN_STATUSES = {"not_started", "running", "completed", "failed", "inconclusive"}
VALID_EVIDENCE_TYPES = {
    "imported_paper_evidence",
    "local_experiment_result",
    "external_result",
    "replication_result",
}


def empty_project_experiments(project_id: str) -> Dict[str, Any]:
    return {
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mutating": False,
        "source_boundary": "dashboard is a read-only projection of project experiment records",
        "summary": {
            "total_experiments": 0,
            "planned": 0,
            "ready": 0,
            "running": 0,
            "blocked": 0,
            "completed": 0,
            "completed_runs": 0,
            "local_result_runs": 0,
            "imported_evidence_runs": 0,
            "strongest_current_evidence": "",
            "highest_priority_unresolved": "",
        },
        "experiments": [],
        "runs": [],
        "next_moves": [],
        "legacy_proposals": {"found": False, "count": 0, "path": f"wiki/projects/{project_id}/experiment-proposals"},
        "empty_message": "No experiments recorded yet.",
    }


def experiment_record_path(root: Path, project_id: str) -> Path:
    if not valid_project_id(project_id):
        raise ValueError("invalid project_id")
    return root / "wiki" / "projects" / project_id / "experiments" / "experiments.json"


def build_project_experiments(root: Path, project_id: str) -> Dict[str, Any]:
    if not valid_project_id(project_id):
        raise ValueError("invalid project_id")
    model = empty_project_experiments(project_id)
    path = experiment_record_path(root, project_id)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("experiments.json must contain an object")
        model["summary"].update(_dict(payload.get("summary")))
        model["experiments"] = [_normalize_experiment(item) for item in _list(payload.get("experiments"))]
        model["runs"] = [_normalize_run(item) for item in _list(payload.get("runs"))]
        model["next_moves"] = [_normalize_next_move(item) for item in _list(payload.get("next_moves"))]
    legacy_dir = root / "wiki" / "projects" / project_id / "experiment-proposals"
    legacy_count = len([path for path in legacy_dir.glob("*.md") if path.is_file()]) if legacy_dir.exists() else 0
    model["legacy_proposals"] = {
        "found": legacy_count > 0,
        "count": legacy_count,
        "path": f"wiki/projects/{project_id}/experiment-proposals",
    }
    _populate_summary(model)
    return model


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> List[str]:
    return [str(item).strip() for item in _list(value) if str(item).strip()]


def _normalize_experiment(item: Any) -> Dict[str, Any]:
    raw = _dict(item)
    status = str(raw.get("status") or "planned")
    if status not in VALID_EXPERIMENT_STATUSES:
        status = "planned"
    return {
        "id": str(raw.get("id") or "EXP").strip(),
        "title": str(raw.get("title") or "Untitled experiment").strip(),
        "status": status,
        "question": str(raw.get("question") or "").strip(),
        "hypothesis": str(raw.get("hypothesis") or "").strip(),
        "linked_claims": _strings(raw.get("linked_claims")),
        "linked_gaps": _strings(raw.get("linked_gaps")),
        "benchmark": str(raw.get("benchmark") or "").strip(),
        "dataset": str(raw.get("dataset") or "").strip(),
        "models": _strings(raw.get("models")),
        "baselines": _strings(raw.get("baselines")),
        "metrics": _strings(raw.get("metrics")),
        "protocol": _strings(raw.get("protocol")),
        "expected_evidence": str(raw.get("expected_evidence") or "").strip(),
        "risks": _strings(raw.get("risks")),
        "next_action": str(raw.get("next_action") or "").strip(),
    }


def _normalize_run(item: Any) -> Dict[str, Any]:
    raw = _dict(item)
    status = str(raw.get("status") or "not_started")
    if status not in VALID_RUN_STATUSES:
        status = "not_started"
    evidence_type = str(raw.get("evidence_type") or "local_experiment_result")
    if evidence_type not in VALID_EVIDENCE_TYPES:
        evidence_type = "local_experiment_result"
    return {
        "id": str(raw.get("id") or "RUN").strip(),
        "experiment_id": str(raw.get("experiment_id") or "").strip(),
        "status": status,
        "evidence_type": evidence_type,
        "completed_at": str(raw.get("completed_at") or "").strip(),
        "summary": str(raw.get("summary") or "").strip(),
        "metrics": [_dict(metric) for metric in _list(raw.get("metrics"))],
        "artifacts": [_dict(artifact) for artifact in _list(raw.get("artifacts"))],
        "interpretation": str(raw.get("interpretation") or "").strip(),
        "claim_impacts": [_dict(impact) for impact in _list(raw.get("claim_impacts"))],
        "weaknesses": _strings(raw.get("weaknesses")),
    }


def _normalize_next_move(item: Any) -> Dict[str, Any]:
    raw = _dict(item)
    return {
        "type": str(raw.get("type") or "interpret").strip(),
        "rationale": str(raw.get("rationale") or "").strip(),
        "suggested_prompt": str(raw.get("suggested_prompt") or "").strip(),
        "linked_experiment": str(raw.get("linked_experiment") or "").strip(),
        "linked_claim": str(raw.get("linked_claim") or "").strip(),
    }


def _populate_summary(model: Dict[str, Any]) -> None:
    experiments = model["experiments"]
    runs = model["runs"]
    summary = model["summary"]
    summary["total_experiments"] = len(experiments)
    for status in ("planned", "ready", "running", "blocked", "completed"):
        summary[status] = sum(1 for item in experiments if item.get("status") == status)
    summary["completed_runs"] = sum(1 for item in runs if item.get("status") == "completed")
    summary["local_result_runs"] = sum(1 for item in runs if item.get("evidence_type") == "local_experiment_result")
    summary["imported_evidence_runs"] = sum(1 for item in runs if item.get("evidence_type") == "imported_paper_evidence")
```

- [ ] **Step 4: Add API handler and route**

Modify `tools/research_browser_server.py` imports:

```python
from tools.experiment_store import build_project_experiments
```

Add handler near `handle_experiment_proposals_request`:

```python
def handle_experiments_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    try:
        model = build_project_experiments(root.resolve(), project_id)
    except (ValueError, json.JSONDecodeError) as exc:
        return json_response({"error": f"Invalid project experiments: {exc}"}, HTTPStatus.BAD_REQUEST)
    return json_response(model)
```

Add route in `do_GET` before legacy proposal route:

```python
        elif request_api_path == "/api/experiments":
            status, payload = handle_experiments_request(root, self.path)
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
python3 -m unittest tests.test_dashboard_public.DashboardPublicTest.test_project_experiments_api_serves_designs_and_runs tests.test_dashboard_public.DashboardPublicTest.test_project_experiments_api_rejects_nested_project_id -v
```

Expected: both tests pass.

## Task 2: Demo Affordance Experiment Data

**Files:**
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/experiments/experiments.json`
- Modify: `tests/test_demo_project.py`

- [ ] **Step 1: Write failing demo tests**

Add path constant:

```python
EXPERIMENTS = PROJECT / "experiments" / "experiments.json"
```

Add `EXPERIMENTS` to `expected` in `test_demo_workspace_contains_expected_files`.

Add test:

```python
    def test_demo_experiments_model_contains_design_and_imported_evidence(self) -> None:
        from tools.experiment_store import build_project_experiments

        model = build_project_experiments(DEMO, "DemoVisualAffordance")

        self.assertEqual(model["schema_version"], "experiments-v1")
        self.assertEqual(model["project_id"], "DemoVisualAffordance")
        self.assertGreaterEqual(len(model["experiments"]), 1)
        self.assertGreaterEqual(len(model["runs"]), 1)
        experiment = model["experiments"][0]
        self.assertIn("AGD20K", experiment["benchmark"])
        self.assertIn("mIoU", experiment["metrics"])
        self.assertIn("C4", experiment["linked_claims"])
        run = model["runs"][0]
        self.assertEqual(run["evidence_type"], "imported_paper_evidence")
        self.assertIn("not reproduced", " ".join(run["weaknesses"]).lower())
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_demo_project.DemoProjectTest.test_demo_workspace_contains_expected_files tests.test_demo_project.DemoProjectTest.test_demo_experiments_model_contains_design_and_imported_evidence -v
```

Expected: missing `experiments.json`.

- [ ] **Step 3: Add demo experiment JSON**

Create `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/experiments/experiments.json`:

```json
{
  "schema_version": "experiments-v1",
  "project_id": "DemoVisualAffordance",
  "summary": {
    "strongest_current_evidence": "Imported baseline evidence suggests geometry and interaction signals compose into useful affordance maps.",
    "highest_priority_unresolved": "Run a local geometry-only / interaction-only / fused ablation to test whether the imported result reproduces."
  },
  "experiments": [
    {
      "id": "EXP1",
      "title": "Geometry-interaction ablation on affordance grounding",
      "status": "planned",
      "question": "Does composing geometric part cues with interaction priors improve affordance grounding compared with either signal alone?",
      "hypothesis": "If VFM affordance reasoning depends on composable geometric and interaction primitives, then the fused method should outperform geometry-only and interaction-only baselines.",
      "linked_claims": ["C2", "C3", "C4"],
      "linked_gaps": ["G1"],
      "benchmark": "AGD20K or UMD affordance segmentation",
      "dataset": "Affordance masks or heatmaps for object-action pairs",
      "models": ["DINO-family geometry features", "Flux / Flux Kontext interaction attention"],
      "baselines": ["geometry-only", "interaction-prior-only", "object-semantics control"],
      "metrics": ["mIoU", "F1", "pointing accuracy", "qualitative contact-region consistency"],
      "protocol": [
        "Run a geometry-only affordance localization baseline.",
        "Run an interaction-prior-only localization baseline.",
        "Run fused geometry plus interaction localization.",
        "Compare spatial mask quality and failure cases.",
        "Inspect cases where object semantics may explain success without contact-region reasoning."
      ],
      "expected_evidence": "Fusion should improve affordance localization if geometry and interaction are genuinely complementary primitives.",
      "risks": [
        "Imported baseline evidence may not reproduce locally.",
        "Object category semantics may explain part of the apparent affordance signal.",
        "AGD20K and UMD masks may under-specify richer action-object relations."
      ],
      "next_action": "Prepare local evaluation split and choose which VFM checkpoints to compare."
    }
  ],
  "runs": [
    {
      "id": "RUN1",
      "experiment_id": "EXP1",
      "status": "completed",
      "evidence_type": "imported_paper_evidence",
      "completed_at": "2026-05-15",
      "summary": "Zhang 2026 reports that geometry-aware VFM features correlate with better affordance probes, verb-conditioned generative attention localizes plausible interaction regions, and fused signals produce competitive zero-shot affordance maps.",
      "metrics": [
        {"name": "mIoU", "value": "reported in source paper"},
        {"name": "F1", "value": "reported in source paper"},
        {"name": "qualitative contact-region consistency", "value": "reported in source paper"}
      ],
      "artifacts": [
        {
          "type": "paper_dossier",
          "path_or_url": "wiki/projects/DemoVisualAffordance/papers/zhang2026-geometry-interaction-vfm/index.md",
          "label": "Zhang 2026 baseline dossier",
          "description": "Imported source evidence for the demo experiment."
        }
      ],
      "interpretation": "The imported evidence supports the fusion claim, but it is not a local reproduction and should stay weak until the project runs its own ablation.",
      "claim_impacts": [
        {"claim": "C2", "impact": "supports", "strength": "weak"},
        {"claim": "C3", "impact": "supports", "strength": "weak"},
        {"claim": "C4", "impact": "supports", "strength": "weak"}
      ],
      "weaknesses": [
        "Evidence is imported from the baseline paper, not reproduced in this local workspace.",
        "The result may still reflect object semantics or benchmark bias rather than causal interaction understanding."
      ]
    }
  ],
  "next_moves": [
    {
      "type": "run",
      "rationale": "The strongest evidence is imported; local replication would make the project claim stronger.",
      "suggested_prompt": "Use Research-Pilot to design the local geometry-only, interaction-only, and fused affordance ablation for AGD20K or UMD.",
      "linked_experiment": "EXP1",
      "linked_claim": "C4"
    },
    {
      "type": "ablate",
      "rationale": "Object semantics may explain apparent localization success.",
      "suggested_prompt": "Design a control that separates object category cues from contact-region affordance evidence.",
      "linked_experiment": "EXP1",
      "linked_claim": "C4"
    }
  ]
}
```

- [ ] **Step 4: Run demo tests**

Run:

```bash
python3 -m unittest tests.test_demo_project.DemoProjectTest.test_demo_workspace_contains_expected_files tests.test_demo_project.DemoProjectTest.test_demo_experiments_model_contains_design_and_imported_evidence -v
```

Expected: pass.

## Task 3: Dashboard Route and Copy

**Files:**
- Create: `dashboard/experiments.html`
- Modify: `dashboard/experiment-proposals.html`
- Modify: `dashboard/app.js`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing route/copy tests**

Add test:

```python
    def test_experiments_page_replaces_proposal_framing(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "dashboard" / "experiments.html").read_text(encoding="utf-8")
        legacy_html = (ROOT / "dashboard" / "experiment-proposals.html").read_text(encoding="utf-8")

        self.assertIn('data-page="experiments"', html)
        self.assertIn("<title>Research Browser · Experiments</title>", html)
        self.assertIn("function experimentsUrl(projectId)", app)
        self.assertIn('current === "experiments"', app)
        self.assertIn(">Experiments</a>", app)
        self.assertIn("/api/experiments", app)
        self.assertNotIn("Experiment Proposals</a>", app)
        self.assertIn('data-page="experiments"', legacy_html)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_experiments_page_replaces_proposal_framing -v
```

Expected: missing `experiments.html` or old proposal copy still present.

- [ ] **Step 3: Create canonical experiments page**

Create `dashboard/experiments.html` by copying `dashboard/experiment-proposals.html` and changing:

```html
<title>Research Browser · Experiments</title>
<body data-page="experiments">
<small>Experiments</small>
<p id="page-kicker" class="page-kicker">Experiments</p>
<h1 id="page-title">Experiments</h1>
```

Keep:

```html
<link rel="stylesheet" href="./styles.css?v=english-dashboard-20260523" />
<script src="./app.js?v=english-dashboard-20260523" defer></script>
```

- [ ] **Step 4: Make old page a compatibility alias**

Modify `dashboard/experiment-proposals.html` to use the same page key and visible copy:

```html
<title>Research Browser · Experiments</title>
<body data-page="experiments">
<small>Experiments</small>
<p id="page-kicker" class="page-kicker">Experiments</p>
<h1 id="page-title">Experiments</h1>
```

- [ ] **Step 5: Rename URL helper and nav copy**

In `dashboard/app.js`, replace:

```javascript
function experimentProposalsUrl(projectId) {
  return dashboardPageUrl("experiment-proposals", { project: projectId });
}
```

with:

```javascript
function experimentsUrl(projectId) {
  return dashboardPageUrl("experiments", { project: projectId });
}
```

Change nav state and copy:

```javascript
const experimentsCurrent = current === "experiments" ? ' aria-current="page"' : "";
...
<a href="${escapeAttr(experimentsUrl(project.id))}"${experimentsCurrent}>Experiments</a>
```

Change renderer dispatch:

```javascript
else if (state.page === "experiments") await renderExperimentsPage();
```

- [ ] **Step 6: Run route/copy test**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_experiments_page_replaces_proposal_framing -v
```

Expected: pass.

## Task 4: Dashboard Experiment Rendering

**Files:**
- Modify: `dashboard/app.js`
- Modify: `dashboard/styles.css`
- Test: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Write failing renderer tests**

Add test:

```python
    def test_experiments_renderer_shows_designs_results_and_next_moves(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn("async function loadExperimentsFromApi(projectId)", app)
        self.assertIn("async function renderExperimentsPage()", app)
        self.assertIn("function renderExperimentDesignCard(experiment)", app)
        self.assertIn("function renderExperimentRunCard(run)", app)
        self.assertIn("Experiment Evidence Summary", app)
        self.assertIn("Active Experiment Designs", app)
        self.assertIn("Results / Evidence", app)
        self.assertIn("Next Experiment Moves", app)
        self.assertIn("imported_paper_evidence", app)
        self.assertIn("Local experiment result", app)
        self.assertNotIn("planned / pending / not yet graph evidence", app)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_experiments_renderer_shows_designs_results_and_next_moves -v
```

Expected: old proposal renderer does not contain new functions/strings.

- [ ] **Step 3: Replace API loader**

In `dashboard/app.js`, replace `loadExperimentProposalsFromApi` with:

```javascript
async function loadExperimentsFromApi(projectId) {
  if (!projectId) return { experiments: [], runs: [], next_moves: [], empty_message: "No experiments recorded yet." };
  try {
    const response = await fetch(`/api/experiments?project=${encodeURIComponent(projectId)}`, { cache: "no-store" });
    if (!response.ok) return { experiments: [], runs: [], next_moves: [], empty_message: "No experiments recorded yet." };
    return response.json();
  } catch (_error) {
    return { experiments: [], runs: [], next_moves: [], empty_message: "No experiments recorded yet." };
  }
}
```

- [ ] **Step 4: Replace proposal renderer with experiment page renderer**

Replace `renderExperimentProposalsPage`, `renderExperimentProposalCard`, and `renderExperimentProposalSection` with:

```javascript
async function renderExperimentsPage() {
  const project = projectById();
  if (!project) {
    renderEmpty("Project not found.");
    return;
  }
  renderProjectNav(project);
  setHeader("Experiments", "Experiments", `${displayProjectTitle(project)} · planned design and completed evidence`);
  el.content.innerHTML = `
    <section class="section-block experiment-page-shell">
      <div class="section-head">
        <div>
          <p class="eyebrow">Experiment Evidence Summary</p>
          <h2>Planned design and completed evidence</h2>
          <p class="section-note">Read-only experiment state from local project records. Imported paper evidence is labeled separately from local experiment results.</p>
        </div>
        <a href="${escapeAttr(projectUrl(project.id))}">Back to Project</a>
      </div>
      <div id="experiment-page-content" class="experiment-page-content">
        <div class="empty-state">Loading experiments...</div>
      </div>
    </section>
  `;
  const model = await loadExperimentsFromApi(project.id);
  const target = document.getElementById("experiment-page-content");
  if (!target) return;
  target.innerHTML = renderExperimentsModel(model);
}

function renderExperimentsModel(model) {
  const experiments = Array.isArray(model?.experiments) ? model.experiments : [];
  const runs = Array.isArray(model?.runs) ? model.runs : [];
  const nextMoves = Array.isArray(model?.next_moves) ? model.next_moves : [];
  if (!experiments.length && !runs.length) {
    return `<div class="empty-state">${escapeHtml(model?.empty_message || "No experiments recorded yet.")}</div>${renderLegacyExperimentNote(model)}`;
  }
  return `
    ${renderExperimentSummary(model)}
    <section class="experiment-page-section">
      <h2>Active Experiment Designs</h2>
      <div class="experiment-card-grid">${experiments.map((experiment) => renderExperimentDesignCard(experiment)).join("") || `<div class="empty-state">No experiment designs recorded.</div>`}</div>
    </section>
    <section class="experiment-page-section">
      <h2>Results / Evidence</h2>
      <div class="experiment-card-grid">${runs.map((run) => renderExperimentRunCard(run)).join("") || `<div class="empty-state">No experiment evidence recorded.</div>`}</div>
    </section>
    <section class="experiment-page-section">
      <h2>Next Experiment Moves</h2>
      <div class="next-move-list">${nextMoves.map((move) => renderExperimentNextMove(move)).join("") || `<div class="empty-state">No next experiment moves recorded.</div>`}</div>
    </section>
    ${renderLegacyExperimentNote(model)}
  `;
}

function renderExperimentSummary(model) {
  const summary = model?.summary || {};
  return `
    <section class="experiment-page-section">
      <h2>Experiment Evidence Summary</h2>
      <dl class="metric-row experiment-summary-row">
        <div><dt>Total</dt><dd>${escapeHtml(summary.total_experiments ?? 0)}</dd></div>
        <div><dt>Planned</dt><dd>${escapeHtml(summary.planned ?? 0)}</dd></div>
        <div><dt>Running</dt><dd>${escapeHtml(summary.running ?? 0)}</dd></div>
        <div><dt>Completed runs</dt><dd>${escapeHtml(summary.completed_runs ?? 0)}</dd></div>
        <div><dt>Imported evidence</dt><dd>${escapeHtml(summary.imported_evidence_runs ?? 0)}</dd></div>
        <div><dt>Local results</dt><dd>${escapeHtml(summary.local_result_runs ?? 0)}</dd></div>
      </dl>
      ${summary.strongest_current_evidence ? `<p class="section-note"><strong>Strongest evidence:</strong> ${escapeHtml(summary.strongest_current_evidence)}</p>` : ""}
      ${summary.highest_priority_unresolved ? `<p class="section-note"><strong>Highest priority unresolved:</strong> ${escapeHtml(summary.highest_priority_unresolved)}</p>` : ""}
    </section>
  `;
}

function renderExperimentDesignCard(experiment) {
  return `
    <article class="experiment-card">
      <div class="experiment-card-head">
        <div>
          <p class="eyebrow">${escapeHtml(experiment?.id || "experiment")}</p>
          <h3>${escapeHtml(experiment?.title || "Untitled experiment")}</h3>
        </div>
        ${statusPill(experiment?.status || "planned")}
      </div>
      ${renderExperimentField("Question", experiment?.question)}
      ${renderExperimentField("Hypothesis", experiment?.hypothesis)}
      ${renderExperimentField("Benchmark", experiment?.benchmark)}
      ${renderExperimentField("Dataset", experiment?.dataset)}
      ${renderExperimentList("Linked claims", experiment?.linked_claims)}
      ${renderExperimentList("Models", experiment?.models)}
      ${renderExperimentList("Baselines", experiment?.baselines)}
      ${renderExperimentList("Metrics", experiment?.metrics)}
      ${renderExperimentList("Protocol", experiment?.protocol)}
      ${renderExperimentField("Expected evidence", experiment?.expected_evidence)}
      ${renderExperimentList("Risks", experiment?.risks)}
      ${renderExperimentField("Next action", experiment?.next_action)}
    </article>
  `;
}

function renderExperimentRunCard(run) {
  const evidenceType = experimentEvidenceTypeLabel(run?.evidence_type);
  return `
    <article class="experiment-card experiment-run-card">
      <div class="experiment-card-head">
        <div>
          <p class="eyebrow">${escapeHtml(run?.id || "run")} · ${escapeHtml(run?.experiment_id || "unlinked")}</p>
          <h3>${escapeHtml(evidenceType)}</h3>
        </div>
        ${statusPill(run?.status || "not_started")}
      </div>
      <p class="experiment-evidence-type ${run?.evidence_type === "imported_paper_evidence" ? "is-imported" : "is-local"}">${escapeHtml(evidenceType)}</p>
      ${renderExperimentField("Completed", run?.completed_at)}
      ${renderExperimentField("Summary", run?.summary)}
      ${renderExperimentList("Metrics", (run?.metrics || []).map((metric) => `${metric.name || "metric"}: ${metric.value || ""}`))}
      ${renderExperimentField("Interpretation", run?.interpretation)}
      ${renderExperimentList("Claim impact", (run?.claim_impacts || []).map((impact) => `${impact.claim || "claim"}: ${impact.impact || "unknown"}${impact.strength ? ` / ${impact.strength}` : ""}`))}
      ${renderExperimentList("Weaknesses", run?.weaknesses)}
      ${renderExperimentList("Artifacts", (run?.artifacts || []).map((artifact) => `${artifact.label || artifact.type || "artifact"}: ${artifact.path_or_url || ""}`))}
    </article>
  `;
}

function experimentEvidenceTypeLabel(value) {
  const labels = {
    imported_paper_evidence: "Imported paper evidence",
    local_experiment_result: "Local experiment result",
    external_result: "External result",
    replication_result: "Replication result",
  };
  return labels[value] || "Local experiment result";
}

function renderExperimentNextMove(move) {
  return `
    <article class="next-move-card">
      <p class="eyebrow">${escapeHtml(move?.type || "next")}</p>
      <h3>${escapeHtml(move?.linked_experiment || move?.linked_claim || "Next move")}</h3>
      <p>${escapeHtml(move?.rationale || "No rationale recorded.")}</p>
      ${move?.suggested_prompt ? `<blockquote>${escapeHtml(move.suggested_prompt)}</blockquote>` : ""}
    </article>
  `;
}

function renderExperimentField(label, value) {
  return value ? `<section class="experiment-field"><h4>${escapeHtml(label)}</h4><p>${escapeHtml(value)}</p></section>` : "";
}

function renderExperimentList(label, value) {
  const items = Array.isArray(value) ? value.filter(Boolean) : [];
  return items.length ? `<section class="experiment-field"><h4>${escapeHtml(label)}</h4><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : "";
}

function renderLegacyExperimentNote(model) {
  const legacy = model?.legacy_proposals || {};
  if (!legacy.found) return "";
  return `<p class="section-note legacy-experiment-note">Legacy proposals found: ${escapeHtml(legacy.count || 0)} in ${escapeHtml(legacy.path || "experiment-proposals")}.</p>`;
}
```

- [ ] **Step 5: Add minimal CSS**

Append to `dashboard/styles.css` near experiment proposal styles:

```css
.experiment-page-content,
.experiment-page-section {
  display: grid;
  gap: 16px;
}

.experiment-summary-row {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.experiment-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.experiment-card,
.next-move-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  padding: 16px;
}

.experiment-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.experiment-field {
  margin-top: 12px;
}

.experiment-field h4 {
  margin: 0 0 4px;
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.experiment-field p,
.experiment-field ul {
  margin: 0;
}

.experiment-evidence-type {
  display: inline-flex;
  width: fit-content;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--text);
}

.experiment-evidence-type.is-imported {
  border-color: var(--accent);
  color: var(--accent);
}

.legacy-experiment-note {
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

@media (max-width: 900px) {
  .experiment-summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

- [ ] **Step 6: Run renderer tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_experiments_renderer_shows_designs_results_and_next_moves -v
```

Expected: pass.

## Task 5: End-to-End Browser Verification

**Files:**
- Test only; no source edits unless browser verification exposes a bug.

- [ ] **Step 1: Run focused unit suite**

Run:

```bash
python3 -m unittest tests.test_dashboard_public tests.test_demo_project tests.test_related_work_lineage_dashboard tests.test_understanding_schema_contracts tests.test_understanding_store tests.test_understanding_cli -v
```

Expected: all tests pass.

- [ ] **Step 2: Start temporary demo dashboard**

Run:

```bash
tmp=/tmp/rp-experiments-dashboard-smoke
rm -rf "$tmp"
python3 tools/research_pilot_init.py "$tmp" --no-git
python3 tools/research_browser_server.py --repo "$tmp" --host 127.0.0.1 --port 8899
```

Expected: server starts. If sandbox blocks binding, rerun the server command with approval.

- [ ] **Step 3: Browser smoke with Playwright**

Run:

```bash
python3 - <<'PY'
from playwright.sync_api import sync_playwright
url = "http://127.0.0.1:8899/dashboard/experiments.html?v=english-dashboard-20260523&project=DemoVisualAffordance"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1200})
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(url, wait_until="networkidle")
    text = page.locator("body").inner_text()
    print({
        "title": page.locator("#page-title").inner_text(),
        "has_experiments": "Experiments" in text,
        "has_designs": "Active Experiment Designs" in text,
        "has_results": "Results / Evidence" in text,
        "has_next_moves": "Next Experiment Moves" in text,
        "has_imported_label": "Imported paper evidence" in text,
        "has_proposal_main_framing": "Experiment Proposals" in text,
        "has_chinese": any("\\u4e00" <= ch <= "\\u9fff" for ch in text),
        "console_errors": errors,
    })
    page.screenshot(path="/tmp/rp_experiments_dashboard.png", full_page=True)
    browser.close()
PY
```

Expected:

```text
title == "Experiments"
has_experiments == True
has_designs == True
has_results == True
has_next_moves == True
has_imported_label == True
has_proposal_main_framing == False
has_chinese == False
console_errors == []
```

- [ ] **Step 4: Stop temporary server**

Stop the server:

```bash
kill $(lsof -tiTCP:8899 -sTCP:LISTEN)
```

- [ ] **Step 5: Check demo package stays clean**

Run:

```bash
find examples/workspaces/demo-visual-affordance -maxdepth 4 \( -name .dashboard -o -name graph.db -o -path '*/graphs/snapshots' \) -print
```

Expected: no output.

## Task 6: Release Check and Final Notes

**Files:**
- No planned source edits.

- [ ] **Step 1: Run release check**

Run:

```bash
./scripts/release_check.sh
```

Expected current known failure may remain in an older lineage-atlas plan that contains a user-local absolute path. If that old failure appears, report it as pre-existing unless the user asks to fix it in this branch.

- [ ] **Step 2: Inspect git status**

Run:

```bash
git status --short
```

Expected: changes are limited to PRD/plan, experiment read model/API, dashboard experiment page, demo experiment data, and focused tests.

- [ ] **Step 3: Final report**

Report:

- files changed
- tests passed
- browser smoke result
- release check result
- local dashboard URL:

```text
http://127.0.0.1:8899/dashboard/experiments.html?v=english-dashboard-20260523&project=DemoVisualAffordance
```

Use the user’s normal port if they run the dashboard on `8898`.

## Self-Review

Spec coverage:

- Planned design plus completed evidence: Tasks 1, 2, 4.
- Read-only page: Tasks 1 and 4 include `mutating: False` and no browser actions.
- One JSON file for MVP: Tasks 1 and 2 use only `experiments/experiments.json`.
- Imported evidence distinct from local results: Tasks 1, 2, 4, 5.
- Legacy proposal no-migration rule: Tasks 1 and 4 show note only.
- Demo affordance example: Task 2.
- API/read model: Task 1.
- Dashboard page: Tasks 3 and 4.
- Verification: Tasks 5 and 6.

Placeholder scan:

- No `TBD`, `TODO`, or fill-in implementation placeholders.

Type consistency:

- API endpoint uses `/api/experiments`.
- Page key uses `experiments`.
- JSON schema uses `experiments-v1`.
- Evidence type uses `imported_paper_evidence` and `local_experiment_result`.
