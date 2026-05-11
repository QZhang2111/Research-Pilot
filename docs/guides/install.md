# Install Guide

Research Pilot is packaged as a Codex plugin source with a manifest at:

```text
.codex-plugin/plugin.json
```

For current local use, install Research Pilot from a checkout:

```bash
./install.sh codex
```

This links skill directories into the Codex-compatible skill directory. The plugin manifest points future plugin tooling at the same `skills/` directory.

After install, create a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Run the agent inside the private workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```
