# Paper Dossier Template

Use `tools/paper_dossier_cli.py create` to generate concrete project paper dossiers.

Required sections:

- `## Source Identity`
- `## Deep Read Notes`
- `## Project Relevance`
- `## Project Graph Delta Proposals`

Delta proposals are fenced JSON objects consumed by:

```bash
python3 tools/paper_dossier_cli.py export-deltas --dossier "$DOSSIER" --output-dir "$OUT"
```
