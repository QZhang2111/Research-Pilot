# Zotero Source Protocol

Core rule:

```text
Zotero = source of truth for papers, metadata, PDFs, collections, and operational paper triage.
wiki = source of truth for digested research knowledge, claims, project reasoning, and long-term taste.
```

Research Pilot does not reimplement citation management.

## Public Boundary

Public source intake records durable source identity:

- Zotero item key;
- DOI;
- arXiv ID;
- URL;
- manual source refs.

Public tooling includes configurable Zotero bridge helpers for metadata, collection, and status-mirror workflows. Credentialed Zotero operations require user-provided local config and must preserve the Zotero-first boundary.

## Human Gate

Agent may intake, summarize, and propose. Human decides approval, project-core status, and graph delta acceptance.
