#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./install.sh codex
  ./install.sh --help

Installs Research Pilot skills for Codex-compatible agents by linking
repo-local skills into ~/.agents/skills.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" != "codex" ]]; then
  usage >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$repo_root/skills"
target_dir="$HOME/.agents/skills"

if [[ ! -d "$source_dir" ]]; then
  echo "skills directory not found: $source_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"

linked=0
for skill_dir in "$source_dir"/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name="$(basename "$skill_dir")"
  target="$target_dir/$skill_name"

  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "refusing to replace non-symlink skill: $target" >&2
    exit 1
  fi

  ln -sfn "$skill_dir" "$target"
  echo "linked $target -> $skill_dir"
  linked=$((linked + 1))
done

if [[ "$linked" -eq 0 ]]; then
  echo "no skills found in $source_dir" >&2
  exit 1
fi

echo "Research Pilot Codex skills installed."
