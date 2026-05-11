# Zotero Source Protocol

Core rule:

```text
Zotero = source of truth for papers, metadata, PDFs, collections, and operational paper triage.
wiki = source of truth for digested research knowledge, claims, project reasoning, and long-term taste.
```

Research Pilot does not reimplement citation management.

## Public MVP Boundary

Current public source intake records durable source identity:

- Zotero item key;
- DOI;
- arXiv ID;
- URL;
- manual source refs.

Full Zotero bridge automation is a later extraction slice unless explicitly present in the installed plugin version.

## Human Gate

Agent may intake, summarize, and propose. Human decides approval, project-core status, and graph delta acceptance.

