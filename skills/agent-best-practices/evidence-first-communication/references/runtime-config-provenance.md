# Runtime Configuration Provenance — Medical Timing Incident (2026-08-15)

## Why this reference exists

A live medication confirmation was held because the system treated a stale reminder window as a clinical boundary. The incident exposed a reusable provenance and semantic-boundary failure class: an operational schedule file was ignored by Git, a live gate consumed it as authoritative, and a candidate design had already changed the intended semantics without being deployed.

## Reproduction/evidence pattern

Live configuration:

- `/home/ubuntu/.hermes/med-schedule.json:34-35`: Slot B nominal `08:00`, window `07:30–08:30`.
- `/home/ubuntu/.hermes/med-schedule.json:59-60`: Slot C nominal `12:00`, window `11:30–12:30`.
- Live metadata: version `1.3.1`, `last_updated=2026-08-12`.

Live consumer:

- `/home/ubuntu/.hermes/scripts/med_safety_gate.py:64-72` parses the window as an inclusive range.
- Lines `247-250` emit `SCHEDULE_TIME_WINDOW` when the stated time falls outside the range.
- Therefore a reported C intake at `12:43` was held solely because it was later than the configured `12:30` endpoint.

Intended candidate semantics:

- `hermes-agent-personal_assistant-work/scripts/med_safety_gate.py:9-12` says `window` is reminder metadata, not a hard intake boundary.
- Lines `74-77` use the schedule/taper `time` as the lower clinical anchor and preserve late actual intake.
- This candidate behavior is not live until deployment and runtime reload are independently proven.

## Provenance checks

For a schedule/config path, run read-only checks separately:

```bash
git check-ignore -v <path>
git ls-files -- <path>
git log --all --follow -- <path>
git show HEAD:<path>
```

Interpretation:

- If `check-ignore` matches, the file is operational/out-of-band.
- If `git log` is empty and `git show HEAD:<path>` fails, a recent merge/rebase is not proven as the file's origin.
- Compare the live copy with candidate copies and dated backups; record version, `last_updated`, mtime, size, and SHA-256.
- If no writer/audit record exists, report `writer provenance: DATA GAP`. Do not infer that a merge, rebase, or deployment wrote it.

In this incident, the same legacy B/C windows appeared in the July 5 candidate, July 11/18 backups, and July 31 P1 backups; the schedule was ignored and absent from `HEAD`. The Aug 12 live update changed taper snapshot metadata/doses but retained the old windows. This proves the stale values predated the recent rebase; it does not prove what process performed the Aug 12 update.

## Reporting rule

Use this wording when appropriate:

> `LIVE CONFIGURED LEGACY VALUE — NOT VERIFIED CLINICAL RULE`

Then separate:

1. the configured value and exact consuming code;
2. the software decision (ALLOW/HOLD/reject) and raw audit evidence;
3. the authoritative clinical rule, which requires a doctor/prescription/source or an explicitly ratified system contract;
4. the remaining provenance gap.

Do not ask the user to confirm or ratify a stale window merely because the live gate reads it. Do not log around a safety hold by direct state mutation. Keep candidate, deployed, and live behavior distinct.

## Recurring-impact evidence

Repeated dated `SCHEDULE_TIME_WINDOW` entries for Slot C (for example observed times `13:28` on 2026-08-02, `14:18` on 2026-08-05, `12:32` on 2026-08-06, `13:00` on 2026-08-09, and `12:55` on 2026-08-10) establish a recurring failure class rather than a single bad event. The log proves the software held those reports; it does not, by itself, prove clinical invalidity.
