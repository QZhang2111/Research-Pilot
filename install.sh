#!/usr/bin/env bash
# Research Pilot installer (macOS / Linux)
#
# Curl-pipe usage:
#   curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s codex
#
# Environment:
#   RP_REPO_URL      Override clone URL (default: official GitHub repo)
#   RP_DIR           Override clone destination (default: $HOME/.research-pilot/repo)
#   RP_PLUGIN_LINK   Override universal plugin symlink (default: $HOME/.research-pilot-plugin)
#   RP_BIN_DIR       Override helper command directory (default: $HOME/.research-pilot/bin)
#   RP_MARKETPLACE_PATH  Override plugin marketplace path (default: $HOME/.agents/plugins/marketplace.json)
#   RP_CATALOG_LINK      Override plugin catalog symlink (default: $HOME/plugins/research-pilot)
#   RP_CODEX_PROMPTS_DIR Override legacy Codex prompt cleanup directory (default: $HOME/.codex/prompts)

set -euo pipefail

REPO_URL="${RP_REPO_URL:-https://github.com/QZhang2111/Research-Pilot.git}"
REPO_DIR="${RP_DIR:-$HOME/.research-pilot/repo}"
PLUGIN_LINK="${RP_PLUGIN_LINK:-$HOME/.research-pilot-plugin}"
BIN_DIR="${RP_BIN_DIR:-$HOME/.research-pilot/bin}"
CODEX_PROMPTS_DIR="${RP_CODEX_PROMPTS_DIR:-$HOME/.codex/prompts}"
MARKETPLACE_PATH="${RP_MARKETPLACE_PATH:-$HOME/.agents/plugins/marketplace.json}"
CATALOG_LINK="${RP_CATALOG_LINK:-$HOME/plugins/research-pilot}"
LEGACY_CATALOG_LINK="${RP_LEGACY_CATALOG_LINK:-$HOME/.agents/plugins/research-pilot}"
MARKETPLACE_SOURCE_PATH="${RP_MARKETPLACE_SOURCE_PATH:-./plugins/research-pilot}"

platforms_table() {
  cat <<EOF
codex|$HOME/.agents/skills|per-skill
EOF
}

platform_ids() {
  platforms_table | cut -d'|' -f1
}

resolve_platform() {
  local id="$1"
  local row
  row="$(platforms_table | awk -F'|' -v id="$id" '$1==id {print; exit}')"
  if [[ -z "$row" ]]; then
    printf 'Unknown platform: %s\n' "$id" >&2
    printf 'Supported: %s\n' "$(platform_ids | tr '\n' ' ')" >&2
    exit 1
  fi
  printf '%s\n' "$row"
}

ensure_git() {
  if ! command -v git >/dev/null 2>&1; then
    printf 'git is required to install Research Pilot.\n' >&2
    exit 1
  fi
}

clone_or_update() {
  ensure_git
  if [[ -d "$REPO_DIR/.git" ]]; then
    printf -- '-> Updating Research Pilot checkout at %s\n' "$REPO_DIR"
    git -C "$REPO_DIR" pull --ff-only
  else
    printf -- '-> Cloning %s -> %s\n' "$REPO_URL" "$REPO_DIR"
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone "$REPO_URL" "$REPO_DIR"
  fi
}

skills_root() {
  printf '%s\n' "$REPO_DIR/skills"
}

list_skills() {
  local root
  root="$(skills_root)"
  if [[ ! -d "$root" ]]; then
    printf 'skills directory not found: %s\n' "$root" >&2
    exit 1
  fi
  local d
  for d in "$root"/*/; do
    [[ -d "$d" ]] || continue
    basename "$d"
  done
}

safe_symlink() {
  local source="$1"
  local target="$2"
  if [[ -e "$target" && ! -L "$target" ]]; then
    printf 'refusing to replace non-symlink path: %s\n' "$target" >&2
    exit 1
  fi
  ln -sfn "$source" "$target"
}

link_skills() {
  local target="$1"
  local style="$2"
  local root
  root="$(skills_root)"
  mkdir -p "$target"
  case "$style" in
    per-skill)
      local skill
      local linked=0
      while IFS= read -r skill; do
        safe_symlink "$root/$skill" "$target/$skill"
        printf '  linked %s -> %s\n' "$target/$skill" "$root/$skill"
        linked=$((linked + 1))
      done < <(list_skills)
      if [[ "$linked" -eq 0 ]]; then
        printf 'no skills found in %s\n' "$root" >&2
        exit 1
      fi
      ;;
    *)
      printf 'Unknown install style: %s\n' "$style" >&2
      exit 1
      ;;
  esac
}

unlink_skills() {
  local target="$1"
  local style="$2"
  [[ -d "$target" ]] || return 0
  case "$style" in
    per-skill)
      if [[ -d "$(skills_root)" ]]; then
        local skill
        while IFS= read -r skill; do
          [[ -L "$target/$skill" ]] && rm -f "$target/$skill"
        done < <(list_skills)
      else
        local link resolved
        for link in "$target"/*; do
          [[ -L "$link" ]] || continue
          resolved="$(readlink "$link" 2>/dev/null || true)"
          [[ "$resolved" == *"/.research-pilot/repo/skills/"* || "$resolved" == "$REPO_DIR/skills/"* ]] || continue
          rm -f "$link"
        done
      fi
      ;;
    *)
      printf 'Unknown uninstall style: %s\n' "$style" >&2
      exit 1
      ;;
  esac
}

link_plugin_root() {
  safe_symlink "$REPO_DIR" "$PLUGIN_LINK"
  printf '  linked %s -> %s\n' "$PLUGIN_LINK" "$REPO_DIR"
}

unlink_plugin_root() {
  [[ -L "$PLUGIN_LINK" ]] && rm -f "$PLUGIN_LINK"
}

link_plugin_catalog() {
  mkdir -p "$(dirname "$CATALOG_LINK")"
  safe_symlink "$REPO_DIR" "$CATALOG_LINK"
  printf '  linked %s -> %s\n' "$CATALOG_LINK" "$REPO_DIR"
}

unlink_plugin_catalog() {
  [[ -L "$CATALOG_LINK" ]] && rm -f "$CATALOG_LINK"
}

cleanup_legacy_plugin_catalog() {
  [[ "$LEGACY_CATALOG_LINK" != "$CATALOG_LINK" ]] || return 0
  [[ -L "$LEGACY_CATALOG_LINK" ]] || return 0
  local resolved
  resolved="$(readlink "$LEGACY_CATALOG_LINK" 2>/dev/null || true)"
  [[ "$resolved" == "$REPO_DIR" || "$resolved" == *"/.research-pilot/repo" ]] || return 0
  rm -f "$LEGACY_CATALOG_LINK"
  printf '  removed legacy catalog link %s\n' "$LEGACY_CATALOG_LINK"
}

write_marketplace_entry() {
  mkdir -p "$(dirname "$MARKETPLACE_PATH")"
  MARKETPLACE_PATH="$MARKETPLACE_PATH" MARKETPLACE_SOURCE_PATH="$MARKETPLACE_SOURCE_PATH" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["MARKETPLACE_PATH"])
source_path = os.environ["MARKETPLACE_SOURCE_PATH"]
if path.exists():
    data = json.loads(path.read_text())
else:
    data = {
        "name": "local-plugins",
        "interface": {"displayName": "Local Plugins"},
        "plugins": [],
    }

data.setdefault("name", "local-plugins")
data.setdefault("interface", {}).setdefault("displayName", "Local Plugins")
plugins = [item for item in data.get("plugins", []) if item.get("name") != "research-pilot"]
plugins.append(
    {
        "name": "research-pilot",
        "source": {"source": "local", "path": source_path},
        "policy": {
            "installation": "INSTALLED_BY_DEFAULT",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }
)
data["plugins"] = plugins
path.write_text(json.dumps(data, indent=2) + "\n")
PY
  printf '  registered marketplace entry %s\n' "$MARKETPLACE_PATH"
}

remove_marketplace_entry() {
  [[ -f "$MARKETPLACE_PATH" ]] || return 0
  MARKETPLACE_PATH="$MARKETPLACE_PATH" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["MARKETPLACE_PATH"])
data = json.loads(path.read_text())
data["plugins"] = [item for item in data.get("plugins", []) if item.get("name") != "research-pilot"]
path.write_text(json.dumps(data, indent=2) + "\n")
PY
  printf '  removed marketplace entry %s\n' "$MARKETPLACE_PATH"
}

link_bins() {
  mkdir -p "$BIN_DIR"
  safe_symlink "$REPO_DIR/tools/research_pilot_init.py" "$BIN_DIR/research-pilot-init"
  printf '  linked %s -> %s\n' "$BIN_DIR/research-pilot-init" "$REPO_DIR/tools/research_pilot_init.py"
}

unlink_bins() {
  [[ -L "$BIN_DIR/research-pilot-init" ]] && rm -f "$BIN_DIR/research-pilot-init"
}

cleanup_legacy_prompt_commands() {
  local command
  for command in research-init research-dashboard; do
    if [[ -L "$CODEX_PROMPTS_DIR/$command.md" ]]; then
      rm -f "$CODEX_PROMPTS_DIR/$command.md"
      printf '  removed legacy prompt link %s\n' "$CODEX_PROMPTS_DIR/$command.md"
    fi
  done
}

unlink_prompt_commands() {
  cleanup_legacy_prompt_commands
}

link_installation() {
  local id="${1:-codex}"
  local row target style
  row="$(resolve_platform "$id")"
  target="$(printf '%s\n' "$row" | cut -d'|' -f2)"
  style="$(printf '%s\n' "$row" | cut -d'|' -f3)"

  printf -- '-> Linking skills for %s\n' "$id"
  link_skills "$target" "$style"
  printf -- '-> Linking plugin root\n'
  link_plugin_root
  printf -- '-> Registering plugin catalog\n'
  cleanup_legacy_plugin_catalog
  link_plugin_catalog
  write_marketplace_entry
  printf -- '-> Linking helper commands\n'
  link_bins
  printf -- '-> Cleaning legacy Codex prompt links\n'
  cleanup_legacy_prompt_commands
}

print_post_install_guidance() {
  printf 'Health check:\n'
  printf '  python3 "%s/tools/plugin_health.py" --plugin-root "%s" --json\n' "$REPO_DIR" "$REPO_DIR"
  printf 'Restart Codex after install or update so plugin metadata reloads.\n'
  printf 'Interface: chat with the agent. Ask: "Use Research Pilot to track my research project."\n'
  printf 'No Research Pilot command memorization is required. Legacy /research-* prompt links are removed from %s.\n' "$CODEX_PROMPTS_DIR"
}

cmd_install() {
  local id="${1:-codex}"
  clone_or_update
  link_installation "$id"

  printf '\nInstalled Research Pilot for %s\n' "$id"
  printf 'Plugin source: %s\n' "$REPO_DIR"
  printf 'Plugin catalog: %s\n' "$MARKETPLACE_PATH"
  printf 'Next step:\n'
  printf '  Restart Codex, then ask: "Use Research Pilot to track my research project."\n'
  printf 'Compatibility helper kept for agents and troubleshooting: %s/research-pilot-init\n' "$BIN_DIR"
  print_post_install_guidance
}

cmd_update() {
  if [[ ! -d "$REPO_DIR/.git" ]]; then
    printf 'No Research Pilot installation found at %s. Run install first.\n' "$REPO_DIR" >&2
    exit 1
  fi
  clone_or_update
  link_installation codex
  printf '\nUpdated Research Pilot for codex\n'
  printf 'Plugin source: %s\n' "$REPO_DIR"
  printf 'Plugin catalog: %s\n' "$MARKETPLACE_PATH"
  print_post_install_guidance
}

cmd_uninstall() {
  local id="${1:-codex}"
  local row target style
  row="$(resolve_platform "$id")"
  target="$(printf '%s\n' "$row" | cut -d'|' -f2)"
  style="$(printf '%s\n' "$row" | cut -d'|' -f3)"

  printf -- '-> Removing Research Pilot links for %s\n' "$id"
  unlink_skills "$target" "$style"
  unlink_plugin_root
  unlink_plugin_catalog
  cleanup_legacy_plugin_catalog
  remove_marketplace_entry
  unlink_bins
  unlink_prompt_commands

  printf '\nUninstalled Research Pilot links for %s\n' "$id"
  printf 'Hidden checkout kept: %s\n' "$REPO_DIR"
  printf 'Remove it manually if wanted:\n'
  printf '  rm -rf "%s"\n' "$(dirname "$REPO_DIR")"
}

usage() {
  cat <<USAGE
Research Pilot installer

Usage:
  install.sh [codex]                 Install for Codex (default)
  install.sh --update                Pull latest hidden checkout and relink
  install.sh --uninstall [codex]     Remove links, keep hidden checkout
  install.sh --help

Curl-pipe:
  curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s codex

Environment:
  RP_REPO_URL      Override clone URL (default: official GitHub repo)
  RP_DIR           Override clone destination (default: \$HOME/.research-pilot/repo)
  RP_PLUGIN_LINK   Override plugin symlink (default: \$HOME/.research-pilot-plugin)
  RP_BIN_DIR       Override helper command directory (default: \$HOME/.research-pilot/bin)
  RP_CODEX_PROMPTS_DIR Override legacy Codex prompt cleanup directory (default: \$HOME/.codex/prompts)
  RP_MARKETPLACE_PATH  Override plugin marketplace path (default: \$HOME/.agents/plugins/marketplace.json)
  RP_CATALOG_LINK      Override plugin catalog symlink (default: \$HOME/plugins/research-pilot)
  RP_MARKETPLACE_SOURCE_PATH Override marketplace source path (default: ./plugins/research-pilot)
USAGE
}

main() {
  case "${1:-}" in
    -h|--help)
      usage
      ;;
    --update)
      cmd_update
      ;;
    --uninstall)
      shift || true
      cmd_uninstall "${1:-codex}"
      ;;
    "")
      cmd_install codex
      ;;
    -*)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
    *)
      cmd_install "$1"
      ;;
  esac
}

main "$@"
