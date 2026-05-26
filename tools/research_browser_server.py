#!/usr/bin/env python3
"""Serve Research Pilot dashboard files and public-safe read APIs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlsplit

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.build_dashboard_index import build_index, extract_section, read_markdown, relpath
from tools.experiment_store import build_project_experiments
from tools.graph_delta_api import decide_graph_delta, dry_run_graph_delta
from tools.graph_store import build_snapshot_from_event_files, graph_event_paths, load_project_graph_maintenance_from_db
from tools.research_dataset_read_models import (
    build_experiments_model,
    build_paper_graph_model as build_dataset_paper_graph_model,
    build_project_graph_model,
    project_exists_in_dataset,
)
from tools.understanding_store import build_project_understanding
from tools.workspace_graph_read_models import build_workspace_graph_model


DEFAULT_INDEX_PATH = ".dashboard/index.json"
BLOCKED_STATIC_PATH = "__research_browser_blocked__"


def json_response(data: Dict[str, Any], status: int = HTTPStatus.OK) -> Tuple[int, bytes]:
    return status, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def rebuild_dashboard_index(root: Path) -> None:
    output = root / DEFAULT_INDEX_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_index(root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_dashboard_index(root: Path) -> Path:
    output = root / DEFAULT_INDEX_PATH
    if not output.exists():
        rebuild_dashboard_index(root)
    return output


def valid_project_id(project_id: str) -> bool:
    parts = Path(project_id).parts
    return bool(project_id) and len(parts) == 1 and not any(part in {"", ".", ".."} for part in parts)


def resolve_project_markdown_path(root: Path, requested: str) -> Path | None:
    if not requested:
        return None
    decoded = unquote(requested)
    parts = Path(decoded).parts
    if any(part in {"", ".", ".."} for part in parts):
        return None
    target = (root / decoded).resolve()
    allowed_root = (root / "wiki" / "projects").resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError:
        return None
    if target.suffix != ".md" or not target.exists() or not target.is_file():
        return None
    return target


def resolve_paper_dossier_path(root: Path, requested: str) -> Path | None:
    target = resolve_project_markdown_path(root, requested)
    if target is None:
        return None
    try:
        rel_parts = target.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return None
    if len(rel_parts) < 6:
        return None
    if rel_parts[0] != "wiki" or rel_parts[1] != "projects" or rel_parts[3] != "papers":
        return None
    if rel_parts[-1] != "index.md":
        return None
    return target


def paper_project_and_slug(root: Path, target: Path) -> Tuple[str, str]:
    rel_parts = target.resolve().relative_to(root.resolve()).parts
    return rel_parts[2], rel_parts[4]


def normalize_source_ref(value: Any) -> str:
    text = unquote(str(value or "").strip()).replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    if text.endswith("/index"):
        text = f"{text}.md"
    return text


def source_refs_match_paper(source_refs: Any, paper_relpath: str, paper_slug: str) -> bool:
    refs = source_refs if isinstance(source_refs, list) else [source_refs]
    paper_relpath = normalize_source_ref(paper_relpath)
    paper_ref = f"paper:{paper_slug}"
    for raw_ref in refs:
        ref = normalize_source_ref(raw_ref)
        if ref == paper_relpath or ref.endswith(f"/{paper_relpath}"):
            return True
        if ref == paper_ref:
            return True
    return False


def raw_snapshot_for_project(root: Path, project_id: str) -> Dict[str, Any] | None:
    snapshot_path = root / "wiki" / "graphs" / "snapshots" / "projects" / f"{project_id}.graph.json"
    if snapshot_path.exists():
        return json.loads(snapshot_path.read_text(encoding="utf-8"))
    event_paths = graph_event_paths(root, project_id)
    if not event_paths:
        return None
    return build_snapshot_from_event_files(event_paths)


def local_graph_id(value: Any) -> str:
    return str(value or "").rsplit(":", 1)[-1]


def paper_node_id(project_local_id: str) -> str:
    return f"P-{project_local_id}"


def paper_node_subtitle(node: Dict[str, Any]) -> str:
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    node_type = str(node.get("node_type") or "")
    if node_type == "Evidence":
        return str(metadata.get("evidence_kind") or metadata.get("source_type") or node.get("status") or "")
    if node_type == "Warrant":
        return str(metadata.get("basis") or node.get("status") or "")
    if node_type == "Limitation":
        return str(metadata.get("severity") or node.get("status") or "")
    return str(metadata.get("role") or metadata.get("status") or node.get("status") or "")


def paper_node_kind(node: Dict[str, Any]) -> str:
    return str(node.get("node_type") or "").lower()


def paper_graph_nodes_for_source(
    snapshot: Dict[str, Any],
    paper_relpath: str,
    paper_slug: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    nodes: List[Dict[str, Any]] = []
    project_to_paper: Dict[str, str] = {}
    for project_node in snapshot.get("nodes", []):
        if not source_refs_match_paper(project_node.get("source_refs", []), paper_relpath, paper_slug):
            continue
        local_id = local_graph_id(project_node.get("local_id") or project_node.get("node_id"))
        if not local_id:
            continue
        p_id = paper_node_id(local_id)
        project_to_paper[str(project_node.get("node_id") or "")] = p_id
        nodes.append(
            {
                "id": p_id,
                "kind": paper_node_kind(project_node),
                "label": str(project_node.get("text") or local_id),
                "subtitle": paper_node_subtitle(project_node),
                "project_node": local_id,
                "source_refs": list(project_node.get("source_refs") or []),
            }
        )
    return nodes, project_to_paper


def paper_graph_links_for_source(snapshot: Dict[str, Any], project_to_paper: Dict[str, str]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for project_link in snapshot.get("links", []):
        if str(project_link.get("link_type") or "") != "ReasoningLink":
            continue
        premises = [project_to_paper[ref] for ref in project_link.get("from_nodes", []) if ref in project_to_paper]
        targets = [project_to_paper[ref] for ref in project_link.get("to_nodes", []) if ref in project_to_paper]
        warrants = [project_to_paper[ref] for ref in project_link.get("warrant_nodes", []) if ref in project_to_paper]
        limitations = [project_to_paper[ref] for ref in project_link.get("limitation_nodes", []) if ref in project_to_paper]
        if not targets or not (premises or warrants or limitations):
            continue
        links.append(
            {
                "id": local_graph_id(project_link.get("local_id") or project_link.get("link_id")),
                "relation": str(project_link.get("relation") or ""),
                "premises": premises,
                "target": targets[0],
                "warrant": warrants[0] if warrants else "",
                "limitations": limitations,
                "project_link": local_graph_id(project_link.get("local_id") or project_link.get("link_id")),
            }
        )
    return links


def paper_graph_translations(project_to_paper: Dict[str, str]) -> List[Dict[str, Any]]:
    translations: List[Dict[str, Any]] = []
    for index, (project_node_id, p_id) in enumerate(project_to_paper.items(), start=1):
        local_id = local_graph_id(project_node_id)
        translations.append(
            {
                "id": f"TL{index}",
                "paper_nodes": [p_id],
                "project_nodes": [local_id],
                "relation": "source_supports_project_node",
                "interpretation": f"Paper dossier contribution is projected into project node {local_id}.",
                "caveat": "Derived read model; source dossier remains unchanged.",
            }
        )
    return translations


def paper_graph_deltas_for_source(
    snapshot: Dict[str, Any],
    paper_relpath: str,
    paper_slug: str,
    project_to_paper: Dict[str, str],
) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    affected_project_ids = set(project_to_paper)
    for delta in snapshot.get("deltas", []):
        affected_nodes = list(delta.get("affected_nodes") or [])
        affected_links = list(delta.get("affected_links") or [])
        matches_source = (
            source_refs_match_paper(delta.get("source_refs", []), paper_relpath, paper_slug)
            or source_refs_match_paper(delta.get("source_dossier", ""), paper_relpath, paper_slug)
            or bool(affected_project_ids.intersection(affected_nodes))
        )
        if not matches_source:
            continue
        source_paper_nodes = [
            project_to_paper[node_id]
            for node_id in affected_nodes
            if node_id in project_to_paper
        ]
        deltas.append(
            {
                "id": local_graph_id(delta.get("local_id") or delta.get("delta_id")),
                "operation": ", ".join(str(item) for item in delta.get("operation", []) if item),
                "status": str(delta.get("lifecycle_status") or delta.get("status") or ""),
                "human_review": str(delta.get("human_review") or ""),
                "source_paper_nodes": source_paper_nodes,
                "affected": [local_graph_id(item) for item in affected_nodes + affected_links],
                "proposed_change": str(delta.get("summary") or ""),
            }
        )
    return deltas


def build_paper_graph_model(root: Path, target: Path) -> Dict[str, Any] | None:
    project_id, paper_slug = paper_project_and_slug(root, target)
    snapshot = raw_snapshot_for_project(root, project_id)
    if snapshot is None:
        return None
    paper_relpath = relpath(target, root)
    frontmatter, _ = read_markdown(target)
    nodes, project_to_paper = paper_graph_nodes_for_source(snapshot, paper_relpath, paper_slug)
    return {
        "schema_version": "paper-graph-v1",
        "project": project_id,
        "paper": paper_slug,
        "title": str(frontmatter.get("title") or paper_slug),
        "path": paper_relpath,
        "source_boundary": "derived_from_project_graph_and_paper_dossier",
        "nodes": nodes,
        "paper_links": paper_graph_links_for_source(snapshot, project_to_paper),
        "translations": paper_graph_translations(project_to_paper),
        "deltas": paper_graph_deltas_for_source(snapshot, paper_relpath, paper_slug, project_to_paper),
    }


def snapshot_graph_for_project(root: Path, project_id: str) -> Dict[str, Any] | None:
    snapshot_path = root / "wiki" / "graphs" / "snapshots" / "projects" / f"{project_id}.graph.json"
    if not snapshot_path.exists():
        event_paths = graph_event_paths(root, project_id)
        if not event_paths:
            return None
        snapshot = build_snapshot_from_event_files(event_paths)
    else:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    from tools.build_dashboard_index import snapshot_to_project_graph

    if snapshot_path.exists():
        return snapshot_to_project_graph(root, snapshot_path)
    temp_path = root / ".dashboard" / f"{project_id}.graph.json"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        return snapshot_to_project_graph(root, temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def db_model_for_project(
    root: Path,
    project_id: str,
    builder: Callable[[Path, str], Dict[str, Any]],
) -> Dict[str, Any] | None:
    if not project_exists_in_dataset(root, project_id):
        return None
    try:
        model = builder(root, project_id)
    except (ValueError, sqlite3.Error, json.JSONDecodeError):
        return None
    if not isinstance(model, dict):
        return None
    return model


def handle_wiki_page_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    requested = parse_qs(urlsplit(request_path).query).get("path", [""])[0]
    target = resolve_project_markdown_path(root.resolve(), requested)
    if target is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response({"path": relpath(target, root), "content": target.read_text(encoding="utf-8")})


def handle_project_graph_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    db_graph = db_model_for_project(root.resolve(), project_id, build_project_graph_model)
    if db_graph is not None:
        return json_response(db_graph)
    graph = snapshot_graph_for_project(root, project_id)
    if graph is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response(graph)


def handle_paper_graph_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    requested = parse_qs(urlsplit(request_path).query).get("path", [""])[0]
    target = resolve_paper_dossier_path(root.resolve(), requested)
    if target is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    try:
        graph = build_dataset_paper_graph_model(root.resolve(), target)
    except (ValueError, sqlite3.Error, json.JSONDecodeError):
        graph = None
    if graph is not None:
        return json_response(graph)
    graph = build_paper_graph_model(root.resolve(), target)
    if graph is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response(graph)


def handle_project_graph_maintenance_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    model = load_project_graph_maintenance_from_db(root, project_id)
    if model is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response(model)


def handle_project_understanding_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    try:
        model = build_project_understanding(root.resolve(), project_id)
    except (ValueError, json.JSONDecodeError) as exc:
        return json_response({"error": f"Invalid project understanding: {exc}"}, HTTPStatus.BAD_REQUEST)
    return json_response(model)


def handle_experiments_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    db_model = db_model_for_project(root.resolve(), project_id, build_experiments_model)
    if db_model is not None:
        return json_response(db_model)
    try:
        model = build_project_experiments(root.resolve(), project_id)
    except (ValueError, json.JSONDecodeError) as exc:
        return json_response({"error": f"Invalid project experiments: {exc}"}, HTTPStatus.BAD_REQUEST)
    return json_response(model)


def handle_workspace_graph_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    query = parse_qs(urlsplit(request_path).query)
    project_id = query.get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    mode = query.get("mode", ["understanding"])[0].strip() or "understanding"
    layer = query.get("layer", [""])[0].strip()
    focus_id = query.get("focus_id", [""])[0].strip()
    selected_id = query.get("selected_id", [""])[0].strip()
    try:
        model = build_workspace_graph_model(
            root.resolve(),
            project_id,
            mode=mode,
            layer=layer,
            focus_id=focus_id,
            selected_id=selected_id,
        )
    except (ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        return json_response(
            {
                "error": "Invalid workspace graph request",
                "message": str(exc),
                "schema_version": "workspace-graph-error-v1",
            },
            HTTPStatus.BAD_REQUEST,
        )
    return json_response(model)


def handle_experiment_proposals_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    experiments_model = db_model_for_project(root.resolve(), project_id, build_experiments_model)
    if experiments_model is None:
        try:
            experiments_model = build_project_experiments(root.resolve(), project_id)
        except (ValueError, json.JSONDecodeError) as exc:
            return json_response({"error": f"Invalid project experiments: {exc}"}, HTTPStatus.BAD_REQUEST)
    return json_response(
        {
            "schema_version": "experiment-proposals-v1",
            "project": project_id,
            "state_note": "Legacy proposal endpoint. Use /api/experiments for planned designs and result evidence.",
            "source_boundary": "dashboard is a read-only projection of project experiment records",
            "mutating": False,
            "empty_message": experiments_model.get("empty_message", "No experiments recorded yet."),
            "proposals": [],
            "experiments_model": experiments_model,
        }
    )


def handle_graph_delta_request(root: Path, request_path: str, body: bytes) -> Tuple[int, bytes]:
    try:
        batch = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return json_response({"error": f"Invalid JSON: {exc}"}, HTTPStatus.BAD_REQUEST)
    if not isinstance(batch, dict):
        return json_response({"error": "Invalid JSON: expected object"}, HTTPStatus.BAD_REQUEST)
    project_id = str(batch.get("project") or batch.get("project_id") or "").strip()
    delta = batch.get("delta") if isinstance(batch.get("delta"), dict) else {}
    path = urlsplit(request_path).path
    if path == "/api/graph-delta/dry-run":
        result = dry_run_graph_delta(root, project_id, delta)
        return json_response(result, HTTPStatus.OK if result.get("valid") else HTTPStatus.BAD_REQUEST)
    decision = str(batch.get("decision") or "").strip()
    delta_id = str(delta.get("local_id") or batch.get("delta_id") or batch.get("id") or "").strip()
    result = decide_graph_delta(root, project_id, delta_id, decision, actor=str(batch.get("actor") or "human"), decision_note=str(batch.get("decision_note") or ""))
    return json_response(result, HTTPStatus.OK if result.get("valid") else HTTPStatus.BAD_REQUEST)


class ResearchBrowserHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        request_path = urlsplit(self.path).path
        if (
            request_path.startswith("/dashboard/")
            or request_path.startswith("/api/")
            or request_path == "/.dashboard/index.json"
        ):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        root = Path(self.directory)
        request_api_path = urlsplit(self.path).path
        if request_api_path == "/":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/dashboard/index.html")
            self.end_headers()
            return
        if request_api_path == "/.dashboard/index.json":
            ensure_dashboard_index(root)
            super().do_GET()
            return
        if request_api_path == "/api/wiki-page":
            status, payload = handle_wiki_page_request(root, self.path)
        elif request_api_path == "/api/workspace-graph":
            status, payload = handle_workspace_graph_request(root, self.path)
        elif request_api_path == "/api/project-graph":
            status, payload = handle_project_graph_request(root, self.path)
        elif request_api_path == "/api/project-graph-maintenance":
            status, payload = handle_project_graph_maintenance_request(root, self.path)
        elif request_api_path == "/api/project-understanding":
            status, payload = handle_project_understanding_request(root, self.path)
        elif request_api_path == "/api/experiments":
            status, payload = handle_experiments_request(root, self.path)
        elif request_api_path == "/api/experiment-proposals":
            status, payload = handle_experiment_proposals_request(root, self.path)
        elif request_api_path == "/api/paper-graph":
            status, payload = handle_paper_graph_request(root, self.path)
        elif request_api_path == "/api/graph-delta/propose-from-dossier":
            status, payload = json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
        else:
            super().do_GET()
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length)
        root = Path(self.directory)
        request_api_path = urlsplit(self.path).path
        if request_api_path in {"/api/graph-delta/dry-run", "/api/graph-delta/apply"}:
            status, payload = handle_graph_delta_request(root, self.path, body)
        else:
            status, payload = json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def translate_path(self, path: str) -> str:
        root = Path(self.directory).resolve()
        decoded_path = unquote(urlsplit(path).path)
        parts = [part for part in decoded_path.split("/") if part]
        if any(part in {".", ".."} for part in parts):
            return str(root / BLOCKED_STATIC_PATH)
        if decoded_path == "/.dashboard/index.json":
            return str(root / DEFAULT_INDEX_PATH)
        dashboard_root = ROOT_DIR / "dashboard"
        if decoded_path == "/dashboard":
            return str(dashboard_root / "index.html")
        if decoded_path.startswith("/dashboard/"):
            target = (ROOT_DIR / decoded_path.lstrip("/")).resolve()
            try:
                target.relative_to(dashboard_root)
            except ValueError:
                return str(root / BLOCKED_STATIC_PATH)
            return str(target)
        return str(root / BLOCKED_STATIC_PATH)

    def list_directory(self, path: str) -> None:
        self.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return None


def make_handler(root: Path) -> type[ResearchBrowserHandler]:
    class BoundResearchBrowserHandler(ResearchBrowserHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(root), **kwargs)

    return BoundResearchBrowserHandler


def serve(root: Path, host: str, port: int) -> None:
    root = root.resolve()
    rebuild_dashboard_index(root)
    server = ThreadingHTTPServer((host, port), make_handler(root))
    print(f"Serving Research Browser at http://{host}:{server.server_port}/")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve local Research Pilot dashboard.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(Path(args.repo), args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
