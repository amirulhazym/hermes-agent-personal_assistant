# Operation Ledger

`ledger.json` is the **shared cross-channel operation ledger**. Telegram and
WhatsApp sessions MUST check it before starting long-running work and attach
themselves to the active task — never duplicate an audit or task already
recorded as active or complete.

## Rules

1. Before long-running work: read `ledger.json`; if a task is `active`, attach
   to it instead of starting a new one.
2. On completion: update the task to `complete` with evidence (SHA, report
   path, date).
3. Non-blocking follow-ups are recorded as `pending` with a note.
4. `operations/**` is a **protected** path — changes require
   `APPROVE RELEASE <sha>`.

## Current state (2026-08-06)

- Gates 1–7: complete (evidence in ledger).
- Post-Gate-7 audit: complete — `LIVE RELEASE PASS`, canonical audit
  `hermes-live-state-audit-20260806-2.md` (crontab SHA-256 `b107c739…`;
  first audit superseded — its `756bdde7…` was MD5).
- Governance v2 bootstrap: **active** on `operator-governance-v2`.
- Audit debt: overlay gap + 12 candidates — classified, queued for
  maintenance release.
- Google Drive offsite copy: pending (non-blocking).
