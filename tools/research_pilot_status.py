#!/usr/bin/env python3
"""Read-only Research Pilot workspace status for agent onboarding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DELTA_STATUS_TO_LIFECYCLE = {
    "proposed": "proposed",
    "registered": "proposed",
    "accepted": "accepted",
    "integrated": "accepted",
    "partially_integrated": "accepted",
    "rejected": "rejected",
    "parked": "parked",
    "revised": "revised",
    "superseded": "revised",
}
OPEN_DELTA_LIFECYCLES = {"proposed", "parked", "revised"}
ZOTERO_API_KEY_ENV = "ZOTERO_API_KEY"


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
            data[key.strip()] = [
                item.strip().strip("\"'") for item in inner.split(",") if item.strip()
            ]
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
            if (
                stripped.startswith(f"{ZOTERO_API_KEY_ENV}=")
                and stripped.split("=", 1)[1].strip()
            ):
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
        title = str(
            frontmatter.get("display_title")
            or frontmatter.get("title")
            or project_dir.name
        )
        maturity_stage = str(frontmatter.get("maturity_stage") or "project_shell")
        projects.append(
            {
                "id": project_dir.name,
                "title": title,
                "maturity_stage": maturity_stage,
                "has_overview": overview.exists(),
                "has_graph_events": (
                    root
                    / "wiki"
                    / "graphs"
                    / "events"
                    / "projects"
                    / f"{project_dir.name}.jsonl"
                ).exists(),
                "has_graph_report": (
                    project_dir / "project-understanding-graph.md"
                ).exists(),
            }
        )
    return projects


def count_files(root: Path, pattern: str) -> int:
    base = root / "wiki"
    if not base.exists():
        return 0
    return sum(1 for _ in base.glob(pattern))


def canonical_delta_lifecycle(value: str) -> str:
    return DELTA_STATUS_TO_LIFECYCLE.get(str(value or "").strip().lower(), "proposed")


def iter_jsonl_objects(path: Path) -> List[Dict[str, Any]]:
    objects: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return objects
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
    return objects


def delta_identities(payload: Dict[str, Any], project_id: str) -> List[str]:
    identities = []
    delta_id = str(payload.get("delta_id") or "")
    local_id = str(payload.get("local_id") or "")
    if delta_id:
        identities.append(delta_id)
    if local_id:
        identities.append(f"{project_id}:{local_id}")
    return identities


def count_open_deltas(root: Path) -> int:
    event_root = root / "wiki" / "graphs" / "events" / "projects"
    if not event_root.exists():
        return 0
    latest_lifecycle: Dict[str, str] = {}
    aliases: Dict[str, str] = {}
    for event_path in sorted(event_root.glob("*.jsonl")):
        project_id = event_path.stem
        for event in iter_jsonl_objects(event_path):
            event_type = str(event.get("event_type") or "")
            if not event_type.startswith("delta."):
                continue
            payload = event.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            identities = delta_identities(payload, project_id)
            if not identities:
                continue
            canonical_id = next(
                (aliases[identity] for identity in identities if identity in aliases),
                identities[0],
            )
            for identity in identities:
                aliases[identity] = canonical_id
            lifecycle = canonical_delta_lifecycle(
                str(
                    payload.get("lifecycle_status")
                    or payload.get("status")
                    or event_type.split(".", 1)[-1]
                )
            )
            latest_lifecycle[canonical_id] = lifecycle
    return sum(
        1 for lifecycle in latest_lifecycle.values() if lifecycle in OPEN_DELTA_LIFECYCLES
    )


def newest_mtime(paths: List[Path]) -> Optional[float]:
    existing = [path.stat().st_mtime for path in paths if path.exists()]
    return max(existing) if existing else None


def read_model_status(root: Path) -> Dict[str, str]:
    dashboard = root / ".dashboard" / "index.json"
    graph_db = root / "wiki" / "graphs" / "graph.db"
    snapshots = root / "wiki" / "graphs" / "snapshots"
    events_root = root / "wiki" / "graphs" / "events"
    event_paths = list(events_root.glob("**/*.jsonl")) if events_root.exists() else []
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
        if (
            event_mtime is not None
            and snapshot_mtime is not None
            and snapshot_mtime < event_mtime
        ):
            snapshot_status = "stale"

    return {
        "dashboard_index": status(dashboard),
        "graph_db": status(graph_db),
        "snapshots": snapshot_status,
    }


def plugin_status() -> Dict[str, Any]:
    home = Path.home()
    candidates = [home / ".research-pilot" / "repo", home / ".research-pilot-plugin"]
    source_path = next((path for path in candidates if path.exists()), None)
    manifest = source_path / ".codex-plugin" / "plugin.json" if source_path else None
    version = ""
    if manifest and manifest.exists():
        try:
            version = str(json.loads(manifest.read_text(encoding="utf-8")).get("version") or "")
        except json.JSONDecodeError:
            version = ""
    return {
        "source_path": str(source_path) if source_path else "",
        "version": version,
        "commands_visible": "unknown",
        "dashboard_fallback_available": bool(
            source_path and (source_path / "tools" / "research_browser_server.py").exists()
        ),
    }


def next_actions_for(stage: str) -> List[Dict[str, str]]:
    actions = {
        "plugin_repo": [
            {
                "id": "initialize_workspace",
                "label": "Initialize a private workspace",
                "reason": "Current directory is plugin source.",
            }
        ],
        "plain_directory": [
            {
                "id": "initialize_workspace",
                "label": "Initialize Research Pilot here or elsewhere",
                "reason": "No workspace markers found.",
            }
        ],
        "empty_workspace": [
            {
                "id": "create_project_shell",
                "label": "Create first project shell",
                "reason": "Workspace has no projects yet.",
            }
        ],
        "project_shell": [
            {
                "id": "configure_zotero_or_add_baselines",
                "label": "Configure Zotero or add baseline anchors",
                "reason": "Project shell exists without graph truth.",
            }
        ],
        "read_models_stale": [
            {
                "id": "rebuild_read_models",
                "label": "Rebuild read models",
                "reason": "Graph events are newer than generated views.",
            }
        ],
        "project_has_graph": [
            {
                "id": "inspect_graph",
                "label": "Inspect current graph and next action",
                "reason": "Project graph exists.",
            }
        ],
    }
    return actions.get(
        stage,
        [
            {
                "id": "inspect_workspace",
                "label": "Inspect workspace",
                "reason": "Workspace state needs review.",
            }
        ],
    )


def classify(root: Path, projects: List[Dict[str, Any]], read_models: Dict[str, str]) -> str:
    if is_plugin_repo(root):
        return "plugin_repo"
    if not is_workspace(root):
        return "plain_directory"
    if any(value == "stale" for value in read_models.values()):
        return "read_models_stale"
    if not projects:
        return "empty_workspace"
    if any(
        project.get("has_graph_events") or project.get("has_graph_report")
        for project in projects
    ):
        return "project_has_graph"
    return "project_shell"


def inspect_workspace(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    valid_workspace = is_workspace(root)
    projects = collect_projects(root) if valid_workspace else []
    read_models = (
        read_model_status(root)
        if valid_workspace
        else {
            "dashboard_index": "missing",
            "graph_db": "missing",
            "snapshots": "missing",
        }
    )
    stage = classify(root, projects, read_models)
    return {
        "valid_workspace": valid_workspace,
        "stage": stage,
        "root": str(root),
        "projects": projects,
        "open_deltas": count_open_deltas(root) if valid_workspace else 0,
        "paper_dossiers": count_files(root, "projects/*/papers/*/index.md"),
        "read_models": read_models,
        "zotero": read_env_flags(root),
        "plugin": plugin_status(),
        "next_actions": next_actions_for(stage),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Research Pilot workspace status.")
    parser.add_argument(
        "--repo", default=".", help="Workspace or plugin path. Default: current directory."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_workspace(Path(args.repo))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
