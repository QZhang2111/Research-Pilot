#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_workspace="${TMPDIR:-/tmp}/research-pilot-mvp-a-smoke"

cd "$repo_root"

rm -rf "$tmp_workspace"
python3 tools/research_pilot_init.py "$tmp_workspace" --no-git >/tmp/research-pilot-mvp-a-init.log

test -f "$tmp_workspace/AGENTS.md"
test -f "$tmp_workspace/wiki/index.md"
test -f "$tmp_workspace/wiki/log.md"
test -f "$tmp_workspace/wiki/_system/workflows/first-run.md"
test -f "$tmp_workspace/.research-pilot/config.example.toml"
test -f "$tmp_workspace/.gitignore"

rg -n "Research Pilot" "$tmp_workspace/AGENTS.md" "$tmp_workspace/wiki/index.md" "$tmp_workspace/wiki/_system/workflows/first-run.md" >/dev/null

for pattern in \
  "/Users/" \
  "/Volumes/" \
  "ZOTERO_API_KEY=" \
  "zotero_api_key[[:space:]]*=" \
  "local_zotero_database" \
  "PRIVATE_RESEARCH_DATA"; do
  if rg -n "$pattern" README.md .codex install.sh skills tools templates >/tmp/research-pilot-mvp-a-leak.log 2>/dev/null; then
    echo "private leak pattern found: $pattern" >&2
    cat /tmp/research-pilot-mvp-a-leak.log >&2
    exit 1
  fi
done

echo "MVP-A smoke passed"
