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
