#!/usr/bin/env python3
"""Initialize a private Research Pilot workspace from public templates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


WORKSPACE_GITIGNORE = """# Research Pilot private/generated data
.research-pilot/config.toml
.research-pilot/generated/
.dashboard/
wiki/graphs/graph.db
wiki/graphs/snapshots/
raw/papers/
raw/**/*.pdf
*.pdf
output/
"""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def copy_template_tree(template_root: Path, target_root: Path, overwrite: bool) -> None:
    if not template_root.is_dir():
        raise SystemExit(f"template directory not found: {template_root}")

    for source in template_root.rglob("*"):
        relative = source.relative_to(template_root)
        target = target_root / relative

        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            continue
        shutil.copy2(source, target)


def ensure_gitignore(target_root: Path) -> None:
    gitignore = target_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

    marker = "# Research Pilot private/generated data"
    if marker in existing:
        return

    if not existing:
        gitignore.write_text(WORKSPACE_GITIGNORE, encoding="utf-8")
        return

    separator = "" if existing.endswith("\n") else "\n"
    gitignore.write_text(f"{existing}{separator}\n{WORKSPACE_GITIGNORE}", encoding="utf-8")


def maybe_git_init(target_root: Path, no_git: bool) -> None:
    if no_git or (target_root / ".git").exists():
        return

    subprocess.run(["git", "init"], cwd=target_root, check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a private Research Pilot workspace."
    )
    parser.add_argument("workspace", help="Path to the private workspace to create or update.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing template files in the target workspace.",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Do not run git init in the target workspace.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    target_root = Path(args.workspace).expanduser().resolve()
    template_root = repo_root() / "templates" / "workspace"

    target_root.mkdir(parents=True, exist_ok=True)
    copy_template_tree(template_root, target_root, args.overwrite)
    ensure_gitignore(target_root)
    maybe_git_init(target_root, args.no_git)

    print(f"Research Pilot workspace initialized: {target_root}")
    print("")
    print("Next steps:")
    print(f"  cd {target_root}")
    print("  Start your agent in this directory.")
    print('  Ask: "Use Research Pilot to inspect this workspace."')
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
