# Timing Overhaul Review Checklist

Use during any medication timing-engine change. This is implementation discipline, not medical advice.

## Locked scheduling semantics

- A (Akurit) is a lower-bound constraint only: the next intake must be at least 60 minutes after the **actual Akurit** time.
- B Dexa default target is 08:00. Resolve pending B as `max(08:00, actual_akurit + 60m)`.
- Do not let early A cascade B/C/D/E. Example: A 05:40 -> B 08:00.
- If A is late enough to make 08:00 unsafe, move only B to the earliest safe time. Example: A 07:18 -> B 08:18.
- Actual Dexa B drives later Dexa timing with exact values; do not round user-stated times. Example: B 07:38 -> C 11:38 -> D 15:38.
- E is a night reminder target no earlier than 20:00. Do not derive it from B+12h or C/D timing. Treat whether an explicitly user-stated earlier E needs a warning as a separate policy decision; do not silently reject or alter stated intake time.
- Calcium/Calcitriol and Pyridoxine are not timing sources for Dexa gaps.

## Required test progression

1. Reproduce the pre-change fault in an isolated copy or isolated HOME.
2. Add failing tests from the exact user examples before implementation.
3. Run targeted tests after each code change.
4. Run whole timing suite and hook suite after all test assumptions are updated.
5. Run the active adapter against a copied production state, never production state.
6. Independently review before deployment.
7. Do not label work live/complete until deployment plus active-path verification has evidence.

## Recurring implementation traps

- A `min_gap` is a lower bound, not a scheduled offset. Never model it as `next = prior + gap`.
- Do not keep a second legacy timing calculation behind an exception handler. Resolver failure must suppress delivery and emit diagnostics.
- A no-agent monitor must update reminder count/cooldown only after a text was successfully generated for delivery. Otherwise failed LLM calls create phantom reminders and suppress the next real one.
- Treat combined drug statements as compound updates. `Done akurit+pyridoxine jam 6.45am` must complete both A drugs at 06:45, not only the first matching drug.
- For timing extraction from partial slots, use the specific timing drug (Akurit for A; relevant Dexa dose for B/C), never the latest drug in the slot.
- Test common Manglish confirmation syntax exactly: `Done` must be a completion signal and both `6.45am` and `6:45am` must parse as 06:45.
- Remove unsafe hardcoded copy and generic fallback delivery paths. Search active source files for obsolete cascade claims such as `geser`; backup files may retain historical text but must not be executable.

## Deployment gate

Before resuming a paused monitor, retain: pre/post hashes, changed-file list, clean syntax checks, targeted/full test output, copied-state dry-run output, reviewer findings resolved, and rollback backups. Keep monitor paused when any blocker remains.
