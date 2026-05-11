#!/usr/bin/env python3
"""Serve Research Pilot dashboard files and public-safe read APIs."""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, unquote, urlsplit

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.build_dashboard_index import build_index, extract_section, read_markdown, relpath
from tools.graph_delta_api import decide_graph_delta, dry_run_graph_delta
from tools.graph_store import build_snapshot_from_event_files, graph_event_paths


DEFAULT_INDEX_PATH = ".dashboard/index.json"
BLOCKED_STATIC_PATH = "__research_browser_blocked__"


def json_response(data: Dict[str, Any], status: int = HTTPStatus.OK) -> Tuple[int, bytes]:
    return status, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def rebuild_dashboard_index(root: Path) -> None:
    output = root / DEFAULT_INDEX_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_index(root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    graph = snapshot_graph_for_project(root, project_id)
    if graph is None:
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response(graph)


def handle_experiment_proposals_request(root: Path, request_path: str) -> Tuple[int, bytes]:
    project_id = parse_qs(urlsplit(request_path).query).get("project", [""])[0].strip()
    if not valid_project_id(project_id):
        return json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
    return json_response(
        {
            "schema_version": "experiment-proposals-v1",
            "project": project_id,
            "state_note": "planned / pending / not yet graph evidence",
            "source_boundary": "dashboard is a read model and does not own graph truth",
            "mutating": False,
            "empty_message": "No experiment proposals yet.",
            "proposals": [],
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
    def do_GET(self) -> None:
        root = Path(self.directory)
        request_api_path = urlsplit(self.path).path
        if request_api_path == "/api/wiki-page":
            status, payload = handle_wiki_page_request(root, self.path)
        elif request_api_path == "/api/project-graph":
            status, payload = handle_project_graph_request(root, self.path)
        elif request_api_path == "/api/experiment-proposals":
            status, payload = handle_experiment_proposals_request(root, self.path)
        elif request_api_path in {"/api/project-graph-maintenance", "/api/paper-graph", "/api/graph-delta/propose-from-dossier"}:
            status, payload = json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
        else:
            if request_api_path == "/":
                self.path = "/dashboard/index.html"
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
