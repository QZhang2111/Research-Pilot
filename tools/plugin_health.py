#!/usr/bin/env python3
"""Inspect Research Pilot plugin installation health."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def read_version(root: str | Path) -> str:
    manifest = Path(root).expanduser() / ".codex-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    version = data.get("version")
    return version if isinstance(version, str) else ""


def git_commit(root: str | Path) -> str:
    plugin_root = Path(root).expanduser()
    if not (plugin_root / ".git").exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(plugin_root), "rev-parse", "--short", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def inspect_plugin(root: str | Path) -> dict[str, object]:
    plugin_root = Path(root).expanduser().resolve()
    home = Path.home()
    bin_dir = Path(os.environ.get("RP_BIN_DIR", home / ".research-pilot" / "bin")).expanduser()
    prompts_dir = Path(os.environ.get("RP_CODEX_PROMPTS_DIR", home / ".codex" / "prompts")).expanduser()
    command_names = ("research-init", "research-dashboard")
    skill_names = ("research-pilot", "research-pilot-first-run")

    return {
        "source_path": str(plugin_root),
        "version": read_version(plugin_root),
        "git_commit": git_commit(plugin_root),
        "command_files": {
            name: (plugin_root / "commands" / f"{name}.md").is_file() for name in command_names
        },
        "prompt_links": {
            name: (prompts_dir / f"{name}.md").exists() for name in command_names
        },
        "commands_visible": "unknown",
        "skill_links": {
            name: (home / ".agents" / "skills" / name).exists() for name in skill_names
        },
        "helper_bins": {
            "research-pilot-init": (bin_dir / "research-pilot-init").exists()
        },
        "dashboard_fallback_available": (plugin_root / "tools" / "research_browser_server.py").is_file(),
        "update_command": (
            "curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh "
            "-o /tmp/research-pilot-install.sh && bash /tmp/research-pilot-install.sh --update"
        ),
        "restart_guidance": (
            "Restart Codex after install or update. Research Pilot also links command prompts into "
            "~/.codex/prompts for Codex builds that load custom slash prompts. If slash commands are "
            "not visible, ask the agent to run the Research Pilot command fallback from the plugin root."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Research Pilot plugin installation health.")
    parser.add_argument("--plugin-root", default=".", help="Research Pilot plugin root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    print(json.dumps(inspect_plugin(args.plugin_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
