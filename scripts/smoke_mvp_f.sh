#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-f-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-f-init.log
mkdir -p "$tmp_workspace/wiki/graphs/events/projects"
cp examples/demo/events/demo-project.jsonl "$tmp_workspace/wiki/graphs/events/projects/DemoProject.jsonl"
python3 tools/build_graph_db.py --repo "$tmp_workspace" --project DemoProject >/tmp/research-pilot-mvp-f-db.log
python3 tools/project_gap_cli.py detect --repo "$tmp_workspace" --project DemoProject --json >/tmp/research-pilot-mvp-f-gaps.json
python3 tools/project_next_action_cli.py suggest --repo "$tmp_workspace" --project DemoProject --json >/tmp/research-pilot-mvp-f-next.json

rg -n '"valid": true' /tmp/research-pilot-mvp-f-gaps.json >/dev/null
rg -n '"valid": true' /tmp/research-pilot-mvp-f-next.json >/dev/null
rg -n '"human_gate_review"' /tmp/research-pilot-mvp-f-next.json >/dev/null

echo "MVP-F smoke passed"
