# Missed-Dose Uncertainty: "Dah Makan Ke Belum?" (confabulation + physical count ground truth)

**Incident 2026-08-12 (levetiracetam, morning dose):** User typed "Letram dah makan jam
~8.35am" in chat, but 40 min later admitted total uncertainty — sachet still had a full
"pair" (2 tabs = pagi + malam per sachet). Physical count proved the chat confirmation was
a **confabulation** (ADHD auto-response: brain "completes" the intended action). The
08:35 state entry was wrong and had to be corrected to the real intake time.

## Ground-truth hierarchy (this user, verified 2026-08-12)

1. **Physical tablet/sachet count** — the ONLY reliable evidence when memory is in doubt.
   levetiracetam: 1 sachet = 2 tabs = pagi + malam. 2 remaining = morning NOT taken.
   1 remaining = morning taken. Never let a chat log override the count.
2. **Chat confirmation** — a claim, not a fact. Especially suspect when it's a reply to a
   nagging reminder (user confirms to stop the nag, not because he ate).
3. **User memory** — least reliable (ADHD, "senang lupa"). The user himself flags this.

## Decision framework: take now vs skip until next scheduled dose

Sources (consistent across all): Medicines For Children UK (twice-daily meds: take missed
dose if remembered within 4h of scheduled time), Mayo Clinic (take ASAP; skip only if
almost time for next dose; never double), FDA label + model-informed study (full dose if
within 2h; half-dose better than skipping entirely), Epilepsy Foundation (missed doses =
#1 breakthrough-seizure trigger; back-to-back misses much worse).

**Rule when UNSURE whether the morning dose was taken:**

- **Take the dose now.** Worst case of double-dosing (took + extra 500mg ~1h apart) =
  transient drowsiness/dizziness; no serious toxicity at 1000mg single dose; even 1500mg/
  day is within approved range. Worst case of skipping = 24-35h washout (t½ 6-8h) =
  breakthrough seizure risk. The asymmetry strongly favors taking.
- This is NOT the standard "never double up" advice — that rule assumes you KNOW you took
  it. Here the evidence says the dose was missed, so recovery is correct.
- Timing check: 09:33 = only ~1.5h past scheduled 08:00 → inside all clinical windows
  (≤2h full dose, ≤4h take-missed-dose). Even beyond those windows, partial dose > skip.

**After-action:**
- Warn user: if unusually sleepy/drowsy after, don't drive 3-4h.
- Red flags requiring clinic escalation: recent seizure activity, doctor's specific
  instructions, or severe drowsiness/difficulty waking.

## State-correction workflow (when a logged intake is later found false)

1. Copy backup FIRST: `med-status.json.bak-<label>-<YYYYMMDD-HHMM>`.
2. Update the drug entry `time` to the REAL intake time + add a `note` explaining the
   correction (suspected confabulation; evidence = sachet count).
3. Append one `logs/med-safety-audit.jsonl` entry: event_type (e.g.
   `LETRAM_TIME_CORRECTION`), raw_statement, parsed_meaning, hold_reason, previous_value,
   corrected_value, basis, timestamp_utc, outcome.
4. Re-run `python3 scripts/chain_calc.py --next` to confirm chain state is sane
   (B completed, next slot correct).
5. Only write after user confirms the actual intake ("ambil skrg, update timing") — never
   rewrite from inference alone.

## Prevention (proposed to user, pending approval)

- Sachet count = ground-truth check for levetiracetam: if a confirmation arrives but the
  count doesn't match, system asks before logging.
- Habit rule for user: take the tablet OUT of the sachet FIRST, then log "dah makan".
  Logging first is the confabulation entry point.
- Reminder message can include a "check sachet count dulu" hint for levetiracetam.