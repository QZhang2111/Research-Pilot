#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-e-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-e-init.log
python3 tools/source_intake_cli.py status --json >/tmp/research-pilot-mvp-e-status.json
python3 tools/source_intake_cli.py intake --repo "$tmp_workspace" --project DemoProject --paper paper-a --title "Paper A" --zotero-key ABC123 --doi 10.000/demo --json >/tmp/research-pilot-mvp-e-intake.json

test -f "$tmp_workspace/wiki/projects/DemoProject/papers/paper-a/index.md"
rg -n '"mode": "manual-fallback"|"mode": "zotero-env"' /tmp/research-pilot-mvp-e-status.json >/dev/null
rg -n 'zotero:item:ABC123|doi:10.000/demo' "$tmp_workspace/wiki/projects/DemoProject/papers/paper-a/index.md" >/dev/null
rg -n '"valid": true' /tmp/research-pilot-mvp-e-intake.json >/dev/null

echo "MVP-E smoke passed"
