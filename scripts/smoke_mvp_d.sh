#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-d-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-d-init.log
python3 tools/paper_dossier_cli.py create --repo "$tmp_workspace" --project DemoProject --paper paper-a --title "Paper A" --source-ref doi:10.000/demo --json >/tmp/research-pilot-mvp-d-create.json
python3 tools/paper_dossier_cli.py validate --dossier "$tmp_workspace/wiki/projects/DemoProject/papers/paper-a/index.md" --json >/tmp/research-pilot-mvp-d-validate.json
python3 tools/paper_dossier_cli.py export-deltas --dossier "$tmp_workspace/wiki/projects/DemoProject/papers/paper-a/index.md" --output-dir "$tmp_workspace/.research-pilot/generated/deltas" --json >/tmp/research-pilot-mvp-d-export.json

test -f "$tmp_workspace/.research-pilot/generated/deltas/D1.json"
rg -n '"valid": true' /tmp/research-pilot-mvp-d-create.json >/dev/null
rg -n '"delta_count": 1' /tmp/research-pilot-mvp-d-validate.json >/dev/null
rg -n 'D1.json' /tmp/research-pilot-mvp-d-export.json >/dev/null

echo "MVP-D smoke passed"
