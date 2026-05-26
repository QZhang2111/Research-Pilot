# Zotero Adapter Guide

Zotero is an optional supported adapter for paper metadata, PDFs, collections, tags, and reading status. Research Pilot is source-agnostic for first-run project memory.

Zotero owns:

- paper metadata;
- PDFs;
- collections;
- tags;
- reading status mirror.

Research Pilot stores project-scoped source identity, source notes, project understanding, literature structure, experiment records, and dashboard read models in the local workspace.

Public source intake records durable source identity and can run without credentials for setup/dry-run checks. This is not a replacement paper manager.

Public tooling also includes configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config.

## Optional Agent-Guided Setup

Normal setup is conversational. Users do not need to memorize commands.

An agent may use `tools/zotero_setup.py` internally to prepare and inspect local Zotero setup. When `.env.example` or `.env` is missing, the agent creates those files. The user creates a Zotero key at `https://www.zotero.org/settings/keys/new`, then pastes only `ZOTERO_API_KEY` into local `.env`.

The agent validates the key without printing it. Later setup steps, such as collection setup, can persist non-secret library metadata like `library_type` and `library_id` to `.research-pilot/config.toml`. API keys stay only in `.env`.

## Standard Collection Tree

Before creating or reusing collections, the agent asks the user for approval. With approval, the agent validates the Zotero key, reuses exact matching collections, and creates missing collections under `Research_Pilot`.

Standard tree:

- `Research_Pilot`
- `Research_Pilot/00 Inbox`
- `Research_Pilot/10 Projects`
- `Research_Pilot/20 Research Areas`
- `Research_Pilot/30 Review Campaigns`
- `Research_Pilot/90 Archive`

Collection keys are non-secret metadata. The agent stores them in `.research-pilot/config.toml` under `[zotero]` with `library_type` and `library_id`. API keys stay only in local `.env` and are never written to `.research-pilot/config.toml`.
