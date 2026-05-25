#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-c-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-c-init.log
mkdir -p "$tmp_workspace/wiki/graphs/events/projects"
cp examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl "$tmp_workspace/wiki/graphs/events/projects/DemoProject.jsonl"

python3 tools/build_graph_db.py --repo "$tmp_workspace" --project DemoProject >/tmp/research-pilot-mvp-c-db.log
python3 tools/graph_delta_cli.py dry-run --repo "$tmp_workspace" --project DemoProject --delta examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json --json >/tmp/research-pilot-mvp-c-dry-run.json
python3 tools/graph_delta_cli.py register --repo "$tmp_workspace" --project DemoProject --delta examples/archive/legacy-demo-fixtures/demo/deltas/refine-demo-claim.json --json >/tmp/research-pilot-mvp-c-register.json
python3 tools/graph_delta_cli.py decide --repo "$tmp_workspace" --project DemoProject --id D1 --decision accept --decision-note "Approved smoke delta." --json >/tmp/research-pilot-mvp-c-accept.json
python3 tools/graph_query_cli.py node --repo "$tmp_workspace" --project DemoProject --id C0 --json >/tmp/research-pilot-mvp-c-node.json

rg -n '"valid": true' /tmp/research-pilot-mvp-c-dry-run.json >/dev/null
rg -n '"registered": true' /tmp/research-pilot-mvp-c-register.json >/dev/null
rg -n '"decision": "accepted"' /tmp/research-pilot-mvp-c-accept.json >/dev/null
rg -n 'Demo claim is supported by demo evidence' /tmp/research-pilot-mvp-c-node.json >/dev/null

echo "MVP-C smoke passed"
