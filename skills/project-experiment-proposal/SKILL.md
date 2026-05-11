---
name: project-experiment-proposal
description: Use when a Research Pilot project needs an experiment proposal from a weak or bounded project claim.
argument-hint: "<project> <claim-id>"
---

# Project Experiment Proposal

Experiment proposals are planning artifacts, not graph evidence.

In the current public extraction, use `project-gap-analysis` to identify bounded claims:

```bash
python3 "$PLUGIN_ROOT/tools/project_gap_cli.py" detect --repo "$WORKSPACE_PATH" --project "$PROJECT_ID" --json
```

Full experiment proposal tooling is a later extraction slice unless present in this plugin version.

Do not append graph events or claim experiment results.

