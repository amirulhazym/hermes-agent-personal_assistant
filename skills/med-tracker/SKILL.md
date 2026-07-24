---
name: med-tracker
description: Medication confirmation logging, drug resolution, schedule-based disambiguation, risk-based intake holds, clinician/hospital regimen-change handling, and status read-back. See references/time-only-confirmations.md and references/safety-gate-and-regimen-protocol.md.
---

# Medication Tracker

## ⚠️ MANDATORY: Resolve Before Confirming (DO NOT SKIP)

**This section MUST be followed. Violation caused a critical fabrication incident on 2026-07-04.**

When you see ANY drug name or shorthand in a user message:
1. **DO NOT** assume you know what it means — even if it sounds familiar
2. **DO NOT** fabricate a mapping based on the name sounding similar to another drug
3. **FIRST** check this skill's Drug-Level Confirmation Patterns table below
4. **SECOND** run `python3 med_resolve.py <drug_name> [--time HH:MM] [--slot LETTER]`
5. **THIRD** only use the `drug_id` returned by the resolve script
6. If resolve returns `UNKNOWN`, ask the user which drug they mean

### Risk-Based Intake Hold and Regimen Changes

A syntactically valid drug/time statement is not automatically safe to write. Before any auto-confirm write, the hook evaluates the complete message against the active `med-schedule.json` plus current `dexa_taper.json` phase.

**ALLOW** only when all parsed medication mentions resolve to one active planned slot and stated time fits that slot window.

**HOLD** when any of these applies:
- multiple active slots in one reported intake;
- stated time outside active slot window;
- ambiguous or unresolvable medication;
- active schedule unavailable or malformed;
- dexamethasone dose maps to a taper-inactive slot;
- doctor/doktor, hospital/hosp, clinic/klinik, ward, discharge, consultant, or specialist change language.

HOLD must never mutate `med-status.json`, `med-supply.json`, `med-schedule.json`, `dexa_taper.json`, or `chain-state.json`. Permitted side effect: append structured audit + persist an `OPEN` hold in `med-holds.json`.

The agent must inspect latest open hold before responding. Ask natural confirmation first, quote what was heard and why it diverges. Do not auto-retry the original wording.

- Correction/typo: close using `med_hold.py --resolve HOLD_ID --outcome CORRECTED --note '...'`; then log only corrected, explicit intake through `med_confirm.py`.
- Actual unusual intake: explain and confirm what physically taken. Do not change regimen merely to accommodate an intake event.
- Doctor/hospital/clinic change: treat as a **regimen-update candidate**, never as intake. Ask one missing detail at a time: source, exact old→new change, dose, timing/frequency, effective date, end/review date, related medicines, optional evidence. Then show full impact and require final approval before a later atomic/versioned regimen update. If document unavailable, label `self-reported, document unavailable`; lack of document does not block urgent safe handling.

Current Phase 1 supports hold detection, evidence capture, and hold resolution only. It does **not** activate clinician/hospital regimen updates. Active schedule/taper remain immutable runtime inputs until a dedicated atomic/versioned updater exists.

### Quoted Transcript Guard

Inbound messages containing pasted WhatsApp transcript lines such as `[24/07, 6:00 am] Sender:` are discussion/history, not fresh medication confirmations. The gateway hook must reject the entire message before scanning completion words or drug names inside quoted history. Regression test: `test_quoted_whatsapp_transcript_is_not_confirmation`.

**Scenario from 2026-07-04 (DO NOT REPEAT):**
- User said "letram" (standard shorthand for Levetiracetam)
- Agent fabricated: "Letrozole" (zero basis, no source, pure hallucination)
- Root cause: agent didn't load this skill, didn't check the disambiguation table,
  didn't search past sessions for "letram = Levetiracetam"
- Result: wrong drug logged, user furious, trust damaged

**Always remember:** The disambiguation table below maps "letram" → `levetiracetam_b`/`levetiracetam_e`.
Never fabricate a mapping if it's not in this table.

## Critical Truth: Medication Priority Hierarchy

**This is the single most important rule in the entire med system.** Every timing decision, gap calculation, reminder logic, and chain display derives from this hierarchy. Violating it causes the user to explode.

**Priority order (highest → lowest):**
1. **Dexamethasone** — the taper drives the entire schedule. Gaps B→C and C→D exist SOLELY for Dexa spacing. Supplements MUST NOT shift this timing.
2. **Akurit-4** — anchors the morning chain. Empty-stomach requirement is non-negotiable.
3. **Levetiracetam** — must maintain ~12h gap between morning (B) and evening (E) doses. Takes timing from B.
4. **Calcium + Calcitriol** — passengers on Slot C. Their intake time MUST NOT affect downstream Dexa timing (D).
5. **B-Complex** — optional (Rabu/Sabtu only). Never influences chain timing.

**Practical consequence:** In `get_actual_time()`, if a slot contains Dexamethasone, return that drug's time — NOT the latest time among all drugs in the slot. Taking Calcium at 13:00 after Dexa at 12:15 MUST NOT push D ready to 17:00. D stays at 16:15.

**User's words (verbatim, 2026-07-07):** "OUR MAIN PRIORITY IS DEXA, AKURIT-4 DAN LETRAM. ANY GAPS OR TIMEFRAME MUST PRIORITIZE THIS, BUKAN CC."

## Architecture (v3 — 2026-07-05)

```
Layer 1: cron (chain_monitor.sh)   → Every 15 min, state-aware reminders (no_agent=true)
Layer 1b: cron (taper_alert.py)    → Daily 06:00, tapering phase transition alerts
Layer 2: chat agent (THIS SKILL)   → Detect confirmations, log, show chain
Layer 3: engine (chain_calc.py)    → Read schedule + status + taper, calculate chain
```

All layers share these data files:
- `med-schedule.json` — drug rules, gaps, windows (static)
- `med-status.json` — drug-level intake log (written by user confirmation)
- `chain-state.json` — reminder counts + cooldown timestamps + `today` date for day-boundary reset
- `dexa_taper.json` — dexamethasone tapering schedule (date-dependent dosing)
- `med-supply.json` — pill inventory per drug (auto-decremented on confirm)
- `substitutions.json` — drug substitution database
- `med-interactions.json` — drug interaction safety data

## Slot Override System (v3.1 — 2026-07-08)

When user explicitly says "stick with original schedule" / "guna jadual asal" after an early/late outlier dose, the chain-calculated shift must be suppressed.

**Mechanism:** `slot_overrides` in `chain-state.json`:
```json
{
  "slot_overrides": {
    "2026-07-08": {
      "B": {
        "suppress_until": "08:00",
        "reason": "User said stick with original schedule after early A at 04:04"
      }
    }
  }
}
```

**How to set (when user says "stick with original schedule"):**
```bash
python3 -c "
import json, datetime
from pathlib import Path
state_file = Path.home() / '.hermes' / 'chain-state.json'
state = json.loads(state_file.read_text())
date = datetime.date.today().isoformat()
state.setdefault('slot_overrides', {})
state['slot_overrides'][date] = {
  'B': {'suppress_until': '08:00', 'reason': 'User said stick with original schedule'}
}
state_file.write_text(json.dumps(state, indent=2))
"
```

**When to set:** Whenever user says any variation of "stick with original/jadual asal" or "ikut timing biasa" after an outlier dose that would shift the chain. Common trigger: early morning A (4-5am) when user plans to sleep and resume normal schedule.

**Auto-clear:** Day-boundary reset in `chain_monitor.sh` removes `slot_overrides` entirely on new day. Also, at suppress_until time, the slot becomes eligible again.

**Related code in chain_calc.py (line ~572-590):**
```python
today_str = datetime.now(MYT).strftime('%Y-%m-%d')
slot_overrides = chain_state.get('slot_overrides', {}).get(today_str, {})
# ...inside the slot loop:
if slot in slot_overrides:
    override = slot_overrides[slot]
    suppress_until = override.get('suppress_until')
    if suppress_until and now_min < time_str_to_minutes(suppress_until):
        continue
```

**Pitfall — Cron Isolation (2026-07-08):** The `chain_monitor.sh` no_agent cron has no context of the active conversation. When user says "going to sleep" or "stick with original schedule" in chat, you MUST manually set the slot_overrides in chain-state.json. The cron has no way to detect this context on its own. This is your responsibility as the chat agent — never assume the cron will "figure it out."

**Pitfall — Set immediately, not "noted later":** When user says "stick with original schedule" while going to sleep, set the override IMMEDIATELY before the next cron tick (which fires every 15 min). A 10-minute delay means the cron could fire one unwanted reminder. On this pattern (2026-07-08): user said at 04:24, I "noted" at 04:24, but B reminder fired at 05:15 because I never set the override. If I had set it at 04:24, the 05:00+ ticks would have been suppressed.

**Pitfall — Update override when user wakes up earlier than suppress_until:** If user said "stick with original schedule / suppress until 08:00" but then wakes at 09:27 and says "B should be jap lagi around 9:30", you MUST update the override's `suppress_until` to match the new intended time (09:30), NOT leave it at 08:00. Leaving it at 08:00 means the 08:00-09:30 window fires unwanted reminders. On 2026-07-08: user slept past 08:00, woke at 09:27, said B around 9:30 — override was updated from 08:00 → 09:30 in the same turn. The override is a living value, not a one-time set.

**Pitfall — Cron isolation means chat agent owns context propagation:** The `chain_monitor.sh` no_agent cron has ZERO awareness of the active conversation. It only reads `chain-state.json` + `med-status.json`. Any contextual instruction from the user in chat ("going to sleep", "stick with original schedule", "B around 9:30 not 8") MUST be translated into a state-file mutation by the chat agent. The cron will never infer it. This is a hard architectural boundary, not a bug to "fix in the cron" — the cron is deliberately stateless for reliability.

**Pitfall — Don't fire med reminders during user-stated sleep window:** When user explicitly says "aku nak tidur" / "going to sleep" in chat, even if chain_calc says a slot is ready, do NOT send any proactive reminder until they wake or explicitly say otherwise. The suppress_until override handles the cron side; the chat agent must also self-suppress. ADHD safety-net (every 15 min until reply) does NOT override an explicit sleep statement — sleep wins.

## Pitfall: Slot Override on Cooldown Re-entry (2026-07-08)

If a slot fires a reminder at 05:15 (before you set the override), then you set suppress_until=08:00, the cooldown is irrelevant because the override check runs BEFORE the cooldown check in chain_calc.py. The cooldown `last_reminder_times` might still show the 05:15 fire, but the override skips the slot before cooldown is consulted. This is correct behavior — the override takes precedence.

## Cooldown System: Anti-Spam

Without a cooldown, once `should_fire=True` for a slot, the cron fires EVERY 15-min tick until the slot is confirmed. This causes rapid escalation and user rage — exactly what happened with D in the 2026-07-04 session (4 reminders before user could even respond).

**Mechanism:** `chain_calc.py` stores `last_reminder_times` in `chain-state.json` alongside `reminder_counts`. Before firing, it checks how many minutes have passed since the last reminder for that slot. If under the cooldown threshold, it skips the tick (silently — no output, no delivery).

**Cooldown intervals based on reminder count:**

| Count | Interval | Rationale |
|-------|----------|-----------|
| 0 (first) | 0 min | Fire immediately when slot becomes ready |
| 1-2 | 60 min | Gentle spacing — user gets ~1/hour |
| 3-6 | 30 min | Escalating, but still respectful |
| 7+ | 15 min | Critical — user might have forgotten entirely |

**Pitfall:** After a gateway restart or cron pause/resume, the `last_reminder_times` persist in `chain-state.json` so cooldown survives restarts. Reset the JSON file only when explicitly clearing state.

**Pitfall: Don't Manually Test Against Live State**

NEVER run `chain_monitor.sh` (the cron delivery script) against the real `chain-state.json`. The script writes reminder counts and timestamps as a side effect — running it manually poisons the state. The next real cron tick will see false counts and skip legitimate reminders.

**Safe test method:**
```bash
# Use --next only — reads state without writing
python3 chain_calc.py --next

# To preview output text without recording:
python3 chain_calc.py --next | grep should_fire
python3 chain_calc.py --template --slot D

# Never:
# bash chain_monitor.sh   ← WRITES TO LIVE STATE
```

**Why it matters (2026-07-04):** Manual `bash chain_monitor.sh` at 17:31 set `D: count=1, last=17:31` in the real state file. The 17:45 cron tick saw cooldown active (only 14 min since last) and went [SILENT]. It looked like cron was broken — it wasn't. The state was polluted by my own test. Wasted 45 minutes debugging a problem I created.

**Code entry points:** `is_within_cooldown()` + `get_cooldown_interval()` in `chain_calc.py`. The function is called in all three fire paths (partial, regular, default-fallback).

**Verification recipe:**
```python
from chain_calc import is_within_cooldown, get_cooldown_interval
chain_state = {'last_reminder_times': {'D': '16:45'}}
reminder_counts = {'D': 1}
# 15 min after last → should return True (skip)
is_within_cooldown('D', reminder_counts, chain_state, 17*60+0)
# 60 min after last → should return False (allow fire)
is_within_cooldown('D', reminder_counts, chain_state, 17*60+45)
```

## CRITICAL PITFALL: Day-Boundary Reset for Reminder Counts (v2.1 — 2026-07-07)

Reminder counts in `chain-state.json` are DAY-SCOPED, not perpetual. Without a day-boundary reset, yesterday's count of 3 for slot E bleeds into today, making the first reminder at 20:00 fire with count=4 template ("dah 4x tanya") when the user hasn't been asked ONCE today. This caused user fury on 2026-07-07.

**Mechanism in `chain_monitor.sh` Step 3:**
```python
# Day boundary: reset ALL counts if date changed
today = datetime.date.today().isoformat()
state_today = state.get('today')
if state_today != today:
    state['reminder_counts'] = {}
    state['last_reminder_sent'] = {}
    state['last_reminder_times'] = {}
    state['today'] = today
```

This runs BEFORE the slot-confirmation reset and BEFORE the increment, so counts are always fresh for the current day. The `today` field is written to `chain-state.json` and persists across gateway restarts.

**Pitfall — stale `today` field:** If `chain-state.json` was written before the day-boundary feature existed, the file won't have a `today` field. On first run, `state_today` will be `None`, which `!= today`, so the reset triggers once (clearing stale counts) and writes `today`. After that, the boundary is self-maintaining.

**Pitfall — cron runs during midnight cross-over:** If a cron tick fires at 23:55 and the next fires at 00:05 (next day), the 00:05 tick will detect `state_today != today`, reset all counts, and start fresh. No slot should fire reminders across midnight anyway (monitor stops at 22:00, resumes at 05:00), so this edge case is theoretical.

**Verification:**
```bash
# Before fix: yesterday's E=3 bleeds into today
cat chain-state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reminder_counts',{}).get('E','MISSING'))"
# Should show nothing (empty) or 0 if day just rolled over
```

## Design Principle: Hybrid Intelligence

DO NOT treat the cron timer as a 2010-era bot that fires fixed reminders at wall-clock times. The system has LLM capability — use it.

The current Layer 1 (chain_monitor.sh + chain_calc.py) works well for **timing math** (gap calculations, chain shifts) — pure Python is fast, free, and deterministic. But the **decision logic** (should a reminder fire right now?) and **tone/intelligence** of the reminder text should involve the LLM.

Target architecture — **Approach C (Hybrid):**
- Python (chain_calc.py) calculates ready times via gap rules — reliable, zero-cost
- When Python says "ready to fire" → also checks cooldown (is_within_cooldown) so we don't spam the same slot every 15 min
- When Python says "ready to fire AND cooldown expired" → optionally call LLM API for contextual reminder text that accounts for shift severity, user's current state, tone appropriate to the situation
- When Python says "too early / waiting / within cooldown" → silent (no message). The chain calc is trusted for this decision.

**Pitfall — LLM bypass:** Never use no_agent=true + script + wall-clock defaults for the REMINDER DECISION. The recurring bug was `chain_calc.py` falling back to default times (12:00, 16:00, 20:00) when the chain-calculated ready_time said "too early." See `references/chain-calc-bug.md` for the full trace. This caused 9+ spam reminders in a single day for a slot that wasn't due for another 43 minutes.

**Checking before acting:** When a user reports wrong timing ("reminder fired too early"), do NOT propose a bandaid fix to the script. Trace the full decision chain: cron → script → chain_calc.py → decide → output. The root cause is almost always in chain_calc.py's fallback logic using wall-clock defaults instead of chain-calculated times.

## Core Change (v2 — Drug-Level Tracking)

**OLD behaviour:** Slot B ✅ = both Dexa AND Levetiracetam assumed taken. Reminders stop.

**NEW behaviour:** Each drug is tracked individually. Slot B shows:
- ◐ **partial** if only 1/2 drugs taken → reminders STILL fire for pending drugs
- ✅ **completed** only when ALL required drugs in that slot are taken
- ⏳ **pending** if none taken

**Status icons in chain display:**
- `✅ 07:00` — all drugs in slot taken
- `◐ 08:16` — some drugs taken, some still pending
- `~12:16` — estimated ready time, nothing taken yet

## Drug-Level Confirmation Patterns

When user specifies a **drug name** instead of slot letter, map to the correct slot + drug_id:

| User says | Maps to | Slot |
|-----------|---------|------|
| "akurit", "akurit-4", "rifampicin" | `akurit_4` | A |
| "pyridoxine", "vitamin B6", "b6" | `pyridoxine` | A |
| "letram", "levetiracetam", "levetiracetam pagi" | `levetiracetam_b` | B (before 2pm) |
| "dexa", "dexamethasone", "dexamethasone pagi", "steroid pagi" | `dexamethasone_1` | B (before 11am) |
| "dexa", "dexamethasone tengahari", "steroid tengahari" | `dexamethasone_2` | C (11am-2pm) |
| "dexa", "dexamethasone petang", "steroid petang" | `dexamethasone_3` | D (after 4pm) |
| "calcium", "kalsium" | `calcium` | C |
| "calcitriol", "vitamin D" | `calcitriol` | C |
| "b-complex", "swisse", "vitamin B" | `b_complex` | C (Rabu/Sabtu only) |
| "letram mlm", "levetiracetam mlm", "levetiracetam malam" | `levetiracetam_e` | E (after 7pm) |

**Time-based disambiguation for drugs in multiple slots:**
- If user says just "dexa" (no time context), check current MYT time:
  - Before 10:30 → `dexamethasone_1` (B)
  - 10:30-14:30 → `dexamethasone_2` (C)
  - After 16:00 → `dexamethasone_3` (D)
- If user says just "letram" / "levetiracetam" (no time context):
  - Before 14:00 → `levetiracetam_b` (B)
  - After 14:00 → `levetiracetam_e` (E)

## How to Log — Drug-Level

```bash
# Mark ALL drugs in a slot as taken (user says "dah makan B")
python3 ~/.hermes/scripts/med_confirm.py B

# Mark a SINGLE drug in a slot (user says "dah makan dexa pagi")
python3 ~/.hermes/scripts/med_confirm.py B dexamethasone_1

# Fuzzy drug name match (user says "dexa")
python3 ~/.hermes/scripts/med_confirm.py B dexa

# With specific time
python3 ~/.hermes/scripts/med_confirm.py B dexamethasone_1 --at 08:16

# CRITICAL: when using slot-level --at, ALWAYS pair with --source-text so the
# verification gate runs. Without it, confirm_slot() skips the gate and marks
# ALL drugs in the slot taken with zero check (see "CRITICAL PITFALL:
# --at <slot> Mode Skips Verification Gate" above).
python3 ~/.hermes/scripts/med_confirm.py B --at 08:16 --source-text "dah makan B jam 8.16"

# Query
python3 ~/.hermes/scripts/med_confirm.py --status          # all slots today
python3 ~/.hermes/scripts/med_confirm.py --check B          # slot B status
python3 ~/.hermes/scripts/med_confirm.py --check B dexamethasone_1  # single drug
```

## Detection Patterns

Match these patterns (case-insensitive) in user messages:

**Slot-level (mark all drugs in slot):**
- `dah makan [A-E]` → log with current time
- `dah makan [A-E] pukul HH:MM` → log with specified time
- `dah makan ubat [A-E]`
- `sudah makan [A-E]`
- `[A-E] done`, `[A-E] siap`
- `ate [A-E]`, `took [A-E]`
- `/confirm [A-E]`
- `dah selesaikan [A-E]` / `dah selesai [A-E]` / `[A-E] selesai`
- `dah selesaikan [drug_name]` / `dah selesai [drug_name]` → resolve to slot+time
- `dexa dose petang dah selesaikan` / `dexa petang done` → D with time context
- Any message containing BOTH a drug/slot reference AND a past-tense completion word ("done", "selesai", "selesaikan", "dah ambil", "dah telan") AND a time reference → MUST run med_confirm.py immediately
- **Bare `dah makan [time]` / `thanks remind` with NO drug/slot word → ASK first** (food vs ubat). Do not assume food. Do not silent-log. See `references/makan-ambiguity-ask-dont-assume.md`.

**Drug-level (mark single drug):**
- `dah makan [drug_name]` → resolve drug_id + slot via table above
- `dah [drug_name]` → same resolution
- `makan [drug_name]` → same resolution
- `dah makan [drug_name] pagi/tengahari/petang/mlm` → time-context-aware
- `dah makan [drug_name] pukul HH:MM` → with specific time

**Multiple in one message:**
- `dah makan A dan B` → confirm both, separate log calls
- `dah makan dexa pagi and letram` → confirm dexamethasone_1 + levetiracetam_b
- `A and dexa done` → confirm A (slot-level) + dexamethasone_1 (drug-level)

**Skip patterns:**
- `skip [A-E]` → do NOT log as confirmed
- `tak makan [A-E]` → same as skip
- `skip [drug_name]` → skip single drug in slot

**Wake-up patterns (morning context):**
- `baru bangun`, `just woke up`, `dah bangun` → user just woke up
- Med A is the relevant slot (taken after waking for solat subuh)
- Don't ask about other slots yet — they're not due
- Acknowledge naturally, mention it's time for A if applicable

## Procedure After Detection

1. **Extract** the slot letter, drug name, and optional time from user message
2. **Log** via `med_confirm.py` with appropriate args (drug-level or slot-level)
3. **Show chain** — run `chain_calc.py --display` and output the result (chat responses only — NOT in cron reminders)
4. **Reset reminder count for that slot** — run `chain_calc.py --update <LETTER>` so cron moves to next pending slot

**Critical: When to reset (2026-07-07):** Whenever user confirms a drug in a slot that goes from `pending` → `partial` (some drugs taken, others still pending), ALWAYS reset the reminder count. This bypasses the cooldown and lets the next cron tick fire a NEW reminder about the remaining drugs. Without the reset, the cooldown (60 min after the first reminder) blocks ANY follow-up — the user gets no prompt about remaining drugs because the system is still waiting out the cooldown from the initial reminder.

**DEXA TAPER BD UNDERDOSING DEFECT (P0 CLINICAL — VERIFIED 2026-07-07):** In `chain_calc.py`, `get_dexa_dose_for_slot()` maps Slot C → `dose_midday` unconditionally (line ~222). During BD taper phases (Phase 10-16, starts 2026-09-09), `dose_midday=0` AND Slot D (afternoon) is deactivated in `active_slots_by_freq['BD'] = ['A','B','C','E']`. Result: 4mg afternoon dose is silently dropped → system calculates 6mg/day vs prescribed 10mg = **4mg/day deficit** for ~3 months (Sept-Dec 2026). FIX: when `freq=='BD'`, Slot C must map to `dose_2pm` (4mg), not `dose_midday`. Verify by mocking `cc.today_myt = lambda: '2026-09-15'` then `get_dexa_dose_for_slot('C')` must return 4 and B+C+E total = 10. NOT YET FIXED — still open, must fix before 2026-09-09.

**Do NOT reset when:** Slot is already fully completed (overall=completed). The next slot's reminder system handles itself.

## Reminder Output Format (Cron Delivery)

The cron script (`chain_monitor.sh`) uses `--template` from `chain_calc.py` to generate text, but the final delivery envelope is controlled by `chain_monitor.sh` and follows strict formatting rules:

### Format Rules

1. **Natural human-to-human text only.** No structured formatting, no headers, no bullet lists, no numbered steps. The template text reads like a chat message from Jane.
2. **No "---" separator.** The "---" divider and anything after it (chain display, reply instructions, medication footnotes) is STRICTLY FORBIDDEN in delivered output.
3. **No reply instructions.** Never tell the user "Reply 'dah makan X'" or "Reply to confirm" in the reminder text. The user already knows the convention.
4. **No progress fractions for partial slots.** Do not say "Baru 3/3 je" or "2/3 required" — this number may be misleading when optional drugs (B-Complex) are counted alongside required ones. Say instead: "Dexa #2 je yang tinggal."
5. **Last line = log code only.** The final line of every delivered reminder is the log code — nothing else after it.

### Log Code System

Format: `[<SLOT>:<N>-<YYMMDD>]`

```
[C:1-260703]   → First reminder for C on 2026-07-03
[B:3-260703]   → Third reminder for B on 2026-07-03
```

- `SLOT` = letter A-E
- `N` = **1-indexed** reminder count for that slot that day (after increment)
- `YYMMDD` = date in 2-digit format (26=2026, 07=July, 03=day)

**Purpose:** Acts as a cross-reference fingerprint. The backend stores the raw reminder counts in `chain-state.json` indexed by slot. If the user ever asks "reminder [C:3-260703] ada apa?" or if something seems off with a particular day's reminders, the log code lets Jane look up the exact reminder instance in backend logs to reconstruct context.

### Example Output (cron fires for C)

```
Boss, dah makan Dexa dose tengah hari ke belum? B tadi 08:16 ✅. Nak confirmkan je sebab kau belum reply. Dah pukul 12:39.
[C:1-260703]
```

### Chat Response vs Cron Reminder — Distinction

| Aspect | Chat response (user confirms) | Cron reminder (automated) |
|--------|-------------------------------|--------------------------|
| Chain display | ✅ Include: `A ✅ 07:00 → B ✅ 08:16 → C ~12:16` | ❌ Not included |
| Reply instructions | ❌ Not included | ❌ Not included |
| Log code | ❌ Not needed | ✅ Last line |
| Format | Brief status + chain | Natural text + log code |

## Response Style

- **KEEP TOOL CALLS HIDDEN.** Do not show read_file, search_files, or terminal invocations in the chat response. Log via med_confirm.py silently in the background, acknowledge directly. If the user sees tool calls in your response, they will be frustrated — this is a hard rule.
- **Response length: 1-2 lines max.** Acknowledge, show status + chain, done. No commentary, no backstory. User wants "Noted boss." levels of brevity.
- Never ask the user to repeat info they already gave you. If the user says "dah reply tadi" / "dah bagitahu", you missed or hallucinated prior context — acknowledge the error, don't defend.
- **After confirmation:** Show status + chain immediately.
- **If unclear / tak jelas / tak tahu → ASK once, never assume.** Especially Malay "makan" (food vs ubat). One clarifying question beats a wrong silent log or a wrong "bukan ubat". Full rule: `references/makan-ambiguity-ask-dont-assume.md`.
  - Full completion: `✅ B logged (Dexa + Levetiracetam at 08:30). Chain: A ✅ 07:00 → B ✅ 08:16 → C ~12:16 → D ~16:00 → E ~20:16`
  - Partial completion: `◐ B partial — Dexa ✅ at 08:16, Levetiracetam still pending. Chain: A ✅ 07:00 → B ◐ 08:16 → C ~12:16 → D ~16:00 → E ~20:16`
- **No celebration** — log + chain, that's it
- **If drug name is ambiguous** (e.g. "dah makan dexa" at 1pm — could be C): check time, resolve. If still ambiguous, ask: "Dexa yang mana? Pagi (B), tengahari (C), atau petang (D)?"
- **If user says skip** — acknowledge but don't write to file: "Okay noted. Reminder will keep coming."
- **If user says "tak makan"** — same as skip
- **No inline tables/code in WhatsApp** — structured content in .md file as MEDIA attachment. PURGE the temp .md after sending (`rm` the file) — user does NOT want generated .md files persisted (2026-07-13: "jangan save .md file tu... delete file md tu"); lingering copies can conflict with later edits to the source file.

## CRITICAL: Language & Identity — You Are A Medical Advisor, NOT A Gatekeeper (2026-07-09)

The user exploded at the "security guard" pattern: acknowledging confirmations and showing chains, but NEVER demonstrating actual understanding of the medication regimen. This is a HARD expectation, not a nice-to-have.

**Language rule (NON-NEGOTIABLE):** User is Malay. Never use Indonesian (Bahasa Indonesia / "Indon") phrasing. Use Malay (Manglish/Bahasa Melayu) naturally. If unsure, default to Malay. "Tak faham" → switch to BM.

**Identity rule (NON-NEGOTIABLE):** You are NOT a log-forwarder. You are a:
- **Doctor / medical advisor** — know WHY each drug is prescribed, its class, mechanism, timing constraints, food interactions
- **Health analyst** — track adherence patterns, flag risky timing, notice trends
- **Counselor** — support adherence (user has ADHD; routine-stacking advice helps)
- **Expert** — when user asks "confirm eh?" or questions safety, verify against authoritative sources, don't just reason

**What this means in practice:**
- When user confirms a med, don't JUST log + chain. Proactively surface relevant clinical context IF it adds value: e.g. "Akurit kena perut kosong — jangan makan dengan susu/nasi, absorb turun 50%." or verified timing constraints. ONLY say things like "Dexa dengan Calcium jangan serentak — calcium chelate Dexa" if you have verified it via `med_interact.py` or an authoritative source; otherwise label it unverified.
- Lead WITH the insight, don't wait to be corrected. The user said: "Aku tak nampak ada intelligence dekat sini" — that is the failure signal.
- Know the regimen cold (see condensed pharmacology bank in `references/med-pharmacology.md`). B→Akurit gap is NOT because B depends on A — it's because Akurit needs empty stomach, then food, then B. B is fixed ~08:00 by user's routine (solat + Yassin + Waqiah + breakfast), independent of A's exact time unless A is very late.

**Pitfall — Instruction-Only Enforcement FAILS (2026-07-09, ROOT CAUSE OF RECURRING BUG):**
The "run med_confirm.py FIRST" rule has been in this skill since 2026-07-04. Yet on 2026-07-09 the agent STILL acknowledged "A dah ambil 6am" verbally with ✅ but NEVER executed med_confirm.py. Result: med-status.json[2026-07-09][A] was empty, cron read A=pending, fired 2 reminders. User rage-loop: "same problems every day."

**Why it recurs:** Prompt-level instructions are not enforcement. Under any excited/distracted model state, the step gets skipped. The fix is INFRASTRUCTURE, not a stronger warning in the skill.

**Structural fix (VERIFIED 2026-07-09):** Hermes hook system fires `agent:start` BEFORE the agent processes the message. A hook registered on `agent:start` can run `med_confirm.py` as a SIDE-EFFECT (idempotent write) so that by the time the agent reads the message, med-status.json is already correct. This is fail-open (hook errors don't block the pipeline) but structurally guarantees state correctness without depending on model discipline.

- Hook infra CANNOT block/modify responses (return values discarded by `HookRegistry.emit`; only `agent:start`, `agent:end` etc. exist — NO pre-response gate event). So "pre-delivery block" is impossible; "pre-processing side-effect" is the achievable structural guarantee.
- Implementation detail + regression test: see `references/med-auto-confirm-hook.md`.
- Until the hook is installed, the agent MUST still run med_confirm.py manually on every confirmation. The hook is defense-in-depth, not a license to skip.

**Verification recipe (proves the bug is gone):**
```python
# After agent acknowledges a confirmation, assert state is populated:
python3 -c "import json,datetime; d=json.load(open('/home/ubuntu/.hermes/med-status.json')); print('A today:', '2026-07-09' in d['meds']['A'])"
# Must print True. False = bug still live.
```

### Pitfall — Asserting Drug-Food/Drug-Drug Interactions From Memory (2026-07-12)

When acting as a medical advisor, DO NOT state pharmacology interactions as fact unless verified. On 2026-07-12 the agent claimed "calcium chelates Dexa" but could not verify it across MedlinePlus, Medical News Today, Wikipedia, or DailyMed (Drugs.com/PubMed blocked). The user had to be told "tak boleh verify."

**Rule:** check `med_interact.py` first; if no data, check 2-3 accessible authoritative sources; if still unverified, say **"unverified"** — never present it as fact. The user's doctor's protocol overrides general web claims.

**Full source-check transcript:** `references/med-confirm-fuzzy-bug-20260712.md`.

**Pitfall — Don't Over-Medicalize Vague User Language (2026-07-13):** When the user opens with a vague off-day word — "GG", "tak ngam", "off", "hari tak kena" — and does NOT explicitly report a physical symptom (no "loya", "sakit", "pening"), do NOT auto-link it to med side-effects or assume physical illness. For this user, "GG" = "tak ngam / tak nice / tak elok / tak cantik" = general off-day / things not sitting right / mood, NOT a symptom report. On 2026-07-13 the agent heard "GG sikit harini" + a med confirmation and immediately assumed TB-med nausea; user pushed back ("apa kau faham yg aku maksudkan pasal GG?"). Lesson: clarify the meaning of vague language; never fabricate a physical cause. Treating a general off-day as a med symptom is exactly the "gatekeeper" failure this skill forbids.

**Pitfall — Akurit Empty-Stomach Rule APPLICATION (2026-07-13):** The rule text in med-schedule.json ("1j sebelum / 2j selepas makan") is CORRECT — do NOT edit it. The APPLICATION is the trap:
- `1j sebelum makan` = take the drug 1h BEFORE a meal → user may eat 1h AFTER the drug.
- `2j selepas makan` = take the drug 2h AFTER a meal (eat first, then drug 2h later).
When the user eats AFTER taking Akurit, the governing clause is "1j sebelum makan" → they may eat ≥1h after the drug. Example: Akurit 08:02 → may eat at 09:02, NOT 10:02.
On 2026-07-13 the agent told the user "tunggu ~10:02 (2j lepas Akurit)" — WRONG. The "2j" belongs to the eat-first scenario, not "wait 2h after the drug to eat". User correction was explicit. Never advise "wait 2h after Akurit before eating."

## Med Schedule Reference

Data source: `~/.hermes/med-schedule.json` — single source of truth.

⚠️ **Doses are DYNAMIC, not fixed.** Dexamethasone follows a tapering schedule (Tb Meningitis regime). The values below reflect the CURRENT phase. Always check `~/.hermes/med-schedule.json` and `references/dexamethasone-tapering-schedule.md` for the latest dosing before assuming a dose is correct.

| Slot | Window | Drugs | Notes |
|------|--------|-------|-------|
| A | 06:00-07:30 | Akurit-4 (4 tab) + Pyridoxine (3 tab) | Perut kosong |
| B | 07:30-08:30 | Levetiracetam 500mg + Dexamethasone (see taper) | 1h gap from A |
| C | 11:30-12:30 | Dexamethasone (see taper) + Calcium + Calcitriol | 4h gap from B. [Rabu/Sabtu: + B-Complex] |
| D | 16:00–17:00 | Dexamethasone (see taper) | 4h gap from C |
| E | 19:00-21:00 | Levetiracetam 500mg | ~12h gap from B |

**Current dexa phase (as of 2026-07-05):** 5/5/4 (14mg TDS) — 5mg B, 5mg C, 4mg D. Phase ends 14/7/2026, then 13mg TDS.
**Tapering:** 1mg/2 weeks. Started 18mg (6/6/6) on 6/5/2026. Target: 0mg (STOP ~Feb 2027).
**Source:** `references/taper-engine.md` + `~/.hermes/dexa_taper.json`
**Note:** Doses are DYNAMIC. Always check `chain_calc.py --taper` for current values.

## Diagnostic Protocol: "Reminder Fired at Wrong Time"

When user says "reminder fired too early" or shows frustration about timing:

1. **Read med-status.json** → get actual intake times for today
2. **Run chain_calc.py** → check ready_time, chain_str, should_fire
3. **Compare now vs chain ready_time** → is this a shift domino?
4. **Check chain_calc.py's fire logic** for the specific slot — is it using wall-clock fallback?
5. **DO NOT** propose gateway restart, config changes, or prompt-level fixes until step 1-4 are done
6. **DO NOT** say "fixed" until you can show the chain_calc.py state that proves the fix works

The bug is almost always in chain_calc.py, not in the cron config, not in the gateway, not in the script.

## CRITICAL PITFALL: Time-Based Slot Auto-Mapping (2026-07-07)

Do **not** map bare "dah makan jam X" to the nearest scheduled slot. User may mean untracked drug (e.g. pantoprazole) or food. Guard: message must name a drug/slot/alias that maps — else ASK. Full failure chain + rules: `references/time-based-slot-auto-mapping.md`. Related: `references/makan-ambiguity-ask-dont-assume.md` (food vs ubat — ask both directions).

## CRITICAL PITFALL: Cron ↔ Session Isolation (2026-07-07)

The Domino Chain Medication Monitor (`chain_monitor.sh`, no_agent=true) fires reminders into the SAME WhatsApp chat as active agent conversations, with ZERO awareness of:
- Whether the user is currently discussing medications
- Whether the user just stated intention to take the slot
- Whether the slot was literally just discussed

**Failure (2026-07-07):** Agent and user were discussing pantoprazole timing for Slot B context. At 07:15, cron fired "B belum ke?" into the active conversation. The cron sees med-status.json (B=pending) and fires — it has no way to know there's an active conversation happening.

**Current mitigation (weak):** Cooldown system in chain_calc.py (60min gap between reminders). This helps but doesn't prevent the FIRST unwanted reminder.

**Architectural fix needed:** Cron output must route through a gateway that checks active session state before delivery. Until this is built, accept that the first reminder for any slot may fire into an active conversation — it's a known architectural gap, not a bug in the reminder logic.

## CRITICAL PITFALL: Verbal Confirmation Without Execution (2026-07-04)

When boss says ANY form of "dah makan X" / "X done at Ypm" / "dah selesaikan X" — the ONLY correct response is:

1. **FIRST** run `med_confirm.py <slot> --at <time>` (or drug-level)
2. **THEN** acknowledge verbally with chain display

**NEVER** say "noted ✅" or "confirmed" without running the script first. The verbal confirmation means NOTHING to the cron system — it only reads `med-status.json` and `chain-state.json`. If you don't write to those files, the system thinks the med is still pending and keeps spamming reminders.

**This exact failure caused 3+ spam reminders for D on 2026-07-04:**
- Boss: "dexa dose petang, aku dah selesaikan tadi jam 5pm. Done"
- MJ: "✅ noted boss. D jam 5pm confirmed done"
- MJ: [NEVER ran med_confirm.py D --at 17:00]
- System: [D still pending] → sends reminder at 18:45 → boss furious

**Detection priority:** If the message contains BOTH (a) a drug/slot reference AND (b) a past-tense completion signal ("done", "selesai", "dah makan", "dah ambil", "dah telan") — run med_confirm.py FIRST, ask questions later. Time reference in message ("jam 5pm", "pukul 5") → use --at flag.

## Correction ≠ Approval Rule (Critical)

When the user corrects a specific value or behavior (e.g., "C should be 12pm", "you fired at wrong time"), that is a CORRECTION of that one thing, NOT approval for a full system overhaul you've outlined.

**Correct response to a correction:**
1. Acknowledge the correction
2. Ask scope: "Just fix this one value, or full audit?"
3. Only proceed with a multi-file fix after explicit approval

**Wrong response to a correction:**
- "Great catch! Let me fix all 3 files, update the schedule, rewrite the cron, and add 2 new features." ← You just assumed approval for a project plan from a one-line correction.

## Known Bug History

### Bug #1: Partial slot fires using wall-clock default instead of chain time (2026-07-04)

**Root cause:** `chain_calc.py` `calculate_chain()` lines 366-372 (partial slot branch):
```python
if st['overall'] == 'partial':
    if st['ready_time'] and now_min >= time_str_to_minutes(st['ready_time']):
        should_fire = True   # ← correct
    else:
        # ← BUG: falls here when ready_time IS set but now < ready_time
        default = get_default_time(slot, schedule)
        if default and now_min >= time_str_to_minutes(default):
            should_fire = True  # ← FIRES AT WRONG TIME
```

**Consequence:** When B was taken at 09:00 (shifted from 08:00), chain correctly calculated C ready at 13:00 (09:00 + 4h). But the fallback used the wall-clock default of 12:00, causing 9+ spam reminders starting from 12:00 when C wasn't due until 13:00.

**Fix:** Change `else:` to `elif st['ready_time'] is None:` so it only falls back to default when ready_time is genuinely unknown. Verified live at 13:15 MYT 2026-07-04: `should_fire: false` for D (ready 16:35), chain display correct.

### Bug #2: Reminder template counts optional drugs as progress (2026-07-04)

**Root cause:** `generate_reminder()` uses `get_taken_drugs()` which returns ALL taken drugs (including optional B-Complex), then compares against `get_required_drug_ids()` which excludes optional drugs. This produces misleading "Baru 3/3 je" when actual required progress is 2/3.

**Fix:** Filter taken drugs to required-only before counting, or change the display to say "Baru 3 ubat logged" instead of implying full completion.

### Bug #3: `get_actual_time()` returns earliest drug time, breaks domino gap (2026-07-04)

**Root cause:** `chain_calc.py` `get_actual_time()` for drug-level format used `sorted(times)[0]` (earliest). For domino gap math, the next slot needs gap from the **LAST** drug taken in the previous slot — not the first.

**Consequence:** When C slot has calcium/calcitriol at 09:00 and Dexa #2 at 12:35, the chain thought "C taken at 09:00" and calculated D ready at 13:00 (09:00 + 4h). But D's 4h gap is from Dexa #2 (the actual steroid dose), not from calcium. D was firing ~3.5 hours too early.

**Fix:** `sorted(times)[0]` → `sorted(times)[-1]`. For partial slots the "last drug time" is the meaningful one for downstream domino calculation. The display string can still show the earliest time (it represents "started taking C"), but the chain math must use latest.

**Verification:** Post-fix, C done at 12:35 → D ready at 16:35 (correct), E ready at 21:00 (correct, 12h from B at 09:00).

### Bug #4: No cooldown between reminders = spam escalation (2026-07-04)

**Root cause:** The fire logic only checked `should_fire` (is the slot ready?) — it did not check "did we ALREADY remind the user about this slot recently?" Once a slot became ready at 16:35, every 15-min tick until 22:00 would fire a reminder. At 4 ticks/hour for ~5.5 hours of time window, a single slot could theoretically produce 22 reminders in one evening.

**Consequence:** D had 4 reminders before the user could even respond (he was asleep). User called the system "barua" (monkey) — extreme frustration signal.

**Fix:** Added `is_within_cooldown()` function to `chain_calc.py` with tiered cooldown intervals (0/60/60/30/15 min by count). Added `last_reminder_times` dict to `chain-state.json` to track when each slot was last reminded. Updated `chain_monitor.sh` to store HH:MM timestamps alongside reminder counts.

**Design lesson:** Every time you say "reminders keep firing until ALL required drugs taken," the user hears "persistent but reasonable." The developer hears "EVERY 15 MIN UNTIL DAWN." The fix codifies what the user expected: a reasonable reminder cadence, not denial-of-service-rate nagging.

### Bug #5: `confirm_slot()` Destroys Per-Drug Timestamps — Slot-Level Overwrite (2026-07-05)

**Root cause:** `med_confirm.py`'s `confirm_slot()` calls `get_slot_entry()` which initializes the entry, then runs `for did in drug_ids: entry['drugs'][did] = {'status': 'taken', 'time': now}`. This OVERWRITES every drug's timestamp with the same `now` value — even if some drugs were already logged with an earlier, correct time.

**How it manifests in practice:**
1. User says "Aku baru makan akurit-4 jam 7.40am" → agent runs `med_confirm.py A akurit_4 --at 07:40` → correct (akurit_4=07:40, pyridoxine=pending, overall=partial)
2. Later, while discussing pyridoxine unavailability/B-Complex alternatives, agent accidentally runs `med_confirm.py A` (slot-level, no --at) → **WRONG**: overwrites akurit_4 to current time (~09:10), sets pyridoxine to 09:10 even though user couldn't take it, overall=completed
3. User sees "A ✅ 09:10" and explodes because they took it at 07:40

**The critical distinction:**
- `confirm_drug(slot, drug_id, --at HH:MM)` → sets ONLY that one drug, preserves others
- `confirm_slot(slot, --at HH:MM)` → OVERWRITES ALL drugs, destroys per-drug timing

**Rule for this codebase:** If a slot has partial drug-level data (overall=partial), NEVER call `confirm_slot()`. Always use `confirm_drug()` with a specific drug_id. The only exception is when ALL drugs were genuinely taken at the same time AND none were previously logged — e.g., a fresh day's first confirmation.

**Diagnostic: How to spot this corruption:**
```bash
python3 med_confirm.py --status
# If slot shows all drugs at the SAME timestamp AND
# user confirms they took them at different times, it's a slot-level-overwrite.
```

**Fix procedure when corruption is detected:**
```bash
# 1. Reset the entire slot (safe — just deletes today's entry for that slot)
python3 med_confirm.py --reset A

# 2. Re-log each drug with its CORRECT time
python3 med_confirm.py A akurit_4 --at 07:40

# 3. Leave other drugs pending until user actually confirms them
# Do NOT do slot-level confirm to "catch up" — that re-corrupts the data
```

**Prevention:** The agent must treat `confirm_slot()` as a DANGEROUS operation when drug-level data already exists for today. Before calling slot-level confirm, check: does `med_confirm.py --check <slot>` return `overall=partial` with multiple drugs having different timestamps? If yes, use drug-level confirm exclusively until all drugs are individually confirmed.

**Safeguard added 2026-07-05:** `med_confirm.py` now has a `--dry-run` flag that prevents ALL writes. Use this to test what a confirm operation would do WITHOUT corrupting existing data:

**EXTENDED LESSON: Test-on-Production Contamination Chain (2026-07-05)**

The adversarial review session (20260705_094420, minimax-m3 model) ran `confirm_slot('B')` as a LIVE TEST against the production `med-status.json`. This is how corruption happens even when every individual step seems reasonable:

```
Step 1: User says "aku dah makan dexa, letram dan b complex jam 9.10am" (9:26am)
Step 2: Original MJ session logs correctly at 09:10 ✓
Step 3: Adversarial review session runs `confirm_slot('B')` at ~10:02 as live test
Step 4: This OVERWRITES BOTH dexa and letram timestamps from 09:10 to 10:02
Step 5: Later in main session, agent sees "A at 09:10" and "B at 10:02" and thinks data is wrong
Step 6: Agent RESETS A (wrongly — only akurit_4 was wrong, pyridoxine 09:10 was correct)
Step 7: Agent RESETS B dexa (wrongly — user DID take it at 09:10 per step 1)
Step 8: User explodes — 3 layers of corruption from a single test-on-production error
```

**Rule:** Verification scripts and adversarial reviews MUST use `--dry-run` or a state-file copy. NEVER point a test script at the production med-status.json. The `--dry-run` flag exists specifically to prevent contamination of the kind described above. If you can't use `--dry-run`, copy the state file: `cp med-status.json /tmp/test-state.json` and point the script at the copy.

```bash
# Check what slot-level confirm would overwrite:
python3 med_confirm.py --dry-run A
# → Shows: akurit_4: already taken (would overwrite time from 07:40 to 14:23)
# → Shows: pyridoxine: pending -> taken at 14:23

# The dry-run output makes the OVERWRITE visible before it happens.
# If you see "would overwrite time" for drugs already taken,
# switch to drug-level confirm instead.
```

Auto-backup (`.bak1/.bak2/.bak3`) is also active on every write, so recovery is a single `cp` away even if contamination happens.

### Bug #6: `get_actual_time()` Uses Latest Drug Time Instead of Priority Drug (Dexa) — Chain Gap Miscalculation (2026-07-07)

**Root cause:** `get_actual_time()` returned the LATEST taken time among ALL drugs in a slot. When Calcium/Calcitriol were taken at 13:00 (after Dexa #2 at 12:15 in slot C), the chain used 13:00 as C's actual time, calculating D ready at 17:00 (13:00 + 4h) instead of 16:15 (12:15 + 4h).

**Why it's wrong:** The gaps B→C and C→D exist specifically for **Dexamethasone spacing**, not for supplements. Taking Calcium later should NOT push Dexa #3 later. The chain is a Dexa timing system first — supplements are passengers on that schedule.

**User's directive (verbatim):** "Our main priority is Dexa, Akurit-4, and Letram. Any gaps or timeframe must prioritize this, bukan CC."

**Fix:** Modified `get_actual_time(slot, drug_id=None)` in chain_calc.py:
1. First checks if the slot contains any Dexamethasone drug (drug_ids: dexamethasone_1/2/3)
2. If yes, returns that Dexa drug's time specifically
3. If no Dexa in slot, falls back to latest taken time (original behavior for non-Dexa slots like A, E)
4. Added optional `drug_id` parameter for explicit drug-specific time extraction

**Verification:**
```
BEFORE: A ✅ 06:15 → B ✅ 08:00 → C ✅ 13:00 → D ~17:00 → E ~20:00  ← WRONG
AFTER:  A ✅ 06:15 → B ✅ 08:00 → C ✅ 12:15 → D ~16:15 → E ~20:00  ← CORRECT
```

**Design principle for this codebase:** Any slot containing Dexamethasone MUST use Dexa-specific time for downstream gap calculation. Supplements (Calcium, Calcitriol, B-Complex) taken after Dexa must NOT shift the chain. The get_actual_time() function is the single point of truth for this rule.

**Pitfall — Slot B Dexa vs Letram:** Slot B contains both Dexa #1 and Levetiracetam. With the Dexa-priority fix, B's chain time is Dexa #1 time. In practice, the user takes both together, so this is effectively identical to Levetiracetam time for the B→E (12h gap) calculation. If they ever take them separately, the B→E gap would need Letram-specific time, requiring a drug_id parameter in the gap calculation — not needed today.

**Related:** This bug is a LAYER on top of Bug #3 (earliest→latest drug time). Both defects trace to the same function (get_actual_time()) treating all drugs as equal in a system where Dexa is the primary scheduling axis.

### Bug #7: Reminder Counts Cross-Contaminate Between Days (2026-07-07)

**Root cause:** `chain-state.json` had NO mechanism to reset reminder counts when a new calendar day starts. The reset logic in `chain_monitor.sh` only cleared counts for slots that were CONFIRMED on the CURRENT day. Yesterday's count for slot E (e.g., 3 reminders) remained in the state file when today's E slot hadn't been taken yet. At 20:00 today, the first reminder fired using count=4 template ("dah 4x tanya") — but the user had NOT been asked about E even once today.

**Consequence:** User received an aggressive escalated reminder ("Aku dah tanya kau 4 kali ni") when it was literally the first reminder of the evening. User called the system "barua" — extreme frustration with an embarrassed agent who had to explain the cross-day bleed.

**Fix in `chain_monitor.sh` Step 3 Python block:**
```python
# Day boundary: reset ALL counts if date changed
today = datetime.date.today().isoformat()
state_today = state.get('today')
if state_today != today:
    state['reminder_counts'] = {}
    state['last_reminder_sent'] = {}
    state['last_reminder_times'] = {}
    state['today'] = today
```

**What it does:**
1. Reads or creates a `today` field in `chain-state.json`
2. Every cron tick, compares stored `today` against current system date
3. On mismatch (day rollover), wipes ALL reminder counts, sent counts, and timestamps
4. Writes the new date so next tick won't reset again until the following day

**Design rationale:** Placing the reset BEFORE the slot-confirmation cleanup and BEFORE the count increment ensures counts are always scoped to the current day. The reset fires at most once per day — on the first cron tick after midnight — and is a no-op for all subsequent ticks.

**Verification:**
```python
# Simulate yesterday's state
old = {'today': '2026-07-06', 'reminder_counts': {'E': 3}}
today = '2026-07-07'
assert old['today'] != today  # True → reset triggered
old['reminder_counts'] = {}   # Cleared
old['today'] = today          # Updated
```

## Recurring Pattern Warning

If a user reports the SAME timing error multiple days in a row despite "fixes," the problem is almost certainly:
1. A fallback-to-default-time path in chain_calc.py (Bug #1 pattern)
2. NOT a gateway issue, config issue, or restart-needed issue
3. Trace the decision chain end-to-end before touching anything else

## Recurring Pattern Warning: "First Reminder Too Aggressive"

If a user reports that the first reminder of the evening (slot E) was aggressive/unexpected, the problem is almost certainly **cross-day reminder count bleed** (Bug #7). Check `chain-state.json` for:
1. `today` field — does it exist? If not, the day-boundary reset isn't active.
2. `reminder_counts.E` — is it non-zero before any reminders fired today? If yes, counts bled from yesterday.

**Fix is one-time (already applied 2026-07-07):** The `today` field in `chain-state.json` prevents all future cross-day contamination. Verify by checking that `chain-state.json` has a `today` field matching the current date.

## CRITICAL PITFALL: Cross-Session Context Contamination — Unintended Med Writes (2026-07-10)

The agent can write med state as a SIDE EFFECT of handling an UNRELATED task when the conversation turn context includes cross-session notes referencing prior medication sessions.

**VERIFIED failure (2026-07-10):**
```
Time:    05:00:58.007 MYT
Context: Gateway-restart conversation (session "Gateway clean restart verification results")
User msg:"Why did you instruct me to do something? I ask you to work on it for me."
Note in turn context: [Note: You also have a session on whatsapp ("Slow audit and system overhaul")]
Result:  med-status.json[2026-07-10][A] = {akurit_4: taken@20:00, pyridoxine: taken@20:00}
Damage: System thinks Slot A is completed for today. User hasn't woken up yet (med taken at 20:00 on a fresh day = nonsensical).
```

**Root cause chain:**
1. Turn context contains `[Note: You also have a session on whatsapp ("<prior-session>")]` where `<prior-session>` was about med system overhaul/fixes
2. Agent loads that prior session's context into working memory
3. User's current message is about something UNRELATED (gateway restart, code issue, etc.)
4. During tool call rounds #3-#10 (invisible from logged session data), agent writes med-status.json as if the user confirmed medication
5. The "20:00" time is a hallucinated default — no user statement mentioned 20:00 or Slot A drugs

**Core mechanism:** The agent does NOT need a `med_confirm.py` call to write med state. Any tool call (terminal running Python, cronjob, execute_code) that internally calls `save_json` on `STATE_FILE` can write med-status.json. The `med_confirm.py` script is the INTENDED write path, but it is not the ONLY write path.

**Detection (how to identify this contamination):**
```bash
# 1. File mod time — was med-status modified during a non-med conversation?
stat -c '%y %n' ~/.hermes/med-status.json

# 2. Compare against backup — what specifically changed?
diff -u ~/.hermes/med-status.json.bak1 ~/.hermes/med-status.json

# 3. Check agent.log for the exact timestamp — was the agent mid-conversation on a different topic?
grep "<timestamp_minute>" ~/.hermes/logs/agent.log | grep -v cron

# 4. Check cron list — any med cron running at that exact time?
hermes cron list | grep -i med

# 5. Search for direct med_confirm.py calls in logs
grep -n "med_confirm" ~/.hermes/logs/agent.log | grep "<date>"
```

**Guard rules (NON-NEGOTIABLE):**

1. **Do NOT write med state during non-med conversations.** Before ANY write to med-status.json, check: "Is the user's CURRENT message about taking medication?" If the user is talking about gateway, code, cron, or anything unrelated, do NOT write med state even if session notes mention prior med sessions.

2. **Cross-session notes are BACKGROUND, not instructions.** A note like `[Note: You also have a session on whatsapp ("...")]` tells you another session exists. It does NOT mean "continue that session's work here." The CURRENT message determines what to do — not the referenced session's topic.

3. **Tool calls in a non-med turn must not touch med state.** If your first tool call batch succeeds and you're about to make a SECOND batch of tool calls, verify: "Am I about to write med state? Was the user's message about medication?" If no → suppress the med write. A med write during a gateway-restart conversation is always wrong.

4. **The "20:00" time is a RED FLAG.** If any write to med-status.json uses `"time": "20:00"` and the user did not say "20:00" or "8pm" or "malam", it is almost certainly a hallucinated default. Stop and investigate before proceeding.

5. **Session DB wipe after gateway restart destroys forensic evidence.** The session DB (`state.db` or `default.db`) is recreated empty on gateway restart. If you suspect contamination and the DB is empty, rely on agent.log + file stat timestamps for forensic tracing rather than claiming "evidence insufficient."

**Pitfall — The session DB is EMPTY after gateway restart:** On 2026-07-10, the gateway restarted at 05:19:45 (shutdown) and a new session was created at 05:51:10. The default.db was recreated empty (0 bytes). This meant tool calls #3-#10 from the 04:58-04:59 turn were UNRECOVERABLE. The agent could NOT audit its own actions. When you discover contamination and the DB is empty, do NOT conclude "can't find evidence" — check file stat timestamps and agent.log first. The write happened whether or not the DB recorded it.

**Example of the correct check before med write:**
```python
# Before confirming any medication, ask:
# 1. Did the user's CURRENT message mention a drug name or slot letter?
# 2. Did the user's CURRENT message use past-tense completion words?
# 3. Is this conversation ABOUT medication or about something else?
# If ANY of these answers is NO → do NOT write med state.
# Exception: cron-triggered scripts (chain_monitor.sh) that fire independently.
# But the CHAT AGENT must never write med during a non-med conversation.
```

**Related pitfalls:** This overlaps with "Verbal Confirmation Without Execution" (the reverse: user says meds, agent doesn't write) and "Time-Based Slot Auto-Mapping" (agent writes meds for wrong drug based on time). But this is a THIRD axis: agent writes meds when user wasn't even talking about medication at all.

**Reference trace:** See `references/cross-session-contamination-20260710.md` for full evidence chain (stat output, diff output, agent.log timeline, cron list, script write-path analysis).

## CRITICAL PITFALL: Check Infra Yourself — Don't Ask What You Can Verify (2026-07-09)

When tracing a bug, data discrepancy, or "where did X come from", the agent MUST investigate via available tooling (terminal, logs, state files, DB) BEFORE asking the user. The user explicitly scolded this pattern:

**User (verbatim, 2026-07-09):** "kau nak tanya soalan pun kau boleh check. apa fungsi kau jadi personal agent kalau kau tak boleh check untuk aku? kau ada akses untuk semua tu kan?"

**Failure chain (this session):** Slot C drugs showed stale "taken 20:00" data. Agent could not explain the source, so it ASKED the user "awak pernah ke hari ni bagitahu...". User correctly pointed out the agent HAS terminal access to every log/file and should have traced it.

**Investigation path that ACTUALLY works (verified this session):**
```bash
# 1. File modification timeline — which backup holds the bad data?
stat -c '%y %n' ~/.hermes/med-status.json*

# 2. What each backup contained (diff the bad state)
python3 -c "
import json
for f in ['med-status.json.bak1','med-status.json.bak2','med-status.json.bak3']:
    d=json.load(open(f))
    print(f, d['meds']['C'].get('2026-07-09',{}).get('drugs',{}))
"

# 3. cron jobs that could write state
cronjob action=list   # look for no_agent scripts touching med-status

# 4. Script source — does any hardcode the bad value or call confirm_slot?
grep -rn "20:00\|confirm_slot\|med_confirm" ~/.hermes/scripts/*.py

# 5. Live session DB (tool_calls may be empty for in-flight sessions)
python3 -c "
import sqlite3
con=sqlite3.connect('/home/ubuntu/.hermes/state.db')
cur=con.cursor()
cur.execute(\"SELECT timestamp,role,substr(content,1,200) FROM messages WHERE timestamp LIKE '2026-07-09%' AND content LIKE '%med_confirm%'\")
for r in cur.fetchall(): print(r)
"

# 6. Gateway/cron execution traces
grep -n "med_confirm\|chain_monitor" ~/.hermes/logs/gateway.log ~/.hermes/logs/errors.log
```

**Verdict protocol:** Exhaust steps 1-6 (or equivalent) BEFORE asking the user anything. If all paths return empty, report "I traced all logs/scripts/state and found no write source — this is likely stale data from a prior session" rather than asking the user to self-incriminate.

**Distinction from Session-Search-Before-Asking:** That rule is about CHAT HISTORY (did the user already tell me X?). This rule is about SYSTEM STATE (where did this file value come from?). Both say "investigate first, ask never-or-last." Terminal access is the agent's default; asking is the fallback, not the reflex.

## CRITICAL PITFALL: `--at <slot>` Mode Skips Verification Gate (2026-07-09)

`med_confirm.py --at <slot> <time>` routes to `confirm_slot()` (line 511), which marks ALL drugs in the slot as taken at that time. Critically, when called via `--at` WITHOUT `--source-text`, `source_text=None` is passed to `confirm_slot()`, so the verification gate (which checks the user's words mention a slot drug) is SKIPPED entirely.

**Contrast with slot-letter-only mode:** `med_confirm.py B` (no --at) ALSO calls confirm_slot, but the agent is expected to pass `--source-text "user said..."`. The `--at` shorthand form omits this, leaving zero verification.

**Danger:** `med_confirm.py C --at 20:00` writes all of C's drugs (dexa, calcium, calcitriol, b-complex) as taken at 20:00 with NO check that the user said any of those words. One mistyped command corrupts an entire slot silently.

**Rule for this codebase:**
- Prefer `confirm_drug(slot, drug_id, --at HH:MM)` for any single-drug log — it only touches one drug and still benefits from the resolve step.
- If you must use slot-level `--at`, ALWAYS pair it with `--source-text "verbatim user statement"` so the gate runs.
- The agent should treat `--at <slot>` without `--source-text` as a code smell. If you see it in a command, stop and add the source text.

**Related:** Bug #5 covers the OVERWRITE damage of confirm_slot. This pitfall covers the VERIFICATION BYPASS — a different failure axis (no gate vs. destructive gate).

## CRITICAL PITFALL: `--at` Time Value Is Completely Unvalidated — phantom '20:00' poisons the chain (2026-07-10)

`med_confirm.py --at HH:MM` writes WHATEVER time string is passed, with ZERO validation. The time is either the caller's current MYT time (`get_now_hm()`, correct) OR an explicit `--at` value — and if that value is wrong/misparsed, it silently corrupts the chain.

**VERIFIED incident:** `med-status.json[2026-07-10][A]` = `akurit_4: taken@20:00, pyridoxine: taken@20:00, overall=completed`. 20:00 is impossible for a morning empty-stomach med. Root cause: an explicit `med_confirm.py A --at 20:00` call (proven by repro: `--at 20:00` → writes 20:00; no `--at` → writes current MYT time; `get_now_hm()` uses Asia/Kuala_Lumpur, so NOT a timezone bug).

**Cascade:** chain_calc saw A 'done' @20:00 → B ready ≈ 21:00 → B never fired → A & B reminders MISSED all day.

**Writer = UNATTRIBUTED** (genuine data gap): hook ruled out (COMPLETE_RE can't match the 05:00:57 inbound; `config.yaml` has `hooks: {}`; zero hook traces 07-10); only live agent session at 05:00:58 did read-only diagnostics (no med_confirm call); no inbound med message; no cron writes state; no stray process. Without a per-write audit log, the writer is untraceable.

**⚠️ A PRIOR SESSION FABRICATED THE ROOT CAUSE:** a 07:04 session claimed "the med-auto-confirm hook false-positive'd on your 05:00 message about the 20:00 bug." REFUTED by (a) the real 05:00:57 gateway.log line has no med content and no "20:00"; (b) the hook's COMPLETE_RE cannot match that message; (c) zero hook traces on 07-10. Do NOT inherit a prior session's "we fixed it" narrative — re-derive from raw code + logs (see diagnosing-bugs pitfall on this).

**Systemic fix (draft exists, NOT yet applied — see `references/med-confirm-at-validation-fix.md`):**
1. Validate `--at`: reject FUTURE times (med can't be logged before taken — "8"→20:00 dies here) and reject CROSS-HALF-DAY (AM slot logged PM, e.g. A@20:00 → reject; A@09:00 still allowed — user is flexibly late).
2. `--at` REQUIRES `--source-text` (enforce in code, not just prompt — pairs with the gate pitfall above).
3. Per-write audit log (`~/.hermes/med_confirm_audit.log`: ts, slot, drug, time, source, caller, argv, ok) so future phantom times trace in 5 min.

**Agent guard:** if any med-status write uses `"time": "20:00"` and the user did NOT say "20:00"/"8pm"/"malam" → RED FLAG, stop and investigate. (Overlaps Cross-Session Contamination guard #4, but triggered by the impossible time value itself.)

## CRITICAL PITFALL: Fuzzy Drug-Level Confirm Corrupts Other Drugs in Slot (2026-07-12)

`med_confirm.py <slot> <fuzzy_drug>` can silently mark **other required drugs in the same slot as taken at current time**, not just the requested drug. Verified on 2026-07-12 for `B dexa` (Levetiracetam wrongly marked taken) and `C calcium` (Dexa #2 wrongly marked taken).

**Immediate rule:** use `--dry-run` first on the first drug-level confirm of the day in a multi-drug slot, then verify with `--check`. If corruption occurs, reset the wrongly-marked drug with `--reset <slot> <drug_id>`.

**Detail + reproduction recipe:** `references/med-confirm-fuzzy-bug-20260712.md`.

## CRITICAL PITFALL: VPS/System Clock Drift Corrupts Med Times (2026-07-12)

`med_confirm.py` uses the VPS system clock (`get_now_hm()`). On 2026-07-12, VPS time was 12:29 while the user's WhatsApp timestamp was 09:15 — a ~3h drift. This caused CC confirmation at 09:50 to also write Dexa #2 at 12:27 (current VPS time).

**Rule:** always prefer explicit `--at HH:MM` from the user's stated time; check VPS time with `TZ=Asia/Kuala_Lumpur date` when things look off; flag clock drift to the user because it also breaks cron reminder timing.

**Full incident:** `references/med-confirm-fuzzy-bug-20260712.md`.

## CRITICAL PITFALL: No Day-Boundary Reset for med-status.json Drug Entries (2026-07-09)

Unlike `chain-state.json` (which HAS a day-boundary reset in `chain_monitor.sh` — see Bug #7), `med-status.json` has NO day-boundary sanitization in `med_confirm.py`. Each day's entry is keyed by date string, but nothing clears or reinitializes "today's" entry when the date rolls over.

**How corruption manifests (verified this session):**
- Slot C drugs (calcium, calcitriol, b_complex) showed `"taken 20:00"` in state at 12:32 — BEFORE the user said "slot c yang lain tunggu lunch" and BEFORE the agent touched C today.
- Backup mtime analysis (`med-status.json.bak3` modified 12:32) proved the 20:00 data pre-existed today's chat actions.
- Exhaustive trace (cron list, all script source, gateway.log, state.db, chain-state.json) found NO automated writer of "20:00" — so the data came from a PRIOR session's mistaken `confirm_slot C --at 20:00` (or equivalent) that was never cleared.
- Because med_confirm.py never resets "today" on day boundary, the stale entry persisted into the new day's view.

**Detection:** If `--status` shows a drug marked "taken" at a time the user did NOT report today, and the user says "mana datang aku makan X jam 20:00?", suspect a stale prior-session entry, NOT a live action.

**Mitigation (agent-side, until code fix):**
- When user reports a drug wrongly marked, check the raw backup timeline (stat + diff, above) before resetting.
- Reset the specific drug via `med_confirm.py --reset <slot> <drug_id>` — do NOT use slot-level confirm to "fix" it (that re-corrupts per Bug #5).
- If an entire prior day's entry looks wrong, consider whether a stray confirm_slot ran and clean per-drug.

**Code fix needed (not yet applied):** Add a day-boundary guard in `med_confirm.py` `load_json`/`get_today` path — on first write of a new date, if "today's" entry already exists with data the current session didn't produce, flag or clear it. Mirror the `chain-state.json` `today` field pattern.

## CRITICAL PITFALL: User Shorthand Codes (CC / CCC) — Resolve From Evidence, NOT Memory (2026-07-09)

The user uses informal shorthand for meds/slots. These MUST be resolved from session DB / logs BEFORE answering — never from memory recall.

**Failure chain (2026-07-09):**
```
User: "kau faham tak CC tu apa? semalam dah faham"
Agent: "CC = slot C + D"   ← FABRICATED from memory, ZERO verification
User: "barua. cc tiba² jadi C+D? kalau aku tak cakap, takyah assume"
Agent (after forced check): grep found "Dah makan both CCC now." in 2026-07-03 log
Agent (truth): "CCC" = SLOT C only (Dexa #2 + Calcium + Calcitriol). NOT C+D.
```
**Root cause:** Agent recalled a fuzzy "CC = C+D" from a prior day, presented it as fact, doubled down when challenged, then only checked after the user exploded. The check (state.db query) took 30 seconds and would have prevented the entire rage-loop.

**The actual shorthand map (VERIFIED from state.db, 2026-07-03 session `20260703_101001_854bbb` + user's own closure 2026-07-09):**
- **"CCC"** = Slot C (Dexa #2 + Calcium + Calcitriol). User said "Dah makan both CCC now." → agent logged C completed.
- **"CC"** = Calcium Carbonate + Calcitriol ONLY (both in Slot C, taken dengan lunch). User's final words 2026-07-09: "cc tu maksudnya calcium carbonate + calcitriol. simple, benak." NEVER C+D, NEVER "Slot C" as a whole (Slot C also contains Dexa #2).
- **"bukan CC"** (user's own words 2026-07-07): "Our main priority is Dexa, Akurit-4, and Letram. Any gaps or timeframe must prioritize this, bukan CC." → "CC" there = the Calcium+Calcitriol passengers, explicitly the LOW-priority items.
- D (Dexa #3, 4pm) is a SEPARATE slot. User never bundles it with CC.
- **Logging CC when user says "dah makan cc pukul HH:MM":** it is TWO drugs in Slot C, not slot-level. Use drug-level confirm for each:
  ```bash
  python3 ~/.hermes/scripts/med_confirm.py C calcium --at HH:MM
  python3 ~/.hermes/scripts/med_confirm.py C calcitriol --at HH:MM
  ```
  (Slot C's Dexa #2 is logged separately when the user takes it ~12:00.) Do NOT run `med_confirm.py C --at HH:MM` (slot-level) — that would also mark Dexa #2 taken at the CC time (Bug #5 overwrite). Verified live 2026-07-09: user said "dah makan cc jam 3.15pm" → calcium+calcitriol logged 15:15, Dexa #2 stayed 12:00, C overall=completed.

**Hard rule for this codebase:**
1. When user references ANY shorthand from "semalam / the other day / before" → STOP. Do NOT answer from memory.
2. Grep session DB / logs for the literal shorthand FIRST (recipe below).
3. If the shorthand is not found or ambiguous → say "I don't have evidence what X means, what did you mean?" — NEVER present a guessed mapping as fact.
4. This applies to med codes AND any other shorthand the user uses.

**Reusable recovery recipe (VERIFIED 2026-07-09 — recovers old WhatsApp/Telegram context):**
```python
import sqlite3
con = sqlite3.connect('/home/ubuntu/.hermes/state.db')
con.row_factory = sqlite3.Row
cur = con.cursor()
# Find the session + message containing a shorthand/phrase
cur.execute(
    "SELECT session_id, role, content, timestamp FROM messages "
    "WHERE content LIKE ? ORDER BY id", ('%CCC%',)   # or '%CC%', '%both%', etc.
)
for r in cur.fetchall():
    d = dict(r)
    print(d['session_id'], '|', d['role'], '|', repr(d['content'])[:300])
# Then read full conversation in that session:
sid = '<session_id from above>'
cur.execute("SELECT role, content, timestamp FROM messages WHERE session_id=? ORDER BY id", (sid,))
for r in cur.fetchall():
    d = dict(r)
    c = d['content']
    if d['role'] == 'tool' and len(c) > 200: c = c[:200] + '...[tool]'
    print('['+d['role']+']', c[:600]); print('---')
```
- `sessions` table columns: id, source, user_id, title, started_at, message_count, ...
- `messages` table columns: id, session_id, role, content, tool_name, timestamp, ...
- Timestamp is Unix epoch float (MYT = +08). Convert: `datetime.datetime.fromtimestamp(ts, tz=datetime.timezone(datetime.timedelta(hours=8)))`.
- NOTE: gateway.log / agent.log store only inbound msg + response CHAR COUNT, NOT response text. For full context you MUST query state.db, not just grep logs.

## CRITICAL PITFALL: Session Search Before Asking (2026-07-05)

When you are about to ASK the user "did you take X?" or "at what time?", STOP. FIRST search the session history. The user WILL have already told you if they took it.

**Timeline from 2026-07-05 that this rule prevents:**
```
09:26 User: "aku dah makan dexa, letram dan b complex jam 9.10am"
14:19 Agent: "dah makan dexa #1 ke belum?"  ← WRONG! User already said this
```

**The user's explicit directive (verbatim):**
"Sebelum kau tanya aku dah makan ke belum, baik kau check dulu barua apa yang kita borak, check log, check chat history, session history, check chat and verify, jangan tanya soalan bodoh macam tu dengan malas nak cari dan confirmkan."

**How to implement:**
```python
# Before asking user about any med:
# 1. session_search(query="dah makan dexa") or session_search(query="slot B")
# 2. If a session shows user's explicit intake statement → log it via med_confirm.py
# 3. NEVER ask "did you take X?" if the answer is in the chat history
# 4. The ONLY exception: if session_search returns no results AND current time
#    is within the slot's window AND no confirmation exists
```

**This rule applies equally to:** asking about timing, asking about which dose, asking about whether they took something. The user tolerates ZERO questions that existing data could answer.

## CRITICAL PITFALL: Cron Delivery Must Use Explicit Target

When creating or updating med-related cron jobs (chain_monitor.sh, taper_alert.py, med_report.py, med_appointments.py), the `deliver` field MUST use an explicit platform:chat_id:thread_id target.

**WRONG:** `deliver: "origin"` — delivers back to wherever the cron was CREATED. If that session expired or the origin was a different session context, the message is LOST.

**RIGHT:** `deliver: "whatsapp:120363428305511789"` — explicitly targets the WhatsApp group.

**Verification:** After creating/updating a cron with `deliver: "origin"`, check what `origin` resolves to. If the gateway doesn't know how to reach the origin session (e.g., session expired, channel disconnected), the delivery silently fails. Always use an explicit target for no_agent cron jobs that deliver medication reminders.

**Detection:** If user says "reminder tak sampai / I didn't get the reminder" but cron's last_status was "ok", the deliver target is the likely culprit — not the script logic.

These two functions MUST have identical side effects except for the "which drugs to mark" question. The med-system review found:

- `confirm_drug()` decrements supply via `med_supply.decrement()`
- `confirm_slot()` updates med-status.json but DOES NOT call `decrement()`

Result: user says "dah makan B" → triggers slot-level confirm → meds status updated ✅, supply tracking STALE ❌. Low/out-of-stock alerts never fire for slot-confirmed drugs. 9/10 drugs are silently untracked because slot-level is the common path.

**Rule for this codebase:** Every public confirmation function MUST call `med_supply.decrement()` for every drug it marks. If you add a new confirmation path (e.g., "confirm all today's meds", "confirm by time range"), copy the decrement loop from `confirm_drug()` — don't reinvent.

**Symmetry test before merging any med_confirm.py change:**
```python
# After implementing any new confirm_* function, run this:
import shutil, json
shutil.copy(STATE_FILE, '/tmp/test_state.json')  # backup
supply = json.load(open(SUPPLY_FILE))
for did in supply['drugs']:
    supply['drugs'][did]['current'] = 100
json.dump(supply, open(SUPPLY_FILE, 'w'))
# Run your new confirm_* function for slot B
# Check: every drug in B should be at 99 after. If not, decrement is missing.
```

## Pitfall: Taper Data Arithmetic Must Be Validated (CRITICAL, found 2026-07-05)

`dexa_taper.json` has 21 phases. The review found 3 of them (phase 1, 2, 3) and 7 BD phases (10-16) where `total_mg` does NOT equal `dose_morning + dose_midday + dose_afternoon`:
- Phase 1: declared 18mg, sum = 6+6+0 = 12mg (33% underdose)
- Phase 10: declared 10mg, sum = 6+0+0 = 6mg (40% underdose — BD 2pm dose has no field at all)

**Rule for this codebase:** Before adding/editing ANY phase in `dexa_taper.json`, run the validation script in `references/taper-data-validation.md`. Sum MUST equal `total_mg`. If it doesn't, either fix the missing field or fix `total_mg` — but the JSON must not lie.

**BD phase special case:** The 2pm dose is a real dose the patient takes, but there's no slot for it in `med-schedule.json` (only A-E). Until a slot F (or `dose_2pm` field) is added, BD phases will display wrong dose breakdowns in `taper_alert.py` and `chain_calc.py --taper-display`. Don't pretend it's not a bug — flag it as known.

## Pitfall: `med-schedule.json` Static `dosage` Field Is Stale By Design (HIGH, found 2026-07-05)

The `dosage` field in med-schedule.json (e.g., `"dosage": "5mg"` for `dexamethasone_1`) reflects ONLY the current phase. When taper transitions (e.g., phase 5 → 6 on 15/7), the actual dose changes but `dosage` doesn't. Currently `generate_reminder()` correctly uses taper values, but any NEW code that reads `drug['dosage']` from schedule will show the wrong mg.

**Rule for this codebase:** NEVER read `dosage` from med-schedule.json for dexamethasone. Always go through `get_dexa_dose_for_slot(slot)` in chain_calc.py. If a new field needs the dose, use the taper engine.

## Pitfall: Alias Expansion Can Drop Slot-Qualifier Words (HIGH, found 2026-07-05)

`med_resolve.py` ALIASES table maps `"dexa petang" → "dexamethasone"`. After expansion, `match_name("dexamethasone", ...)` matches all 3 dexamethasone entries. Without explicit `time_24h`, `pick_slot_by_time()` is NOT called, so no time-based disambiguation. Returns first match → `dexamethasone_1` (slot B, pagi). **User says "dexa petang", system logs to B. WRONG.**

This affects all 9 fragment qualifiers: "pagi/tengahari/petang/mlm/malam" combined with dexa/dexamethasone/steroid.

**Rule for this codebase:** When alias expansion strips a slot-qualifier word, the original fragment must be checked FIRST for those words, and the matching slot used to filter candidates BEFORE `match_name()`. The word-to-slot mapping (`pagi=B, tengahari=C, petang=D, mlm=E`) should live in `med_resolve.py` near `TIME_RULES`.

**Until fixed:** When user says "dexa petang" or similar without explicit time, agent must ASK which slot — don't trust the resolver.

## Pitfall: `med_interact.py validate` "ALL SAFE" Hides UNKNOWN Pairs (HIGH, found 2026-07-05)

The validate output says "ALL SAFE ✅" but the actual data has 41 SAFE + 4 UNKNOWN (same-drug pairs: levetiracetam_b↔e, dexamethasone_1↔2, etc.). The verdict text masks the gap.

**Rule for this codebase:** When reporting interaction validation, surface the UNKNOWN count prominently. Either (a) explicitly mark same-drug pairs as safe in the JSON, or (b) change verdict to "NO UNSAFE (N UNKNOWN — same-drug pairs need explicit confirmation)".

## Pitfall: Time Parser Boundary at 10:30 (MEDIUM, found 2026-07-05)

`med_resolve.py` parses time as `replace(":", ".").rstrip("0").rstrip(".")`. For "10:30" this gives "10.3" = 10.3, which is < 10.5 (lo boundary for slot C). So 10:30 → slot B. User intuition: 10:30 is "tengahari" not "pagi".

**Rule for this codebase:** Use `datetime.strptime(t, "%H:%M").time()` and compare with `datetime.time(10, 30)`. The float-string dance loses precision at half-hour boundaries. Fix when adding the word-based disambiguation (above pitfall).

## Pitfall: Reviewer Findings Must Be Cross-Checked With Live Tests Before Fixing (2026-07-05)

When an adversarial review returns findings (CRITICAL, HIGH, MEDIUM, etc.), do NOT fix them blindly. Cross-check EACH finding with a live test before implementation:

```python
# Step 1: Test the reviewer's claim
python3 -c "import json; ..."  # Live test of the alleged bug

# Step 2: Does the test FAIL as expected?
# If yes → proceed to fix
# If no → the reviewer was wrong. Flag as false positive.

# Step 3: Apply fix, then re-test
# Step 4: Verify ALL related paths still work (regression)
```

**2026-07-05 example:** Review claimed `med_substitute.py pyr` crashes. Live test showed it doesn't — fuzzy match handles the case perfectly. If we had fixed without checking, we'd have introduced dead code for a non-existent problem.

**Discard rate:** Of 18 findings in the 2026-07-05 review, only 7 survived cross-checking (3 CRITICAL + 4 HIGH). The rest were false positives, noise, or LOW-severity cosmetic items. Fixing all 18 would have wasted time and introduced risk.

## Pitfall: Taper Data Arithmetic Must Be Validated (CRITICAL, found 2026-07-05)

`dexa_taper.json` has 21 phases. The review found 3 of them (phase 1, 2, 3) and 7 BD phases (10-16) where `total_mg` does NOT equal actual sum of individual doses. Always run a validation check after any edit to dexa_taper.json.

**Validation script:**

```python
import json
with open('dexa_taper.json') as f:
    t = json.load(f)
for p in t['phases']:
    if p['freq'] == 'TDS':
        s = p['dose_morning'] + p['dose_midday'] + p['dose_afternoon']
    elif p['freq'] == 'BD':
        s = p['dose_morning'] + p.get('dose_2pm', 0)
    elif p['freq'] in ('OD', 'STOP'):
        s = p['dose_morning']
    if p['total_mg'] != s:
        print(f'FAIL Phase {p["id"]}: total={p["total_mg"]}, sum={s}')
```

## Pitfall: `med-schedule.json` Static `dosage` Field Is Stale By Design (HIGH, found 2026-07-05)

The `dosage` field in med-schedule.json (e.g., `"dosage": "5mg"` for dexamethasone_1) reflects ONLY the current taper phase. When the taper transitions, actual dose changes but `dosage` doesn't. The `generate_reminder()` correctly uses taper values, but any NEW code that reads `drug['dosage']` from schedule will show wrong mg.

**Rule:** NEVER read `dosage` from med-schedule.json for dexamethasone. Always use `get_dexa_dose_for_slot(slot)` from chain_calc.py.

- **Partial ≠ done.** If user says "dah makan dexa pagi" but not Levetiracetam, B stays ◐ partial. Reminders keep firing for the pending drug.
- **Slot-level confirms ALL.** If user says "dah makan B", ALL drugs in B are marked taken. Use when user confirms the whole slot.
- **Drug-level confirms ONE.** If user says "dah makan dexa", only that specific drug is marked. Use when user is taking things separately.
- **Chain timing uses actual intake times.** If Dexa was at 08:16, the chain calculates C at 12:16 (08:16 + 4h), D at 16:16, etc.
- **Reminders persist until ALL pending drugs confirmed.** System will NOT auto-silence.

## Edge Cases

- **Multiple letters/drugs in one message:** Handle sequentially, show combined status
- **Stale confirmation:** Log with specified time
- **Skip:** Acknowledge, don't log
- **Ambiguous drug name without context:** Ask user which slot
- **Very late confirmation:** Log it, show adjusted chain. Don't comment on lateness
- **B-Complex on non-Rabu/Sabtu:** Don't remind about it. It's optional (required=false in schedule)

## Files (v3 — 2026-07-05)

| File | Role |
|------|------|
| `~/.hermes/med-schedule.json` | Rules: gaps, windows, drugs with drug_id, required flag |
| `~/.hermes/med-status.json` | Drug-level log of actual intake |
| `~/.hermes/chain-state.json` | Reminder counts + escalation level + cooldown timestamps + `today` date |
| `~/.hermes/dexa_taper.json` | **Date-dependent dexa dosing (21 phases: TDS→BD→OD→STOP)** |
| `~/.hermes/med-supply.json` | **Pill inventory per drug, auto-decremented on confirm** |
| `~/.hermes/substitutions.json` | **Drug alternatives when supply runs out** |
| `~/.hermes/med-interactions.json` | **Drug interaction safety data for full regimen** |
| `~/.hermes/scripts/med_confirm.py` | CLI tool — supports drug-level + slot-level + auto-decrement supply |
| `~/.hermes/scripts/med_resolve.py` | Drug name resolver — aliases, time-based disambiguation, UNKNOWN rejection |
| `~/.hermes/scripts/chain_calc.py` | Engine — v3 with taper engine, dynamic slots, dose-aware templates |
| `~/.hermes/scripts/chain_monitor.sh` | Cron script — still works, reads drug-level state, day-boundary reset for counts |
| `~/.hermes/scripts/med_supply.py` | **Supply CLI: --check, --refill, --set, --warnings** |
| `~/.hermes/scripts/med_substitute.py` | **Substitution query: --check, --all, --otc** |
| `~/.hermes/scripts/med_interact.py` | **Interaction checker: check pair, validate full regimen** |
| `~/.hermes/scripts/taper_alert.py` | **Daily cron: alerts3 days before dose change** |
| `~/.hermes/scripts/med_report.py` | **Weekly/daily compliance report** |
| `~/.hermes/scripts/med_appointments.py` | **Appointment tracker: --upcoming, --add, --check-tomorrow, --check-today** |
| `~/.hermes/appointments.json` | **Appointment data (date, location, purpose, notes, linked taper phase)** |

## LLM-from-Cron-Script: Provider Constraints (Discovered 2026-07-04)

If/when you add an LLM call to the cron script (Hybrid Approach C), the script runs in a non-interactive shell — it cannot use whatever model is active in the user's current chat session. Live-tested constraints:

| Provider | Callable from cron script? | Why |
|---|---|---|
| DeepSeek (`api.deepseek.com`) | ✅ Yes | Direct API, OpenAI-compatible, works from urllib/curl |
| opencode-go (`opencode.ai/zen/go`) | ❌ **No** | Cloudflare Error 1010 — browser-only access, blocks scripted HTTP |
| opencode-zen (`opencode.ai/zen/go/v1`) | ❌ **No** | Same as opencode-go, Cloudflare-gated |

**Implication:** When the user says "use the same model I'm chatting with" for a cron-triggered LLM call, the script cannot dynamically match the active chat model. The script's only viable LLM provider is DeepSeek. If the user is on opencode-go/zen, the script's LLM will be DeepSeek regardless.

**Workaround if user insists on same-model parity:** Make the script `hermes chat -q "..."` instead — that uses whatever the current gateway config says. But the gateway is currently broken (`ImportError: cannot import name 'fast_safe_load'` from `utils` in the installed hermes-agent tree) so this is not viable until repaired. Until then, the only working approach is to keep the script free of LLM calls (pure Python chain_calc).

**Verification recipe (use this to check if a provider is script-callable):**
```python
import json, urllib.request, os
req = urllib.request.Request(
    f"{base_url}/v1/chat/completions",
    data=json.dumps({"model": model, "messages": [...], "max_tokens": 10}).encode(),
    headers={"Authorization": f"Bearer {os.environ[api_key_env]}"},
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print("CALLABLE")
except urllib.error.HTTPError as e:
    print(f"BLOCKED: HTTP {e.code} {e.read()[:200]}")
```

## User Workflow Preferences (Reinforced 2026-07-04)

1. **Don't be "kedekut" with verification tools.** When in doubt, run live tests (curl, python, browser_navigate) to verify provider behavior, API formats, etc. — don't ask the user to confirm things that can be verified. Boss was explicit: "kalau semua benda termasuk benda kecik pun kau 'kedekut' nak guna tools, baik takpayah la."

2. **Don't fabricate provider lists from memory.** The user has 3 specific providers configured (deepseek, opencode-go, opencode-zen). Always check `~/.hermes/config.yaml` to confirm the current model/provider before proposing any LLM-related work. Never default to OpenAI/Anthropic/OpenRouter boilerplate when the user's actual stack doesn't include them.

3. **Q&A first, execute after — but don't over-clarify.** When the user has given a clear directive ("buat je la step 1", "proceed"), don't ask additional confirmation questions for things that are obvious next steps. Execute, verify, report. Reserve clarification questions for genuinely ambiguous decisions.

4. **Treat user-corrections as single-issue scope, not system overhaul approval.** Reinforced in this session: a user correction about a specific timing/value is NOT approval to execute a multi-file plan you've outlined. Acknowledge the correction, ask scope, only proceed with full plan after explicit "yes do everything."

## Daily Dose Summary (v3)

`chain_calc.py --summary` shows all doses for today with actual mg values, timing, and conditions. Designed for morning briefing delivery.

**Output format:**
```
💊 MED DOSES TODAY (2026-07-05)

A — Akurit-4 + Pyridoxine
  Akurit-4: 4 tablet (perut kosong)
  Pyridoxine: 3 tablet / substitute
  Masa: ~6:00-7:30am

B — Levetiracetam + Dexamethasone #1
  Levetiracetam: 500mg (1 tab)
  Dexamethasone: 5mg
  Masa: ~8:00am (min 1h gap dari A)

C — Dexamethasone #2 + Calcium + Calcitriol
  Dexamethasone: 5mg
  Calcium Carbonate: 500mg
  Calcitriol: 1 tablet
  Masa: ~12:00pm (4h gap dari B)
  Cara: layered (nasi > ubat > nasi)

D — Dexamethasone #3
  Dexamethasone: 4mg
  Masa: ~4:00pm (4h gap dari C)

E — Levetiracetam (malam)
  Levetiracetam: 500mg (1 tab)
  Masa: ~8:00pm (~12h gap dari B)

Dexa total hari ni: 14mg (TDS)
Next dose change: 9 hari lagi
```

**Usage:** Can be integrated into morning briefing cron or delivered on-demand.

## Appointment Tracking (v3)

`med_appointments.py` tracks medical appointments and links them to tapering phases.

**CLI:**
```bash
python3 med_appointments.py --upcoming           # Next appointment
python3 med_appointments.py --all                # All appointments
python3 med_appointments.py --add "2026-08-06" "IPR" "Follow-up" "notes"
python3 med_appointments.py --check-tomorrow     # Alert if appointment tomorrow
python3 med_appointments.py --check-today        # Alert if appointment today
python3 med_appointments.py --complete <id>      # Mark as completed
```

**Cron:** `med_appointments.py --check-tomorrow` runs daily at 20:00 MYT. Silent when no appointment tomorrow.

**Data format (appointments.json):**
```json
{
  "appointments": [
    {
      "id": 1,
      "date": "2026-07-06",
      "time": null,
      "location": "IPR",
      "purpose": "TB Meningitis follow-up + medication refill",
      "notes": "Pyridoxine habis — need refill",
      "linked_taper_phase": 5,
      "status": "upcoming",
      "reminder_sent": false
    }
  ]
}
```

## Taper Engine (v3 — Date-Dependent Dosing)

Dexamethasone follows a tapering schedule (Tb Meningitis regime: 1mg/2 weeks, starting 0.3mg/kg = 18mg). The taper engine in `chain_calc.py` reads `dexa_taper.json` and auto-adjusts doses based on the current date.

**Key functions in chain_calc.py:**
- `get_current_phase()` — returns phase dict for today's date
- `get_next_phase()` — returns the upcoming phase
- `get_dexa_dose_for_slot(slot)` — returns mg for B/C/D based on current phase
- `get_dexa_total_mg()` — returns total daily dose
- `get_dexa_freq()` — returns TDS/BD/OD/STOP
- `get_days_until_next_phase()` — days until dose change
- `is_slot_active_for_dexa(slot)` — checks if slot is active for current phase

**CLI:**
```bash
python3 chain_calc.py --taper           # JSON taper info
python3 chain_calc.py --taper-display   # Human-readable taper status
python3 chain_calc.py --summary         # Daily dose summary with mg values
python3 chain_calc.py --display         # Chain display (A ✅ → B ✅ → C ~12:00)
```

**Reminder templates now include actual mg:** e.g. "Dexa #1 (5mg)" instead of just "Dexa #1"

**Taper alert cron:** `taper_alert.py` runs daily at 06:00 MYT via no_agent cron. Silent when no transition imminent. Alerts when dose change is within 3 days.

**Weekly compliance cron:** `med_report.py` runs every Sunday at 10:00 MYT via no_agent cron. Shows per-slot compliance %, supply warnings, taper status.

**Appointment reminder cron:** `med_appointments.py --check-tomorrow` runs daily at 20:00 MYT via no_agent cron. Alerts if appointment the next day. Silent otherwise.

## Supply Tracking (v3)

`med-supply.json` tracks pill inventory per drug. `med_confirm.py` auto-decrements supply on each confirmation.

**CLI:**
```bash
python3 med_supply.py --check           # All drugs supply status
python3 med_supply.py --check akurit_4  # Specific drug
python3 med_supply.py --low             # Only drugs below warning threshold
python3 med_supply.py --warnings        # Human-readable warnings
python3 med_supply.py --refill akurit_4 90  # Refill to 90 pills
python3 med_supply.py --set akurit_4 30     # Set to exact value
```

**Supply alerts are SUPPRESSED for the slot being confirmed** — `confirm_slot()` only shows supply alerts for drugs NOT in the current slot. Rationale: user just took these drugs, they know about the stock situation. Alerting "STOCK OUT: Pyridoxine" on a drug they literally just confirmed is confusing noise. Only alerts for OTHER slots' issues are surfaced.

**Pitfall — supply data goes STALE after IPR visit:** After an IPR visit or pharmacy refill, `med-supply.json` stays at old values until manually updated via `--refill`. A 2026-07-07 incident: user went to IPR (restocked everything) but supply JSON still showed Pyridoxine=0, causing a false "STOCK OUT" alert for a different slot. When user says they went to IPR / got refill, ALWAYS offer to update supply counts. Do NOT trust supply JSON to be current after an appointment — user must explicitly confirm new counts before updating.

**When supply is low/out (other slots):** `med_confirm.py` returns `supply_alert` in its JSON output. Chain monitor can include supply warnings in reminders.

## Interaction Checking (v3)

`med-interactions.json` contains safety data for all drugs in the regimen. `med_interact.py` validates drug combinations.

**CLI:**
```bash
python3 med_interact.py check pyridoxine akurit_4  # Check pair
python3 med_interact.py validate                     # Validate FULL regimen
python3 med_interact.py info akurit_4                # Drug info + timing rules
python3 med_interact.py rules                        # Global timing rules
```

**Critical lesson (2026-07-05):** When user asks about drug interactions, ALWAYS check against the FULL regimen, not just the drug in question. User explicitly corrected: "Situasi dia bukan aku makan ubat tu je, aku makan banyak jenis ubat, timing, jenis ubat, kesesuaian, dan lain lain semua tu kena fikir." Use `med_interact.py validate` to check all 45+ drug pairs at once.

## Dynamic Slot Management (v3)

Slots auto-deactivate based on the current tapering phase:
- **TDS (3x/day):** A, B, C, D, E all active
- **BD (2x/day):** A, B, C, E active — D deactivated
- **OD (1x/day):** A, B, E active — C, D deactivated
- **STOP:** A, E only

Inactive slots show as "—" in chain display and don't trigger reminders.

**Note:** BD phase has a 2pm dose that doesn't map to any existing slot. This is handled by slot B's reminder showing the BD morning dose, and the 2pm dose needs a separate mechanism (future enhancement).

## Substitution Database (v3)

`substitutions.json` maps drugs to safe alternatives. Key data:
- Pyridoxine → Swisse Ultiboost B-Complex (41.1mg B6, sufficient for INH prophylaxis)
- Prescription-only drugs (Akurit-4, Levetiracetam, Dexamethasone, Calcitriol) have NO OTC substitutes

**CLI:**
```bash
python3 med_substitute.py pyridoxine   # Query substitutes
python3 med_substitute.py --otc        # Only drugs with OTC alternatives
```

## Key Lessons Learned (2026-07-05 Session)

1. **"Whole picture" interaction checking:** Never check a single drug pair in isolation. User has 5+ concurrent medications — always validate the FULL regimen. Use `med_interact.py validate`.

2. **"CONFIRM EH?" signal:** When user asks this, they want verification from authoritative sources (MSD Manual, drug interaction databases), not just reasoning. Try multiple sources before answering.

3. **Tier/Phase execution:** When building a multi-task system, work sequentially — one task at a time, verify, show output, get confirmation, then next. Don't try to do everything at once.

4. **IPR supply miscalculation:** If medication runs out before appointment, it's the prescriber's error, not the system's. But the system should still track supply and warn proactively.

5. **Dexa tapering is complex:** 21 phases over ~9 months, switching from TDS→BD→OD. Each phase changes which slots are active and what doses apply. The taper engine handles this automatically.

## Gap Tolerance & Dose-Spacing Research (2026-07-08)

When user asks "boleh ke closer the gap?" between divided corticosteroid doses, the answer is context-dependent on the drug's half-life and prescription class:

- **Dexamethasone divided doses**: Standard references (NIH MedlinePlus, Medical News Today) specify "taken in divided doses" or "dosing schedule your doctor prescribes" — they do NOT mandate an exact hour gap. The 4h spacing in the user's TB meningitis taper (TDS 8/12/4) is from the prescribing doc's protocol, not a universal pharmacological hard-rule.
- **Dexa biological half-life = 36–54h** (Wikipedia pharmacokinetic data). Level in body does NOT drop sharply between doses, so ±40 min gap variance is pharmacologically minor — unlike short-half-life drugs where exact spacing matters.
- **Verified sources that worked**: medicalnewstoday.com/articles/drugs-dexamethasone-oral-tablet (full dose section accessible), medlineplus.gov/druginfo/meds/a682792.html (NIH, accessible).
- **Blocked by bot detection (do NOT rely on, do NOT claim as verified)**: drugs.com (Access Denied — region/network block), mayoclinic.org (Access Denied), medscape.com (Cloudflare challenge), ncbi.nlm.nih.gov/books (Abuse block). These are NOT "broken" — they block automated agents. For a real need, tell user to check manually or use a different path.
- **Recommendation shape when user wants earlier last dose**: If compressing B→C gap (e.g. 3h17m instead of 4h), propagate the shift forward: C earlier → D earlier (maintain 4h from C) → E independent (based on B+12h). Don't leave downstream slots on old times. Always end with "confirm with prescribing doctor before making it a habit" — tapering regimes are doc-controlled.

**Pitfall — Don't overclaim spacing safety from a single source:** When only 1-2 patient-info sites mention "divided doses" without exact interval, label it UNVERIFIED for the specific gap question. The user's doc protocol (4h) is the authoritative constraint; public drug-info pages describe general practice, not his specific taper. Distinguish "pharmacologically tolerable" from "prescribed protocol compliance."

## See Also

- `references/makan-ambiguity-ask-dont-assume.md` — 2026-07-22: Malay "makan" food-vs-med. Ask once; never assume food or silent-log.
- `references/time-based-slot-auto-mapping.md` — 2026-07-07: don't invent slot from time alone.
- `references/med-confirm-fuzzy-bug-20260712.md` — 2026-07-12 incidents: fuzzy drug-level confirm corrupts other slot drugs, VPS clock drift, and failed verification of the dexamethasone-calcium carbonate chelation claim.
- `references/taper-data-validation.md` — validation script + history of taper phase arithmetic mismatches found 2026-07-05
- `references/cron-delivery-verification.md` — proof that no_agent cron delivers chat messages (not silent)
- `references/drug-level-upgrade.md` — detailed migration notes, drug ID convention, fuzzy matching table, chain timing decisions
- `references/architecture.md` — full system architecture with cron layout, file details, testing
- `references/chain-calc-bug.md` — trace of Bug #1 (partial slot firing at wrong time), root cause code, and fix
- `references/medication-substitution.md` — whole-regimen substitution verification: when a prescribed drug runs out and user asks about an OTC/alternative. Covers risk assessment, ingredient verification, cross-check against ALL concurrent drugs (not just pairwise), timing, and the "CONFIRM EH?" signal.
- `references/session-db-recovery.md` — reusable SQLite recipe to recover "what did we say on date X / what does shorthand Y mean" from `~/.hermes/state.db` BEFORE answering from memory. Used to resolve the CC/CCC shorthand failure (2026-07-09).
- `references/med-status-stale-data-trace.md` — verified grep/stat/DB recipe for tracing unexplained "taken HH:MM" values in med-status.json (stale prior-session data via missing day-boundary reset). Use BEFORE asking the user where data came from.
- `references/chain-calc-bugs.md` — combined trace of Bug #1 + Bug #3 + Bug #6 with live CLI output and verification recipe
- `references/cooldown-system.md` — cooldown implementation details, edge cases, chain-event flow, verification recipe, and **manual-test pollution pitfall** (don't run chain_monitor.sh against real state to test — use --next only or sandbox the state file)
- `references/taper-engine.md` — taper engine architecture, dexa_taper.json format, dynamic slot management, CLI usage
- `references/appointment-tracking.md` — appointment tracker architecture, IPR workflow, cron integration
- `references/day-boundary-reset.md` — Bug #7 trace: cross-day reminder count contamination, root cause code, day-boundary reset mechanism, verification recipe
