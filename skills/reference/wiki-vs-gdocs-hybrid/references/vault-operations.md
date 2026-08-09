# Vault operations — ~/wiki (the local side of the hybrid, as built)

Status: operational since 27 Jul 2026 (Fase 1), expanded 31 Jul (Fase 2).
Authoritative rules live in `~/wiki/AGENTS.md` — read it before any vault work.

## Location & layout

- Vault: `~/wiki/` — local-only git repo (0 remotes, verified 31 Jul).
- `wiki/` = curated, indexed knowledge (target 30–60 files; 4 as of 31 Jul).
- `decisions/` = APPEND-ONLY. `NNNN-short-slug.md` naming. Superseded →
  `status: superseded` + `superseded_by:` field. Never edit/delete old entries.
- `runbooks/` = verb-object.md naming (e.g. `google-reauth.md`).
- `raw/` = greppable, NOT indexed.
- ONE `index.md` at vault root only. Every new file gets a line there.

## Frontmatter contract (SCHEMA.md)

Required keys: `title, type, status, created, updated, source,
evidence_tier, supersedes`. Enums: type ∈ note|decision|runbook|raw|index;
status ∈ draft|active|superseded|archived; evidence_tier ∈
evidence|inference|unknown. Dates YYYY-MM-DD; `updated >= created`;
`updated` bumped on EVERY content change; `created` never changes.

## Hard rules (AGENTS.md)

1. Wiki = single source of truth. Google Docs are rendered snapshots —
   NEVER read Drive for knowledge.
2. Every file needs complete frontmatter.
3. Every write followed by a git commit (no silent writes).
4. decisions/ append-only.
5. Cite the exact file path when answering from the vault.
6. Never present inference as measurement (`evidence_tier`).

## Tools (built 31 Jul 2026)

- `~/.hermes/scripts/lint_md.py` — vault linter. Enforces frontmatter
  contract + naming + index rule + superseded_by. Usage:
  `python3 ~/.hermes/scripts/lint_md.py --vault ~/wiki` → exit 0 = clean.
  Tested: 7 fixtures → 11 violations caught; real vault → 0.
- `~/.hermes/scripts/wiki_gate_measure.py` — Fasa 1 gate measurement.
  Metric: `cache_read/(cache_read+input_tokens)` from state.db sessions
  table (7-day window). `cache_read/input` is INVALID (>100%).
  ⚠ Baseline 76.0% (26 Jul doc) is NOT reproducible from state.db/billing.py —
  same formula on 26 Jul gives 96.96%. Baseline method must be agreed
  BEFORE the 3 Aug gate verdict (see runbooks/measure-cache-gate.md).

## Migration workflow (proven 31 Jul, 6 commits)

For each content batch:
1. Transform source to clean markdown via script (never hand-copy 400-line
   docs — extraction artifacts like `[TABLE]` markers must be converted;
   verify pipe-consistent tables afterwards).
2. Prepend SCHEMA-compliant frontmatter; `created` = original content date,
   `updated` = migration date.
3. Additive-only: append changelog entries with dates, never rewrite body.
4. Lint (`lint_md.py`) → must pass before commit.
5. Update `index.md` + bump its `updated` field.
6. Commit per file with descriptive message (AGENTS.md rule 3).
7. Git identity on this VPS: `Ubuntu <owner@example.invalid>` —
   fine for local-only repo.

## Pitfalls

- `updated` field forgotten → linter passes but rule violated. Check each
  touched file's frontmatter before committing.
- Extracting GDrive docs: text extraction misses TABLE content — must walk
  table cells too (30 tables in the health doc were invisible to naive
  extraction).
- Wiki is NOT Obsidian — no [[wikilinks]] machinery, ripgrep only.
- Health/PII content: vault is local-only git (0 remotes) — acceptable
  for the user's own health profile; NEVER commit raw med-status.json
  dumps.
