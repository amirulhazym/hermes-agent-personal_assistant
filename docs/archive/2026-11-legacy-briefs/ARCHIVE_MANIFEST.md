# Archive Manifest — `docs/archive/2026-11-legacy-briefs/`

Archived: **2026-11-16** (owner-approved cleanup, `/xcute` runbook Phase 3).
Reason (all rows): *Superseded audit/continuation brief or one-off execution prompt moved from the
repository root for workspace hygiene. Content is historical; it is not live instruction.*

Selection rule actually applied (evidence, not guesswork): every file below is a
`CONTINUATION-BRIEF-*` / audit-prompt / overhaul-prompt artifact from 2026-06-28 → 2026-07-18, and
none is referenced by `tests/guard/` or `.github/workflows/`. Files referenced by live operational
docs (`AGENTS.md`, `RUNBOOK.md`, `DECISIONS.md`, `PROGRESS.md`, `PRD.md`, `AUDIT.md`) were **kept**
in root.

| # | Original path | Archived at | Last content date | Reason |
|---|---|---|---|---|
| 1 | `/CONTINUATION-BRIEF.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF.md` | 2026-07-11 | Superseded continuation brief; 0 inbound references |
| 2 | `/CONTINUATION-BRIEF-P2.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF-P2.md` | 2026-07-11 | Superseded continuation brief (Phase 2) |
| 3 | `/CONTINUATION-BRIEF-P3.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF-P3.md` | 2026-07-13 | Superseded continuation brief (Phase 3); 0 inbound references |
| 4 | `/CONTINUATION-BRIEF-P4.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF-P4.md` | 2026-07-13 | Superseded continuation brief (Phase 4) |
| 5 | `/CONTINUATION-BRIEF-PX1.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF-PX1.md` | 2026-07-18 | Superseded continuation brief (PX1) |
| 6 | `/CONTINUATION-BRIEF-PX2.md` | `docs/archive/2026-11-legacy-briefs/CONTINUATION-BRIEF-PX2.md` | 2026-07-18 | Superseded continuation brief (PX2) |
| 7 | `/CLAUDE_AUDIT_PROMPT.md` | `docs/archive/2026-11-legacy-briefs/CLAUDE_AUDIT_PROMPT.md` | 2026-06-28 | One-off external-audit prompt for an obsolete audit cycle |
| 8 | `/NEW_AUDIT_PROMPT.md` | `docs/archive/2026-11-legacy-briefs/NEW_AUDIT_PROMPT.md` | 2026-06-28 | One-off external-audit prompt for an obsolete audit cycle |
| 9 | `/OVERHAUL-EXECUTION-PROMPT.md` | `docs/archive/2026-11-legacy-briefs/OVERHAUL-EXECUTION-PROMPT.md` | 2026-07-11 | One-off overhaul execution prompt; superseded by `skills/operator/xcute` + `AGENTS.md` |

## Kept in repository root (and why)

| File | Reason kept |
|---|---|
| `README.md` | Repository entry point |
| `AGENTS.md` | Operator constitution — authoritative |
| `RUNBOOK.md` | Live operational runbook |
| `DECISIONS.md` | Living decision log |
| `PROGRESS.md` | Living status log |
| `PRD.md` | Product requirements (living) |
| `ADVANCED-IDEAS.md` | Idea backlog, still referenced |
| `AUDIT.md` | Historical audit **record** (not a prompt); referenced by 19 files under `audits/` |
| `MEDICATION-SAFETY-REGIMEN-DESIGN.md` | Live medical-safety design |
| `PX1-RESEARCH-TRACK-PLAN.md` | Research track plan, still referenced by `DECISIONS.md`/`PROGRESS.md` |
| `PX2-PROBLEM-INTELLIGENCE-PRD.md` | PRD still referenced by `DECISIONS.md`/`PROGRESS.md` |

## Known side effect

`docs/manifest-coverage-map.md` and `audit-prep/01-VPS-BASELINE.md` still name the old root paths
(`/CLAUDE_AUDIT_PROMPT.md`, `/NEW_AUDIT_PROMPT.md`, `/OVERHAUL-EXECUTION-PROMPT.md`). Those are
historical text references, not automated readers; the new paths are recorded in this manifest.
