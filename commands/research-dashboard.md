---
description: Agent-internal compatibility runbook for opening the local Research Pilot dashboard from natural-language intent.
argument-hint: "[workspace_path] [port]"
---

# Research Pilot Dashboard Runbook

This is an agent-internal compatibility runbook, not a user command surface.

Users should ask a natural-language intent:

```text
Open the Research Pilot dashboard.
```

The agent may use this runbook to resolve workspace, start or reuse the dashboard server, verify readiness, and open or report the local URL.

## Arguments

- `workspace_path`: optional path to the private research workspace.
- `port`: optional local port. Default: `8765`.

If no workspace path is provided:

- use the current directory if it is an initialized Research Pilot workspace;
- if the current directory is the Research Pilot plugin repo, use `examples/workspaces` as the public example workspace;
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

Health check:

```bash
python3 "$PLUGIN_ROOT/tools/plugin_health.py" --plugin-root "$PLUGIN_ROOT" --json
```

## Workspace Check

The workspace must contain:

```text
AGENTS.md
wiki/index.md
wiki/log.md
.research-pilot/
```

If missing, route to the Research Pilot initialization workflow first.

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

## Natural-Language Operation

When the user asks to open the dashboard, the agent must run these server steps from chat. Resolve `PLUGIN_ROOT`, run the health check, start `tools/research_browser_server.py`, verify the URL, and report the same completion summary.

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
