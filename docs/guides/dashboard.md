# Dashboard Guide

Dashboard is a required public browser component and a read-model observer.

It reads:

- `.dashboard/index.json`;
- graph snapshots;
- `wiki/graphs/graph.db`;
- project markdown.

Graph truth remains:

```text
wiki/graphs/events/**/*.jsonl
```

Build and serve:

```text
/research-dashboard ~/Research/MyResearchWiki
```

Manual fallback:

```bash
python3 tools/build_dashboard_index.py --repo "$WORKSPACE" --output .dashboard/index.json
python3 tools/research_browser_server.py --repo "$WORKSPACE" --port 8765
```
