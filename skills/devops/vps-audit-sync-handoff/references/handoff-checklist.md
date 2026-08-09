# Pre-Delivery Checklist — VPS Audit Handoff

Run this loop before telling the user "ready for OpenCode."

## Artifacts present?
- [ ] `0X-SYNC-UPDATE-<date>.md` — corrects stale baseline
- [ ] `0Y-FULL-TIMELINE-<range>.md` — all sessions in range, dated
- [ ] `0Z-EVIDENCE-APPENDIX.md` — raw: cron list, git diff, file:line, .env names, session IDs, med state
- [ ] `0W-MASTER-SYNC-DOC.md` — unifies above
- [ ] `~/hermes-snapshot-<YYYYMMDD>/` — fresh rsync, secrets excluded
- [ ] `README-SNAPSHOT.md` inside snapshot — integrity commands

## Claims verified (not memory)?
- [ ] config.yaml live state pasted verbatim
- [ ] models.py / run.py edits show exact file:line
- [ ] cron count matches live `hermes cron list`
- [ ] med-schedule.json slots listed
- [ ] git status shows uncommitted 9/7 fixes (if any)
- [ ] Windows snapshot explicitly flagged STALE if applicable

## Gaps flagged as OPEN (not hidden)?
- [ ] Unimplemented user requests (e.g. B→C med gap)
- [ ] Known bugs with no fix (e.g. gateway stale-state)
- [ ] Fabricated external-audit claims struck + noted
- [ ] User-ignored issues noted (e.g. minimax)

## Role clarity in master doc?
- [ ] Native agent = verifier post-handoff
- [ ] External agent = executor
- [ ] Access scope stated (rsync + read-only SSH)

## Snapshot integrity
- [ ] `.env` NOT in snapshot (ls check)
- [ ] config.yaml IS in snapshot
- [ ] models.py IS in snapshot
- [ ] MASTER-SYNC-DOC copied into snapshot
