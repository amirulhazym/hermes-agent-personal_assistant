# Gate 5 PC Workspace Classification Ledger — 2026-08-06

Base: integration/reconcile-20260806. PC primary repo F:\AI Prep\OVIS\Hermes Agent\MJay
(overhaul/exec @ 2b43b7a) + worktree .worktrees/px1b-web-operator (feature/px1b-web-operator @ bb22d56).

| PC path | Classification | Resolution |
|---|---|---|
| .vscode/settings.json (2B, {}) | PORT-TOOLING | COMMITTED 19f1dbb (portable, non-personal) |
| .mimocode/package.json + package-lock.json + .gitignore | ARCHIVE | Plugin self-ignores its metadata (.gitignore excludes package.json/lock); node_modules excluded; preserved in Gate 1 pc-ignored-valuable tar |
| .mimocode/plans/1782790853171-gentle-cabin.md | PORT-DOC (scrubbed) | COMMITTED f0f9132 as docs/plans/vps-migration-plan-2026-06-30-SUPERSEDED.md; F:\ paths + usernames scrubbed; SUPERSEDED label |
| docs/VPS-MIGRATION-GUIDE.md | PORT-DOC (scrubbed) | COMMITTED f0f9132 as docs/migration/VPS-MIGRATION-GUIDE.md; scrubbed |
| docs/compose/plans/rebuild-plan.md | PORT-DOC (scrubbed) | COMMITTED f0f9132 as docs/plans/rebuild-plan-2026-06-30-SUPERSEDED.md; scrubbed |
| PX1B PROGRESS.md (modified) | ALREADY-PRESENT/SUPERSEDED | Integration PROGRESS.md + px1b-live-contracts.md (d13110ce) already contain all unique facts (Telegram E2E table line 59, cua-driver 0.7.1 line 90, 20/20 acceptance); no merge to avoid overwriting newer content |
| PX1B docs/px1b-live-contracts.md | ALREADY-PRESENT/SUPERSEDED | Integration version (d13110ce, 203 lines) is newer — "feature worktree abandoned per human choice"; PC worktree version preserved in Gate 1 pc-px1b-files tar |
| .mimocode/.gitignore | ARCHIVE | Plugin convention; preserved in Gate 1 |
| audit-prep/med-status.json | RUNTIME/PII | NEVER TRACKED (runtime medical state; Gate 1 pc-ignored-valuable + encrypted preserves) |

Gate 1 PC artifacts: D:\hermes-gate1\pc (8 files, 2,642,885 B) verified intact during preflight.
