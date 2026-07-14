# Research-to-Knowledge Contract (Fasa 4)

Defines the interface between PX-1 research artifacts and long-term knowledge storage
(Obsidian vault, or equivalent). Not a full vault product — a contract + thin stub.

---

## 1. Artifact as Handoff Unit

Research artifacts (under `~/.hermes/research/artifacts/`) are the **single source of truth**
for PX-1 research output. Knowledge storage reads artifacts — never writes them.

```
Research Expert  ──produces──►  Artifact Package  ──imported──►  Knowledge Vault
                                    │                                (Obsidian)
                                    └── SSOT, never modified ──►
```

## 2. Artifact → Vault Mapping

| Artifact file | Vault destination | Notes |
|---------------|-------------------|-------|
| `report.md` | `Research/{YYYY}/{MM}/{slug}.md` | Primary research note |
| `meta.yaml` | Frontmatter (YAML) | Injected into the note as YAML frontmatter |
| `sources.json` | Backlinks section | Links under `## Sources` with Obsidian `[title](URL)` |
| `trace.md` | Optional — not imported to vault (audit trail only) | Log file, not knowledge product |

## 3. Frontmatter Contract

Every research note imported to vault gets this frontmatter:

```yaml
---
title: "<report title>"
date: "YYYY-MM-DD"
created_utc: "ISO8601"
question: "<original user question>"
confidence: high | medium | low
labels:
  validated: N
  untested: N
  rejected: N
  pending: N
sources: N
backends:
  search: [tavily, ddgs]
  extract: [trafilatura, crawl4ai]
tags:
  - research
  - PX-1
  - <auto-tags from question keywords>
---
```

## 4. Policy

### Auto-import (disabled by default)
- No silent vault writes. The user controls when/how research enters their vault.
- Agent may offer to "Save this research to your vault?" with a one-click confirmation.
- Vault path: user-configured in `.env` as `OBSIDIAN_VAULT_PATH` (optional).

### Manual import (default)
- User copies the artifact folder to their vault.
- `report.md` is the ready-to-use note.
- Frontmatter is pre-formatted, can be copy-pasted.

### Write-back (disabled)
- Research artifacts are read-only from knowledge perspective.
- Knowledge vault may contain user notes, amendments, follow-ups — but these do not feed back into PX-1 pipeline.
- If the user wants to re-research a topic, a new artifact is produced.

## 5. Thin Stub Interface

A minimal CLI/Python helper (`~/.hermes/scripts/knowledge_export.py`) to:

```python
# Core interface — never checks for vault existence (that's user concern)
def artifact_to_frontmatter(meta_path: Path) -> dict:
    """Parse meta.yaml → Obsidian frontmatter dict"""

def artifact_to_markdown(artifact_dir: Path) -> str:
    """Produce a single .md file with frontmatter + report + sources"""

def artifact_to_backlinks(sources_path: Path) -> str:
    """Produce Obsidian [[backlink]] section from sources.json"""

def export_artifact(artifact_dir: Path, output_dir: Path) -> Path:
    """Full export: produce vault-ready .md note"""
```

The stub lives at `~/.hermes/scripts/research_knowledge.py`. It:
- Does NOT auto-write to any vault directory
- Does NOT import Obsidian SDK
- Produces the `.md` file in the artifact directory
- User copies it manually

### CLI

```bash
# Export one artifact
~/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/scripts/research_knowledge.py \
  ~/.hermes/research/artifacts/2026-07-14-deepseek-pricing/
# Output: ~/.hermes/research/artifacts/2026-07-14-deepseek-pricing/vault-note.md

# List recent artifacts
~/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/scripts/research_knowledge.py --list
```

## 6. Out of Scope (explicit)

- Automatic vault sync
- Obsidian plugin or `.obsidian/` config
- Bidirectional updates (vault → research)
- Tag taxonomies (user defines)
- Folder structure beyond the convention above
- Graph/navigation linking
- Full vault search

## 7. Future (Fasa 4+, PX-1b)

- Optional: one-click export via Hermes chat action
- Auto-tags from question NLP
- Link to related research notes (shared sources)
- Knowledge freshness check (compare artifact date vs current date)

---

## 8. Vault-Note Template Section

Appended to `templates/research-artifact.md`:

```markdown
## Export (Fasa 4+)

Export this research to your knowledge vault:
```bash
# Run from artifact directory
python3 ~/.hermes/scripts/research_knowledge.py .
# Produces: vault-note.md
```

Copy `vault-note.md` to your Obsidian vault. The frontmatter is pre-formatted.
```
