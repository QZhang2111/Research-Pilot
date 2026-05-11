#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-dashboard-smoke"
port="${RESEARCH_PILOT_DASHBOARD_SMOKE_PORT:-8899}"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-dashboard-init.log
mkdir -p "$tmp_workspace/wiki/graphs/events/projects"
cp examples/demo/events/demo-project.jsonl "$tmp_workspace/wiki/graphs/events/projects/DemoProject.jsonl"

python3 tools/build_graph_snapshot.py --repo "$tmp_workspace" --project DemoProject >/tmp/research-pilot-dashboard-snapshot.log
python3 tools/build_graph_db.py --repo "$tmp_workspace" --project DemoProject >/tmp/research-pilot-dashboard-db.log
python3 tools/build_dashboard_index.py --repo "$tmp_workspace" --output .dashboard/index.json >/tmp/research-pilot-dashboard-index.log

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ.get("TMPDIR", "/tmp")) / "research-pilot-dashboard-smoke"
data = json.loads((root / ".dashboard" / "index.json").read_text(encoding="utf-8"))
assert data["projects"][0]["id"] == "DemoProject"
assert data["project_graphs"][0]["project"] == "DemoProject"
PY

python3 tools/research_browser_server.py --repo "$tmp_workspace" --host 127.0.0.1 --port "$port" >/tmp/research-pilot-dashboard-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" >/dev/null 2>&1 || true' EXIT
sleep 0.8

curl -fsS "http://127.0.0.1:${port}/dashboard/index.html" >/tmp/research-pilot-dashboard-page.html
curl -fsS "http://127.0.0.1:${port}/.dashboard/index.json" >/tmp/research-pilot-dashboard-index-response.json
curl -fsS "http://127.0.0.1:${port}/api/project-graph?project=DemoProject" >/tmp/research-pilot-dashboard-project-graph.json
curl -fsS "http://127.0.0.1:${port}/api/project-graph-maintenance?project=DemoProject" >/tmp/research-pilot-dashboard-project-maintenance.json

rg -n "研究浏览器|项目论文审阅" /tmp/research-pilot-dashboard-page.html >/dev/null
rg -n '"projects"|"project_graphs"' /tmp/research-pilot-dashboard-index-response.json >/dev/null
rg -n '"project": "DemoProject"' /tmp/research-pilot-dashboard-project-graph.json >/dev/null
rg -n '"schema_version": "graph-maintenance-v1"|"open_deltas"' /tmp/research-pilot-dashboard-project-maintenance.json >/dev/null

echo "Dashboard smoke passed"
