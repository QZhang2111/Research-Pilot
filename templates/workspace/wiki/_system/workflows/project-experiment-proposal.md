# Project Experiment Proposal

Purpose: turn a graph claim weakness into a concrete experiment proposal that could produce project-owned evidence.

Experiment proposals are planning artifacts. They are not graph evidence.

## Boundary

This workflow must not append graph events, run experiments, edit Q/C/E/W/L/RL/TL, or claim experiment results.

If an experiment later creates real evidence, route the result through Delta Update Protocol with D* dry-run and human gate.

## Expected Input

Start from:

```text
Claim + ReasoningLink support + Limitation + Warrant + current Evidence
```

Good targets:

- overbounded claim;
- weak warrant;
- claim supported only by paper evidence;
- claim whose limitation implies missing benchmark, dataset, metric, or intervention.

## Tooling

Use `tools/project_experiment_cli.py` when command-line support is useful. Tool output remains a planning proposal until a real experiment is run and routed back through a human-gated graph delta.
