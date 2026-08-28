# Medication confirmation provenance and parser-gate reconciliation

**Pattern-Key:** `med-confirm-provenance-and-parser-gates`
**Observed:** 2026-08-14
**Scope:** inbound medication confirmation → auto-confirm hook → `med-status.json` → chain state

## Why this reference exists

A hook can write a syntactically valid medication entry with the wrong time. The audit line proves that a write happened; it does not prove that the parser selected the user's stated time.

## Reproduction/evidence from the session

User message:

```text
Dah makan letram malam jam 8.20pm tadi
```

Live evidence before correction:

- `med_resolve.py 'letram malam' --slot E --time 20:20` resolved to `levetiracetam_e` / Slot E.
- Live Slot E window was `19:00–21:00`; the stated 20:20 was in-window.
- `med-status.json.bak1`, `.bak2`, and `.bak3` had no E entry before the current turn.
- `med-status.json` was modified at `21:01:05`, immediately after the inbound message at `21:00:58`.
- `med-auto-confirm-audit.log` recorded:

```text
[2026-08-14 21:01:05] CONFIRM slot=E drug=levetiracetam_e time=20:26 msg='[Fri 2026-08-14 21:00:58 +08] Dah makan letram malam jam 8.20pm tadi'
```

Conclusion: the same-turn hook/parser write was proven, but `20:26` conflicted with the explicit `8.20pm`. Do not accept the state just because the audit says `CONFIRM`.

## Safe correction sequence

1. Resolve the canonical drug ID and parse the user's stated time independently.
2. Run a dry-run using the exact source text. A `taken -> taken at <user-time>` result is an overwrite warning, not proof that the existing time is right.
3. Inspect the audit log, file mtime, and rotating backups before changing state.
4. Correct only the affected drug:

```bash
python3 ~/.hermes/scripts/med_confirm.py E levetiracetam_e \
  --at 20:20 \
  --source-text 'Dah makan letram malam jam 8.20pm tadi'
```

5. Read back `--check E`, run `chain_calc.py --display`, then `chain_calc.py --update E`.
6. Verify the corrected state and retain the bad before-image in `.bak1` for audit.

Observed read-back after correction:

```text
E: levetiracetam_e taken @20:20
A ✅ 06:32 → B ✅ 08:32 → C ✅ 12:16 → D ✅ 17:00 → E ✅ 20:20
```

The `--check` command can return exit code 1 while emitting valid JSON for status output; inspect the JSON rather than treating that semantic status code as a failed write.

## Manglish lexical-gate false negative

The live compound confirmation path rejected this exact, source-backed wording during dry-run:

```text
Dh mkn cc 15 min lepas | Aku baru clarify, sorry, yes, it is true, aku makan 18.16pm
```

Raw rejection:

```text
REJECTED: source-backed intake completion wording required
```

Cause proven from the live source: `COMPLETION_RE` recognized forms such as `dah makan`, `sudah makan`, `done`, and `confirm`, but not `Dh mkn` or plain `aku makan`.

Do not solve this by appending `dah makan`, `confirm`, or component names to the source quote. That fabricates evidence. The tested tactical workaround was:

1. Keep the exact user messages as the source evidence.
2. Copy `med-status.json`, `med-supply.json`, and `med-schedule.json` into a temporary `HERMES_HOME`.
3. Use process-local compatibility parsing only; do not edit the live source file.
4. Run the compound transaction in dry-run mode; require `ok=true`, both components in `would_set`, unchanged copied-state hashes, and no transaction journal.
5. Apply the existing atomic compound transaction to live state only after that preflight.
6. Read back both components, Slot C, chain output, and transaction-journal absence.

Observed CC result:

```text
calcium taken @18:16
calcitriol taken @18:16
Slot C overall: completed
transaction journal: absent
```

This workaround is **TACTICAL / UNRESOLVED PARSER GAP**, not a permanent fix or deployment. A permanent lexical-parser change needs a separate approved code change plus regression tests for `Dh mkn`, `baru makan`, `aku makan`, and future-intent phrases such as `nanti makan`.

## General rule

Keep these evidence layers separate:

- **Inbound evidence:** what the user actually said;
- **Write provenance:** which hook/script wrote, when, and what the before-image contained;
- **Value correctness:** whether live state matches the user's stated drug and time;
- **Downstream correctness:** whether chain display and reminder state were recomputed from the corrected value.
