# Install Guide

Research Pilot is packaged as a Codex plugin source with a manifest at:

```text
.codex-plugin/plugin.json
```

Install Research Pilot with:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash
```

This clones or updates the plugin source into:

```text
~/.research-pilot/repo
```

It links skills into:

```text
~/.agents/skills/
```

It registers the plugin in:

```text
~/.agents/plugins/marketplace.json
~/plugins/research-pilot
```

The marketplace entry uses `./plugins/research-pilot`; with a home-local marketplace this resolves to `~/plugins/research-pilot`.

It also creates compatibility helper links:

```text
~/.research-pilot-plugin
~/.research-pilot/bin/research-pilot-init
```

After restart, Research Pilot should appear as a local plugin in Codex plugin views. If a Codex build only reads skills, the installed skills still work.

Check plugin health:

```bash
python3 "$HOME/.research-pilot/repo/tools/plugin_health.py" --plugin-root "$HOME/.research-pilot/repo" --json
```

The health check reports plugin version, source path, command files, helper links, and whether the dashboard server fallback is available. `commands_visible` is `unknown` because command exposure is host state; restart Codex after install or update so plugin metadata reloads.

After install, start Codex and use the plugin command:

```bash
codex
```

```text
/research-init ~/Research/MyResearchWiki
```

Manual fallback:

```bash
~/.research-pilot/bin/research-pilot-init ~/Research/MyResearchWiki
```

If `/research-init` is not visible, ask the agent to resolve `PLUGIN_ROOT` and run:

```bash
python3 "$PLUGIN_ROOT/tools/research_pilot_init.py" "$WORKSPACE_PATH"
```

Run the agent inside the private workspace after initialization:

```bash
cd ~/Research/MyResearchWiki
codex
```

Then ask:

```text
Use Research Pilot to inspect this workspace.
```

Open the dashboard:

```text
/research-dashboard ~/Research/MyResearchWiki
```

If `/research-dashboard` is not visible, ask the agent to use the host fallback in `commands/research-dashboard.md`. The fallback starts `tools/research_browser_server.py` from the plugin root, verifies the local URL, and opens or prints it. Slash command visibility is not required.

Update plugin source:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s -- --update
```

Remove skill links while keeping the hidden checkout:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s -- --uninstall codex
```
