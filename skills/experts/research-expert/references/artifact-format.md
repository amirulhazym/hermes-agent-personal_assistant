# Research Artifact Package Format

## Directory

```
~/.hermes/research/artifacts/YYYY-MM-DD-<slug>/
  meta.yaml           # required
  report.md           # required — user-facing synthesis
  sources.json        # required — structured sources
  extracts/           # optional — one file per URL
    01-<host>.md
  trace.md            # optional until Fasa 3 — stage log
```

`<slug>` = lowercase kebab from question (max ~40 chars).

## meta.yaml

```yaml
schema: research-artifact/v1
created_utc: "2026-07-13T00:00:00Z"
question: "..."
slug: "..."
pipeline: [plan, search, extract, verify, synthesize]
search_backends_used: [tavily]   # and/or ddgs
extract_backends_used: [trafilatura, crawl4ai]
source_count: 0
confidence: medium   # high | medium | low
labels:
  validated: 0
  untested: 0
  rejected: 0
  pending: 0
constraints:
  max_spawn_depth: 1
  max_concurrent_children: 3
med_touch: false
```

## sources.json

```json
{
  "schema": "research-sources/v1",
  "sources": [
    {
      "id": "S1",
      "title": "",
      "url": "",
      "accessed_utc": "",
      "search_backend": "tavily",
      "extract_backend": "trafilatura",
      "snippet": "",
      "label": "VALIDATED"
    }
  ]
}
```

## report.md

Use `templates/research-artifact.md` structure.

## Knowledge-layer note (Fasa 4 contract)

Artifacts are the handoff unit for Obsidian/knowledge import.
See `references/knowledge-contract.md` for the interface definition.

**Quick export (Fasa 4 stub):**
```bash
python3 ~/.hermes/scripts/research_knowledge.py <artifact_dir>
# Produces: vault-note.md — copy to Obsidian manually
```

Do not dual-write vault unless user asks; this package is SSOT for PX-1.
