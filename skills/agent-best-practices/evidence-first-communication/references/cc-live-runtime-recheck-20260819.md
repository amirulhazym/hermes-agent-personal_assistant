# CC live-runtime recheck — 2026-08-19

## Scope

Session-specific evidence for a `CC` confirmation. This records current live capability/state and the no-double-write decision; it is not proof that a new compound transaction was executed during this session.

## Direct live evidence

- Exact user text: `Cc done 135pm`.
- `~/.hermes/scripts/med_resolve.py cc --time 13:35 --slot C` returned:
  - `ok: true`
  - `compound: true`
  - `compound_id: cc`
  - components: `calcium`, `calcitriol`
  - Slot C
- Direct inspection of live `~/.hermes/scripts/med_confirm.py` showed `COMPOUNDS["cc"]`, `confirm_compound()`, compound locking/transaction code, and `--compound` CLI dispatch. This is live-runtime capability evidence, not source-clone inference.

## Guard and result

Before any manual confirm, read today's live state. It already contained:

```json
{
  "drugs": {
    "calcitriol": {"status": "taken", "time": "13:35"},
    "calcium": {"status": "taken", "time": "13:35"},
    "dexamethasone_2": {"status": "taken", "time": "13:27"}
  },
  "overall": "completed"
}
```

Therefore the compound write was skipped; no second write or fabricated component source was used.

Post-checks:

- Both CC components matched `taken @ 13:35`.
- Dexa #2 remained `taken @ 13:27`.
- Slot C remained `overall: completed`.
- `.med-confirm-transaction.json` was absent.
- Chain display: `A ✅ 08:05 → B ✅ 09:05 → C ✅ 13:27 → D ✅ 17:18 → E ~20:00`.

## Reusable rule

For every medication confirmation, even when the live atomic capability is present:

1. Preserve exact user text and normalize only the stated time (`135pm` → `13:35`).
2. Resolve the canonical drug/compound against the live resolver.
3. Read today's live state before dry-run/write.
4. If the exact component(s) and time are already present, acknowledge and stop; do not dry-run or write again.
5. Otherwise use the live atomic compound path with exact `--source-text`, dry-run first, then serialized write and full child/parent/chain/journal read-back.

`med_confirm.py --check C` emitted valid completed JSON but returned exit code `1`; classify from the structured payload and preserve the exit code as wrapper metadata, per the parent skill.

## Status label

`CAPABILITY-VERIFIED` for live CC resolver/CLI on 2026-08-19; `STATE-VERIFIED` for the exact existing confirmation; `NEW-TRANSACTION-NOT-EXECUTED` by design.