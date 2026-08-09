# Anthropic docx Skill Analysis (fetched 2026-08-01)

Source: `https://github.com/anthropics/skills` → `skills/docx/SKILL.md` (6,911 bytes, main branch).
Path note: older references to `document-skills/docx` 404 — the skill lives at `skills/docx/` now.
License: **source-available, NOT open source** (proprietary LICENSE.txt, same for pdf/pptx/xlsx).
Rule that follows: port IDEAS and methodology, never copy code or scripts.

## What the docx skill actually contains (it is 100% mechanical)

| Section | Content |
|---|---|
| Task routing | Create → docx-js script; Edit → unzip/edit `word/document.xml`/zip; Read → `pandoc -t markdown` |
| Gotchas | 14+ explicit footguns: A4 page default, dual table widths (columnWidths + per-cell), `ShadingType.CLEAR` not SOLID, bullet numbering config not literal `•`, `ImageRun` needs `type:`, PageBreak inside Paragraph, no `\n` in runs, TOC needs `HeadingLevel.*`, PositionalTab for dot-leaders |
| Visual verify | Render to PDF → `pdftoppm -jpeg -r 100` → read the images. The ONLY check that catches visual defects |
| Edit path | `unzip -q` → strip symlinks → `merge_runs.py` (coalesce fragmented runs) → edit XML in place (do NOT pretty-print) → `zip -Xr` → `validate.py` (XSD checks, `--auto-repair`) |
| Redlining | `validate.py --author "<name>"` checks every edit is tracked |

## Key insight: ZERO formatting/structure guidance

The docx skill contains **no** content-structure guidance, section-order rules, or writing style.
It is purely mechanical. Therefore "merge anthropic formatting preferences into our docs" is a
non-question — there is nothing to merge. Our verdict-first / Q1–Q10 / evidence-tables strength
comes from `documentation-workflow` itself, and it is what the user wants kept.

## Capability gap table (gdocs v2.0.0 vs docx skill)

| Capability | docx | gdocs v2.0.0 | Status |
|---|---|---|---|
| Task routing create/edit/read | Yes | Create-only | GAP → planned: CREATE/EDIT/READ/CLONE routing |
| Footgun catalog | Yes (14+) | Partial (C1, rate limit, `--body` forbidden) | GAP → planned: consolidated failure-mode table |
| Visual verification | Yes (soffice→PDF→images) | No | GAP → planned: Drive export→PDF→images |
| Edit existing docs | Yes | No | GAP → planned (with before/after change report) |
| Auto-repair | Yes (`validate.py --auto-repair`) | No | GAP → planned: verify→fix→re-verify loop |
| Content structure guidance | **No** | Yes (Q1–Q10) | We already win |

## Design doc pointer

Full upgrade design (problem statement, root cause F1–F5, 9 ideas + 1 deferred, format variant
registry, plan, risks O1–O7, source register): `~/.hermes/tmp/gdocs-skill-upgrade-design-20260801.md`
(status DRAFT — do not implement from it without user approval; research/analysis input only).

## Prerequisite gap found during audit (2026-08-01)

`gdocs/SKILL.md` step 3 references `python3 $SK/lint_md.py` ("if present") but the script only
exists at `/home/ubuntu/wiki/lint_md.py` (P2 S1 commit `b931226`), never installed into
`google-workspace/scripts/`. Every /gdocs run silently skips the self-check layer. Fix = copy it
over; this was the ONLY friction point in the 31 Jul PRD session traceable to P2 (the rest were
pre-existing CLI gaps, C1 design, and flash-model authoring artifacts).
