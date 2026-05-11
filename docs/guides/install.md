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

It also creates:

```text
~/.research-pilot-plugin
~/.research-pilot/bin/research-pilot-init
```

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

Run the agent inside the private workspace after initialization:

```bash
cd ~/Research/MyResearchWiki
codex
```

Then ask:

```text
Use Research Pilot to inspect this workspace.
```

Update plugin source:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s -- --update
```

Remove skill links while keeping the hidden checkout:

```bash
curl -fsSL https://raw.githubusercontent.com/QZhang2111/Research-Pilot/main/install.sh | bash -s -- --uninstall codex
```
