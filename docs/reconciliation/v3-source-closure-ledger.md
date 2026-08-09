# v3 Source-Closure Candidate Ledger — 2026-08-08

This is the bounded source-closure recovery/action universe. It contains path metadata and disposition only; no secret, medical, account, session, persona or runtime values. The machine-readable source is `v3-source-closure-ledger.jsonl`.

- Base application `main`: `13baa13950223c090a9fc97e31baa748874c0edf`
- Nested evidence HEAD: `68d068d67d0103eb5e47a8072d023f0b591246ea`
- Records: `191`
- Dedupe key: `scope + live_path` (unique `191`)

## Scope counts

- `live-agents`: `30`
- `live-hooks`: `7`
- `live-persona`: `3`
- `live-plugins`: `26`
- `live-scripts`: `11`
- `live-skills`: `71`
- `nested-current-gap`: `5`
- `nested-p1-p5`: `38`

## Disposition counts

- `OWNER-DECISION`: `0`
- `PORT-RAW`: `174`
- `PORT-SANITIZED`: `10`
- `PORT-TEMPLATE`: `3`
- `PRIVATE-BACKUP`: `4`

## Exact arithmetic

- `43 nested/current-or-P1–P5 + 148 non-nested = 191 records`
- `148 non-nested = 71 skills + 26 plugins + 7 hooks + 11 scripts + 3 persona + 30 agents`
- The config schema path is an existing source path and is tracked separately as a schema-update action, not added to this live-action universe.

## Included synthetic fixture

- `tests/gateway/test_status_canonical_display.py`: included as `PORT-SANITIZED`; the test uses clearly synthetic identifiers and a placeholder token only. No owner/contact value is published.
- `scripts/whatsapp-bridge/reconnect-controller.js`: included as `PORT-RAW`; it is the adjacent implementation dependency required by the ported bridge reconnect test and does not read session state.

## Exclusions with reasons

- `skills/productivity/documentation-workflow/SKILL.md.bak-20260726`: stale backup; canonical `SKILL.md` is represented, so backup is not active source.
- Hook `.bak*` variants: backup records; canonical active hook paths are represented and backups remain in private preservation evidence.
- Raw account CSV exports and account batch log: private mutable runtime; adjacent source/templates are represented, raw rows/log bytes are not public.
- Live persona/memory values: private runtime; safe public structures only.

## Status discipline

`PORT-RAW` rows are source ports pending guards; `PORT-SANITIZED` rows are source ports with email-like literals or fixtures replaced by safe placeholders; `PORT-TEMPLATE` rows are safe persona structures; `PRIVATE-BACKUP` rows are intentionally outside public Git. All 191 rows are classified; none remains `OWNER-DECISION`. None of these rows is release approval.