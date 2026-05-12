# Research Pilot Trial Defects Full Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve RP-001 through RP-013 from `docs/research-pilot-trial-defects.md` with a stage-aware, chat-first Research Pilot flow.

**Architecture:** Add small agent-facing helpers for workspace status, project shell creation, Zotero setup, plugin health, and job records. Update existing skills, workflow templates, and dashboard indexing so the user talks to the agent while tools provide reliable state inspection and execution. Preserve graph events as source of truth and keep dashboard read-only.

**Tech Stack:** Python 3 standard library, Markdown workflow files, Bash installer, unittest, local JSON/TOML-like config writing.

---

## Scope Boundary

This plan covers all defects RP-001 through RP-013.

The implementation must not:

- depend on Zotero MCP in user-facing flows;
- accept graph deltas without explicit human approval;
- turn dashboard into a writer;
- print Zotero API keys;
- require users to memorize CLI commands.

## File Structure

Create:

```text
tools/research_pilot_status.py
tools/project_shell_cli.py
tools/zotero_setup.py
tools/plugin_health.py
tools/job_records.py
tests/test_research_pilot_status.py
tests/test_project_shell_cli.py
tests/test_zotero_setup.py
tests/test_plugin_health.py
tests/test_job_records.py
```

Modify:

```text
tools/build_dashboard_index.py
tools/source_intake_cli.py
tools/zotero_bridge.py
tools/research_pilot_init.py
install.sh
commands/research-dashboard.md
commands/research-init.md
skills/research-pilot/SKILL.md
skills/research-pilot-first-run/SKILL.md
templates/workspace/.research-pilot/config.example.toml
templates/workspace/AGENTS.md
templates/workspace/wiki/_system/workflows/first-run.md
docs/guides/workspace.md
docs/guides/zotero.md
docs/guides/dashboard.md
docs/research-pilot-trial-defects.md
tests/test_dashboard_public.py
tests/test_source_intake_cli.py
tests/test_first_run_protocol.py
tests/test_plugin_commands.py
tests/test_hidden_installer.py
```

Responsibilities:

- `research_pilot_status.py`: read-only workspace, Zotero, read-model, project, and plugin stage detector.
- `project_shell_cli.py`: deterministic project shell file creator that does not create graph truth.
- `zotero_setup.py`: agent-facing Zotero `.env` setup/status, key validation, collection tree create/reuse, config persistence.
- `plugin_health.py`: local plugin install, link, command fallback, and update guidance report.
- `job_records.py`: durable execution-state records for long research tasks.
- `build_dashboard_index.py`: display project metadata, question semantics, jobs, and status without mutating truth.

## Task 1: Workspace Status Helper

**Files:**

- Create: `tools/research_pilot_status.py`
- Create: `tests/test_research_pilot_status.py`
- Modify: `skills/research-pilot/SKILL.md`
- Modify: `skills/research-pilot-first-run/SKILL.md`
- Modify: `templates/workspace/wiki/_system/workflows/first-run.md`

- [ ] **Step 1: Write failing status tests**

Create `tests/test_research_pilot_status.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from tools.research_pilot_status import inspect_workspace
from tools.research_pilot_init import main as init_workspace_main


class ResearchPilotStatusTest(unittest.TestCase):
    def test_plugin_repo_stage(self):
        result = inspect_workspace(Path("."))

        self.assertEqual(result["stage"], "plugin_repo")
        self.assertFalse(result["valid_workspace"])
        self.assertEqual(result["next_actions"][0]["id"], "initialize_workspace")

    def test_empty_workspace_stage_after_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])

            result = inspect_workspace(root)

        self.assertTrue(result["valid_workspace"])
        self.assertEqual(result["stage"], "empty_workspace")
        self.assertEqual(result["projects"], [])
        self.assertEqual(result["next_actions"][0]["id"], "create_project_shell")

    def test_project_shell_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\nmaturity_stage: project_shell\nhuman_review: pending\n---\n# Demo Project\n",
                encoding="utf-8",
            )

            result = inspect_workspace(root)

        self.assertEqual(result["stage"], "project_shell")
        self.assertEqual(result["projects"][0]["id"], "DemoProject")
        self.assertEqual(result["projects"][0]["title"], "Demo Project")
        self.assertEqual(result["next_actions"][0]["id"], "configure_zotero_or_add_baselines")

    def test_read_models_stale_when_events_newer_than_dashboard_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            events = root / "wiki" / "graphs" / "events" / "projects" / "DemoProject.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text('{"event_id":"E0"}\n', encoding="utf-8")
            dashboard = root / ".dashboard" / "index.json"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("{}", encoding="utf-8")
            events.touch()

            result = inspect_workspace(root)

        self.assertEqual(result["read_models"]["dashboard_index"], "stale")
        self.assertEqual(result["stage"], "read_models_stale")

    def test_status_json_is_serializable_and_masks_zotero_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            (root / ".env").write_text("ZOTERO_API_KEY=secret-value\n", encoding="utf-8")

            result = inspect_workspace(root)
            encoded = json.dumps(result)

        self.assertIn('"api_key_present": true', encoded)
        self.assertNotIn("secret-value", encoded)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run status tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_research_pilot_status -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.research_pilot_status'`.

- [ ] **Step 3: Implement `tools/research_pilot_status.py`**

Create `tools/research_pilot_status.py`:

```python
#!/usr/bin/env python3
"""Read-only Research Pilot workspace status for agent onboarding."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[text.find("\n", end + 4) + 1 :]
    data: Dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("\"'")
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key.strip()] = [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
        else:
            data[key.strip()] = value
    return data, body


def is_plugin_repo(root: Path) -> bool:
    return (
        (root / "install.sh").exists()
        and (root / "tools" / "research_pilot_init.py").exists()
        and (root / "skills" / "research-pilot" / "SKILL.md").exists()
    )


def is_workspace(root: Path) -> bool:
    return (
        (root / "AGENTS.md").exists()
        and (root / "wiki" / "index.md").exists()
        and (root / "wiki" / "log.md").exists()
        and (root / ".research-pilot").exists()
    )


def read_env_flags(root: Path) -> Dict[str, Any]:
    env_path = root / ".env"
    api_key_present = False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("ZOTERO_API_KEY=") and stripped.split("=", 1)[1].strip():
                api_key_present = True
                break
    return {
        "configured": False,
        "api_key_present": api_key_present,
        "api_key_valid": False,
        "library_type": "",
        "library_id": "",
        "mode": "env-present" if api_key_present else "not-configured",
    }


def collect_projects(root: Path) -> List[Dict[str, Any]]:
    projects_root = root / "wiki" / "projects"
    if not projects_root.exists():
        return []
    projects: List[Dict[str, Any]] = []
    for project_dir in sorted(path for path in projects_root.iterdir() if path.is_dir()):
        overview = project_dir / "overview.md"
        frontmatter: Dict[str, Any] = {}
        if overview.exists():
            frontmatter, _ = parse_frontmatter(overview.read_text(encoding="utf-8"))
        title = str(frontmatter.get("display_title") or frontmatter.get("title") or project_dir.name)
        maturity_stage = str(frontmatter.get("maturity_stage") or "project_shell")
        projects.append(
            {
                "id": project_dir.name,
                "title": title,
                "maturity_stage": maturity_stage,
                "has_overview": overview.exists(),
                "has_graph_report": (project_dir / "project-understanding-graph.md").exists(),
            }
        )
    return projects


def count_files(root: Path, pattern: str) -> int:
    base = root / "wiki"
    if not base.exists():
        return 0
    return sum(1 for _ in base.glob(pattern))


def newest_mtime(paths: List[Path]) -> Optional[float]:
    existing = [path.stat().st_mtime for path in paths if path.exists()]
    return max(existing) if existing else None


def read_model_status(root: Path) -> Dict[str, str]:
    dashboard = root / ".dashboard" / "index.json"
    graph_db = root / "wiki" / "graphs" / "graph.db"
    snapshots = root / "wiki" / "graphs" / "snapshots"
    event_paths = list((root / "wiki" / "graphs" / "events").glob("**/*.jsonl"))
    event_mtime = newest_mtime(event_paths)

    def status(path: Path) -> str:
        if not path.exists():
            return "missing"
        if event_mtime is not None and path.stat().st_mtime < event_mtime:
            return "stale"
        return "fresh"

    snapshot_status = "missing"
    if snapshots.exists():
        snapshot_files = list(snapshots.glob("**/*.json"))
        snapshot_status = "fresh" if snapshot_files else "missing"
        snapshot_mtime = newest_mtime(snapshot_files)
        if event_mtime is not None and snapshot_mtime is not None and snapshot_mtime < event_mtime:
            snapshot_status = "stale"

    return {
        "dashboard_index": status(dashboard),
        "graph_db": status(graph_db),
        "snapshots": snapshot_status,
    }


def plugin_status() -> Dict[str, Any]:
    home = Path.home()
    candidates = [home / ".research-pilot" / "repo", home / ".research-pilot-plugin"]
    source_path = next((path for path in candidates if path.exists()), Path(""))
    manifest = source_path / ".codex-plugin" / "plugin.json" if source_path else Path("")
    version = ""
    if manifest.exists():
        try:
            version = str(json.loads(manifest.read_text(encoding="utf-8")).get("version") or "")
        except json.JSONDecodeError:
            version = ""
    return {
        "source_path": str(source_path) if source_path else "",
        "version": version,
        "commands_visible": "unknown",
        "dashboard_fallback_available": bool(source_path and (source_path / "tools" / "research_browser_server.py").exists()),
    }


def next_actions_for(stage: str) -> List[Dict[str, str]]:
    actions = {
        "plugin_repo": [
            {"id": "initialize_workspace", "label": "Initialize a private workspace", "reason": "Current directory is plugin source."}
        ],
        "plain_directory": [
            {"id": "initialize_workspace", "label": "Initialize Research Pilot here or elsewhere", "reason": "No workspace markers found."}
        ],
        "empty_workspace": [
            {"id": "create_project_shell", "label": "Create first project shell", "reason": "Workspace has no projects yet."}
        ],
        "project_shell": [
            {"id": "configure_zotero_or_add_baselines", "label": "Configure Zotero or add baseline anchors", "reason": "Project shell exists without graph truth."}
        ],
        "read_models_stale": [
            {"id": "rebuild_read_models", "label": "Rebuild read models", "reason": "Graph events are newer than generated views."}
        ],
        "project_has_graph": [
            {"id": "inspect_graph", "label": "Inspect current graph and next action", "reason": "Project graph exists."}
        ],
    }
    return actions.get(stage, [{"id": "inspect_workspace", "label": "Inspect workspace", "reason": "Workspace state needs review."}])


def classify(root: Path, projects: List[Dict[str, Any]], read_models: Dict[str, str]) -> str:
    if is_plugin_repo(root):
        return "plugin_repo"
    if not is_workspace(root):
        return "plain_directory"
    if any(value == "stale" for value in read_models.values()):
        return "read_models_stale"
    if not projects:
        return "empty_workspace"
    if any(project.get("has_graph_report") for project in projects):
        return "project_has_graph"
    return "project_shell"


def inspect_workspace(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    projects = collect_projects(root) if is_workspace(root) else []
    read_models = read_model_status(root) if is_workspace(root) else {
        "dashboard_index": "missing",
        "graph_db": "missing",
        "snapshots": "missing",
    }
    stage = classify(root, projects, read_models)
    return {
        "valid_workspace": is_workspace(root),
        "stage": stage,
        "root": str(root),
        "projects": projects,
        "open_deltas": count_files(root, "graphs/events/deltas/*.jsonl"),
        "paper_dossiers": count_files(root, "projects/*/papers/*/index.md"),
        "read_models": read_models,
        "zotero": read_env_flags(root),
        "plugin": plugin_status(),
        "next_actions": next_actions_for(stage),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Research Pilot workspace status.")
    parser.add_argument("--repo", default=".", help="Workspace or plugin path. Default: current directory.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_workspace(Path(args.repo))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run status tests**

Run:

```bash
python3 -m unittest tests.test_research_pilot_status -v
```

Expected: PASS.

- [ ] **Step 5: Update router and first-run language**

Edit `skills/research-pilot/SKILL.md`, `skills/research-pilot-first-run/SKILL.md`, and `templates/workspace/wiki/_system/workflows/first-run.md` so first inspection says:

```text
Before suggesting next actions, run:

python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json

Summarize the returned stage in chat. Offer at most two next actions. Do not mutate graph truth during status inspection.
```

Replace wording that says first-run must immediately reach first graph update with:

```text
If the user only has a venue, broad direction, or baseline-paper need, create a project shell first. Defer the first graph delta until the user provides a real question, claim, evidence pressure, paper synthesis, or experiment result.
```

- [ ] **Step 6: Run protocol tests**

Run:

```bash
python3 -m unittest tests.test_first_run_protocol tests.test_research_pilot_status -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/research_pilot_status.py tests/test_research_pilot_status.py skills/research-pilot/SKILL.md skills/research-pilot-first-run/SKILL.md templates/workspace/wiki/_system/workflows/first-run.md
git commit -m "feat: add stage-aware workspace status"
```

## Task 2: Project Shell Before Graph Truth

**Files:**

- Create: `tools/project_shell_cli.py`
- Create: `tests/test_project_shell_cli.py`
- Modify: `templates/workspace/.research-pilot/config.example.toml`
- Modify: `templates/workspace/AGENTS.md`
- Modify: `tests/test_first_run_protocol.py`

- [ ] **Step 1: Write failing project shell tests**

Create `tests/test_project_shell_cli.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tools.project_shell_cli import create_project_shell
from tools.research_pilot_init import main as init_workspace_main


class ProjectShellCliTest(unittest.TestCase):
    def test_create_project_shell_without_graph_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])

            result = create_project_shell(
                root,
                project_id="AAAI2027Affordance",
                display_title="AAAI 2027 Affordance Estimation",
                target_venue="AAAI 2027",
                maturity_stage="project_shell",
                research_direction="Affordance estimation from visual observations.",
                baseline_anchors=["Gibson 1979", "Do et al. 2018"],
                seed_questions=["Which baselines define the contribution bar?"],
                search_questions=["Find affordance estimation baselines for AAAI."],
                overwrite=False,
            )

            overview = root / "wiki" / "projects" / "AAAI2027Affordance" / "overview.md"
            query_pack = root / "wiki" / "projects" / "AAAI2027Affordance" / "project-query-pack.md"
            graph_events = root / "wiki" / "graphs" / "events" / "projects" / "AAAI2027Affordance.jsonl"

        self.assertTrue(result["created"])
        self.assertTrue(overview.exists())
        self.assertTrue(query_pack.exists())
        self.assertFalse(graph_events.exists())
        text = overview.read_text(encoding="utf-8")
        self.assertIn('display_title: "AAAI 2027 Affordance Estimation"', text)
        self.assertIn('target_venue: "AAAI 2027"', text)
        self.assertIn("maturity_stage: project_shell", text)
        self.assertIn("## Seed Questions", text)
        self.assertIn("Which baselines define the contribution bar?", text)

    def test_existing_shell_is_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_workspace_main([str(root), "--no-git"])
            first = create_project_shell(root, "Demo", "Demo", "", "project_shell", "First", [], [], [], False)
            second = create_project_shell(root, "Demo", "Demo Changed", "", "project_shell", "Second", [], [], [], False)
            overview = root / "wiki" / "projects" / "Demo" / "overview.md"

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertIn("First", overview.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run project shell tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_project_shell_cli -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.project_shell_cli'`.

- [ ] **Step 3: Implement `tools/project_shell_cli.py`**

Create `tools/project_shell_cli.py`:

```python
#!/usr/bin/env python3
"""Create early Research Pilot project shells without graph truth."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


VALID_MATURITY_STAGES = {
    "project_shell",
    "baseline_collection",
    "question_forming",
    "graph_started",
    "active_research",
    "archived",
}


def quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(values: List[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(quote(value) for value in values) + "]"


def bullet_lines(values: List[str], fallback: str) -> str:
    items = values or [fallback]
    return "\n".join(f"- {item}" for item in items)


def normalize_project_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", value.strip().replace(" ", "-"))
    return cleaned or "Project"


def render_overview(
    *,
    project_id: str,
    display_title: str,
    target_venue: str,
    maturity_stage: str,
    research_direction: str,
    baseline_anchors: List[str],
    seed_questions: List[str],
    search_questions: List[str],
) -> str:
    today = date.today().isoformat()
    return f"""---
title: {quote(display_title)}
type: project-overview
project_id: {project_id}
display_title: {quote(display_title)}
target_venue: {quote(target_venue)}
maturity_stage: {maturity_stage}
research_direction: {quote(research_direction)}
baseline_anchors: {yaml_list(baseline_anchors)}
human_review: pending
created: {today}
updated: {today}
---

# {display_title}

## Project Direction

{research_direction}

## Maturity Stage

{maturity_stage}

## Target Venue

{target_venue or "Not specified yet."}

## Baseline Anchors

{bullet_lines(baseline_anchors, "No baseline anchors captured yet.")}

## Seed Questions

{bullet_lines(seed_questions, "What should this project clarify before graph truth starts?")}

## Search Questions

{bullet_lines(search_questions, "Which papers should anchor this project?")}

## Accepted Questions

No accepted project questions yet. Accepted questions come from human-approved graph updates.
"""


def render_query_pack(display_title: str, research_direction: str, search_questions: List[str]) -> str:
    today = date.today().isoformat()
    return f"""---
title: {quote(display_title + " Query Pack")}
type: project-query-pack
human_review: pending
created: {today}
updated: {today}
---

# {display_title} Query Pack

## First Search Contract

{research_direction}

## Seed Search Prompts

{bullet_lines(search_questions, "Find baseline papers that define the contribution bar.")}
"""


def create_project_shell(
    root: Path,
    project_id: str,
    display_title: str,
    target_venue: str,
    maturity_stage: str,
    research_direction: str,
    baseline_anchors: List[str],
    seed_questions: List[str],
    search_questions: List[str],
    overwrite: bool = False,
) -> Dict[str, object]:
    if maturity_stage not in VALID_MATURITY_STAGES:
        raise ValueError(f"Invalid maturity_stage: {maturity_stage}")
    root = Path(root).expanduser().resolve()
    project_id = normalize_project_id(project_id)
    project_dir = root / "wiki" / "projects" / project_id
    overview = project_dir / "overview.md"
    query_pack = project_dir / "project-query-pack.md"
    already_exists = overview.exists()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "papers").mkdir(exist_ok=True)
    (project_dir / "experiment-proposals").mkdir(exist_ok=True)
    (project_dir / "papers" / ".gitkeep").touch()
    (project_dir / "experiment-proposals" / ".gitkeep").touch()

    if not overview.exists() or overwrite:
        overview.write_text(
            render_overview(
                project_id=project_id,
                display_title=display_title,
                target_venue=target_venue,
                maturity_stage=maturity_stage,
                research_direction=research_direction,
                baseline_anchors=baseline_anchors,
                seed_questions=seed_questions,
                search_questions=search_questions,
            ),
            encoding="utf-8",
        )
    if not query_pack.exists() or overwrite:
        query_pack.write_text(render_query_pack(display_title, research_direction, search_questions), encoding="utf-8")
    decisions = project_dir / "decisions.md"
    if not decisions.exists() or overwrite:
        decisions.write_text(f"# {display_title} Decisions\n\nNo human-approved decisions yet.\n", encoding="utf-8")
    return {
        "created": not already_exists or overwrite,
        "project": project_id,
        "path": str(project_dir),
        "graph_events_created": False,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Research Pilot project shell without graph truth.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--project", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--target-venue", default="")
    parser.add_argument("--maturity-stage", default="project_shell", choices=sorted(VALID_MATURITY_STAGES))
    parser.add_argument("--direction", required=True)
    parser.add_argument("--baseline-anchor", action="append", default=[])
    parser.add_argument("--seed-question", action="append", default=[])
    parser.add_argument("--search-question", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = create_project_shell(
        Path(args.repo),
        args.project,
        args.title,
        args.target_venue,
        args.maturity_stage,
        args.direction,
        args.baseline_anchor,
        args.seed_question,
        args.search_question,
        args.overwrite,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Update workspace config and agent instructions**

Append to `templates/workspace/.research-pilot/config.example.toml`:

```toml

[project_lifecycle]
default_maturity_stage = "project_shell"
allow_project_shell_without_graph = true
```

Add to `templates/workspace/AGENTS.md` under Human Gate:

```markdown
## Project Lifecycle

Early projects may start as project shells with venue, broad direction, baseline anchors, and setup prompts.
Project shells are not graph truth.
Create graph deltas only after the human supplies or approves a graph-level question, claim, evidence pressure, paper synthesis, or experiment result.
```

- [ ] **Step 5: Extend first-run protocol test**

Modify `tests/test_first_run_protocol.py` so `test_public_repo_contains_first_run_skill_and_workspace_workflow` also asserts:

```python
self.assertIn("project shell", skill.read_text(encoding="utf-8"))
self.assertIn("project shell", workflow.read_text(encoding="utf-8"))
self.assertIn("defer", workflow.read_text(encoding="utf-8").lower())
```

- [ ] **Step 6: Run project shell tests**

Run:

```bash
python3 -m unittest tests.test_project_shell_cli tests.test_first_run_protocol -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/project_shell_cli.py tests/test_project_shell_cli.py templates/workspace/.research-pilot/config.example.toml templates/workspace/AGENTS.md tests/test_first_run_protocol.py
git commit -m "feat: support project shells before graph truth"
```

## Task 3: Dashboard Display Metadata And Question Semantics

**Files:**

- Modify: `tools/build_dashboard_index.py`
- Modify: `tests/test_dashboard_public.py`
- Modify: `docs/guides/dashboard.md`

- [ ] **Step 1: Add failing dashboard tests**

Append to `DashboardPublicTest` in `tests/test_dashboard_public.py`:

```python
    def test_project_card_prefers_overview_display_title_over_query_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Overview\ndisplay_title: Demo Display Title\ntype: project-overview\nmaturity_stage: project_shell\n---\n"
                "# Demo Display Title\n\n## Project Direction\n\nBroad direction.\n\n## Seed Questions\n\n- Setup prompt\n",
                encoding="utf-8",
            )
            (project / "project-query-pack.md").write_text(
                "---\ntitle: Demo Query Pack\ntype: project-query-pack\n---\n# Demo Query Pack\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["projects"][0]["title"], "Demo Display Title")
        self.assertEqual(index["projects"][0]["overview"]["seed_questions"], ["Setup prompt"])
        self.assertEqual(index["projects"][0]["overview"]["accepted_questions"], [])
        self.assertNotIn("Setup prompt", index["projects"][0]["overview"]["current_questions"])

    def test_dashboard_accepted_questions_come_from_graph_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "wiki" / "projects" / "DemoProject"
            project.mkdir(parents=True)
            (project / "overview.md").write_text(
                "---\ntitle: Demo Project\ntype: project-overview\n---\n# Demo\n\n## Search Questions\n\n- Search prompt\n",
                encoding="utf-8",
            )
            (project / "project-understanding-graph.md").write_text(
                "---\ntitle: Demo Graph\ntype: project-understanding-graph\n---\n"
                "# Demo Graph\n\n## Project Questions\n\n"
                "| ID | Question | Role | Status | Confidence | Human Review | Source Refs | Bounds |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q0 | Does the model encode interaction knowledge? | main | active | medium | accepted | human | none |\n",
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(
            index["projects"][0]["overview"]["accepted_questions"],
            ["Does the model encode interaction knowledge?"],
        )
        self.assertEqual(index["projects"][0]["overview"]["search_questions"], ["Search prompt"])
```

- [ ] **Step 2: Run dashboard tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_dashboard_public -v
```

Expected: FAIL because `collect_projects` uses `project-query-pack.md` first and does not return `seed_questions`, `search_questions`, or `accepted_questions`.

- [ ] **Step 3: Add dashboard helpers**

In `tools/build_dashboard_index.py`, add after `collect_core_files`:

```python
def section_bullets(body: str, heading: str) -> List[str]:
    section = extract_section(body, heading)
    return [
        line.strip("- ").strip()
        for line in section.splitlines()
        if line.strip().startswith("- ") and line.strip("- ").strip()
    ]


def accepted_questions_from_graph(project_id: str, project_graphs: List[Dict[str, Any]]) -> List[str]:
    for graph in project_graphs:
        if graph.get("project") != project_id:
            continue
        questions = []
        for node in graph.get("nodes", []):
            if node.get("kind") != "question":
                continue
            human_review = str(node.get("human_review") or "").lower()
            status = str(node.get("status") or "").lower()
            if human_review in {"accepted", "approved"} or status in {"active", "accepted"}:
                label = str(node.get("label") or "").strip()
                if label:
                    questions.append(label)
        return questions
    return []
```

- [ ] **Step 4: Change `collect_projects` signature and title source**

Change:

```python
def collect_projects(root: Path) -> List[Dict[str, Any]]:
```

to:

```python
def collect_projects(root: Path, project_graphs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
```

Inside it, replace:

```python
query_pack = project_dir / "project-query-pack.md"
overview_file = query_pack if query_pack.exists() else project_dir / "overview.md"
```

with:

```python
project_graphs = project_graphs or []
overview_file = project_dir / "overview.md"
query_pack = project_dir / "project-query-pack.md"
if not overview_file.exists() and query_pack.exists():
    overview_file = query_pack
```

Replace the `overview` object with:

```python
seed_questions = section_bullets(body, "Seed Questions")
search_questions = section_bullets(body, "Search Questions")
accepted_questions = section_bullets(body, "Accepted Questions")
if not accepted_questions:
    accepted_questions = accepted_questions_from_graph(project_dir.name, project_graphs)
current_questions = accepted_questions
if not current_questions:
    current_questions = section_bullets(body, "Current Questions")

"title": scalar(frontmatter, "display_title") or scalar(frontmatter, "title", project_dir.name),
"overview": {
    "direction": direction,
    "current_questions": current_questions,
    "seed_questions": seed_questions,
    "search_questions": search_questions,
    "accepted_questions": accepted_questions,
    "search_contract": search_contract,
    "human_gates": [
        line.strip("- ").strip()
        for line in human_gates_section.splitlines()
        if line.strip().startswith("- ")
    ],
},
```

- [ ] **Step 5: Change build order**

In `build_index`, change:

```python
projects = collect_projects(root)
project_graphs = collect_project_graphs(root)
```

to:

```python
project_graphs = collect_project_graphs(root)
projects = collect_projects(root, project_graphs)
```

- [ ] **Step 6: Update dashboard guide**

Add to `docs/guides/dashboard.md`:

```markdown
## Project Display Semantics

Project cards use `overview.md` display metadata first. `project-query-pack.md` is an internal planning artifact and must not determine the project title.

Dashboard question labels distinguish:

- `seed_questions`: setup prompts for early project formation;
- `search_questions`: prompts for finding or collecting baseline papers;
- `accepted_questions`: human-approved graph questions or explicitly approved overview content.

Seed and search prompts are not project truth.
```

- [ ] **Step 7: Run dashboard tests**

Run:

```bash
python3 -m unittest tests.test_dashboard_public -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/build_dashboard_index.py tests/test_dashboard_public.py docs/guides/dashboard.md
git commit -m "fix: separate dashboard project display semantics"
```

## Task 4: Agent-Facing Zotero Setup And Status

**Files:**

- Create: `tools/zotero_setup.py`
- Create: `tests/test_zotero_setup.py`
- Modify: `tools/source_intake_cli.py`
- Modify: `tests/test_source_intake_cli.py`
- Modify: `docs/guides/zotero.md`
- Modify: `skills/research-pilot/SKILL.md`

- [ ] **Step 1: Write failing Zotero setup tests**

Create `tests/test_zotero_setup.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tools.zotero_setup import prepare_env_files, zotero_status


class ZoteroSetupTest(unittest.TestCase):
    def test_prepare_env_files_creates_example_and_local_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = prepare_env_files(root)

            env_example = root / ".env.example"
            env = root / ".env"

        self.assertTrue(result["env_example_created"])
        self.assertTrue(result["env_created"])
        self.assertIn("ZOTERO_API_KEY=", env_example.read_text(encoding="utf-8"))
        self.assertIn("ZOTERO_API_KEY=", env.read_text(encoding="utf-8"))

    def test_status_reads_workspace_env_without_printing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("ZOTERO_API_KEY=secret-value\n", encoding="utf-8")

            result = zotero_status(root, validate=False)

        self.assertTrue(result["api_key_present"])
        self.assertEqual(result["mode"], "env-present")
        self.assertNotIn("secret-value", str(result))

    def test_status_uses_configured_library_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / ".research-pilot" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[zotero]\nlibrary_type = "users"\nlibrary_id = "123456"\n', encoding="utf-8")
            (root / ".env").write_text("ZOTERO_API_KEY=secret-value\n", encoding="utf-8")

            result = zotero_status(root, validate=False)

        self.assertEqual(result["library_type"], "users")
        self.assertEqual(result["library_id"], "123456")
        self.assertFalse(result["api_key_valid"])
```

- [ ] **Step 2: Run Zotero setup tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_zotero_setup -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.zotero_setup'`.

- [ ] **Step 3: Implement `tools/zotero_setup.py` status foundation**

Create `tools/zotero_setup.py`:

```python
#!/usr/bin/env python3
"""Agent-facing Zotero setup/status helpers for Research Pilot."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


ENV_TEMPLATE = """# Research Pilot local secrets
# Paste a Zotero key created at https://www.zotero.org/settings/keys/new
ZOTERO_API_KEY=
"""


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_simple_toml(path: Path) -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}
    section = ""
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            continue
        if "=" in line and section:
            key, value = line.split("=", 1)
            data.setdefault(section, {})[key.strip()] = value.strip().strip('"').strip("'")
    return data


def prepare_env_files(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    env_example = root / ".env.example"
    env = root / ".env"
    env_example_created = not env_example.exists()
    env_created = not env.exists()
    if env_example_created:
        env_example.write_text(ENV_TEMPLATE, encoding="utf-8")
    if env_created:
        env.write_text(ENV_TEMPLATE, encoding="utf-8")
    return {
        "env_example_created": env_example_created,
        "env_created": env_created,
        "env_example": str(env_example),
        "env": str(env),
        "key_url": "https://www.zotero.org/settings/keys/new",
    }


def validate_key(api_key: str) -> Dict[str, str]:
    request = urllib.request.Request("https://api.zotero.org/keys/current")
    request.add_header("Zotero-API-Key", api_key)
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    user_id = str(payload.get("userID") or payload.get("userId") or payload.get("library", {}).get("id") or "")
    return {
        "library_type": "users",
        "library_id": user_id,
    }


def zotero_status(root: Path, *, validate: bool = True) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    env = load_env_file(root / ".env")
    config = parse_simple_toml(root / ".research-pilot" / "config.toml")
    zotero_config = config.get("zotero", {})
    api_key = env.get("ZOTERO_API_KEY", "")
    result: Dict[str, Any] = {
        "configured": False,
        "api_key_present": bool(api_key),
        "api_key_valid": False,
        "library_type": zotero_config.get("library_type", ""),
        "library_id": zotero_config.get("library_id", ""),
        "mode": "env-present" if api_key else "not-configured",
        "key_url": "https://www.zotero.org/settings/keys/new",
    }
    if api_key and validate:
        try:
            validation = validate_key(api_key)
            result.update(validation)
            result["api_key_valid"] = bool(result.get("library_id"))
            result["configured"] = result["api_key_valid"]
            result["mode"] = "zotero-web-api" if result["api_key_valid"] else "env-present"
        except Exception as exc:
            result["error"] = f"{exc.__class__.__name__}: key validation failed"
    elif api_key and result.get("library_id"):
        result["configured"] = True
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Agent-facing Zotero setup/status helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare-env")
    prepare.add_argument("--repo", default=".")
    prepare.add_argument("--json", action="store_true")
    status = subparsers.add_parser("status")
    status.add_argument("--repo", default=".")
    status.add_argument("--no-validate", action="store_true")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "prepare-env":
        result = prepare_env_files(Path(args.repo))
    else:
        result = zotero_status(Path(args.repo), validate=not args.no_validate)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Wire source intake status to the shared helper**

Modify `tools/source_intake_cli.py`:

Add import:

```python
from tools.zotero_setup import zotero_status as workspace_zotero_status
```

Change:

```python
def zotero_status() -> Dict[str, Any]:
```

to:

```python
def zotero_status(repo: str = ".") -> Dict[str, Any]:
    return workspace_zotero_status(Path(repo), validate=False)
```

In `main`, add `--repo` to status parser:

```python
status.add_argument("--repo", default=".")
```

Change result selection to:

```python
result = zotero_status(args.repo) if args.command == "status" else intake_source(args)
```

- [ ] **Step 5: Update source intake tests**

Add to `tests/test_source_intake_cli.py`:

```python
    def test_zotero_status_reads_workspace_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("ZOTERO_API_KEY=secret-value\n", encoding="utf-8")

            status = zotero_status(str(root))

        self.assertTrue(status["api_key_present"])
        self.assertNotIn("secret-value", str(status))
```

- [ ] **Step 6: Update Zotero docs and skill wording**

In `docs/guides/zotero.md`, add:

```markdown
## Agent-Guided Setup

The user-facing flow is conversational. The agent may use `tools/zotero_setup.py` internally, but users should not need to memorize commands.

Flow:

1. Agent creates `.env.example` and `.env` when missing.
2. User creates a Zotero key at `https://www.zotero.org/settings/keys/new`.
3. User pastes only `ZOTERO_API_KEY` into local `.env`.
4. Agent validates the key without printing it.
5. Agent writes non-secret library metadata to `.research-pilot/config.toml`.
```

In `skills/research-pilot/SKILL.md`, add under Zotero routing:

```text
For Zotero setup, use the agent-facing helper:

python3 "$PLUGIN_ROOT/tools/zotero_setup.py" prepare-env --repo "$WORKSPACE_PATH" --json
python3 "$PLUGIN_ROOT/tools/zotero_setup.py" status --repo "$WORKSPACE_PATH" --json

Do not print API keys. Do not mention Zotero MCP as part of the normal user flow.
```

- [ ] **Step 7: Run Zotero status tests**

Run:

```bash
python3 -m unittest tests.test_zotero_setup tests.test_source_intake_cli -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/zotero_setup.py tests/test_zotero_setup.py tools/source_intake_cli.py tests/test_source_intake_cli.py docs/guides/zotero.md skills/research-pilot/SKILL.md
git commit -m "feat: add agent-facing Zotero setup status"
```

## Task 5: Zotero Collection Tree Create/Reuse

**Files:**

- Modify: `tools/zotero_setup.py`
- Modify: `tools/zotero_bridge.py`
- Modify: `tests/test_zotero_setup.py`
- Modify: `docs/guides/zotero.md`

- [ ] **Step 1: Add failing collection tree tests**

Append to `tests/test_zotero_setup.py`:

```python
from tools.zotero_setup import ensure_collection_tree, write_zotero_config


class FakeCollectionClient:
    def __init__(self, collections=None):
        self.collections = list(collections or [])
        self.created = []

    def fetch_collections(self):
        return self.collections

    def create_collection(self, name, parent_collection=""):
        key = f"KEY{len(self.collections) + 1:03d}"
        record = {"key": key, "data": {"key": key, "name": name, "parentCollection": parent_collection or False}}
        self.collections.append(record)
        self.created.append((name, parent_collection, key))
        return record


class ZoteroCollectionTreeTest(unittest.TestCase):
    def test_ensure_collection_tree_creates_standard_tree(self):
        client = FakeCollectionClient()

        result = ensure_collection_tree(client)

        names = [item[0] for item in client.created]
        self.assertEqual(
            names,
            ["Research_Pilot", "00 Inbox", "10 Projects", "20 Research Areas", "30 Review Campaigns", "90 Archive"],
        )
        self.assertEqual(result["root_collection_key"], "KEY001")
        self.assertEqual(result["projects_collection_key"], "KEY003")

    def test_ensure_collection_tree_reuses_existing_root(self):
        client = FakeCollectionClient(
            [{"key": "ROOT1", "data": {"key": "ROOT1", "name": "Research_Pilot", "parentCollection": False}}]
        )

        result = ensure_collection_tree(client)

        self.assertEqual(result["root_collection_key"], "ROOT1")
        self.assertNotIn(("Research_Pilot", "", "KEY002"), client.created)

    def test_write_zotero_config_persists_non_secret_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_zotero_config(
                root,
                {
                    "library_type": "users",
                    "library_id": "123456",
                    "root_collection_key": "ROOT1",
                },
            )
            text = (root / ".research-pilot" / "config.toml").read_text(encoding="utf-8")

        self.assertIn('library_type = "users"', text)
        self.assertIn('library_id = "123456"', text)
        self.assertIn('root_collection_key = "ROOT1"', text)
        self.assertNotIn("ZOTERO_API_KEY", text)
```

- [ ] **Step 2: Run collection tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_zotero_setup -v
```

Expected: FAIL because `ensure_collection_tree` and `write_zotero_config` do not exist.

- [ ] **Step 3: Add collection create API to Zotero client**

In `tools/zotero_bridge.py`, add method to `ZoteroClient` after `fetch_collections`:

```python
    def create_collection(self, name: str, parent_collection: str = "") -> Dict[str, Any]:
        payload = [
            {
                "name": name,
                "parentCollection": parent_collection or False,
            }
        ]
        request = urllib.request.Request(
            f"{self.base_url}/collections",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        if self.api_key:
            request.add_header("Zotero-API-Key", self.api_key)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            created = json.loads(response.read().decode("utf-8"))
        successful = created.get("successful", {}) if isinstance(created, dict) else {}
        if successful:
            first = successful[sorted(successful.keys())[0]]
            key = str(first.get("key") or "")
            return {"key": key, "data": {"key": key, "name": name, "parentCollection": parent_collection or False}}
        raise ValueError(f"Zotero collection creation failed for {name}")
```

- [ ] **Step 4: Implement tree helpers**

In `tools/zotero_setup.py`, add:

```python
COLLECTION_TREE = [
    ("inbox_collection_key", "00 Inbox"),
    ("projects_collection_key", "10 Projects"),
    ("areas_collection_key", "20 Research Areas"),
    ("campaigns_collection_key", "30 Review Campaigns"),
    ("archive_collection_key", "90 Archive"),
]


def collection_name(record: Dict[str, Any]) -> str:
    data = record.get("data", record)
    return str(data.get("name") or "")


def collection_key(record: Dict[str, Any]) -> str:
    data = record.get("data", record)
    return str(data.get("key") or record.get("key") or "")


def collection_parent(record: Dict[str, Any]) -> str:
    data = record.get("data", record)
    parent = data.get("parentCollection")
    return "" if parent in (False, None, "") else str(parent)


def find_collection(collections: List[Dict[str, Any]], name: str, parent: str = "") -> Dict[str, Any]:
    for collection in collections:
        if collection_name(collection) == name and collection_parent(collection) == parent:
            return collection
    return {}


def ensure_collection_tree(client: Any) -> Dict[str, str]:
    collections = client.fetch_collections()
    root = find_collection(collections, "Research_Pilot")
    if not root:
        root = client.create_collection("Research_Pilot", "")
        collections = client.fetch_collections()
    root_key = collection_key(root)
    result = {"root_collection_key": root_key}
    for config_key, name in COLLECTION_TREE:
        existing = find_collection(collections, name, root_key)
        if not existing:
            existing = client.create_collection(name, root_key)
            collections = client.fetch_collections()
        result[config_key] = collection_key(existing)
    return result


def write_zotero_config(root: Path, values: Dict[str, str]) -> None:
    root = Path(root).expanduser().resolve()
    config = root / ".research-pilot" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    merged = parse_simple_toml(config)
    zotero = dict(merged.get("zotero", {}))
    zotero.update({key: str(value) for key, value in values.items() if value})
    lines = ["[zotero]", "enabled = true"]
    for key in sorted(key for key in zotero if key != "enabled"):
        lines.append(f'{key} = "{zotero[key]}"')
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 5: Add CLI `ensure-collections`**

In `tools/zotero_setup.py`, add subparser:

```python
collections = subparsers.add_parser("ensure-collections")
collections.add_argument("--repo", default=".")
collections.add_argument("--json", action="store_true")
```

Add command branch:

```python
elif args.command == "ensure-collections":
    from tools.zotero_bridge import ZoteroClient
    status = zotero_status(Path(args.repo), validate=True)
    if not status.get("api_key_valid"):
        result = {**status, "error": "Zotero API key is not valid"}
    else:
        api_key = load_env_file(Path(args.repo) / ".env").get("ZOTERO_API_KEY", "")
        client = ZoteroClient(
            library_id=status["library_id"],
            library_type=status["library_type"],
            api_key=api_key,
        )
        tree = ensure_collection_tree(client)
        write_zotero_config(Path(args.repo), {**status, **tree})
        result = {**status, **tree, "configured": True}
```

- [ ] **Step 6: Update Zotero guide collection flow**

Add to `docs/guides/zotero.md`:

```markdown
## Standard Collection Tree

After the API key validates, the agent asks before creating or reusing Zotero collections.

Standard tree:

```text
Research_Pilot/
  00 Inbox
  10 Projects
  20 Research Areas
  30 Review Campaigns
  90 Archive
```

Collection keys are stored in `.research-pilot/config.toml`. API keys stay only in `.env`.
```

- [ ] **Step 7: Run Zotero setup and bridge tests**

Run:

```bash
python3 -m unittest tests.test_zotero_setup tests.test_zotero_bridge_public -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/zotero_setup.py tools/zotero_bridge.py tests/test_zotero_setup.py docs/guides/zotero.md
git commit -m "feat: manage Zotero collection tree"
```

## Task 6: Plugin Health And Dashboard Command Fallback

**Files:**

- Create: `tools/plugin_health.py`
- Create: `tests/test_plugin_health.py`
- Modify: `commands/research-dashboard.md`
- Modify: `commands/research-init.md`
- Modify: `install.sh`
- Modify: `tests/test_plugin_commands.py`
- Modify: `tests/test_hidden_installer.py`
- Modify: `docs/guides/install.md`

- [ ] **Step 1: Write failing plugin health tests**

Create `tests/test_plugin_health.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tools.plugin_health import inspect_plugin


class PluginHealthTest(unittest.TestCase):
    def test_inspect_plugin_reports_dashboard_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text('{"version":"0.1.0"}\n', encoding="utf-8")
            (root / "commands").mkdir()
            (root / "commands" / "research-dashboard.md").write_text("# /research-dashboard\n", encoding="utf-8")
            (root / "tools").mkdir()
            (root / "tools" / "research_browser_server.py").write_text("", encoding="utf-8")

            result = inspect_plugin(root)

        self.assertEqual(result["version"], "0.1.0")
        self.assertTrue(result["command_files"]["research-dashboard"])
        self.assertTrue(result["dashboard_fallback_available"])
        self.assertEqual(result["commands_visible"], "unknown")
        self.assertIn("install.sh --update", result["update_command"])
```

- [ ] **Step 2: Run plugin health tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_plugin_health -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.plugin_health'`.

- [ ] **Step 3: Implement `tools/plugin_health.py`**

Create `tools/plugin_health.py`:

```python
#!/usr/bin/env python3
"""Inspect local Research Pilot plugin installation health."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def read_version(root: Path) -> str:
    manifest = root / ".codex-plugin" / "plugin.json"
    if not manifest.exists():
        return ""
    try:
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version") or "")
    except json.JSONDecodeError:
        return ""


def git_commit(root: Path) -> str:
    if not (root / ".git").exists():
        return ""
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def inspect_plugin(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    command_files = {
        "research-init": (root / "commands" / "research-init.md").exists(),
        "research-dashboard": (root / "commands" / "research-dashboard.md").exists(),
    }
    skill_links = {
        "research-pilot": (Path.home() / ".agents" / "skills" / "research-pilot").exists(),
        "research-pilot-first-run": (Path.home() / ".agents" / "skills" / "research-pilot-first-run").exists(),
    }
    return {
        "source_path": str(root),
        "version": read_version(root),
        "git_commit": git_commit(root),
        "command_files": command_files,
        "commands_visible": "unknown",
        "skill_links": skill_links,
        "helper_bins": {
            "research-pilot-init": (Path.home() / ".research-pilot" / "bin" / "research-pilot-init").exists(),
        },
        "dashboard_fallback_available": (root / "tools" / "research_browser_server.py").exists(),
        "update_command": "curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s -- --update",
        "restart_guidance": "Restart Codex if plugin commands or skills were relinked.",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Research Pilot plugin health.")
    parser.add_argument("--plugin-root", default=".", help="Research Pilot plugin source path.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_plugin(Path(args.plugin_root))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Update command docs with fallback**

Add to `commands/research-dashboard.md` after the unrecognized command concern:

```markdown
## Host Fallback

If Codex does not expose `/research-dashboard`, the agent should still perform this workflow from chat by running the same server steps directly. The user-facing experience remains "open the research dashboard"; the slash command is not required for product correctness.

Agent-facing health check:

```bash
python3 "$PLUGIN_ROOT/tools/plugin_health.py" --plugin-root "$PLUGIN_ROOT" --json
```
```

Add to `commands/research-init.md`:

```markdown
If `/research-init` is not visible in the current Codex host, the agent should run `tools/research_pilot_init.py` from the resolved plugin root and report the same completion summary.
```

- [ ] **Step 5: Update installer output**

In `install.sh`, update `cmd_install` and `cmd_update` completion text to include:

```bash
  printf 'Health check:\n'
  printf '  python3 %s/tools/plugin_health.py --plugin-root %s --json\n' "$REPO_DIR" "$REPO_DIR"
  printf 'If slash commands are not visible, restart Codex or ask the agent to use the fallback workflow.\n'
```

- [ ] **Step 6: Update command tests**

Modify `tests/test_plugin_commands.py`:

```python
self.assertIn("Host Fallback", text)
self.assertIn("plugin_health.py", text)
```

inside `test_research_dashboard_command_exists`.

Add to `test_research_init_command_exists`:

```python
self.assertIn("not visible", text)
self.assertIn("research_pilot_init.py", text)
```

- [ ] **Step 7: Run plugin tests**

Run:

```bash
python3 -m unittest tests.test_plugin_health tests.test_plugin_commands tests.test_hidden_installer -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/plugin_health.py tests/test_plugin_health.py commands/research-dashboard.md commands/research-init.md install.sh tests/test_plugin_commands.py tests/test_hidden_installer.py docs/guides/install.md
git commit -m "feat: add plugin health and command fallback"
```

## Task 7: Durable Job Records

**Files:**

- Create: `tools/job_records.py`
- Create: `tests/test_job_records.py`
- Modify: `tools/build_dashboard_index.py`
- Modify: `tests/test_dashboard_public.py`
- Modify: `skills/research-pilot/SKILL.md`
- Modify: `docs/guides/core-workflows.md`

- [ ] **Step 1: Write failing job record tests**

Create `tests/test_job_records.py`:

```python
import tempfile
import unittest
from pathlib import Path

from tools.job_records import create_job_record, list_job_records, validate_job_record


class JobRecordsTest(unittest.TestCase):
    def test_create_job_record_is_execution_state_not_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            record = create_job_record(
                root,
                job_type="paper_search",
                project="DemoProject",
                status="queued",
                inputs={"gap_id": "RL0"},
                artifacts=[],
                result_summary="Queued search. No graph truth changed.",
            )
            records = list_job_records(root)

        self.assertTrue(record["id"].startswith("job-"))
        self.assertEqual(records[0]["human_gate"], "required_before_graph_update")
        self.assertEqual(records[0]["truth_boundary"], "execution_state_only")

    def test_validate_rejects_graph_mutation_claim(self):
        record = {
            "id": "job-1",
            "type": "paper_search",
            "project": "Demo",
            "status": "done",
            "human_gate": "required_before_graph_update",
            "truth_boundary": "graph_truth_changed",
        }

        result = validate_job_record(record)

        self.assertFalse(result["valid"])
        self.assertIn("truth_boundary", result["errors"][0])
```

- [ ] **Step 2: Run job tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_job_records -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.job_records'`.

- [ ] **Step 3: Implement `tools/job_records.py`**

Create `tools/job_records.py`:

```python
#!/usr/bin/env python3
"""Durable execution-state job records for long Research Pilot work."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_TYPES = {"paper_search", "deep_read", "evidence_synthesis", "experiment_proposal"}
VALID_STATUSES = {"queued", "running", "needs_review", "done", "failed"}


def now_string() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def jobs_dir(root: Path) -> Path:
    return Path(root).expanduser().resolve() / ".research-pilot" / "jobs"


def validate_job_record(record: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if record.get("type") not in VALID_TYPES:
        errors.append("type must be one of " + ", ".join(sorted(VALID_TYPES)))
    if record.get("status") not in VALID_STATUSES:
        errors.append("status must be one of " + ", ".join(sorted(VALID_STATUSES)))
    if record.get("human_gate") != "required_before_graph_update":
        errors.append("human_gate must be required_before_graph_update")
    if record.get("truth_boundary") != "execution_state_only":
        errors.append("truth_boundary must be execution_state_only")
    return {"valid": not errors, "errors": errors}


def create_job_record(
    root: Path,
    *,
    job_type: str,
    project: str,
    status: str,
    inputs: Dict[str, Any],
    artifacts: List[str],
    result_summary: str,
) -> Dict[str, Any]:
    directory = jobs_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = now_string()
    job_id = "job-" + timestamp.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    record = {
        "id": job_id,
        "type": job_type,
        "project": project,
        "status": status,
        "created_at": timestamp,
        "updated_at": timestamp,
        "owner": "agent",
        "human_gate": "required_before_graph_update",
        "truth_boundary": "execution_state_only",
        "inputs": inputs,
        "artifacts": artifacts,
        "result_summary": result_summary,
    }
    validation = validate_job_record(record)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    path = directory / f"{job_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def list_job_records(root: Path) -> List[Dict[str, Any]]:
    directory = jobs_dir(root)
    if not directory.exists():
        return []
    records: List[Dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["path"] = str(path.relative_to(Path(root).expanduser().resolve()))
        records.append(record)
    return records


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Research Pilot job records.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_cmd = subparsers.add_parser("list")
    list_cmd.add_argument("--repo", default=".")
    list_cmd.add_argument("--json", action="store_true")
    create = subparsers.add_parser("create")
    create.add_argument("--repo", default=".")
    create.add_argument("--type", required=True, choices=sorted(VALID_TYPES))
    create.add_argument("--project", required=True)
    create.add_argument("--status", default="queued", choices=sorted(VALID_STATUSES))
    create.add_argument("--summary", required=True)
    create.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "list":
        result: Any = list_job_records(Path(args.repo))
    else:
        result = create_job_record(Path(args.repo), job_type=args.type, project=args.project, status=args.status, inputs={}, artifacts=[], result_summary=args.summary)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Expose jobs in dashboard index**

In `tools/build_dashboard_index.py`, add import near top:

```python
from tools.job_records import list_job_records
```

In `build_index`, add:

```python
jobs = list_job_records(root)
```

and add to returned dict:

```python
"jobs": jobs,
```

- [ ] **Step 5: Add dashboard job test**

Append to `tests/test_dashboard_public.py`:

```python
    def test_dashboard_index_exposes_job_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs = root / ".research-pilot" / "jobs"
            jobs.mkdir(parents=True)
            (jobs / "job-1.json").write_text(
                '{"id":"job-1","type":"paper_search","project":"Demo","status":"needs_review","human_gate":"required_before_graph_update","truth_boundary":"execution_state_only"}\n',
                encoding="utf-8",
            )

            index = build_index(root)

        self.assertEqual(index["jobs"][0]["id"], "job-1")
        self.assertEqual(index["jobs"][0]["truth_boundary"], "execution_state_only")
```

- [ ] **Step 6: Update skill and workflow docs**

Add to `skills/research-pilot/SKILL.md`:

```text
For long search, deep-read, synthesis, or experiment-proposal work, create a durable job record under `.research-pilot/jobs/`.
Job records are execution state only. They do not change graph truth.
Human gate remains in the main agent/user conversation before any graph delta acceptance.
```

Add to `docs/guides/core-workflows.md`:

```markdown
## Durable Research Jobs

Long paper search, deep-read, synthesis, and experiment-proposal tasks may create `.research-pilot/jobs/*.json` records.

These records track execution state:

- `queued`
- `running`
- `needs_review`
- `done`
- `failed`

They are not graph truth. Any project-understanding change still goes through D* dry-run and human acceptance.
```

- [ ] **Step 7: Run job and dashboard tests**

Run:

```bash
python3 -m unittest tests.test_job_records tests.test_dashboard_public -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/job_records.py tests/test_job_records.py tools/build_dashboard_index.py tests/test_dashboard_public.py skills/research-pilot/SKILL.md docs/guides/core-workflows.md
git commit -m "feat: add durable research job records"
```

## Task 8: Docs, Defect Log, Retest Queue, And Full Verification

**Files:**

- Modify: `docs/research-pilot-trial-defects.md`
- Modify: `docs/guides/workspace.md`
- Modify: `README.md`
- Modify: `tests/test_codex_plugin_manifest.py`

- [ ] **Step 1: Update defect log statuses**

In `docs/research-pilot-trial-defects.md`, change all RP-001 through RP-013 `Status` values from `open` to `planned`.

Replace RP-001 row with:

```markdown
| RP-001 | 2026-05-12 | Onboarding | Initial workspace inspection | Agent clearly explains plugin/workspace state and next action | Initial inspection was only a seed entry and did not create an actionable first-run diagnosis | Trial evidence could not drive implementation without a concrete status contract | medium | planned | Covered by `research_pilot_status.py` and stage-aware first-run flow. |
```

Update retest queue expected triggers:

```markdown
| RP-001 | First-run onboarding clarity | Run `research_pilot_status.py` through agent workflow from plugin repo and workspace | Planned: expect stage plus one or two next actions | 2026-05-12 |
```

- [ ] **Step 2: Update workspace guide**

Add to `docs/guides/workspace.md`:

```markdown
## Workspace Stages

Research Pilot workspaces are stage-aware:

- empty workspace;
- project shell;
- graph started;
- papers present;
- open deltas;
- stale read models;
- Zotero setup needed.

The agent should inspect stage before suggesting next actions.
```

- [ ] **Step 3: Update README mental model**

In `README.md`, add under Core Loop:

```markdown
Early projects may start as a project shell before graph truth exists. A project shell can capture target venue, maturity stage, broad direction, baseline anchors, and setup/search prompts. Graph truth starts only after a human-approved D* delta.
```

Add under Quick Start after dashboard command:

```markdown
If a slash command is not visible in your Codex host, ask the agent to open the Research Pilot dashboard. The agent can use the same dashboard server fallback from the plugin tools.
```

- [ ] **Step 4: Add manifest capability test**

In `tests/test_codex_plugin_manifest.py`, assert plugin description remains chat-first:

```python
self.assertIn("private research workspace", manifest["interface"]["longDescription"])
self.assertIn("human-gated", manifest["interface"]["longDescription"])
```

- [ ] **Step 5: Run targeted suite**

Run:

```bash
python3 -m unittest \
  tests.test_research_pilot_status \
  tests.test_project_shell_cli \
  tests.test_dashboard_public \
  tests.test_zotero_setup \
  tests.test_source_intake_cli \
  tests.test_zotero_bridge_public \
  tests.test_plugin_health \
  tests.test_job_records \
  tests.test_first_run_protocol \
  tests.test_plugin_commands \
  tests.test_hidden_installer \
  tests.test_codex_plugin_manifest \
  -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 7: Run release check**

Run:

```bash
./scripts/release_check.sh
```

Expected: PASS.

- [ ] **Step 8: Commit docs and final verification**

```bash
git add docs/research-pilot-trial-defects.md docs/guides/workspace.md README.md tests/test_codex_plugin_manifest.py
git commit -m "docs: mark trial defects planned for full coverage"
```

## Coverage Map

- RP-001: Task 1 status contract and Task 8 defect log update.
- RP-002: Task 1 stage-aware status and next actions.
- RP-003: Task 6 command fallback and plugin health.
- RP-004: Task 2 maturity-aware project shell intake.
- RP-005: Task 2 project shell before graph truth.
- RP-006: Task 7 durable job records and human gate boundary.
- RP-007: Task 3 dashboard title metadata.
- RP-008: Task 3 seed/search/accepted question split.
- RP-009: Task 4 API-key-first setup flow.
- RP-010: Task 4 `.env`-reading Zotero status helper.
- RP-011: Task 5 Zotero collection tree.
- RP-012: Task 4 docs/skills remove Zotero MCP dependency from normal flow.
- RP-013: Task 6 plugin health/update status.

## Final Handoff Checklist

- [ ] `git status --short` shows only intentional files.
- [ ] Full `python3 -m unittest discover -s tests -v` passes.
- [ ] `./scripts/release_check.sh` passes.
- [ ] No output includes a Zotero API key.
- [ ] Dashboard index includes `jobs` and question semantic fields.
- [ ] Skills say chat is primary interface and tools are agent-facing helpers.
- [ ] Defect log RP-001 through RP-013 no longer reads as unprocessed trial input.
