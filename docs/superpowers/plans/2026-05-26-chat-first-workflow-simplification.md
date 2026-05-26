# Chat-First Workflow Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align Research-Pilot's README, installer output, plugin metadata, skills, command shims, workspace templates, and public guides with the chat-first product model where users talk to an agent and Research-Pilot supplies local memory resources behind that agent.

**Architecture:** This is a workflow-surface cleanup, not a runtime architecture change. Keep dashboard UI, dashboard routes, `research-pilot.db` schema, demo affordance data, graph/delta tools, and server implementation unchanged. Update docs, plugin metadata, tests, and agent-facing instructions so normal use defaults to project-local DB/UnderstandingUpdate/project memory, while D*/graph/Zotero/manual commands remain clearly advanced/internal fallback.

**Tech Stack:** Markdown docs, Codex plugin manifest JSON, Bash installer, Python unittest, existing release/smoke scripts.

---

## Reading Note

This plan includes literal Markdown snippets that themselves contain code fences. If rendered Markdown looks confusing, use the raw file view and follow the checkbox steps in order.

## Product Constraints For Every Task

- Do not edit `dashboard/**`.
- Do not edit `tools/research_dataset*.py`.
- Do not edit `tools/research_browser_server.py`.
- Do not edit `tools/graph_*.py` unless a test-only wording assertion forces a tiny non-runtime copy change; prefer not to.
- Do not edit `examples/workspaces/research-pilot.db`.
- Do not move or delete `examples/workspaces` or `examples/archive`.
- Do not delete graph/delta/Zotero tools or skills.
- Do not remove `research-pilot-init` helper link behavior in `install.sh`; demote its output only.
- Do not change dashboard server lifecycle implementation in this PR.
- Keep all public docs ASCII.
- Keep "Research Pilot" as display/product name in user copy. Use `research-pilot.db` only for filename references.

## File Structure

### Files To Modify

- `README.md`: public first impression and quick start.
- `.codex-plugin/plugin.json`: plugin product metadata and default prompts.
- `install.sh`: post-install guidance only; keep installation behavior.
- `skills/README.md`: skill status taxonomy and cleanup boundary.
- `skills/research-pilot/SKILL.md`: primary intent router.
- `skills/research-pilot-first-run/SKILL.md`: first-run defaults.
- `skills/project-understanding-update/SKILL.md`: normal update vs strict review.
- `skills/paper-discovery-intake/SKILL.md`: source-agnostic intake first, Zotero optional.
- `skills/single-paper-deep-read/SKILL.md`: source identity not Zotero-only.
- `skills/project-evidence-synthesis/SKILL.md`: UnderstandingUpdate/DB default; D* advanced.
- `commands/research-init.md`: internal runbook wording.
- `commands/research-dashboard.md`: internal runbook wording.
- `templates/workspace/AGENTS.md`: workspace-level agent rules.
- `templates/workspace/wiki/_system/workflows/first-run.md`: copied first-run protocol.
- `templates/workspace/wiki/_system/workflows/project-understanding-update.md`: copied update protocol.
- `templates/workspace/wiki/_system/workflows/paper-discovery-intake.md`: copied source intake protocol.
- `templates/workspace/wiki/_system/workflows/single-paper-deep-read.md`: copied source deep-read protocol.
- `templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md`: copied synthesis protocol.
- `templates/workspace/wiki/_system/workflows/zotero-source-protocol.md`: copied adapter protocol.
- `docs/guides/install.md`: user install path.
- `docs/guides/dashboard.md`: dashboard as agent-opened observer.
- `docs/guides/workspace.md`: local dataset mental model.
- `docs/guides/core-workflows.md`: split normal vs advanced paths.
- `docs/guides/source-boundaries.md`: source-agnostic first.
- `docs/guides/zotero.md`: optional adapter framing.
- `tests/test_chat_first_workflow_surface.py`: new surface-alignment tests.
- `tests/test_codex_plugin_manifest.py`: update manifest expectations.
- `tests/test_plugin_commands.py`: update README/command shim expectations.
- `tests/test_first_run_protocol.py`: update first-run protocol expectations.
- `tests/test_hidden_installer.py`: update installer output expectations.

### Files To Inspect But Not Modify Unless Necessary

- `tools/README.md`: already says tools are implementation API, not product navigation.
- `scripts/release_check.sh`: should still pass without changes.
- `scripts/smoke_mvp_*.sh`: should still pass without changes.
- `scripts/smoke_dashboard.sh`: should still pass without changes.

---

## Task 1: Add Failing Surface Tests

**Files:**

- Create: `tests/test_chat_first_workflow_surface.py`
- Modify: `tests/test_codex_plugin_manifest.py`
- Modify: `tests/test_plugin_commands.py`
- Modify: `tests/test_first_run_protocol.py`
- Modify: `tests/test_hidden_installer.py`

Purpose: lock the product direction before copy changes. These tests should fail on the current codebase.

- [ ] **Step 1: Create `tests/test_chat_first_workflow_surface.py`**

Add this file:

```python
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


class ChatFirstWorkflowSurfaceTests(unittest.TestCase):
    def test_readme_leads_with_chat_first_local_memory(self) -> None:
        text = read("README.md")
        opening = text.split("## Quick Start", 1)[0]

        self.assertIn("local project memory", opening.lower())
        self.assertIn("read-only dashboard", opening.lower())
        self.assertIn("agent", opening.lower())
        self.assertNotIn("Zotero-first", opening)
        self.assertNotIn("Human-gated", opening)
        self.assertNotIn("D* deltas", opening)

    def test_readme_quick_start_does_not_foreground_helper_commands(self) -> None:
        text = read("README.md")
        quick_start = text.split("## Quick Start", 1)[1].split("## What You Can Ask", 1)[0]

        self.assertIn("Use Research Pilot to track this project.", quick_start)
        self.assertIn("Open the Research Pilot dashboard.", quick_start)
        self.assertNotIn("research-pilot-init", quick_start)
        self.assertNotIn("/research-init", quick_start)
        self.assertNotIn("/research-dashboard", quick_start)
        self.assertNotIn("Manual fallback", quick_start)
        self.assertNotIn("human-gated graph update", quick_start)

    def test_primary_agent_skill_is_intent_router_not_command_catalog(self) -> None:
        text = read("skills/research-pilot/SKILL.md")

        self.assertIn("User-facing interface is chat", text)
        self.assertIn("start_or_track_project", text)
        self.assertIn("open_dashboard", text)
        self.assertIn("strict_review", text)
        self.assertNotIn("## Current Capabilities", text)
        self.assertNotIn("Build generated SQLite graph read models", text)
        self.assertNotIn("Register proposed graph deltas", text)

    def test_first_run_defaults_to_db_project_brief_not_delta(self) -> None:
        skill = read("skills/research-pilot-first-run/SKILL.md")
        workflow = read("templates/workspace/wiki/_system/workflows/first-run.md")

        for text in (skill, workflow):
            self.assertIn("research-pilot.db", text)
            self.assertIn("initial project brief", text.lower())
            self.assertIn("UnderstandingUpdate", text)
            self.assertIn("strict review", text.lower())
            self.assertNotIn("first question, claim, evidence pressure, paper synthesis, or experiment result becomes proposed D*", text)
            self.assertNotIn("First graph update", text)

    def test_workspace_template_presents_db_as_primary_memory(self) -> None:
        text = read("templates/workspace/AGENTS.md")

        self.assertIn("research-pilot.db = primary workspace dataset", text)
        self.assertIn("graph events/deltas = advanced strict review", text)
        self.assertIn("Zotero = optional supported adapter", text)
        self.assertNotIn("Zotero = paper metadata, PDFs, collections, tags, reading status mirror", text)

    def test_public_guides_label_advanced_or_adapter_surfaces(self) -> None:
        core = read("docs/guides/core-workflows.md")
        zotero = read("docs/guides/zotero.md")
        source = read("docs/guides/source-boundaries.md")

        self.assertIn("Normal chat-first path", core)
        self.assertIn("Advanced review mode", core)
        self.assertIn("optional adapter", zotero.lower())
        self.assertIn("source-agnostic", source.lower())

    def test_command_shims_are_internal_runbooks(self) -> None:
        init = read("commands/research-init.md")
        dashboard = read("commands/research-dashboard.md")

        for text in (init, dashboard):
            self.assertIn("agent-internal compatibility runbook", text)
            self.assertIn("natural-language intent", text)
            self.assertNotIn("Slash command visibility is not required", text)

    def test_no_user_facing_first_run_copy_promotes_dstar_or_zotero_first(self) -> None:
        user_paths = [
            "README.md",
            "docs/guides/install.md",
            "docs/guides/dashboard.md",
            "docs/guides/workspace.md",
            "docs/guides/source-boundaries.md",
        ]
        forbidden = re.compile(r"Zotero-first|D\* delta|human-gated graph update|graph event log is the source of truth")
        for path in user_paths:
            with self.subTest(path=path):
                self.assertIsNone(forbidden.search(read(path)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Update `tests/test_codex_plugin_manifest.py`**

In `test_manifest_interface`, replace these two assertions:

```python
self.assertIn("private research workspace", interface["longDescription"])
self.assertIn("human-gated", interface["longDescription"])
```

with:

```python
self.assertIn("local project memory", interface["longDescription"])
self.assertIn("read-only dashboard", interface["longDescription"])
self.assertNotIn("human-gated", interface["longDescription"])
self.assertNotIn("Zotero remains", interface["longDescription"])
```

In `test_default_prompts_stay_codex_sized`, after the loop, add:

```python
self.assertEqual(
    prompts,
    [
        "Use Research Pilot to track this project.",
        "Read this source and record what matters for the project.",
        "Open the Research Pilot dashboard.",
    ],
)
```

- [ ] **Step 3: Update `tests/test_plugin_commands.py` README expectations**

In `test_readme_uses_chat_first_as_primary_init_path`, replace the body after `quick_start = ...` with:

```python
self.assertIn("Use Research Pilot to track this project.", quick_start)
self.assertIn("local workspace", quick_start.lower())
self.assertIn("research-pilot.db", quick_start)
self.assertNotIn("Use Research Pilot to initialize", quick_start)
self.assertNotIn("Manual fallback", quick_start)
self.assertNotIn("research-pilot-init", quick_start)
self.assertNotIn("human-gated graph update", quick_start)
self.assertNotIn("do not register new top-level slash commands", quick_start)
```

In `test_readme_uses_chat_first_as_primary_dashboard_path`, replace:

```python
self.assertIn("Use Research Pilot to open the dashboard for ~/Research/MyResearchWiki.", quick_start)
self.assertIn("Slash command visibility is not required", quick_start)
self.assertNotIn("python3 ~/.research-pilot/repo/tools/build_dashboard_index.py", quick_start)
```

with:

```python
self.assertIn("Open the Research Pilot dashboard.", quick_start)
self.assertIn("agent starts or reuses the local dashboard server", quick_start)
self.assertNotIn("Slash command visibility is not required", quick_start)
self.assertNotIn("python3 ~/.research-pilot/repo/tools/build_dashboard_index.py", quick_start)
```

In `test_research_init_command_exists`, replace:

```python
self.assertIn("Slash command visibility is not required", text)
self.assertIn("research-pilot-first-run", text)
```

with:

```python
self.assertIn("agent-internal compatibility runbook", text)
self.assertIn("natural-language intent", text)
self.assertIn("research-pilot-first-run", text)
```

In `test_research_dashboard_command_exists`, replace:

```python
self.assertIn("Chat-First Operation", text)
```

with:

```python
self.assertIn("agent-internal compatibility runbook", text)
self.assertIn("natural-language intent", text)
```

- [ ] **Step 4: Update `tests/test_first_run_protocol.py`**

In `test_public_repo_contains_first_run_skill_and_workspace_workflow`, replace assertions after existence checks with:

```python
skill_text = skill.read_text(encoding="utf-8")
workflow_text = workflow.read_text(encoding="utf-8")
self.assertIn("research-pilot.db", skill_text)
self.assertIn("research-pilot.db", workflow_text)
self.assertIn("initial project brief", skill_text.lower())
self.assertIn("initial project brief", workflow_text.lower())
self.assertIn("UnderstandingUpdate", skill_text)
self.assertIn("UnderstandingUpdate", workflow_text)
self.assertIn("strict review", skill_text.lower())
self.assertIn("strict review", workflow_text.lower())
self.assertNotIn("first project graph update", skill_text)
self.assertNotIn("First graph update", workflow_text)
```

- [ ] **Step 5: Update `tests/test_hidden_installer.py`**

In `test_no_arg_install_clones_hidden_repo_and_links_codex_skills`, keep helper link assertions unchanged. Replace final stdout assertions:

```python
self.assertIn("Health check", result.stdout)
self.assertIn("plugin_health.py", result.stdout)
self.assertIn("chat with the agent", result.stdout.lower())
self.assertIn("do not register", result.stdout.lower())
```

with:

```python
self.assertIn("Health check", result.stdout)
self.assertIn("plugin_health.py", result.stdout)
self.assertIn("Restart Codex", result.stdout)
self.assertIn("Use Research Pilot to track my research project.", result.stdout)
self.assertIn("chat with the agent", result.stdout.lower())
self.assertNotIn("Initialize a private workspace:", result.stdout)
```

- [ ] **Step 6: Run failing tests**

Run:

```bash
python3 -m unittest \
  tests.test_chat_first_workflow_surface \
  tests.test_codex_plugin_manifest \
  tests.test_plugin_commands \
  tests.test_first_run_protocol \
  tests.test_hidden_installer
```

Expected: FAIL. Failures should mention old README quick start, old manifest `human-gated`, old first-run D*, old installer output, or old command shim copy.

- [ ] **Step 7: Commit failing tests**

Run:

```bash
git add tests/test_chat_first_workflow_surface.py tests/test_codex_plugin_manifest.py tests/test_plugin_commands.py tests/test_first_run_protocol.py tests/test_hidden_installer.py
git commit -m "test: lock chat-first workflow surface"
```

Expected: commit succeeds. If the repo policy rejects committing failing tests, skip commit until Task 8 and record in final notes.

---

## Task 2: Reframe README As Chat-First Product Entry

**Files:**

- Modify: `README.md`
- Test: `tests/test_chat_first_workflow_surface.py`
- Test: `tests/test_plugin_commands.py`

Purpose: make public first impression match new product direction.

- [ ] **Step 1: Replace README hero subtitle**

Replace:

```html
<strong>Turn papers, research chats, experiments, and project notes into a private research memory your AI agent can understand, update, and use to plan the next move.</strong>
<br />
<em>Codex-compatible. Zotero-first. Local workspace. Human-gated project understanding.</em>
```

with:

```html
<strong>Give your research agent local project memory and a read-only dashboard for what it currently understands.</strong>
<br />
<em>Chat-first. Local workspace. Source-agnostic. Read-only project dashboard.</em>
```

- [ ] **Step 2: Replace badge block terms**

In the badge block:

- Keep Quick Start, License, Codex Compatible, Research Browser, Local Private.
- Replace the Zotero badge with a Source-Agnostic badge:

```html
<a href="#source-agnostic-intake"><img src="https://img.shields.io/badge/Source_Agnostic-PDF_URL_arXiv_DOI_Zotero-4C8A2B?style=for-the-badge" alt="Source Agnostic"></a>
```

- [ ] **Step 3: Replace opening product explanation**

Replace the opening section from the line starting:

```markdown
**You are starting a research project.
```

through the quote block ending:

```markdown
> **Research Pilot does not replace Zotero...
```

with this copy:

```markdown
**You are researching through an AI agent. The agent reads, compares, reasons, and writes, but important project understanding can disappear into chat history.**

Research Pilot gives that agent a local project memory. Each workspace has one `research-pilot.db` that stores projects, sources, paper understanding, project understanding, literature structure, experiments, updates, and audit history by `project_id`.

The user-facing interface is still chat. Ask the agent normal research questions. Research Pilot provides the local dataset, typed tools, workspace templates, and read-only dashboard that let the agent keep durable project state.

The dashboard is an observer. It shows the current project state from local read models; it is not where users operate workflows or edit research memory.

> **Research Pilot does not replace your judgment, your research taste, or your paper manager. It helps your agent accumulate observable local understanding of a project instead of starting over from each chat.**
```

- [ ] **Step 4: Replace `## ✨ What It Helps You Do` section**

Replace the full section from:

```markdown
## ✨ What It Helps You Do
```

through the closing `</table>` before Quick Start with:

```markdown
## What It Helps You Do

### Track project understanding through chat

Ask the agent to track a project. Research Pilot creates or updates local project memory while the conversation stays natural.

### Keep sources connected to the project

Give the agent a PDF, URL, arXiv link, DOI, note, experiment result, or Zotero item. The agent records source identity, reading depth, relevance, and project impact.

### Preserve what changed after agent work

After meaningful research work, the agent can record an UnderstandingUpdate: what source was used, what claim changed, what evidence or uncertainty appeared, and what should be inspected next.

### Observe without operating workflows

Open the read-only dashboard to see project state, papers, technical lineage, experiments, recent understanding, and graph views where available.

### Use strict review when needed

Formal graph events and D* review still exist as advanced strict review mode for high-impact claim/evidence changes. They are not required for normal first-run use.
```

- [ ] **Step 5: Replace Quick Start**

Replace the full `## 🚀 Quick Start` section up to `## 🧪 What You Can Ask The Agent` with:

```markdown
## Quick Start

### 1. Install Research Pilot

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

This installs the local plugin source under `~/.research-pilot/repo`, links Research Pilot skills for Codex-compatible agents, and keeps helper tools available for the agent.

### 2. Start Codex

```bash
codex
```

Then ask:

```text
Use Research Pilot to track this project.
```

Give the agent your topic, current question, source, note, or experiment result. If a workspace path is needed, the agent will ask for one concise path.

### 3. Work normally in chat

Example:

```text
My project asks whether vision-language models understand object interactions or only learn object co-occurrence.
Track this with Research Pilot.
```

The agent creates or selects a local workspace, initializes `research-pilot.db`, creates or selects a project, records the initial project brief or UnderstandingUpdate, and keeps working from chat.

Fresh workspaces include `DemoVisualAffordance` by default so the dashboard has visible example data. The public repo includes an example initialized workspace at `examples/workspaces`; its root `research-pilot.db` contains `DemoVisualAffordance` as one project.

### 4. Add sources naturally

```text
Read this arXiv paper and record what matters for the project: https://arxiv.org/...
```

Research Pilot supports PDF paths, URLs, arXiv links, DOI strings, Markdown notes, experiment results, manual references, and Zotero items. Zotero is optional.

### 5. Open the dashboard

```text
Open the Research Pilot dashboard.
```

The agent starts or reuses the local dashboard server, waits until it is ready, then opens the browser or reports the local URL.
```

Markdown fence warning: when applying this step, escape nested code fences correctly. The final README must render with separate `bash` and `text` fences.

- [ ] **Step 6: Replace `## 🧪 What You Can Ask The Agent` heading and examples**

Rename heading to:

```markdown
## What You Can Ask The Agent
```

Replace example prompts with:

```markdown
```text
Use Research Pilot to track this project.
```

```text
Read this source and record what matters for the project.
```

```text
What does the project currently understand?
```

```text
Compare this paper with our current claim.
```

```text
Record this experiment result as project evidence.
```

```text
Open the Research Pilot dashboard.
```

```text
Use strict review for this claim update.
```
```

- [ ] **Step 7: Replace Core Loop section**

Replace the old graph/D* core loop with:

```markdown
## Core Loop

```text
user asks agent
-> agent reads / compares / reasons / writes
-> agent records durable project understanding
-> workspace-local research-pilot.db stores project data
-> dashboard renders read-only project state
-> user observes and asks the next better prompt
```

Normal updates go through typed Research Pilot tools and UnderstandingUpdates. Advanced strict review can still use graph deltas and human approval when formal graph truth changes are needed.
```

- [ ] **Step 8: Replace Mental Model section**

Ensure `## Mental Model` says exactly these layer definitions:

```text
Research Pilot repo = plugin source and implementation resources
User workspace = private local research dataset
research-pilot.db = primary workspace dataset, one DB per workspace
Agent chat = primary user control surface
Dashboard = read-only observation surface
Skills/tools = agent-operated internal resources
Wiki/Markdown = agent-readable context and compatibility artifacts
Graph events/deltas = advanced strict review mode
Zotero = optional supported paper-manager adapter
```

- [ ] **Step 9: Demote advanced CLI sections**

Below the main user-facing sections, keep developer/operator commands only under a section named:

```markdown
## Advanced Internal Tools
```

In that section, add this warning before any command block:

```markdown
Normal users should not need these commands. They are kept for agent internals, diagnostics, compatibility, and strict review mode.
```

Move or leave existing CLI examples under this warning. Do not delete them in this task unless they duplicate another section exactly.

- [ ] **Step 10: Run README-related tests**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface tests.test_plugin_commands
```

Expected: README-related assertions pass or fail only because other files remain old. No Markdown syntax checker exists; manually inspect README headings after edit.

- [ ] **Step 11: Commit README changes**

Run:

```bash
git add README.md tests/test_chat_first_workflow_surface.py tests/test_plugin_commands.py
git commit -m "docs: reframe README around chat-first project memory"
```

---

## Task 3: Update Plugin Manifest And Installer Guidance

**Files:**

- Modify: `.codex-plugin/plugin.json`
- Modify: `install.sh`
- Test: `tests/test_codex_plugin_manifest.py`
- Test: `tests/test_hidden_installer.py`

Purpose: make installed plugin metadata and post-install guidance match chat-first behavior.

- [ ] **Step 1: Update plugin manifest keywords**

In `.codex-plugin/plugin.json`, replace:

```json
"keywords": [
  "research",
  "papers",
  "zotero",
  "knowledge-graph",
  "agent-memory",
  "codex"
],
```

with:

```json
"keywords": [
  "research",
  "agent-memory",
  "local-first",
  "project-memory",
  "dashboard",
  "codex"
],
```

- [ ] **Step 2: Update plugin manifest longDescription**

Replace `interface.longDescription` with:

```json
"Research Pilot gives Codex-compatible agents local project memory for research work. It stores project understanding in a workspace-local dataset and renders a read-only dashboard so users can see what the agent currently understands. Sources can come from PDFs, URLs, arXiv, DOI, notes, experiment results, or Zotero; strict graph review remains available as advanced mode.",
```

- [ ] **Step 3: Update plugin default prompts**

Replace `interface.defaultPrompt` with:

```json
"defaultPrompt": [
  "Use Research Pilot to track this project.",
  "Read this source and record what matters for the project.",
  "Open the Research Pilot dashboard."
],
```

- [ ] **Step 4: Update `install.sh` post-install guidance**

In `print_post_install_guidance`, replace the `Interface:` and `Slash commands:` lines:

```bash
printf 'Interface: chat with the agent, e.g. "Use Research Pilot to initialize ~/Research/MyResearchWiki".\n'
printf 'Slash commands: local Codex plugins do not register /research-* commands; legacy prompt links are removed from %s.\n' "$CODEX_PROMPTS_DIR"
```

with:

```bash
printf 'Interface: chat with the agent. Ask: "Use Research Pilot to track my research project."\n'
printf 'No Research Pilot command memorization is required. Legacy /research-* prompt links are removed from %s.\n' "$CODEX_PROMPTS_DIR"
```

In `cmd_install`, replace:

```bash
printf 'Initialize a private workspace:\n'
printf '  %s/research-pilot-init ~/Research/MyResearchWiki\n' "$BIN_DIR"
printf 'Then run Codex from inside that workspace.\n'
```

with:

```bash
printf 'Next step:\n'
printf '  Restart Codex, then ask: "Use Research Pilot to track my research project."\n'
printf 'Compatibility helper kept for agents and troubleshooting: %s/research-pilot-init\n' "$BIN_DIR"
```

- [ ] **Step 5: Run targeted tests**

Run:

```bash
python3 -m unittest tests.test_codex_plugin_manifest tests.test_hidden_installer
```

Expected: PASS.

- [ ] **Step 6: Commit manifest and installer**

Run:

```bash
git add .codex-plugin/plugin.json install.sh tests/test_codex_plugin_manifest.py tests/test_hidden_installer.py
git commit -m "chore: align plugin metadata with chat-first workflow"
```

---

## Task 4: Rewrite Primary Router And First-Run Skills

**Files:**

- Modify: `skills/README.md`
- Modify: `skills/research-pilot/SKILL.md`
- Modify: `skills/research-pilot-first-run/SKILL.md`
- Test: `tests/test_chat_first_workflow_surface.py`
- Test: `tests/test_first_run_protocol.py`
- Test: `tests/test_plugin_commands.py`

Purpose: make agent-facing primary routing default to natural intents and local dataset/UnderstandingUpdate, not graph command catalogs.

- [ ] **Step 1: Update `skills/README.md` opening**

Replace:

```markdown
Skills are the agent-facing workflow surface. The dashboard is read-only; skills
and tools are the write layer.
```

with:

```markdown
Skills are agent-facing routing instructions. Users should not need to know skill
names or workflow names. The normal user surface is chat; skills let the agent
operate Research Pilot's local dataset, source adapters, dashboard observer, and
advanced review tools.
```

Update status table meanings:

```markdown
| Core | Normal chat-first project tracking, source recording, dashboard opening, and project-understanding updates. |
| Supported adapter | Useful bridge into project understanding, but not product identity or first-run requirement. |
| Advanced | Strict review / graph rigor kept behind the normal product surface. |
| Transition | Still tested and usable, but naming or product role should be replaced before expanding. |
```

Update Core list:

```markdown
- `research-pilot`: intent router for project tracking, workspace inspection, dashboard opening, source recording, project updates, literature mapping, experiment records, and strict review.
- `research-pilot-first-run`: first workspace/project setup with DB/project brief defaults.
- `project-understanding-update`: ambient project understanding updates from agent work.
- `related-work-lineage`: paper-only literature structure and technical lineage.
```

- [ ] **Step 2: Replace `skills/research-pilot/SKILL.md`**

Replace the full file with:

```markdown
---
name: research-pilot
description: Use when the user wants an agent to track, inspect, or operate Research Pilot project memory through natural chat.
argument-hint: "[natural language intent]"
---

# Research Pilot

Research Pilot is the primary intent router for chat-first, agent-operated research memory.

User-facing interface is chat. The user should not need to know command names, skill names, workflow files, server commands, graph deltas, or read-model mechanics.

## Product Model

```text
user asks agent
-> agent uses Research Pilot resources
-> workspace-local research-pilot.db stores project data
-> dashboard observes read models
-> user keeps researching through chat
```

## Default Boundaries

- `research-pilot.db` is the primary workspace dataset.
- Dashboard is read-only observation.
- Skills and tools are agent-operated resources.
- UnderstandingUpdates / DB-backed project memory are normal update path.
- Graph events and D* deltas are advanced strict review mode.
- Zotero is an optional supported adapter, not a first-run requirement.
- Program context is taste and north-star background only; it is not evidence, project truth, or an automatic decision source.

## Workspace Detection

A directory is a Research Pilot workspace when it has:

```text
research-pilot.db
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/config.example.toml or .research-pilot/config.toml
```

Legacy workspaces may not yet have `research-pilot.db`; if workspace markers exist, inspect status before deciding whether initialization/import is needed.

## Intent Routes

### start_or_track_project

User examples:

```text
Use Research Pilot to track this project.
Start Research Pilot for this research idea.
Track my project memory here.
```

Agent behavior:

1. Resolve workspace path only if needed.
2. Initialize or inspect workspace with `tools/research_pilot_init.py` / `tools/research_pilot_status.py`.
3. Create or select project.
4. Record initial project brief or UnderstandingUpdate.
5. Offer to open dashboard.
6. Do not require D* review for first-run unless user asks for strict review.

### inspect_workspace_or_project

User examples:

```text
What does this project currently understand?
Where does this workspace stand?
```

Agent behavior:

1. Run `tools/research_pilot_status.py --repo "$WORKSPACE_PATH" --json`.
2. Prefer DB-backed read models where available.
3. Summarize state in product terms: project, sources, understanding, literature, experiments, dashboard readiness.
4. Avoid exposing read-model rebuild mechanics unless needed for diagnosis.

### open_dashboard

User examples:

```text
Open the Research Pilot dashboard.
Show me the dashboard.
```

Agent behavior:

1. Detect workspace; if current directory is plugin repo, use `examples/workspaces`.
2. Reuse or start `tools/research_browser_server.py`.
3. Wait until dashboard URL responds.
4. Open browser or report URL.
5. Keep boundary: dashboard is read-only.

### record_source

User examples:

```text
Track this PDF.
Read this arXiv link.
Use this DOI as a source.
Add this note to the project.
```

Agent behavior:

1. Accept PDF path, URL, arXiv, DOI, Markdown note, experiment result, manual reference, or Zotero item.
2. Record source identity/status/relevance through source tools or DB writer.
3. Use Zotero only when provided/configured or when user asks.
4. If project understanding changes, write an UnderstandingUpdate.

### deep_read_source

User examples:

```text
Read this paper deeply in project context.
Extract the claims and limitations that matter for this project.
```

Agent behavior:

1. Create or update source/paper note.
2. Separate source-level understanding from project-level understanding.
3. Record project impact through UnderstandingUpdate or DB-backed update.
4. Use D* only under strict review.

### update_project_understanding

User examples:

```text
This changes our hypothesis.
Compare this with the current claim.
Record this experiment result as project evidence.
```

Agent behavior:

1. Classify the update.
2. Write normal project memory update through UnderstandingUpdate / typed dataset tools.
3. Preserve uncertainty/status.
4. Use strict review for high-impact formal graph updates or when user asks.

### map_literature

User examples:

```text
Map related work around this project.
Build a technical lineage around this baseline paper.
```

Agent behavior:

Use `related-work-lineage`; keep output paper-only and read-only. Do not append graph events or mutate project graph truth.

### record_experiment

User examples:

```text
Track this planned experiment.
Record these completed experiment results.
```

Agent behavior:

Record planned design or completed evidence as project experiment data. Connect to claims/evidence when available. Do not call proposal-only framing normal product language.

### strict_review

User examples:

```text
Use strict review for this claim update.
Make this a formal graph update.
```

Agent behavior:

1. Draft D* proposal.
2. Dry-run.
3. Summarize effect.
4. Wait for human accept/reject/park/revise.
5. Append accepted graph event only after explicit approval.

## Internal Tools

Tools are internal implementation APIs. Use exact CLI commands from tool docs or advanced workflow docs when needed, but do not ask users to memorize them.
```

- [ ] **Step 3: Replace `skills/research-pilot-first-run/SKILL.md`**

Replace the full file with:

```markdown
---
name: research-pilot-first-run
description: Use when a new user wants an agent to start Research Pilot from scratch, create or inspect a local workspace, create the first project, or begin project tracking.
argument-hint: "[workspace path] [project id]"
---

# Research Pilot First Run

Guide a user from natural chat intent to a working local Research Pilot workspace and first project.

Primary user intent:

```text
Use Research Pilot to track this project.
```

## Goal

Create the minimum working research memory loop:

```text
workspace exists
-> research-pilot.db exists
-> first project exists
-> initial project brief or UnderstandingUpdate exists
-> dashboard can observe the project
-> agent continues through natural chat
```

Do not require Zotero setup, D* delta review, graph events, or manual read-model rebuilds for normal first-run value.

## State Detection

Before suggesting next actions, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_status.py" --repo "$WORKSPACE_PATH" --json
```

Summarize the returned stage in product terms. Do not expose command mechanics unless diagnosis is needed.

Use returned stage values:

- `plugin_repo`: current directory contains plugin source. Explain repo vs workspace and ask for/infer a workspace path.
- `plain_directory`: no workspace markers. Ask whether to initialize this directory or another path.
- `empty_workspace`: workspace exists without projects. Create or import first project.
- `project_shell`: project shell exists. Record initial project brief/update if missing.
- `read_models_stale`: read models may need internal rebuild before dashboard observation.
- `project_has_graph`: project graph exists. Treat graph as existing strict-review/advanced structure, not mandatory first-run path.

## First-Run Flow

### 1. Initialize or confirm workspace

If workspace does not exist, run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

Resolve `PLUGIN_ROOT` in this order:

```text
~/.research-pilot/repo
~/.research-pilot-plugin
current directory, only if it is the plugin repo
```

### 2. Explain the boundary once

Use concise language:

```text
Research Pilot repo = plugin source and agent tools.
Your workspace = private local project memory.
research-pilot.db = primary workspace dataset.
Dashboard = read-only observer.
Chat = control surface.
Strict graph review = optional advanced mode.
Zotero = optional source adapter.
```

### 3. Collect minimum project intake

Ask only for missing essentials:

- project name or short id;
- one-sentence research direction;
- first question, uncertainty, source, note, or experiment result.

Do not ask for Zotero status unless the user gives a Zotero source or asks for Zotero setup.

### 4. Create project memory

Create or select project in the workspace dataset. Create compatibility project files when needed:

```text
wiki/projects/<ProjectId>/overview.md
wiki/projects/<ProjectId>/project-query-pack.md
wiki/projects/<ProjectId>/decisions.md
wiki/projects/<ProjectId>/papers/.gitkeep
wiki/projects/<ProjectId>/experiments/.gitkeep
```

Record an initial project brief or UnderstandingUpdate. Use `human_review: pending` for unapproved claims and explicit status labels for uncertainty.

### 5. Dashboard readiness

If the user asks to see the dashboard, start or reuse the dashboard server through the dashboard runbook. Do not require the user to run build or server commands.

### 6. Strict review only when requested

If the user asks for strict review or a formal graph update:

```text
draft D*
-> dry-run
-> summarize effect
-> wait for accept/reject/park/revise
-> append accepted event only after explicit approval
```

Normal first-run does not require this.

### 7. Completion response

End with:

```text
Workspace:
Project:
Initial memory:
Dashboard:
Strict review:
Next natural prompts:
```

Offer at most three natural chat prompts, for example:

- read a source and record what matters;
- open the dashboard;
- use strict review for a specific claim.

## Stop Points

Stop for human approval before:

- accepting a strict-review graph delta;
- marking a paper project-core or global-core;
- changing research direction as a decision;
- interpreting experiment results as confirmed project evidence;
- writing Zotero status mirrors with `--apply`.
```

- [ ] **Step 4: Run targeted skill tests**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface tests.test_first_run_protocol tests.test_plugin_commands
```

Expected: skill-related assertions pass or fail only because workspace templates/docs remain old.

- [ ] **Step 5: Commit skill router changes**

Run:

```bash
git add skills/README.md skills/research-pilot/SKILL.md skills/research-pilot-first-run/SKILL.md tests/test_chat_first_workflow_surface.py tests/test_first_run_protocol.py tests/test_plugin_commands.py
git commit -m "docs: simplify Research Pilot skill routing"
```

---

## Task 5: Reframe Workspace Templates

**Files:**

- Modify: `templates/workspace/AGENTS.md`
- Modify: `templates/workspace/wiki/_system/workflows/first-run.md`
- Modify: `templates/workspace/wiki/_system/workflows/project-understanding-update.md`
- Modify: `templates/workspace/wiki/_system/workflows/paper-discovery-intake.md`
- Modify: `templates/workspace/wiki/_system/workflows/single-paper-deep-read.md`
- Modify: `templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md`
- Modify: `templates/workspace/wiki/_system/workflows/zotero-source-protocol.md`
- Test: `tests/test_chat_first_workflow_surface.py`
- Test: `tests/test_first_run_protocol.py`
- Test: `scripts/smoke_mvp_a.sh`

Purpose: new workspaces inherit the chat-first / local dataset model.

- [ ] **Step 1: Replace `templates/workspace/AGENTS.md`**

Replace full file with:

```markdown
# Research Pilot Workspace Instructions

This directory is a private Research Pilot workspace.

## Core Rule

Agent operates the workspace through chat. Files and databases are durable memory and execution state, not the main human UI.

## Source Boundaries

```text
research-pilot.db = primary workspace dataset
wiki = durable agent-readable context and compatibility artifacts
wiki/program = research taste and north-star context only
dashboard = read-only observer over workspace read models
chat/agent = primary control surface
graph events/deltas = advanced strict review
Zotero = optional supported adapter
```

## Program Context

`wiki/program/` is an agent context layer for taste and north-star framing. It is not evidence, not project truth, and not a decision source.

Read it when it helps interpret the user's research style. Do not use it to make project decisions for the user. Do not copy program context into project truth.

## Normal Project Memory

After meaningful research work, record durable project understanding through Research Pilot tools. Prefer workspace dataset / UnderstandingUpdate style records for normal updates.

Meaningful work includes:

- starting or reframing a project;
- reading or comparing a source;
- mapping literature structure;
- recording experiment design or result evidence;
- revising a claim, uncertainty, limitation, or project brief.

## Strict Review

Use graph events and D* deltas only for advanced strict review:

- user explicitly asks for strict review;
- high-impact project claim/evidence changes need formal approval;
- compatibility workflows require graph-level Q/C/E/W/L/RL/TL changes.

Only the human may approve:

- strict-review graph delta acceptance;
- project-core papers;
- global-core memory;
- research direction decisions;
- experiment result interpretation as confirmed project evidence.

## Private Data

Do not publish this workspace unless the human explicitly says it is sanitized.
Do not commit PDFs, API keys, local Zotero databases, private workspace datasets, or generated SQLite/dashboard read models.
```

- [ ] **Step 2: Replace copied first-run workflow**

Copy the final `skills/research-pilot-first-run/SKILL.md` body logic into `templates/workspace/wiki/_system/workflows/first-run.md`, preserving frontmatter:

```markdown
---
title: "Research Pilot First-Run Protocol"
type: workflow
status: active
human_review: approved
---
```

After frontmatter, use the same headings and content from Task 4 Step 3, but remove skill frontmatter (`name`, `description`, `argument-hint`). Keep title `# Research Pilot First-Run Protocol`.

- [ ] **Step 3: Rewrite `project-understanding-update.md` default path**

Replace "Core Rule" section with:

```markdown
## Core Rule

Project understanding has two paths:

```text
normal path = workspace dataset / UnderstandingUpdate / project memory
strict review = graph events and D* deltas for formal Q/C/E/W/L/RL/TL changes
```

Use the normal path for ordinary agent learning, source notes, uncertainty updates, brief changes, and recent understanding. Use strict review when the user asks for it or when a high-impact formal graph change needs explicit approval.
```

In the input type table, change default handling:

```markdown
| question | New/reframed project question | normal update; strict review if formal graph change |
| claim | Contestable project judgment | normal update with status; strict review if high-impact |
| evidence_pressure | Evidence accumulation suggests Q/C change | normal update; strict review if formal graph change |
| limitation_pressure | Caveats bound or weaken current claim | normal update; strict review if formal graph change |
| search_need | Missing literature support | record need; source/literature discovery may follow |
| experiment_need | Missing generated evidence | record planned experiment/design need |
```

Rename `## Graph Updates` to:

```markdown
## Strict Review Updates
```

Change first sentence under it to:

```markdown
Require Delta Update Protocol only when the user asks for strict review or a formal graph-level Q/C/E/W/L/RL/TL change is being accepted.
```

Change output format to:

```text
Update type:
Project memory:
Strict review:
Human gate:
Next natural prompt:
```

- [ ] **Step 4: Rewrite source intake and single-paper workflows**

In `paper-discovery-intake.md`, replace title and first paragraph with:

```markdown
# Source Intake

Purpose: add source identity into Research Pilot project memory without forcing a paper-manager workflow.

Accepted source types:

- PDF path;
- URL;
- arXiv link;
- DOI;
- Markdown note;
- experiment result;
- manual reference;
- Zotero item.
```

Replace "Core Boundary" section with:

```markdown
## Core Boundary

Research Pilot records project-scoped source identity, source state, and relevance. Zotero is an optional supported adapter for paper metadata/PDF management; it is not required for first-run value.
```

Keep existing command block, but introduce it with:

```markdown
Agent may use this internal tool when command-line support is useful:
```

In `single-paper-deep-read.md`, replace Boundary bullets with:

```markdown
- Source identity can come from PDF, URL, arXiv, DOI, manual note, experiment result, or Zotero.
- Zotero is optional unless the user gives a Zotero item or asks for Zotero setup.
- The source/paper note is project-local working memory, not global approved memory.
- Project-level impact should be recorded through normal project memory; use strict review only when formal graph changes are requested or required.
```

Replace final sentence:

```markdown
Graph deltas remain proposals until the human approves them through the graph delta loop.
```

with:

```markdown
Strict-review graph deltas remain proposals until the human explicitly approves them.
```

- [ ] **Step 5: Rewrite project evidence synthesis**

In `project-evidence-synthesis.md`, replace first description paragraph with:

```markdown
Use this protocol when multiple sources, notes, dossiers, search results, or experiment records must be synthesized into project-level understanding.

The output is project-facing evidence synthesis. Normal output should update project memory / UnderstandingUpdate records. Strict-review D* proposals are optional advanced outputs when formal graph changes are needed.
```

In "Source Boundary", replace allowed list with:

```markdown
Allowed:

- compare sources;
- identify agreement, conflict, missing evidence, and uncertainty;
- update project memory through normal Research Pilot tools;
- propose strict-review graph changes only when needed;
- recommend natural next prompts.
```

Rename `## Proposed Project Understanding Delta` in required output to:

```markdown
## Project Understanding Update
Normal update summary and affected project records.
```

Add optional section:

```markdown
## Optional Strict Review
D* proposal summary only when formal graph review is requested or necessary.
```

Replace "Stop Point" with:

```markdown
## Stop Point

Stop before accepting strict-review graph changes unless the human explicitly accepts.
```

- [ ] **Step 6: Rewrite Zotero protocol**

In `zotero-source-protocol.md`, replace title and opening with:

```markdown
# Zotero Adapter Protocol

Core rule:

```text
Research Pilot is source-agnostic for first-run project memory.
Zotero is an optional supported adapter for paper metadata, PDFs, collections, and operational paper triage.
```

Research Pilot does not reimplement citation management and does not require Zotero before first value.
```

Replace "Public Boundary" with:

```markdown
## Public Boundary

Source intake records durable source identity from:

- PDF path;
- URL;
- arXiv ID;
- DOI;
- manual source refs;
- experiment result refs;
- Zotero item key.
```

- [ ] **Step 7: Run template tests and initialization smoke**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface tests.test_first_run_protocol
bash scripts/smoke_mvp_a.sh
```

Expected: PASS.

- [ ] **Step 8: Commit workspace template changes**

Run:

```bash
git add templates/workspace/AGENTS.md templates/workspace/wiki/_system/workflows/first-run.md templates/workspace/wiki/_system/workflows/project-understanding-update.md templates/workspace/wiki/_system/workflows/paper-discovery-intake.md templates/workspace/wiki/_system/workflows/single-paper-deep-read.md templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md templates/workspace/wiki/_system/workflows/zotero-source-protocol.md tests/test_chat_first_workflow_surface.py tests/test_first_run_protocol.py
git commit -m "docs: update workspace templates for chat-first memory"
```

---

## Task 6: Reframe Update/Source/Synthesis Skills

**Files:**

- Modify: `skills/project-understanding-update/SKILL.md`
- Modify: `skills/paper-discovery-intake/SKILL.md`
- Modify: `skills/single-paper-deep-read/SKILL.md`
- Modify: `skills/project-evidence-synthesis/SKILL.md`
- Test: `tests/test_chat_first_workflow_surface.py`

Purpose: align installed agent skills with copied workspace protocols.

- [ ] **Step 1: Update `project-understanding-update` skill**

Change description line to:

```yaml
description: Use when a research project needs normal project memory updated from human intent, sources, evidence pressure, experiment results, or direction changes; strict graph review is optional advanced mode.
```

In Boundary, replace current graph-first text with:

```markdown
## Boundary

Human intent is first-class input.

Normal project understanding updates should be recorded through Research Pilot project memory / UnderstandingUpdate / typed dataset tools. The agent may classify, preserve, compare, and propose. It must not silently convert a human idea into a confirmed claim, project decision, or strict graph truth.

Strict graph-level changes use Delta Update Protocol only when the user asks for strict review or a formal Q/C/E/W/L/RL/TL change is being accepted:

```text
input
-> classify meaning
-> normal project memory update
-> optional strict-review D* proposal
-> dry-run
-> human accept/reject/park/revise
-> append accepted graph event only after approval
```
```

Update Output section to:

```markdown
## Output

End with:

```text
Update type:
Project memory:
Strict review:
Human gate:
Next natural prompt:
```
```

- [ ] **Step 2: Update `paper-discovery-intake` skill**

Change frontmatter:

```yaml
name: paper-discovery-intake
description: Use when the user wants to add source identity from PDF, URL, arXiv, DOI, note, experiment result, manual reference, or Zotero item into a Research Pilot project.
argument-hint: "<project> <source>"
```

Replace body opening with:

```markdown
# Source Intake

Create project-local source identity without forcing a paper-manager workflow.

Accepted source types:

- PDF path;
- URL;
- arXiv link;
- DOI;
- Markdown note;
- experiment result;
- manual reference;
- Zotero item.

Use Zotero identity when available, but do not require it for first-run value.
```

Keep existing CLI examples, but label them:

```markdown
Agent-internal CLI examples:
```

Replace final line with:

```markdown
This skill records durable source identity. Zotero is a supported adapter, not the product identity.
```

- [ ] **Step 3: Update `single-paper-deep-read` skill**

Change description:

```yaml
description: Use when the user wants an agent to create or update a project-local source/paper note from a PDF, URL, arXiv, DOI, manual source, or Zotero item.
```

Replace opening "Create or update" sentence with:

```markdown
Create or update a project-local source/paper note:
```

Replace final paragraph with:

```markdown
Then fill the note with source identity, key claims, evidence, methods, assumptions, limitations, project relevance, and project impact. If project understanding changes, record a normal project memory update. Use graph delta proposals only in strict review mode.
```

- [ ] **Step 4: Update `project-evidence-synthesis` skill**

Change description:

```yaml
description: Use when a set of sources, dossiers, graph records, or experiment notes must be synthesized into project understanding, evidence pressure, uncertainty, and optional strict-review graph proposals.
```

Replace Boundary with:

```markdown
## Boundary

Do not approve sources. Do not mark sources project-core/global-core. Do not mutate strict graph truth directly.

Allowed:

- compare sources;
- extract agreement/conflict;
- identify evidence pressure;
- record normal project memory updates;
- propose strict-review graph deltas only when needed;
- recommend natural next prompts.
```

Replace required output sections with:

```markdown
## Required Output Sections

```markdown
# Project Evidence Synthesis

## Current Project State
## Source Set
## Agreement and Conflict
## Claim/Evidence Table
## Evidence Pressure
## Project Understanding Update
## Optional Strict Review
## Next Natural Prompts
```
```

Replace stop point:

```markdown
## Stop Point

Stop before applying strict-review graph changes unless the human explicitly accepts a D* delta.
```

- [ ] **Step 5: Run skill surface tests**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface
```

Expected: PASS or fail only because command/guides remain old.

- [ ] **Step 6: Commit skill updates**

Run:

```bash
git add skills/project-understanding-update/SKILL.md skills/paper-discovery-intake/SKILL.md skills/single-paper-deep-read/SKILL.md skills/project-evidence-synthesis/SKILL.md tests/test_chat_first_workflow_surface.py
git commit -m "docs: align source and update skills with chat-first memory"
```

---

## Task 7: Demote Command Shims To Internal Runbooks

**Files:**

- Modify: `commands/research-init.md`
- Modify: `commands/research-dashboard.md`
- Test: `tests/test_chat_first_workflow_surface.py`
- Test: `tests/test_plugin_commands.py`
- Test: `tests/test_plugin_health.py`

Purpose: keep compatibility runbooks but stop making them look like user commands.

- [ ] **Step 1: Rewrite `commands/research-init.md` opening**

Replace frontmatter description with:

```yaml
description: Agent-internal compatibility runbook for starting or inspecting a Research Pilot workspace from natural-language project-tracking intent.
argument-hint: "[workspace_path]"
```

Replace title and opening through Status paragraph with:

```markdown
# Research Pilot Start/Track Runbook

This is an agent-internal compatibility runbook, not a user command surface.

Users should ask a natural-language intent:

```text
Use Research Pilot to track this project.
```

The agent may use this runbook to resolve plugin root, initialize a workspace, inspect status, and hand off to `research-pilot-first-run`.
```

In workflow steps, replace graph-first steps 6-9 with:

```markdown
6. Record initial project brief or UnderstandingUpdate.
7. Offer to open the dashboard.
8. Use strict-review D* only if the user explicitly asks for formal graph review.
```

Replace boundary copy:

```text
Research Pilot plugin = hidden agent capability.
Workspace = visible private research memory.
research-pilot.db = primary workspace dataset.
Dashboard = read-only observer.
Strict review = optional graph/D* mode.
```

Replace completion block:

```text
Workspace:
Project:
Initial memory:
Dashboard:
Strict review:
Next natural prompts:
```

- [ ] **Step 2: Rewrite `commands/research-dashboard.md` opening**

Replace frontmatter description with:

```yaml
description: Agent-internal compatibility runbook for opening the local Research Pilot dashboard from natural-language intent.
argument-hint: "[workspace_path] [port]"
```

Replace title/opening with:

```markdown
# Research Pilot Dashboard Runbook

This is an agent-internal compatibility runbook, not a user command surface.

Users should ask a natural-language intent:

```text
Open the Research Pilot dashboard.
```

The agent may use this runbook to resolve workspace, start or reuse the dashboard server, verify readiness, and open or report the local URL.
```

Keep the existing server command block and completion report. Remove the phrase:

```text
Slash command visibility is not required
```

Replace `## Chat-First Operation` heading with:

```markdown
## Natural-Language Operation
```

- [ ] **Step 3: Update `tests/test_plugin_health.py` if needed**

Only update if failure occurs. The health test can continue checking `command_files` because command files remain.

- [ ] **Step 4: Run command tests**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface tests.test_plugin_commands tests.test_plugin_health
```

Expected: PASS.

- [ ] **Step 5: Commit command shim changes**

Run:

```bash
git add commands/research-init.md commands/research-dashboard.md tests/test_chat_first_workflow_surface.py tests/test_plugin_commands.py tests/test_plugin_health.py
git commit -m "docs: demote command shims to internal runbooks"
```

---

## Task 8: Reframe Public Guides

**Files:**

- Modify: `docs/guides/install.md`
- Modify: `docs/guides/dashboard.md`
- Modify: `docs/guides/workspace.md`
- Modify: `docs/guides/core-workflows.md`
- Modify: `docs/guides/source-boundaries.md`
- Modify: `docs/guides/zotero.md`
- Test: `tests/test_chat_first_workflow_surface.py`
- Test: `tests/test_plugin_commands.py`

Purpose: split normal user path from agent/internal/advanced docs.

- [ ] **Step 1: Rewrite `docs/guides/install.md` normal path**

After install command, keep clone/link details but add this section before health check:

```markdown
## Normal User Path

After install, restart Codex and ask:

```text
Use Research Pilot to track my research project.
```

The agent handles workspace initialization, `research-pilot.db`, project creation, and dashboard opening through internal tools.
```

Move direct helper fallback under:

```markdown
## Agent/Internal Fallbacks
```

Ensure the helper fallback paragraph says:

```markdown
Normal users should not need this command. It remains available for agent internals, diagnostics, and troubleshooting.
```

Replace "Use Research Pilot to initialize..." with "Use Research Pilot to track my research project."

- [ ] **Step 2: Rewrite `docs/guides/dashboard.md`**

Replace opening with:

```markdown
# Dashboard Guide

Dashboard is a read-only browser observer over workspace read models.

Normal user path:

```text
Open the Research Pilot dashboard.
```

The agent detects the workspace, starts or reuses the local dashboard server, waits for readiness, and opens or reports the URL.
```

Keep technical read list, but change:

```markdown
Graph truth remains:
```

to:

```markdown
Advanced strict-review graph events remain:
```

Move direct helper fallback under:

```markdown
## Agent/Internal Fallback
```

- [ ] **Step 3: Rewrite `docs/guides/workspace.md` mental model**

After initialized workspace tree, add:

```markdown
## Primary Dataset

`research-pilot.db` is the primary local workspace dataset. It stores project-scoped research memory by `project_id`.

Normal users interact through chat. Agents write through Research Pilot tools. The dashboard reads generated API/read models.
```

Change workspace stages list to product terms:

```markdown
- no workspace yet;
- workspace initialized;
- project exists;
- project has sources;
- project has understanding updates;
- project has literature structure;
- project has experiment design/results;
- strict-review graph data exists;
- dashboard read models need refresh.
```

Move `--no-demo` command under `## Agent/Internal Fallback`.

- [ ] **Step 4: Rewrite `docs/guides/core-workflows.md`**

Replace file opening with:

```markdown
# Core Workflows

## Normal chat-first path

Normal Research Pilot use starts with chat:

```text
user asks agent
-> agent uses Research Pilot tools
-> project memory is recorded in the workspace dataset / UnderstandingUpdates
-> dashboard observes read models
```

Users should not need to memorize workflow names or commands.
```

Keep technical sections, but rename:

- `## Delta Update` to `## Advanced review mode`
- `## Gap Detection` to `## Advanced graph-derived gap inspection`
- `## Paper Dossier` to `## Source/Paper deep-read note`

Before command blocks, add:

```markdown
Agent/internal command examples:
```

Change "Project-understanding changes still use D*..." to:

```markdown
Normal project-understanding changes use workspace project memory / UnderstandingUpdates. Strict graph review uses D* dry-run, registration, and explicit human acceptance.
```

- [ ] **Step 5: Rewrite `docs/guides/source-boundaries.md`**

Replace full source boundary code block with:

```text
research-pilot.db = primary workspace dataset
sources = PDF, URL, arXiv, DOI, Markdown note, experiment result, manual reference, or Zotero item
wiki = durable agent-readable context and compatibility artifacts
wiki/program = research taste and north-star context only
dashboard = read-only observer
chat/agent = primary control surface
graph events/deltas = advanced strict review
Zotero = optional supported adapter
```

Add:

```markdown
Research Pilot is source-agnostic for first-run value. Zotero remains useful when the user already manages papers there, but it is not required before project memory or dashboard observation works.
```

- [ ] **Step 6: Rewrite `docs/guides/zotero.md` as adapter guide**

Change title:

```markdown
# Zotero Adapter Guide
```

Replace opening:

```markdown
Zotero is an optional supported adapter for paper metadata, PDFs, collections, tags, and reading status. Research Pilot is source-agnostic for first-run project memory.
```

Replace "Research Pilot owns" list with:

```markdown
Research Pilot stores project-scoped source identity, source notes, project understanding, literature structure, experiment records, and dashboard read models in the local workspace.
```

Keep setup details, but label as:

```markdown
## Optional Agent-Guided Setup
```

- [ ] **Step 7: Run guide tests**

Run:

```bash
python3 -m unittest tests.test_chat_first_workflow_surface tests.test_plugin_commands
```

Expected: PASS.

- [ ] **Step 8: Commit guide updates**

Run:

```bash
git add docs/guides/install.md docs/guides/dashboard.md docs/guides/workspace.md docs/guides/core-workflows.md docs/guides/source-boundaries.md docs/guides/zotero.md tests/test_chat_first_workflow_surface.py tests/test_plugin_commands.py
git commit -m "docs: split normal workflow from advanced internals"
```

---

## Task 9: Final Scans, Compatibility Tests, And Release Check

**Files:**

- Modify only if tests reveal stale assertions.
- Test: all affected tests and release check.

Purpose: ensure surface cleanup did not break runtime, demo, dashboard, or packaging.

- [ ] **Step 1: Run targeted unit tests**

Run:

```bash
python3 -m unittest \
  tests.test_chat_first_workflow_surface \
  tests.test_codex_plugin_manifest \
  tests.test_plugin_commands \
  tests.test_hidden_installer \
  tests.test_first_run_protocol \
  tests.test_plugin_health
```

Expected: PASS.

- [ ] **Step 2: Run workflow smoke tests that copy templates**

Run:

```bash
bash scripts/smoke_mvp_a.sh
bash scripts/smoke_dashboard.sh
```

Expected:

- `MVP-A smoke passed`
- `Dashboard smoke passed`

- [ ] **Step 3: Run product-surface scans**

Run:

```bash
rg -n "Zotero-first|Human-gated|D\\* delta approval as the normal|Use Research Pilot to initialize|Manual fallback|/research-init|/research-dashboard" README.md docs/guides skills/research-pilot/SKILL.md skills/research-pilot-first-run/SKILL.md templates/workspace/AGENTS.md templates/workspace/wiki/_system/workflows/first-run.md commands
```

Expected:

- No matches in `README.md`, `docs/guides/install.md`, `docs/guides/dashboard.md`, `docs/guides/workspace.md`, `docs/guides/source-boundaries.md`, `skills/research-pilot/SKILL.md`, `skills/research-pilot-first-run/SKILL.md`, `templates/workspace/AGENTS.md`, or `templates/workspace/wiki/_system/workflows/first-run.md`.
- Matches may remain in advanced docs/skills only if clearly labeled advanced strict review or compatibility.

Run:

```bash
rg -n "research-pilot-init" README.md docs/guides install.sh commands
```

Expected:

- No match in README Quick Start.
- Matches in `install.sh` and guides only as compatibility/internal fallback.

- [ ] **Step 4: Verify no forbidden runtime files changed**

Run:

```bash
git diff --name-only HEAD~8..HEAD
```

Expected: changed files are docs, skills, command shims, manifest, installer, and tests only. No `dashboard/**`, `tools/research_dataset*.py`, `tools/research_browser_server.py`, `tools/graph_*.py`, or `examples/workspaces/research-pilot.db`.

If commit count differs because Task 1 commit was delayed, use:

```bash
git diff --name-only main...HEAD
```

- [ ] **Step 5: Run full release check**

Run:

```bash
bash scripts/release_check.sh
```

Expected: `release check passed`.

If release check fails because old smoke tests assert old product copy, update only those assertions to match chat-first product language. Do not change runtime behavior unless a real regression is found.

- [ ] **Step 6: Commit final test assertion cleanup if needed**

Only if Step 5 required test-only edits:

```bash
git add tests scripts
git commit -m "test: update workflow surface release checks"
```

- [ ] **Step 7: Final status**

Run:

```bash
git status --short
```

Expected: clean working tree.

---

## Self-Review Checklist For Implementer

- [ ] README describes Research Pilot as local project memory + read-only dashboard for an agent.
- [ ] README Quick Start does not mention `research-pilot-init`, `/research-init`, `/research-dashboard`, manual fallback, or first-run D*.
- [ ] Installer still links `research-pilot-init`, but output does not foreground it as normal user path.
- [ ] Plugin manifest default prompts are exactly:
  - `Use Research Pilot to track this project.`
  - `Read this source and record what matters for the project.`
  - `Open the Research Pilot dashboard.`
- [ ] Router skill uses intent route names: `start_or_track_project`, `inspect_workspace_or_project`, `open_dashboard`, `record_source`, `deep_read_source`, `update_project_understanding`, `map_literature`, `record_experiment`, `strict_review`.
- [ ] First-run skill/template success criteria include `research-pilot.db`, project, initial project brief/UnderstandingUpdate, dashboard observation.
- [ ] First-run skill/template do not make proposed D* or graph event acceptance the default success condition.
- [ ] Workspace AGENTS says `research-pilot.db = primary workspace dataset`.
- [ ] Source intake docs accept PDF, URL, arXiv, DOI, Markdown note, experiment result, manual reference, and Zotero item.
- [ ] Zotero docs call Zotero an optional supported adapter.
- [ ] Command files call themselves agent-internal compatibility runbooks.
- [ ] Advanced graph/delta tools remain documented somewhere as strict review mode.
- [ ] No dashboard UI, DB schema, demo DB, graph runtime, or dashboard server implementation changed.
- [ ] `bash scripts/release_check.sh` passes.

## Execution Notes

Recommended implementation mode:

```text
Subagent-Driven
worker model: gpt-5.5 medium
one worker per task
review after each task
```

If a worker finds a contradiction between this plan and `docs/superpowers/specs/2026-05-26-chat-first-workflow-simplification-prd.md`, stop and report the contradiction before editing unrelated files.
