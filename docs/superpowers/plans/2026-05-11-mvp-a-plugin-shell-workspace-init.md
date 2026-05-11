# Research Pilot MVP-A Plugin Shell And Workspace Init Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first public extraction slice: a Codex-installable Research Pilot shell that can initialize a private research workspace with no private data.

**Architecture:** The public repository is the plugin source. The user workspace is a separate private directory created by `tools/research_pilot_init.py` from bundled templates. MVP-A installs only the router skill and initializer; graph tools, Zotero bridge, dashboard, and full workflows are deferred to MVP-B/C/D.

**Tech Stack:** Markdown, Bash, Python 3 standard library, Git.

---

## Scope Boundary

MVP-A builds:

- public README boundary;
- public `.gitignore` guardrails;
- `.codex/INSTALL.md`;
- `install.sh`;
- `skills/research-pilot/SKILL.md` router skeleton;
- `tools/research_pilot_init.py`;
- workspace templates under `templates/workspace/`;
- one smoke test script for workspace init and private-leak scan.

MVP-A does not build:

- graph DB/query/delta tools;
- Zotero bridge;
- dashboard;
- paper deep-read workflows;
- gap detection;
- Codex marketplace metadata.

The existing design spec currently says "Core graph tools can run against the initialized workspace" under MVP-A. Treat that as MVP-B scope. MVP-A only guarantees the initialized workspace is graph-ready.

## File Structure

Create or modify these files:

```text
README.md
.gitignore
.codex/INSTALL.md
install.sh
skills/research-pilot/SKILL.md
tools/research_pilot_init.py
scripts/smoke_mvp_a.sh
templates/workspace/AGENTS.md
templates/workspace/wiki/index.md
templates/workspace/wiki/log.md
templates/workspace/wiki/projects/.gitkeep
templates/workspace/wiki/graphs/events/.gitkeep
templates/workspace/wiki/graphs/schema/.gitkeep
templates/workspace/wiki/_system/workflows/.gitkeep
templates/workspace/wiki/_system/templates/.gitkeep
templates/workspace/.research-pilot/config.example.toml
```

Responsibilities:

- `README.md`: public positioning and MVP-A quick start.
- `.gitignore`: prevent generated/private artifacts from entering the public repo.
- `.codex/INSTALL.md`: agent-readable install instructions.
- `install.sh`: clone/update/link skills for Codex-compatible skill directories.
- `skills/research-pilot/SKILL.md`: primary user-facing router and workspace-init instructions.
- `tools/research_pilot_init.py`: deterministic workspace initializer.
- `scripts/smoke_mvp_a.sh`: reproducible smoke verification.
- `templates/workspace/**`: private workspace skeleton copied by the initializer.

## Task 1: Public Boundary README And Ignore Rules

**Files:**

- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Replace README with Research Pilot boundary statement**

Write `README.md` with this content:

````markdown
# Research Pilot

Research Pilot is an agent-operated research memory plugin.

It helps AI agents initialize and operate a private research workspace where papers, project questions, claims, evidence, warrants, limitations, graph deltas, and human decisions can accumulate over time.

## Status

Experimental public extraction.

MVP-A only includes:

- Codex-compatible install instructions;
- a `research-pilot` router skill skeleton;
- a private workspace initializer;
- workspace templates with no private research data.

Graph tools, Zotero workflows, dashboard support, and full paper-to-delta automation are extracted in later MVP slices.

## Mental Model

```text
Research Pilot public repo = plugin source and tools
User research workspace = private research memory
Agent chat = primary interface
Markdown files = long-term agent-readable memory
Graph events = append-only project-understanding truth
Generated DB/dashboard files = rebuildable read models
```

## Source Boundaries

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only project understanding graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = optional browser view over read models and wiki state
chat/agent = primary control surface
```

## Quick Start

Install skills for Codex-compatible agents:

```bash
./install.sh codex
```

Initialize a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Then start your agent inside that workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

## Private Data Rule

Do not put real paper PDFs, Zotero API keys, local Zotero databases, private project dossiers, generated private dashboard data, or personal research memory into this public repo.

Each user should keep their research memory in their own private workspace.
````

- [ ] **Step 2: Append Research Pilot public safety ignores**

Append this block to `.gitignore`:

```gitignore

# Research Pilot private/generated data
.research-pilot/config.toml
.dashboard/
wiki/graphs/graph.db
wiki/graphs/snapshots/
wiki/graphs/events/
raw/papers/
raw/**/*.pdf
*.pdf
output/

# Local plugin installation checkouts and symlink scratch
.research-pilot-install/
```

- [ ] **Step 3: Verify README contains public/private boundary**

Run:

```bash
rg -n "public repo|private research workspace|plugin source|Private Data Rule" README.md
```

Expected: four or more matching lines.

- [ ] **Step 4: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: define Research Pilot public plugin boundary"
```

## Task 2: Workspace Template Skeleton

**Files:**

- Create: `templates/workspace/AGENTS.md`
- Create: `templates/workspace/wiki/index.md`
- Create: `templates/workspace/wiki/log.md`
- Create: `templates/workspace/wiki/projects/.gitkeep`
- Create: `templates/workspace/wiki/graphs/events/.gitkeep`
- Create: `templates/workspace/wiki/graphs/schema/.gitkeep`
- Create: `templates/workspace/wiki/_system/workflows/.gitkeep`
- Create: `templates/workspace/wiki/_system/templates/.gitkeep`
- Create: `templates/workspace/.research-pilot/config.example.toml`

- [ ] **Step 1: Create template directories**

Run:

```bash
mkdir -p templates/workspace/wiki/projects
mkdir -p templates/workspace/wiki/graphs/events
mkdir -p templates/workspace/wiki/graphs/schema
mkdir -p templates/workspace/wiki/_system/workflows
mkdir -p templates/workspace/wiki/_system/templates
mkdir -p templates/workspace/.research-pilot
```

Expected: command exits successfully.

- [ ] **Step 2: Create workspace AGENTS template**

Create `templates/workspace/AGENTS.md`:

````markdown
# Research Pilot Workspace Instructions

This directory is a private Research Pilot workspace.

## Core Rule

Agent operates the workspace through chat. Files are durable memory and execution state, not the main human UI.

## Source Boundaries

```text
Zotero = paper metadata, PDFs, collections, tags, reading status mirror
wiki = digested research understanding and project files
wiki/graphs/events = append-only project understanding graph truth
graph.db/snapshots/reports = rebuildable read models
dashboard = optional browser view
chat/agent = primary control surface
```

## Human Gate

Agent may propose, summarize, lint, query, and draft graph deltas.

Only the human may approve:

- project-core papers;
- global-core memory;
- graph delta acceptance;
- research direction changes;
- experiment result interpretation.

## Private Data

Do not publish this workspace unless the human explicitly says it is sanitized.
Do not commit PDFs, API keys, local Zotero databases, or generated SQLite/dashboard read models.
````

- [ ] **Step 3: Create workspace index template**

Create `templates/workspace/wiki/index.md`:

```markdown
---
title: "Research Workspace Index"
type: index
created: 1970-01-01
updated: 1970-01-01
domains: []
tags: [index]
aliases: []
sources: []
status: active
human_review: pending
confidence: medium
---

# Research Workspace Index

This workspace was initialized by Research Pilot.

## Projects

No projects yet.

## System

- Workflows: `wiki/_system/workflows/`
- Templates: `wiki/_system/templates/`
- Graph events: `wiki/graphs/events/`
```

- [ ] **Step 4: Create workspace log template**

Create `templates/workspace/wiki/log.md`:

```markdown
---
title: "Research Workspace Log"
type: log
created: 1970-01-01
updated: 1970-01-01
domains: []
tags: [log]
aliases: []
sources: []
status: active
human_review: pending
confidence: medium
---

# Research Workspace Log

Append-only operation log.
```

- [ ] **Step 5: Create config example**

Create `templates/workspace/.research-pilot/config.example.toml`:

```toml
# Research Pilot workspace configuration.
# Copy to config.toml and fill values when ready.

[workspace]
name = "My Research Workspace"

[zotero]
# Required for normal paper workflows in later MVP slices.
# Keep real credentials out of public repos.
library_id = ""
library_type = "user"
api_key_env = "ZOTERO_API_KEY"

[paths]
wiki = "wiki"
graph_events = "wiki/graphs/events"
```

- [ ] **Step 6: Create .gitkeep files**

Run:

```bash
touch templates/workspace/wiki/projects/.gitkeep
touch templates/workspace/wiki/graphs/events/.gitkeep
touch templates/workspace/wiki/graphs/schema/.gitkeep
touch templates/workspace/wiki/_system/workflows/.gitkeep
touch templates/workspace/wiki/_system/templates/.gitkeep
```

Expected: command exits successfully.

- [ ] **Step 7: Verify template file list**

Run:

```bash
find templates/workspace -type f | sort
```

Expected output includes:

```text
templates/workspace/.research-pilot/config.example.toml
templates/workspace/AGENTS.md
templates/workspace/wiki/_system/templates/.gitkeep
templates/workspace/wiki/_system/workflows/.gitkeep
templates/workspace/wiki/graphs/events/.gitkeep
templates/workspace/wiki/graphs/schema/.gitkeep
templates/workspace/wiki/index.md
templates/workspace/wiki/log.md
templates/workspace/wiki/projects/.gitkeep
```

- [ ] **Step 8: Commit**

```bash
git add templates/workspace
git commit -m "feat: add private workspace template skeleton"
```

## Task 3: Workspace Initializer

**Files:**

- Create: `tools/research_pilot_init.py`

- [ ] **Step 1: Create initializer script**

Create `tools/research_pilot_init.py`:

```python
#!/usr/bin/env python3
"""Initialize a private Research Pilot workspace from bundled templates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "workspace"


def copy_template(target: Path, *, force: bool = False) -> list[Path]:
    if not TEMPLATE_ROOT.exists():
        raise FileNotFoundError(f"template root not found: {TEMPLATE_ROOT}")
    copied: list[Path] = []
    for source in sorted(path for path in TEMPLATE_ROOT.rglob("*") if path.is_file()):
        rel = source.relative_to(TEMPLATE_ROOT)
        dest = target / rel
        if dest.exists() and not force:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        copied.append(dest)
    return copied


def ensure_gitignore(target: Path) -> Path:
    gitignore = target / ".gitignore"
    block = """# Research Pilot generated/private files
.research-pilot/config.toml
wiki/graphs/graph.db
wiki/graphs/snapshots/
.dashboard/
raw/papers/
raw/**/*.pdf
*.pdf
"""
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        if "# Research Pilot generated/private files" in text:
            return gitignore
        gitignore.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")
    else:
        gitignore.write_text(block, encoding="utf-8")
    return gitignore


def init_git(target: Path) -> bool:
    if (target / ".git").exists():
        return False
    subprocess.run(["git", "init"], cwd=target, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize a private Research Pilot workspace.")
    parser.add_argument("workspace", help="Workspace directory to create or update.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files.")
    parser.add_argument("--no-git", action="store_true", help="Do not initialize a git repository.")
    args = parser.parse_args(argv)

    target = Path(args.workspace).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    copied = copy_template(target, force=args.force)
    gitignore = ensure_gitignore(target)
    git_created = False
    if not args.no_git:
        try:
            git_created = init_git(target)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"warning: could not initialize git repository: {exc}", file=sys.stderr)

    print(f"Research Pilot workspace: {target}")
    print(f"Template files copied: {len(copied)}")
    print(f"Gitignore: {gitignore.relative_to(target)}")
    print(f"Git initialized: {'yes' if git_created else 'no'}")
    print("")
    print("Next steps:")
    print("1. cd into the workspace")
    print("2. copy .research-pilot/config.example.toml to .research-pilot/config.toml when configuring Zotero")
    print("3. start your agent and ask Research Pilot to inspect the workspace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Make script executable**

Run:

```bash
chmod +x tools/research_pilot_init.py
```

Expected: command exits successfully.

- [ ] **Step 3: Run initializer in a temporary location**

Run:

```bash
rm -rf /tmp/research-pilot-mvp-a-workspace
python3 tools/research_pilot_init.py /tmp/research-pilot-mvp-a-workspace --no-git
```

Expected output contains:

```text
Research Pilot workspace: /tmp/research-pilot-mvp-a-workspace
Template files copied:
Git initialized: no
```

- [ ] **Step 4: Verify initialized files**

Run:

```bash
test -f /tmp/research-pilot-mvp-a-workspace/AGENTS.md
test -f /tmp/research-pilot-mvp-a-workspace/wiki/index.md
test -f /tmp/research-pilot-mvp-a-workspace/wiki/log.md
test -f /tmp/research-pilot-mvp-a-workspace/.research-pilot/config.example.toml
test -f /tmp/research-pilot-mvp-a-workspace/.gitignore
```

Expected: command exits successfully.

- [ ] **Step 5: Commit**

```bash
git add tools/research_pilot_init.py
git commit -m "feat: add Research Pilot workspace initializer"
```

## Task 4: Router Skill Skeleton

**Files:**

- Create: `skills/research-pilot/SKILL.md`

- [ ] **Step 1: Create router skill directory**

Run:

```bash
mkdir -p skills/research-pilot
```

Expected: command exits successfully.

- [ ] **Step 2: Create router SKILL.md**

Create `skills/research-pilot/SKILL.md`:

````markdown
---
name: research-pilot
description: Use when the user wants to initialize, inspect, or operate a Research Pilot workspace for agent-operated research memory.
argument-hint: "[init <path>|inspect]"
---

# Research Pilot

Research Pilot is the primary router skill for agent-operated research memory.

## Current MVP-A Capabilities

- Explain plugin vs workspace boundary.
- Initialize a private research workspace.
- Inspect whether the current directory looks like a Research Pilot workspace.

Graph querying, Zotero paper workflows, dashboard launching, and paper-to-delta automation are extracted in later MVP slices.

## Workspace Detection

A directory is a Research Pilot workspace when it has:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/config.example.toml or .research-pilot/config.toml
```

## Intent Routing

### Initialize Workspace

When the user asks to initialize/create/set up a research workspace:

1. Resolve the requested path. If no path is provided, ask for one concise path.
2. Resolve the plugin root by locating the installed `research-pilot` skill symlink and going two directories up to the Research Pilot repo checkout.
3. Run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

4. Report the workspace path and next steps.

### Inspect Workspace

When the user asks to inspect current Research Pilot status during MVP-A:

1. Check for the workspace detection files.
2. If present, report that the workspace skeleton is initialized.
3. If absent, explain that the user should run initialization first.

## Boundaries

Do not claim graph workflows, Zotero workflows, dashboard support, or paper deep-read automation are available until those MVP slices are extracted.

Do not store private research data in the public plugin repo.
````

- [ ] **Step 3: Verify skill metadata exists**

Run:

```bash
rg -n "name: research-pilot|MVP-A|Workspace Detection" skills/research-pilot/SKILL.md
```

Expected: three matching lines.

- [ ] **Step 4: Commit**

```bash
git add skills/research-pilot/SKILL.md
git commit -m "feat: add Research Pilot router skill skeleton"
```

## Task 5: Codex Install Path

**Files:**

- Create: `.codex/INSTALL.md`
- Create: `install.sh`

- [ ] **Step 1: Create .codex directory**

Run:

```bash
mkdir -p .codex
```

Expected: command exits successfully.

- [ ] **Step 2: Create Codex install instructions**

Create `.codex/INSTALL.md`:

````markdown
# Research Pilot Codex Install

This installer makes Research Pilot skills available to Codex-compatible agents.

## Install From A Local Checkout

From the Research Pilot repo root:

```bash
./install.sh codex
```

The installer links each skill directory from this repo into:

```text
~/.agents/skills/
```

## Initialize A Workspace

After installation, create a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Then run Codex from inside the workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

## Current Status

MVP-A installs the router skill and workspace initializer only.

Graph workflows, Zotero workflows, dashboard support, and deep-read automation are later MVP slices.
````

- [ ] **Step 3: Create install.sh**

Create `install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./install.sh codex
  ./install.sh --help

Installs Research Pilot skills by symlinking this repo's skills into
~/.agents/skills for Codex-compatible agents.
EOF
}

if [[ "${1:-}" == "--help" || $# -eq 0 ]]; then
  usage
  exit 0
fi

platform="$1"
if [[ "$platform" != "codex" ]]; then
  echo "Unsupported platform: $platform" >&2
  echo "Supported: codex" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
skills_root="$repo_root/skills"
target_root="$HOME/.agents/skills"

if [[ ! -d "$skills_root" ]]; then
  echo "Skills directory not found: $skills_root" >&2
  exit 1
fi

mkdir -p "$target_root"

linked=0
for skill_dir in "$skills_root"/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name="$(basename "$skill_dir")"
  ln -sfn "$skill_dir" "$target_root/$skill_name"
  echo "linked $target_root/$skill_name -> $skill_dir"
  linked=$((linked + 1))
done

echo "Installed Research Pilot skills for Codex-compatible agents."
echo "Skills linked: $linked"
echo "Restart your agent session to reload skills."
```

- [ ] **Step 4: Make installer executable**

Run:

```bash
chmod +x install.sh
```

Expected: command exits successfully.

- [ ] **Step 5: Dry-run help**

Run:

```bash
./install.sh --help
```

Expected output includes:

```text
Usage:
  ./install.sh codex
```

- [ ] **Step 6: Commit**

```bash
git add .codex/INSTALL.md install.sh
git commit -m "feat: add Codex install path"
```

## Task 6: MVP-A Smoke Script

**Files:**

- Create: `scripts/smoke_mvp_a.sh`

- [ ] **Step 1: Create scripts directory**

Run:

```bash
mkdir -p scripts
```

Expected: command exits successfully.

- [ ] **Step 2: Create smoke script**

Create `scripts/smoke_mvp_a.sh`:

```bash
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
test -f "$tmp_workspace/.research-pilot/config.example.toml"
test -f "$tmp_workspace/.gitignore"

rg -n "Research Pilot" "$tmp_workspace/AGENTS.md" "$tmp_workspace/wiki/index.md" >/dev/null

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
```

- [ ] **Step 3: Make smoke script executable**

Run:

```bash
chmod +x scripts/smoke_mvp_a.sh
```

Expected: command exits successfully.

- [ ] **Step 4: Run smoke script**

Run:

```bash
./scripts/smoke_mvp_a.sh
```

Expected output:

```text
MVP-A smoke passed
```

- [ ] **Step 5: Commit**

```bash
git add scripts/smoke_mvp_a.sh
git commit -m "test: add MVP-A workspace init smoke check"
```

## Task 7: MVP-A Final Verification

**Files:**

- No new files.

- [ ] **Step 1: Verify expected files exist**

Run:

```bash
find . -maxdepth 4 -type f | sort
```

Expected output includes:

```text
./.codex/INSTALL.md
./README.md
./install.sh
./scripts/smoke_mvp_a.sh
./skills/research-pilot/SKILL.md
./tools/research_pilot_init.py
./templates/workspace/AGENTS.md
./templates/workspace/wiki/index.md
./templates/workspace/wiki/log.md
```

- [ ] **Step 2: Run final smoke**

Run:

```bash
./scripts/smoke_mvp_a.sh
```

Expected output:

```text
MVP-A smoke passed
```

- [ ] **Step 3: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted changes except intentionally untracked future docs, if the user has chosen not to commit docs yet.

- [ ] **Step 4: Optional local install check**

Run:

```bash
./install.sh codex
test -L "$HOME/.agents/skills/research-pilot"
```

Expected: command exits successfully and prints at least one linked skill.

Do this only if it is acceptable to update local skill symlinks.

## Self-Review

Spec coverage:

- Public/private boundary: Task 1.
- Plugin install path: Task 5.
- Router skill skeleton: Task 4.
- Workspace initialization: Tasks 2 and 3.
- No private data: Tasks 1, 6, and 7.
- Graph/Zotero/dashboard deferred: Scope Boundary and router skill boundaries.

No placeholders remain in implementation steps. MVP-A deliberately avoids copying graph, Zotero, dashboard, and private workflow content.
