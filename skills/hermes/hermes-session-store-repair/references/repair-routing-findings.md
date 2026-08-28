# repair-routing dry-run findings (reference session 2026-08-13)

## Command
```
hermes sessions repair-routing          # report-only, NO --apply
```

## Result (condensed)
- 20260811_065757_36297d00 (whatsapp, 39 messages) -> adopt into agent:main:whatsapp:dm:601166557800 (from 20260811_065805_7d30b652, evidence: contiguity)
- 20260811_071542_919409 (telegram, 93 messages) -> NOT repairable: parent session carries no gateway identity of this source
- ... 924 more NOT repairable lines (all telegram/whatsapp older rows) ...
- Final: "2 of 926 orphaned session(s) can be repaired. Re-run with --apply to perform them."

## Interpretation
- The tool found 926 orphaned rows (NULL session_key) total.
- It confidently re-stamps only 2 -- because each has a keyed predecessor whose identity is unambiguous (contiguity evidence).
- The other 924 are rejected with "parent session carries no gateway identity of this source" -- the parent chain itself is also untagged, so the tool cannot prove which lane the row belongs to. This is CORRECT conservative behavior, not a bug.
- Therefore the official tool alone does NOT solve the bulk (870 older rows). Those need chain-proven manual backfill (see SKILL.md step 3) -- which the user (solo operator) explicitly approved as the "unsafe but fine for me" path.

## Key takeaway for future sessions
Always run repair-routing (dry run) first -- it is the blessed, fail-closed path and catches the unambiguous cases for free. Do not treat its low fix-count as "the tool failed"; it is working as designed. Plan the manual backfill for the rest using cross-checked proven keys (sessions.json + gateway_routing).
