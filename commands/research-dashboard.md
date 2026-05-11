---
description: Open the local Research Pilot dashboard for a private research workspace.
argument-hint: "[workspace_path] [port]"
---

# /research-dashboard

Open the Research Pilot dashboard for a workspace.

## Arguments

- `workspace_path`: optional path to the private research workspace.
- `port`: optional local port. Default: `8765`.

If no workspace path is provided:

- use the current directory if it is an initialized Research Pilot workspace;
- otherwise ask for one concise workspace path.

## Plugin Root

Resolve `PLUGIN_ROOT` in this order:

```text
~/.research-pilot/repo
~/.research-pilot-plugin
current directory, only if it is the Research Pilot plugin repo
```

Stop with a clear install instruction if no plugin root is found:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

## Workspace Check

The workspace must contain:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/
```

If missing, route to `/research-init` first.

## Workflow

1. Resolve `WORKSPACE_PATH`.
2. Resolve `PORT`, defaulting to `8765`.
3. If the requested port is busy, choose the next available port in `8765..8799`.
4. Start the dashboard server in the background:

```bash
mkdir -p "$WORKSPACE_PATH/.research-pilot"
nohup python3 "$PLUGIN_ROOT/tools/research_browser_server.py" \
  --repo "$WORKSPACE_PATH" \
  --host 127.0.0.1 \
  --port "$PORT" \
  > "$WORKSPACE_PATH/.research-pilot/dashboard-server.log" 2>&1 &
```

5. Verify the server responds:

```bash
URL="http://127.0.0.1:$PORT/dashboard/index.html"
curl -fsS "$URL" >/dev/null
```

6. Open the local dashboard on macOS:

```bash
open "$URL"
```

If `open` is unavailable, print the URL.

## Boundary

Dashboard is a read-model observer. This command may rebuild `.dashboard/index.json` through the dashboard server, but it must not append graph events, accept deltas, edit project truth, or change Zotero state.

## Completion

Report:

```text
Dashboard:
Workspace:
Port:
Server log:
Boundary: read-only observer
```

