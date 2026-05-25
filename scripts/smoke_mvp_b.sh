#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-b-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-b-init.log
mkdir -p "$tmp_workspace/wiki/graphs/events/projects"
cp examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl "$tmp_workspace/wiki/graphs/events/projects/DemoProject.jsonl"

python3 tools/graph_validate.py --repo "$tmp_workspace" --project DemoProject
python3 tools/build_graph_snapshot.py --repo "$tmp_workspace" --project DemoProject --generated-at 2026-05-11T00:01:00Z
python3 tools/build_graph_db.py --repo "$tmp_workspace" --project DemoProject
python3 tools/build_project_graph_report.py --repo "$tmp_workspace" --project DemoProject
python3 tools/graph_query_cli.py summary --repo "$tmp_workspace" --project DemoProject --json >/tmp/research-pilot-mvp-b-summary.json
python3 tools/graph_query_cli.py node --repo "$tmp_workspace" --project DemoProject --id C0 --json >/tmp/research-pilot-mvp-b-node.json
python3 tools/graph_query_cli.py open --repo "$tmp_workspace" --project DemoProject --json >/tmp/research-pilot-mvp-b-open.json

rg -n 'DemoProject Project Understanding Graph|Demo claim needs evidence|Connect demo evidence to demo claim' "$tmp_workspace/wiki/projects/DemoProject/project-understanding-graph.md" >/dev/null
rg -n '"open_delta_count": 1|"Claim": 1' /tmp/research-pilot-mvp-b-summary.json >/dev/null
rg -n 'Demo claim needs evidence' /tmp/research-pilot-mvp-b-node.json >/dev/null
rg -n '"D0"' /tmp/research-pilot-mvp-b-open.json >/dev/null

echo "MVP-B smoke passed"
