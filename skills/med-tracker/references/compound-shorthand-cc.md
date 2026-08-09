# Compound Shorthand: CC

## Pattern

"CC" = Calcium Carbonate + Calcitriol (Slot C ONLY). This is NOT C+D.

User uses "CC" as a natural shorthand — never treat it as UNKNOWN.

## Resolution — Use --compound Flag (Primary Path)

When user says "CC done" or "dah makan CC":

```bash
# Correct: log both drugs atomically via the compound path
python3 med_confirm.py C --compound cc --at HH:MM --source-text "user's words here"
```

This logs both calcium + calcitriol in one recoverable transaction. The source text must contain either "cc" (as a whole word) or both "calcium" and "calcitriol" explicitly.

**Do NOT use individual drug-level calls** (`med_confirm.py C calcium`, then `med_confirm.py C calcitriol`). The verification gate on `confirm_drug()` now requires `_source_mentions_drug()` to match the exact drug_id, and the compound gate on `confirm_compound()` blocks individual writes when the slot already has a partial compound state. The `--compound` flag is the only reliable path for CC.

## Fallback — Individual Calls (When --compound Rejects COMPLETION_RE)

If the user's phrase doesn't match `COMPLETION_RE` (e.g. "baru lepas makan" instead of "dah makan"), use the individual drug-level workaround:

```bash
python3 med_confirm.py C calcium --at HH:MM --source-text "calcium calcitriol"
python3 med_confirm.py C calcitriol --at HH:MM --source-text "calcium calcitriol"
```

Each call requires the literal drug name in source text. "CC" alone won't match `_source_mentions_drug()` because resolve returns `compound: true` not a drug_id. See `references/compound-confirmation-pitfalls.md` for full details.

## med_resolve.py Alias

The alias table in `med_resolve.py` has:
```python
"cc": "calcium",
```

This resolves CC to the calcium drug_id. The agent must additionally confirm calcitriol — resolve alone doesn't cover both drugs.

## Detection Pattern

Match in user messages:
- `CC done`, `CC siap`, `dah makan CC`
- `CC 1pm`, `CC pukul 13:00` (with time)

## Why This Exists

User naturally says "CC" for the calcium+calcitriol combo. It's a single "action" from their perspective (take both pills together at lunch). The system needs to map this to two separate drug confirmations.

Added: 2026-07-14 (from session where med_resolve returned UNKNOWN for "CC")
