# Compound-confirmation runtime drift — 2026-08-04

## Finding

The loaded med-tracker references documented a `med_confirm.py C --compound cc ...` path and described it as the preferred atomic CC transaction. On 2026-08-04, the live script at `~/.hermes/scripts/med_confirm.py` did not implement `--compound`; it treated the invocation as an unknown option. The live script also rejected the user's exact source text `Dah makan cc jam 1.25pm` for individual `calcium`/`calcitriol` confirmation because `med_resolve.py cc` returned `UNKNOWN`.

## Safe operational sequence

1. Do not fabricate source text by appending component names to the user's message.
2. Do not use slot-level confirmation: it can mark Dexa #2 or optional B-Complex incorrectly.
3. Inspect the live script's CLI and implementation before using a documented compound flag.
4. If the compound implementation exists only in a candidate worktree, isolate-test it first. The 2026-08-04 candidate passed 9/9 `test_cc_atomic` tests covering validation rejection, rollback, journal recovery, idempotency, CLI dispatch, HERMES_HOME isolation, and both-component writes.
5. Run a live dry-run with explicit `HOME`/`HERMES_HOME`; compare before/after state hashes and require unchanged hashes.
6. Only then perform the compound write, with the user's exact source text, and read back `med-status.json`, `med_confirm.py --check C`, chain output, and transaction-journal absence.
7. Report the implementation provenance honestly: candidate code used against live state is not the same as deploying/fixing the live runtime script.

## Verified outcome from this session

- User shorthand: `cc` = Calcium Carbonate + Calcitriol only, Slot C; never the entire Slot C and never B-Complex.
- Intake time: 13:25 on 2026-08-04.
- Read-back: calcium and calcitriol both `taken` at `13:25`; Slot C `completed`; Dexa #2 remained `12:58`.
- Chain remained Dexa-driven: `A 06:22 -> B 08:03 -> C 12:58 -> D ~16:58 -> E ~20:00`.
- Supply counters were `null` by design (exact count not tracked), so no numeric decrement occurred.

## 2026-08-08 live-runtime reproduction and safe workaround

User statement: `Dah makan cc jam 9.35pm tadi` → stated intake time `21:35`.

Live preflight evidence:

- Live `med_resolve.py calcium --time 21:35 --slot C` → `drug_id=calcium`.
- Live `med_resolve.py calcitriol --time 21:35 --slot C` → `drug_id=calcitriol`.
- Live `med_resolve.py` had no `COMPOUND_ALIASES`; `med_confirm.py` had no `--compound` dispatch.
- `med_confirm.py C calcium --at 21:35` and the equivalent Calcitriol command both rejected with `REJECTED: source-backed CONFIRM_INTAKE required`; the literal source only contains `cc`, so appending component names would have fabricated source text.
- Slot-level `med_confirm.py C --at ...` was not used because it would also mark Dexa #2 at the CC time.

Safe workaround used:

1. Candidate atomic implementation: `/home/ubuntu/hermes-agent-personal_assistant-work/scripts/med_confirm.py`; its `test_cc_atomic.py` ran `9 tests ... OK`.
2. Copied live `med-status.json`, `med-supply.json`, and `med-schedule.json` to a temporary `HERMES_HOME`.
3. Dry-run with exact source text returned `ok=true`, `would_set={calcium: 21:35, calcitriol: 21:35}`; live status and supply SHA-256 hashes remained unchanged.
4. Ran the tested compound transaction against live runtime state. Output: `overall=completed`, both drugs `taken` at `21:35`; supply values remained `null` by design.
5. Read-back: `med_confirm.py --check C` showed Dexa #2 at `12:22`, Calcium and Calcitriol at `21:35`, `overall=completed`; chain was `A ✅ 06:08 → B ✅ 08:16 → C ✅ 12:22 → D ✅ 17:52 → E ✅ 20:17`; `.med-confirm-transaction.json` was absent.

Important provenance: this is a tested candidate runtime-state transaction, not proof that compound support is deployed in the live `~/.hermes/scripts/med_confirm.py`. Future CC confirmations should repeat the inspect → isolated test → copied-state dry-run → explicit live transaction → read-back sequence until the live implementation is deployed and re-tested.

## Maintenance rule

References describing `--compound` must be treated as candidate/unverified until the live script's CLI and function are inspected. Keep this reference linked from the main skill until the compound path is deployed to `~/.hermes/scripts/med_confirm.py` and re-tested against the live runtime.