# Demo Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a sanitized, deletable `DemoVisualAffordance` project that new Research Pilot workspaces receive by default and that developers can use to inspect dashboard changes immediately.

**Architecture:** Keep demo source in `examples/workspaces/demo-visual-affordance/` and copy only selected demo project files into initialized user workspaces. Dashboard remains read-only; it only marks demo projects with a badge from read-model metadata. Sanitization tests guard against private paths, generated files, PDFs, and raw CVPR workspace identifiers.

**Tech Stack:** Python stdlib CLIs and `unittest`; Research Pilot markdown workspace templates; existing dashboard vanilla JS/CSS; existing graph and lineage validation tools.

---

## File Structure

- Create `examples/workspaces/demo-visual-affordance/`: sanitized example workspace containing one project, one graph event file, paper dossiers, and one related-work lineage artifact.
- Modify `tools/research_pilot_init.py`: add `--no-demo`, copy demo by default, preserve existing overwrite semantics.
- Modify `tools/build_dashboard_index.py`: expose `demo: true` from project frontmatter.
- Modify `dashboard/app.js`: render demo badge on project list and project header.
- Modify `dashboard/styles.css`: style demo badge.
- Create `tests/test_demo_project.py`: fixture validation, init behavior, no-overwrite behavior, dashboard metadata, graph/lineage validation, private-token scan.
- Modify `tests/test_related_work_lineage_dashboard.py`: verify `renderDemoBadge(project)` and project-list badge output.
- Modify `docs/guides/install.md`, `docs/guides/dashboard.md`, `docs/guides/workspace.md`: document default demo and deletion commands.

## Storage Path Alignment

Existing workspace source template lives at `templates/workspace/`. Existing lightweight demo fixtures live under `examples/demo/`. Existing dashboard read model scans project files under `wiki/projects/<Project>` and lineage artifacts under `wiki/projects/<Project>/literature-rounds/<Round>/related-work-lineage.json`.

This plan uses:

```text
examples/workspaces/demo-visual-affordance/
```

as source demo workspace, then copies these runtime paths into initialized workspaces:

```text
wiki/projects/DemoVisualAffordance/
wiki/graphs/events/projects/DemoVisualAffordance.jsonl
```

This keeps demo data outside `templates/workspace/`, avoids treating demo as system template truth, and preserves existing workspace project/event conventions.

## Task 1: Add Demo Fixture And Sanitization Tests

**Files:**
- Create: `tests/test_demo_project.py`
- Create: `examples/workspaces/demo-visual-affordance/AGENTS.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/index.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/log.md`
- Create: `examples/workspaces/demo-visual-affordance/.research-pilot/config.example.toml`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/overview.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/project-query-pack.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/project-understanding-graph.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/decisions.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/papers/<paper-id>/index.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json`
- Create: `examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.md`
- Create: `examples/workspaces/demo-visual-affordance/wiki/graphs/events/projects/DemoVisualAffordance.jsonl`

- [ ] **Step 1: Write failing fixture tests**

Append this new test file:

```python
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_dashboard_index import build_index
from tools.related_work_lineage_cli import validate_lineage_map


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "workspaces" / "demo-visual-affordance"
PROJECT = DEMO / "wiki" / "projects" / "DemoVisualAffordance"
LINEAGE = PROJECT / "literature-rounds" / "demo-affordance-lineage" / "related-work-lineage.json"


class DemoProjectTest(unittest.TestCase):
    def test_demo_workspace_contains_expected_files(self) -> None:
        expected = [
            DEMO / "AGENTS.md",
            DEMO / "wiki" / "index.md",
            DEMO / "wiki" / "log.md",
            DEMO / ".research-pilot" / "config.example.toml",
            PROJECT / "overview.md",
            PROJECT / "project-query-pack.md",
            PROJECT / "project-understanding-graph.md",
            PROJECT / "decisions.md",
            LINEAGE,
            LINEAGE.with_suffix(".md"),
            DEMO / "wiki" / "graphs" / "events" / "projects" / "DemoVisualAffordance.jsonl",
        ]
        for path in expected:
            self.assertTrue(path.exists(), str(path))

    def test_demo_tree_has_no_private_or_generated_artifacts(self) -> None:
        forbidden_text = [
            "/Users/" + "qing",
            "Personal" + "ResearchWiki",
            "CVPR" + "2026_VisualAffordance",
            "Zotero/storage",
            "AAAI2027",
            "submission_" + "affordance.pdf",
        ]
        forbidden_suffixes = {".pdf", ".sqlite", ".db"}
        for path in DEMO.rglob("*"):
            self.assertNotEqual(path.name, ".dashboard")
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), forbidden_suffixes, str(path))
                text = path.read_text(encoding="utf-8")
                for token in forbidden_text:
                    self.assertNotIn(token, text, f"{token} found in {path}")

    def test_demo_lineage_validates(self) -> None:
        payload = json.loads(LINEAGE.read_text(encoding="utf-8"))
        result = validate_lineage_map(payload)
        self.assertTrue(result["valid"], result)
        self.assertEqual(payload["project"], "DemoVisualAffordance")
        self.assertLessEqual(result["paper_count"], 20)

    def test_demo_dashboard_index_exposes_project_lineage_and_demo_flag(self) -> None:
        index = build_index(DEMO)
        project = next(item for item in index["projects"] if item["id"] == "DemoVisualAffordance")
        self.assertTrue(project["demo"])
        self.assertEqual(project["title"], "Demo Visual Affordance")
        self.assertEqual(len(index["lineage_maps"]), 1)
        self.assertEqual(index["lineage_maps"][0]["project"], "DemoVisualAffordance")

    def test_demo_graph_events_validate(self) -> None:
        completed = subprocess.run(
            [
                "python3",
                "tools/graph_validate.py",
                "--repo",
                str(DEMO),
                "--project",
                "DemoVisualAffordance",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
```

- [ ] **Step 2: Run fixture tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_demo_project -v
```

Expected: FAIL because `examples/workspaces/demo-visual-affordance` does not exist.

- [ ] **Step 3: Create sanitized demo workspace files**

Create demo files with these constraints:

```text
project id: DemoVisualAffordance
title: Demo Visual Affordance
demo frontmatter: demo: true
paper count: 6 to 10
lineage paper count: 6 to 10
routes:
  - affordance-datasets-and-grounding
  - part-and-geometry-priors
  - open-vocabulary-affordance
  - foundation-model-probing
```

Use public paper anchors from the existing local example where safe:

```text
Luo2022 Learning Affordance Grounding from Exocentric Images
Li2023 LOCATE
Li2024 One-Shot Open Affordance Learning with Foundation Models
Qian2024 AffordanceLLM
Amir2022 Deep ViT Features as Dense Visual Descriptors
Simeoni2025 DINOv3
Bolya2025 Perception Encoder
```

`overview.md` frontmatter must include:

```yaml
---
title: "Demo Visual Affordance"
display_title: "Demo Visual Affordance"
type: project-overview
demo: true
created: 2026-05-14
updated: 2026-05-14
domains: [embodied-intelligence, scene-understanding]
tags: [demo, affordance, related-work-lineage]
status: active
human_review: approved
confidence: medium
---
```

`related-work-lineage.json` must use existing schema:

```json
{
  "schema_version": "related-work-lineage-v1",
  "project": "DemoVisualAffordance",
  "round": "demo-affordance-lineage",
  "title": "Demo Visual Affordance Related Work Lineage",
  "status": "candidate",
  "source_boundary": "related_work_lineage_only_not_graph_truth",
  "max_papers": 20,
  "route_narrowing": {
    "input_mode": "baseline_papers",
    "user_direction": "Visual affordance grounding with geometry and interaction cues.",
    "selected_anchor_papers": ["paper:luo2022-agd20k", "paper:li2024-ooal"],
    "candidate_routes": []
  },
  "routes": [],
  "papers": [],
  "explicit_edges": [],
  "positioning_note": "Demo project sits between affordance grounding, dense geometry priors, and open-vocabulary foundation-model probing."
}
```

Fill `routes`, `papers`, and `explicit_edges` with valid entries. Every paper entry must include `id`, `kind: "paper"`, `title`, `year`, `route`, `roles`, `source_url`, non-empty `identity`, `source_evidence`, and `review_status`.

`DemoVisualAffordance.jsonl` should be compact. Use graph events adapted from `examples/demo/events/demo-project.jsonl`, renamed to `project:DemoVisualAffordance:*`, with one accepted question, two claims, two evidence nodes, one warrant, one limitation, and at least one reasoning link.

- [ ] **Step 4: Run tests and validation**

Run:

```bash
python3 -m unittest tests.test_demo_project -v
python3 tools/related_work_lineage_cli.py validate --path examples/workspaces/demo-visual-affordance/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json --json
python3 tools/graph_validate.py --repo examples/workspaces/demo-visual-affordance --project DemoVisualAffordance
```

Expected: all pass. JSON validate output includes `"valid": true`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_demo_project.py examples/workspaces/demo-visual-affordance
git commit -m "Add sanitized demo visual affordance workspace"
```

## Task 2: Copy Demo On Workspace Init

**Files:**
- Modify: `tools/research_pilot_init.py`
- Modify: `tests/test_demo_project.py`

- [ ] **Step 1: Add failing init tests**

Append to `DemoProjectTest`:

```python
from tools.research_pilot_init import main as research_pilot_init_main


    def test_init_copies_demo_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            result = research_pilot_init_main([str(workspace), "--no-git"])
            demo_overview = workspace / "wiki" / "projects" / "DemoVisualAffordance" / "overview.md"
            demo_events = workspace / "wiki" / "graphs" / "events" / "projects" / "DemoVisualAffordance.jsonl"
            self.assertEqual(result, 0)
            self.assertTrue(demo_overview.exists())
            self.assertTrue(demo_events.exists())

    def test_init_no_demo_skips_demo_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            result = research_pilot_init_main([str(workspace), "--no-git", "--no-demo"])
            self.assertEqual(result, 0)
            self.assertFalse((workspace / "wiki" / "projects" / "DemoVisualAffordance").exists())
            self.assertFalse((workspace / "wiki" / "graphs" / "events" / "projects" / "DemoVisualAffordance.jsonl").exists())

    def test_init_does_not_overwrite_demo_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            research_pilot_init_main([str(workspace), "--no-git"])
            overview = workspace / "wiki" / "projects" / "DemoVisualAffordance" / "overview.md"
            overview.write_text("local edit\n", encoding="utf-8")
            research_pilot_init_main([str(workspace), "--no-git"])
            self.assertEqual(overview.read_text(encoding="utf-8"), "local edit\n")
            research_pilot_init_main([str(workspace), "--no-git", "--overwrite"])
            self.assertIn("Demo Visual Affordance", overview.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run init tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_demo_project -v
```

Expected: FAIL because `research_pilot_init.py` has no `--no-demo` and does not copy demo.

- [ ] **Step 3: Implement demo copy**

In `tools/research_pilot_init.py`, add:

```python
def copy_demo_workspace(repo: Path, target_root: Path, overwrite: bool) -> bool:
    demo_root = repo / "examples" / "workspaces" / "demo-visual-affordance"
    if not demo_root.is_dir():
        return False
    copy_template_tree(demo_root, target_root, overwrite)
    return True
```

Add parser flag:

```python
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="Do not copy the built-in DemoVisualAffordance project.",
    )
```

Call after template copy:

```python
    copied_demo = False
    if not args.no_demo:
        copied_demo = copy_demo_workspace(repo_root(), target_root, args.overwrite)
```

Print after next steps:

```python
    if copied_demo:
        print("")
        print("Demo project installed: DemoVisualAffordance")
        print("Delete it by removing wiki/projects/DemoVisualAffordance and wiki/graphs/events/projects/DemoVisualAffordance.jsonl.")
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_demo_project tests.test_plugin_commands -v
```

Expected: PASS. Existing workflow-copy test still passes even though demo copies by default.

- [ ] **Step 5: Commit**

```bash
git add tools/research_pilot_init.py tests/test_demo_project.py
git commit -m "Copy demo project during workspace init"
```

## Task 3: Expose Demo Metadata In Dashboard Index

**Files:**
- Modify: `tools/build_dashboard_index.py`
- Modify: `tests/test_dashboard_public.py`
- Modify: `tests/test_demo_project.py`

- [ ] **Step 1: Add failing dashboard metadata test**

Append to `DashboardPublicTest`:

```python
    def test_project_index_exposes_demo_flag_from_overview_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\ndemo: true\n---\n"
                "# Demo Project\n\n## Project Direction\n\nDemo direction.\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertTrue(index["projects"][0]["demo"])
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_dashboard_public.DashboardPublicTest.test_project_index_exposes_demo_flag_from_overview_frontmatter -v
```

Expected: FAIL with missing `demo` key.

- [ ] **Step 3: Add project demo field**

In `collect_projects`, include:

```python
                "demo": bool(frontmatter.get("demo")),
```

in each project dict. In `ensure_graph_projects`, include:

```python
                "demo": False,
```

for graph-only projects.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_dashboard_public tests.test_demo_project -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/build_dashboard_index.py tests/test_dashboard_public.py tests/test_demo_project.py
git commit -m "Expose demo project metadata in dashboard index"
```

## Task 4: Render Demo Badge In Dashboard

**Files:**
- Modify: `dashboard/app.js`
- Modify: `dashboard/styles.css`
- Modify: `tests/test_related_work_lineage_dashboard.py`

- [ ] **Step 1: Add failing badge rendering test**

Append to `RelatedWorkLineageDashboardTest`:

```python
    def test_demo_badge_rendering_is_escaped(self):
        script = textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");
            const elements = {
              "page-title": { textContent: "", innerHTML: "", className: "" },
              "page-subtitle": { textContent: "", innerHTML: "", className: "" },
              "page-kicker": { textContent: "", innerHTML: "", className: "" },
              "page-content": { textContent: "", innerHTML: "", className: "" },
              "project-nav": { textContent: "", innerHTML: "", className: "" },
            };
            const document = {
              body: { dataset: { page: "index" }, querySelector: () => null },
              documentElement: { dataset: {} },
              getElementById: (id) => elements[id] || null,
              querySelector: () => null,
              querySelectorAll: () => [],
            };
            const window = {
              location: { search: "" },
              localStorage: { getItem: () => null, setItem: () => null },
            };
            const context = {
              console, document, window, URL, URLSearchParams, Map, Set,
              fetch: async () => ({ ok: true, json: async () => ({}) }),
              setTimeout, clearTimeout,
              requestAnimationFrame: () => 0,
              cancelAnimationFrame: () => {},
            };
            vm.createContext(context);
            const source = fs.readFileSync("__APP_JS__", "utf8").replace(/\\nboot\\(\\);\\s*$/, "\\n");
            vm.runInContext(source, context);
            assert.equal(context.renderDemoBadge({ demo: true }), '<span class="demo-badge">Demo</span>');
            assert.equal(context.renderDemoBadge({ demo: false }), "");
            context.state.data = {
              schema_version: "research-browser-v2",
              projects: [{ id: "DemoVisualAffordance", title: "Demo Visual Affordance", demo: true, overview: {} }],
              papers: [],
              rounds: [],
            };
            context.renderProjectsIndex();
            assert(elements["page-content"].innerHTML.includes("demo-badge"), elements["page-content"].innerHTML);
            """
        ).replace("__APP_JS__", (ROOT / "dashboard" / "app.js").as_posix())
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard.RelatedWorkLineageDashboardTest.test_demo_badge_rendering_is_escaped -v
```

Expected: FAIL because `renderDemoBadge` is undefined.

- [ ] **Step 3: Implement badge helper and use it**

Add after `statusPill`:

```javascript
function renderDemoBadge(project) {
  return project?.demo ? '<span class="demo-badge">Demo</span>' : "";
}
```

Update project list heading:

```javascript
<h2><a href="./project.html?project=${escapeAttr(project.id)}">${escapeHtml(displayProjectTitle(project))}</a>${renderDemoBadge(project)}</h2>
```

In `renderProjectWorkspace`, after `setHeader(...)`, set subtitle HTML for demo project:

```javascript
  setHeader("项目", displayProjectTitle(project), project.overview?.direction || "");
  if (project.demo && el.subtitle) {
    el.subtitle.className = "project-title-meta";
    el.subtitle.innerHTML = `
      ${renderDemoBadge(project)}
      <span>${escapeHtml(project.overview?.direction || "")}</span>
    `;
  }
```

- [ ] **Step 4: Style badge**

Add to `dashboard/styles.css` near status/chip styles:

```css
.demo-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 22px;
  margin-left: 8px;
  padding: 2px 8px;
  border: 1px solid rgba(37, 99, 235, 0.35);
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1;
  vertical-align: middle;
}

.project-title-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
```

Add light theme override if needed:

```css
:root[data-theme="light"] .demo-badge {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1e40af;
}
```

- [ ] **Step 5: Run dashboard tests**

Run:

```bash
python3 -m unittest tests.test_related_work_lineage_dashboard -v
node --check dashboard/app.js
```

Expected: PASS and `node --check` exits 0.

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.js dashboard/styles.css tests/test_related_work_lineage_dashboard.py
git commit -m "Show demo badge in dashboard"
```

## Task 5: Document Demo Project And Deletion

**Files:**
- Modify: `docs/guides/install.md`
- Modify: `docs/guides/dashboard.md`
- Modify: `docs/guides/workspace.md`
- Modify: `README.md`
- Modify: `tests/test_plugin_commands.py`

- [ ] **Step 1: Add failing docs test**

Append to `PluginCommandTests`:

```python
    def test_docs_explain_default_demo_project_and_deletion(self) -> None:
        install = (REPO / "docs" / "guides" / "install.md").read_text(encoding="utf-8")
        dashboard = (REPO / "docs" / "guides" / "dashboard.md").read_text(encoding="utf-8")
        workspace = (REPO / "docs" / "guides" / "workspace.md").read_text(encoding="utf-8")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for text in [install, dashboard, workspace, readme]:
            self.assertIn("DemoVisualAffordance", text)
        self.assertIn("--no-demo", install)
        self.assertIn("rm -rf wiki/projects/DemoVisualAffordance", workspace)
        self.assertIn("wiki/graphs/events/projects/DemoVisualAffordance.jsonl", workspace)
```

- [ ] **Step 2: Run docs test and verify failure**

Run:

```bash
python3 -m unittest tests.test_plugin_commands.PluginCommandTests.test_docs_explain_default_demo_project_and_deletion -v
```

Expected: FAIL because docs do not mention demo project.

- [ ] **Step 3: Update docs**

Add to `docs/guides/install.md` after init fallback:

````markdown
By default, initialization installs the deletable `DemoVisualAffordance` project so the dashboard has visible data immediately.

Clean workspace fallback:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH" --no-demo
```
````

Add to `docs/guides/workspace.md`:

````markdown
## Demo Project

New workspaces include `DemoVisualAffordance` by default. It is sanitized example data for learning the workflow and inspecting dashboard changes.

Delete it from a workspace:

```bash
rm -rf wiki/projects/DemoVisualAffordance
rm -f wiki/graphs/events/projects/DemoVisualAffordance.jsonl
python3 "$PLUGIN_ROOT/tools/build_dashboard_index.py" --repo "$PWD" --output .dashboard/index.json
```

The dashboard is read-only and does not delete projects.
````

Add one sentence to `docs/guides/dashboard.md`:

```markdown
Projects with `demo: true` display a `Demo` badge; this marks example data only.
```

Add one sentence to `README.md` quick start or feature list:

```markdown
Fresh workspaces include a deletable `DemoVisualAffordance` demo project; pass `--no-demo` to the init helper for an empty workspace.
```

- [ ] **Step 4: Run docs tests**

Run:

```bash
python3 -m unittest tests.test_plugin_commands -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/guides/install.md docs/guides/dashboard.md docs/guides/workspace.md README.md tests/test_plugin_commands.py
git commit -m "Document default demo project"
```

## Task 6: Final Integration Verification

**Files:**
- No new source files unless tests expose a defect.

- [ ] **Step 1: Build initialized workspace smoke**

Run:

```bash
tmp="$(mktemp -d)"
python3 tools/research_pilot_init.py "$tmp/workspace" --no-git
python3 tools/build_dashboard_index.py --repo "$tmp/workspace" --output .dashboard/index.json
python3 tools/related_work_lineage_cli.py validate --path "$tmp/workspace/wiki/projects/DemoVisualAffordance/literature-rounds/demo-affordance-lineage/related-work-lineage.json" --json
python3 tools/graph_validate.py --repo "$tmp/workspace" --project DemoVisualAffordance
```

Expected:

```text
Research Pilot workspace initialized:
```

Lineage validation JSON contains `"valid": true`. Graph validation exits 0.

- [ ] **Step 2: Run focused suite**

Run:

```bash
python3 -m unittest tests.test_demo_project tests.test_plugin_commands tests.test_dashboard_public tests.test_related_work_lineage_cli tests.test_related_work_lineage_dashboard -v
node --check dashboard/app.js
```

Expected: all tests pass.

- [ ] **Step 3: Run release check**

Run:

```bash
scripts/release_check.sh
```

Expected: exits 0 and prints `release check passed`.

- [ ] **Step 4: Inspect git diff and private token scan**

Run:

```bash
git diff --check
rg -n "/Users/""qing|Personal""ResearchWiki|CVPR""2026_VisualAffordance|Zotero/storage|AAAI2027|submission_""affordance\\.pdf" examples/workspaces/demo-visual-affordance docs README.md tools dashboard tests
```

Expected: `git diff --check` exits 0. `rg` exits 1 for no matches in committed demo tree; docs may mention token names only inside sanitization rules from design docs, not runtime demo files.

- [ ] **Step 5: Commit final fixes if needed**

If verification changed files, inspect and commit them with:

```bash
git status --short
git add docs/guides/install.md docs/guides/dashboard.md docs/guides/workspace.md README.md tools/research_pilot_init.py tools/build_dashboard_index.py dashboard/app.js dashboard/styles.css tests/test_demo_project.py tests/test_plugin_commands.py tests/test_dashboard_public.py tests/test_related_work_lineage_dashboard.py examples/workspaces/demo-visual-affordance
git commit -m "Harden demo project integration"
```

If no files changed, do not create an empty commit.

## Self-Review

Spec coverage:

- Built-in demo source: Task 1.
- Default copy and `--no-demo`: Task 2.
- Deletable model: Task 5.
- Dashboard demo badge: Tasks 3 and 4.
- Sanitization guard: Tasks 1 and 6.
- Lineage visibility: Tasks 1 and 6.

No parallel graph truth is introduced. Dashboard remains read-only. Demo data is copied into existing project and graph-event paths only.
