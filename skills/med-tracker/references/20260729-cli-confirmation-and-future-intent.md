# Confirmation CLI and Future-Intent Handling (2026-07-29)

## Evidence from the session

- `med_resolve.py 'Akurit 2' --time 06:07` returned `UNKNOWN` but suggested the canonical ID `akurit_2 (Akurit-2, slot A)`.
- `med_resolve.py akurit_2 --time 06:07 --slot A` returned `ok: true`, `drug_id: akurit_2`, `slot: A`.
- `med_confirm.py A akurit_2 --at 06:07 --source-text ...` returned `ok: true`, date `2026-07-29`, drug `akurit_2`, time `06:07`.
- `med_confirm.py B dexamethasone_1 --at 07:50 --source-text ...` returned `ok: true`, time `07:50`, `overall: partial` because the other B drug was still pending.
- `med_confirm.py --check B` returned structured JSON with `confirmed: false` and exit code 1 because B was partial. This is an incomplete-status signal, not proof that the earlier write failed.
- `chain_calc.py --display` returned: `A ✅ 06:07 → B ◐ 07:50 → C ~11:50 → D ~15:50 → E ~20:00`.

## Reusable procedure

1. Resolve every named medicine before writing. If natural language is `UNKNOWN` but the resolver supplies an explicit canonical suggestion, run the suggested ID through the resolver and use only its returned `drug_id`.
2. Split confirmed intake from future intent. “Dah makan X; jap lagi makan Y” logs X only. Do not log Y until the user reports that Y was actually taken.
3. For drug-level confirmation, use the resolved slot and drug ID, explicit `--at HH:MM`, and the original message as `--source-text`.
4. Read the JSON result, especially `ok`, `drug`, `time`, and `overall`. A non-zero exit from a status/check command may mean `partial` or `confirmed: false`; inspect the payload before calling it a failure.
5. Run each partial-slot check separately; do not use `check A && check B` when a partial A/B result legitimately returns exit code 1.
6. After confirmation, run the required chain display and reminder-state update, then perform a read-back of the affected slot(s).