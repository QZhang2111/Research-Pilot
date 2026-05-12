# Zotero Guide

Research Pilot is Zotero-first for normal paper management.

Zotero owns:

- paper metadata;
- PDFs;
- collections;
- tags;
- reading status mirror.

Research Pilot owns:

- digested paper dossiers;
- project graph events;
- claims, evidence, warrants, limitations;
- human-gated graph deltas.

Public source intake records durable source identity and can run without credentials for setup/dry-run checks. This is not a replacement paper manager.

Public tooling also includes configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config.

## Agent-Guided Setup

Normal setup is conversational. Users do not need to memorize commands.

An agent may use `tools/zotero_setup.py` internally to prepare and inspect local Zotero setup. When `.env.example` or `.env` is missing, the agent creates those files. The user creates a Zotero key at `https://www.zotero.org/settings/keys/new`, then pastes only `ZOTERO_API_KEY` into local `.env`.

The agent validates the key without printing it. Later setup steps, such as collection setup, can persist non-secret library metadata like `library_type` and `library_id` to `.research-pilot/config.toml`. API keys stay only in `.env`.
