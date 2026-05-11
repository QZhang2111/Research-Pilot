#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

for pattern in \
  "PersonalResearchWiki" \
  "CVPR2026" \
  "/Users/qing" \
  "submission_affordance"; do
  if rg -n "$pattern" . --glob '!/.git/**' --glob '!scripts/release_check.sh'; then
    echo "release check failed: leaked pattern $pattern" >&2
    exit 1
  fi
done

if rg -n 'ZOTERO_API_KEY=[^"[:space:]]' . --glob '!/.git/**' --glob '!scripts/release_check.sh'; then
  echo "release check failed: possible Zotero API key assignment" >&2
  exit 1
fi

if find . -path ./.git -prune -o \( -name '*.pdf' -o -name '*.sqlite' -o -name 'graph.db' -o -path './.dashboard/*' \) -print | rg .; then
  echo "release check failed: generated/private artifact found" >&2
  exit 1
fi

python3 -m unittest \
  tests.test_codex_plugin_manifest \
  tests.test_plugin_commands \
  tests.test_hidden_installer \
  tests.test_first_run_protocol \
  tests.test_graph_schema_contracts \
  tests.test_source_intake_cli \
  tests.test_graph_core \
  tests.test_project_graph_report \
  tests.test_graph_delta_loop \
  tests.test_paper_dossier_cli \
  tests.test_dashboard_public \
  tests.test_gap_next_action_cli \
  tests.test_gap_search_experiment_cli \
  tests.test_zotero_bridge_public

for smoke in \
  scripts/smoke_mvp_a.sh \
  scripts/smoke_mvp_b.sh \
  scripts/smoke_mvp_c.sh \
  scripts/smoke_mvp_d.sh \
  scripts/smoke_mvp_e.sh \
  scripts/smoke_mvp_f.sh \
  scripts/smoke_mvp_g.sh \
  scripts/smoke_dashboard.sh; do
  "$smoke"
done

echo "release check passed"
