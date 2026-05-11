# Install Guide

Install Research Pilot from a local checkout:

```bash
./install.sh codex
```

This links skill directories into the Codex-compatible skill directory.

After install, create a private workspace:

```bash
python3 tools/research_pilot_init.py ~/Research/MyResearchWiki
```

Run the agent inside the private workspace and ask:

```text
Use Research Pilot to inspect this workspace.
```

