#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-g-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-g-init.log
mkdir -p "$tmp_workspace/wiki/graphs/events/projects"
cp examples/archive/legacy-demo-fixtures/demo/events/demo-project.jsonl "$tmp_workspace/wiki/graphs/events/projects/DemoProject.jsonl"
python3 tools/build_graph_db.py --repo "$tmp_workspace" --project DemoProject >/tmp/research-pilot-mvp-g-db.log

python3 tools/project_experiment_cli.py suggest --repo "$tmp_workspace" --project DemoProject --target C0 --json >/tmp/research-pilot-mvp-g-experiment.json
python3 tools/gap_search_cli.py contract --repo "$tmp_workspace" --project DemoProject --target RL0 --json >/tmp/research-pilot-mvp-g-contract.json
python3 tools/research_gap_discovery_cli.py run --repo "$tmp_workspace" --project DemoProject --gap RL0 --source none --json >/tmp/research-pilot-mvp-g-discovery.json

rg -n '"valid": true' /tmp/research-pilot-mvp-g-experiment.json >/dev/null
rg -n '"experiment_proposal"' /tmp/research-pilot-mvp-g-experiment.json >/dev/null
rg -n '"valid": true' /tmp/research-pilot-mvp-g-contract.json >/dev/null
rg -n '"search_contract"' /tmp/research-pilot-mvp-g-contract.json >/dev/null
rg -n '"valid": true' /tmp/research-pilot-mvp-g-discovery.json >/dev/null

echo "MVP-G smoke passed"
