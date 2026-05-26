# Chat-First Research-Pilot Workflow Simplification PRD

Status: draft PRD

Date: 2026-05-26

Related PRDs:

- `docs/superpowers/specs/2026-05-23-understanding-update-architecture-prd.md`
- `docs/superpowers/specs/2026-05-25-research-pilot-local-dataset-architecture-prd.md`

## 1. Executive Summary

Research-Pilot should simplify its public and agent-facing workflow surface around one product idea:

```text
The user keeps talking to an AI agent.
Research-Pilot gives that agent durable local project memory, typed tools, and a read-only dashboard.
```

Users should not need to learn Research-Pilot commands, formal workflow names, D* delta terminology, read-model mechanics, or Zotero-first setup before getting value. Those concepts may remain in the codebase as internal tools, compatibility paths, and advanced review mode. The first-run product experience should feel like a stronger research agent with persistent local project understanding, not a workflow system the user must operate.

This PRD covers user workflow exposure cleanup only: README, install output, plugin manifest, skills, command shims, workspace templates, and public guides. It does not change the dashboard UI, `research-pilot.db` schema, demo affordance data, graph/delta tooling, or server implementation.

## 2. Product Thesis

Research-Pilot is a local-first research memory layer for AI-assisted research.

The product core is:

```text
agent-operated local project understanding
```

Primary loop:

```text
user asks agent
-> agent researches / reads / reasons / writes
-> Research-Pilot records durable project understanding
-> dashboard observes current project state
-> user asks a better next prompt
```

The user-facing interaction surface is chat. The dashboard is the read-only observation surface. Scripts, skills, commands, DB writers, graph tools, importers, and dashboard servers are agent-operated resources.

## 3. Problem

The codebase now has the right architectural direction: a workspace-local `research-pilot.db`, DB-backed read models, UnderstandingUpdates, read-only dashboard APIs, and a preserved demo project. However, the public workflow language still exposes the old product center.

Current first-run and guide materials still emphasize:

- explicit initialization commands;
- slash command compatibility;
- Zotero-first source identity;
- D* delta approval as the normal first update;
- graph event truth as the first mental model;
- read-model rebuilds;
- gap workflows and next-action routers;
- experiment proposal workflows;
- manual CLI fallback commands.

This creates a mismatch:

```text
Target product: user chats naturally; agent handles Research-Pilot resources.
Current surface: user learns Research-Pilot workflows and command concepts.
```

The result is avoidable cognitive load. A new user can incorrectly conclude that Research-Pilot is a command/workflow system instead of an ambient local memory layer for their agent.

## 4. Target Users

Primary user:

```text
a researcher using an AI agent such as Codex to work on a project
```

They want to say things like:

- "Use Research-Pilot to track this project."
- "Read this paper and remember what matters."
- "Compare this result with our current claim."
- "Open the dashboard."
- "What does the project currently understand?"
- "Use strict review for this claim change."

They do not want to memorize:

- `research-pilot-init`;
- `/research-init`;
- `/research-dashboard`;
- graph delta commands;
- dashboard server commands;
- read-model rebuild commands;
- Zotero setup before first value;
- workflow file names.

Secondary user:

```text
an agent or developer inspecting Research-Pilot internals
```

They need stable internal runbooks and tools, but those should be clearly labeled as agent/internal/advanced surfaces rather than normal user workflows.

## 5. Product Principles

### Chat Is the Control Surface

Normal user operations should be natural-language intents. The agent resolves workspace paths, initializes DBs, starts dashboard servers, writes updates, and runs internal tools.

### Resources, Not Commands

Research-Pilot should provide fixed local resources:

```text
research-pilot.db
dashboard frontend
API/read-model builders
typed writer tools
skills
workspace templates
demo workspace
advanced graph/delta tools
```

The user should not experience those as things to operate manually.

### First Value Before Formal Rigor

First-run success should be:

```text
workspace exists
project exists in local DB
project brief exists
agent can record UnderstandingUpdates
dashboard can show the project
```

The first-run success condition should not require a D* proposal, graph event acceptance, Zotero setup, or read-model rebuild discussion.

### Advanced Review Remains Available

Graph events, D* deltas, human gate review, strict validation, and graph snapshots remain useful. They should be exposed as advanced review mode when the user asks for stricter control or when a high-impact project claim change requires formalization.

### Source-Agnostic First

Normal source intake should accept PDF, URL, arXiv, DOI, manual note, experiment result, and Zotero item. Zotero remains a supported adapter, not product identity.

### Dashboard Remains Read-Only

No dashboard redesign is in scope. The dashboard should continue to observe the workspace dataset/read models.

## 6. Current Surface Inventory

### User-Facing Docs

Surfaces:

- `README.md`
- `docs/guides/install.md`
- `docs/guides/dashboard.md`
- `docs/guides/workspace.md`
- `docs/guides/core-workflows.md`
- `docs/guides/zotero.md`
- `docs/guides/source-boundaries.md`

Problem:

They still present old first-run concepts too early: Zotero-first, D*, human-gated deltas, graph truth, CLI fallbacks, gap contracts, and experiment proposals.

### Agent-Facing Skills

Surfaces:

- `skills/research-pilot/SKILL.md`
- `skills/research-pilot-first-run/SKILL.md`
- `skills/project-understanding-update/SKILL.md`
- `skills/paper-discovery-intake/SKILL.md`
- `skills/single-paper-deep-read/SKILL.md`
- `skills/project-evidence-synthesis/SKILL.md`
- advanced/transition skills under `skills/`

Problem:

The router skill lists too many low-level capabilities and still makes D* the normal first project update. Several skill descriptions make Zotero or graph deltas appear central.

### Command Shims

Surfaces:

- `commands/research-init.md`
- `commands/research-dashboard.md`

Problem:

They are already labeled chat-first shims, but their names and docs can still look like user commands. They should become internal agent runbooks or compatibility docs, not advertised product navigation.

### Workspace Templates

Surfaces:

- `templates/workspace/AGENTS.md`
- `templates/workspace/wiki/_system/workflows/*.md`
- `templates/workspace/wiki/index.md`

Problem:

New workspaces inherit old workflow language. The workspace instructs agents that graph events are the central truth and that first-run success includes D* and human gate. This contradicts the newer local dataset/UnderstandingUpdate direction.

### Installer and Plugin Manifest

Surfaces:

- `install.sh`
- `.codex-plugin/plugin.json`

Problem:

Install output still advertises `research-pilot-init`. Plugin prompts still emphasize graph updates and missing evidence rather than project tracking, source intake, and dashboard observation.

## 7. Target Experience

### First Install

User runs the unavoidable install command once:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

After install, guidance should say:

```text
Restart Codex.
Then ask:
"Use Research-Pilot to track my research project."
```

It should not ask users to run `research-pilot-init` unless troubleshooting.

### First Workspace

User says:

```text
Use Research-Pilot to track this project.
My topic is ...
```

Agent should:

```text
detect current context
choose or ask for workspace path only if needed
initialize workspace-local research-pilot.db
create or select project
record project brief / initial understanding
keep DemoVisualAffordance if default workspace/demo behavior applies
offer to open dashboard
```

No first-run D* is required.

### Open Dashboard

User says:

```text
Open the Research-Pilot dashboard.
```

Agent should:

```text
detect workspace
reuse or start dashboard server
wait until ready
open browser or print URL
```

User should not need to know port, command, server process, or `.dashboard/index.json`.

### Research Work

User says:

```text
Read this paper and track what matters.
```

Agent should:

```text
create source record
read/summarize as needed
write source-level notes when useful
write project-level UnderstandingUpdate when project understanding changes
update DB/read models through tools
```

Only if a formal project graph change is requested or necessary should the agent invoke advanced review mode.

### Strict Review

User says:

```text
Use strict review for this claim update.
```

Agent should:

```text
create D* proposal
dry-run
summarize effect
wait for accept/reject/park/revise
append accepted graph event only after explicit approval
```

This is advanced mode, not default first-run.

## 8. User Stories

### Story 1: Chat-First Project Start

As a researcher, I want to say "Use Research-Pilot to track this project," so that the agent creates or selects the local workspace/project without requiring me to learn commands.

Acceptance criteria:

- Given Research-Pilot is installed
- When the user gives a project topic in chat
- Then the agent can initialize or select a workspace and project
- And the project exists in `research-pilot.db`
- And initial project brief or UnderstandingUpdate is recorded
- And no D* delta is required unless the user asks for strict review

### Story 2: Invisible Dashboard Open

As a researcher, I want to say "open dashboard," so that the agent handles server, port, readiness, and URL internally.

Acceptance criteria:

- Given a workspace has `research-pilot.db`
- When the user asks to open the dashboard
- Then the agent reuses or starts the dashboard server
- And the dashboard opens or a URL is reported
- And user-facing docs do not require the user to run dashboard server commands

### Story 3: Ambient Research Update

As a researcher, I want Research-Pilot to record what changed after meaningful agent research work, so that dashboard state reflects current project understanding.

Acceptance criteria:

- Given the agent completes a meaningful research task
- When project understanding changes
- Then the agent records an UnderstandingUpdate or equivalent DB-backed update
- And recent changes/current understanding can be rendered through existing read-only surfaces
- And formal D* review is optional advanced mode

### Story 4: Source-Agnostic Intake

As a researcher, I want to give the agent a PDF, URL, arXiv link, DOI, note, experiment result, or Zotero item, so that Research-Pilot records the source without forcing Zotero setup.

Acceptance criteria:

- Given a user provides a source in chat
- When the agent records it
- Then source identity is stored with type/status/relevance
- And Zotero is not required for first-run value
- And Zotero docs remain available as supported adapter docs

### Story 5: Advanced Review Mode

As a careful researcher, I want optional strict graph review, so that important claim changes can still use D* rigor without making normal use procedural.

Acceptance criteria:

- Given a user asks for strict review or the agent detects a high-impact graph-level change
- When the agent proposes a formal graph update
- Then D* dry-run and human gate are used
- And advanced docs explain the protocol
- And README/first-run docs do not present it as mandatory normal use

## 9. Requirements

### R1: Reframe Public README

The README should lead with:

```text
Research-Pilot gives your AI agent local project memory and a read-only dashboard.
```

It should demote:

- Zotero-first identity;
- human-gated deltas;
- D* terminology;
- graph source-of-truth explanation;
- CLI fallback blocks;
- gap contracts and next-action workflows;
- experiment proposal framing.

It should promote:

- chat-first loop;
- workspace-local `research-pilot.db`;
- source-agnostic intake;
- UnderstandingUpdates / durable project understanding;
- read-only dashboard observation;
- demo workspace;
- advanced review mode as optional.

### R2: Simplify Installer Output

`install.sh` should keep technical installation behavior but change post-install guidance.

Normal output should say:

```text
Restart Codex.
Ask the agent: "Use Research-Pilot to track my research project."
```

It should not foreground `research-pilot-init`. Helper command links may remain for compatibility/troubleshooting, but they should be labeled internal fallback.

### R3: Rewrite Plugin Manifest Prompts

`.codex-plugin/plugin.json` should describe Research-Pilot as chat-first local research memory.

Default prompts should avoid graph/delta wording and prefer:

- "Use Research-Pilot to track this project."
- "Read this source and record what matters for the project."
- "Open the Research-Pilot dashboard."

Keywords should demote product identity around Zotero and knowledge graph if possible.

### R4: Convert Router Skill to Intent Router

`skills/research-pilot/SKILL.md` should become a concise intent router:

```text
start/track project
inspect workspace/project
open dashboard
record source
record project understanding update
read source deeply
map literature
record experiment design/result
use strict review
```

It should not list every underlying graph/query/build command as current capability. Low-level commands should move under advanced/internal sections.

### R5: Reframe First-Run

`skills/research-pilot-first-run/SKILL.md` and `templates/workspace/wiki/_system/workflows/first-run.md` should make first-run success:

```text
workspace exists
research-pilot.db exists
project exists
initial brief/update exists
dashboard can observe it
agent knows next natural chat prompt
```

D* should move to strict review mode.

### R6: Reframe Workspace Instructions

`templates/workspace/AGENTS.md` should present the workspace as local project memory:

```text
research-pilot.db = primary workspace dataset
wiki = durable agent-readable context and compatibility artifacts
dashboard = read-only observer
chat/agent = primary control surface
graph events/deltas = advanced strict review
Zotero = optional supported adapter
```

### R7: Demote Command Shims

`commands/research-init.md` and `commands/research-dashboard.md` should remain only as agent-internal compatibility runbooks.

They should avoid sounding like user commands and should point back to natural-language intents.

### R8: Update Public Guides

Guides should be split by audience:

- normal user guide: chat-first operations;
- agent/internal guide: tools and lifecycle;
- advanced review guide: graph/delta/D*;
- adapter guide: Zotero.

Existing docs may remain but should have clear labels.

### R9: Preserve Advanced Tools

No advanced graph/delta tools should be deleted in this cleanup. They should be kept as advanced compatibility unless a separate deletion plan proves no tests, docs, or skills depend on them.

## 10. Non-Goals

This PRD does not include:

- dashboard UI redesign;
- dashboard route changes;
- `research-pilot.db` schema changes;
- demo affordance data migration;
- deletion of graph/delta tools;
- deletion of transition skills;
- cloud sync;
- new dashboard server lifecycle implementation;
- source connector implementation;
- changing test architecture beyond docs/surface expectations;
- removing command files if they are still useful as internal runbooks.

## 11. Suggested File Scope

Likely modified files:

```text
README.md
install.sh
.codex-plugin/plugin.json
commands/research-init.md
commands/research-dashboard.md
skills/README.md
skills/research-pilot/SKILL.md
skills/research-pilot-first-run/SKILL.md
skills/project-understanding-update/SKILL.md
skills/paper-discovery-intake/SKILL.md
skills/single-paper-deep-read/SKILL.md
skills/project-evidence-synthesis/SKILL.md
templates/workspace/AGENTS.md
templates/workspace/wiki/_system/workflows/first-run.md
templates/workspace/wiki/_system/workflows/project-understanding-update.md
templates/workspace/wiki/_system/workflows/paper-discovery-intake.md
templates/workspace/wiki/_system/workflows/single-paper-deep-read.md
templates/workspace/wiki/_system/workflows/project-evidence-synthesis.md
templates/workspace/wiki/_system/workflows/zotero-source-protocol.md
docs/guides/install.md
docs/guides/dashboard.md
docs/guides/workspace.md
docs/guides/core-workflows.md
docs/guides/source-boundaries.md
docs/guides/zotero.md
```

Likely untouched files:

```text
dashboard/**
tools/research_dataset*.py
tools/research_browser_server.py
tools/graph_*.py
examples/workspaces/research-pilot.db
examples/archive/**
```

## 12. Success Criteria

### Product Clarity

A new user should be able to explain Research-Pilot as:

```text
local project memory and a read-only dashboard for my research agent
```

They should not describe it as:

```text
a command system
a Zotero-first workflow
a graph delta approval tool
a dashboard database builder
```

### First-Run Clarity

After install, docs should require only:

```text
restart Codex
ask the agent to track a project
```

Manual command fallbacks may exist but should not be the main path.

### Agent Clarity

Agent-facing docs should make these defaults clear:

```text
normal update = DB/UnderstandingUpdate/project memory
strict update = optional D* advanced review
source intake = source-agnostic first
dashboard = read-only observer
```

### Regression Safety

Existing release checks should still pass. Demo affordance should remain available in `examples/workspaces/research-pilot.db`. Dashboard should still open over the example workspace.

## 13. Risks and Mitigations

### Risk: Oversimplification hides needed rigor

Mitigation:

Keep advanced review docs and D* tools. Rename and demote, do not delete.

### Risk: Agent writes too freely without user approval

Mitigation:

Normal updates may record agent understanding, but high-impact graph-level changes use strict review mode. User decisions still require explicit human approval.

### Risk: Docs become inconsistent with existing tools

Mitigation:

Split docs by audience and keep internal runbooks precise. User docs can be simple; agent/internal docs can keep exact commands.

### Risk: Users cannot recover if chat routing fails

Mitigation:

Keep helper commands and command shims as troubleshooting/internal fallback, but label them clearly.

## 14. Open Questions

1. Should command shim files stay under `commands/`, or move/rename to an internal runbook location later?
2. Should install still create `~/.research-pilot/bin/research-pilot-init`, or only keep it for update compatibility?
3. Should `project-next-action` remain installed as a visible skill, or be demoted further into router-internal logic?
4. Should the README use "Research-Pilot" or "Research Pilot" consistently in public copy?

## 15. PM Recommendation

Proceed with a documentation/agent-surface cleanup PR before more dashboard or DB work.

Priority order:

```text
1. README and install output
2. plugin manifest prompts
3. router and first-run skills
4. workspace templates
5. command shims
6. public guides
7. doc/test scans for old first-run language
```

This should be treated as architecture cleanup because agent-facing instructions shape runtime behavior. The goal is not cosmetic copy polish. The goal is to align the codebase's operational instructions with the product architecture:

```text
Research-Pilot provides local memory resources.
The agent operates them.
The user keeps researching through chat.
```
