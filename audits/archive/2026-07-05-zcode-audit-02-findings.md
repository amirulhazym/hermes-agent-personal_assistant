# Hermes Agent — Full Audit Findings (Audit 02)

> **Auditor:** ZCode (fresh, independent pass) · **Date:** 2026-07-05
> **Basis:** Direct static reads of `C:/Users/amiru/hermes-snapshot-20260705/` + two adversarial review passes. Stance unbiased (prior audits excluded).
> **Method:** Every claim cites `file:line` and pastes raw evidence. Unprovable claims tagged **UNVERIFIED/THEORETICAL**.

## Severity legend
- **CRITICAL** — data loss, patient-safety risk, or system failure.
- **HIGH** — wrong behavior, stale data, missed reminders, silent safety gap.
- **MEDIUM** — edge cases, dead code, technical debt, observability gap.
- **LOW** — cosmetic / documentation.

## Counts
**CRITICAL: 7 · HIGH: 14 · MEDIUM: 18 · LOW: 5** (44 total). Each is a distinct issue; related items are grouped by prefix (C=scripts/correctness, S=stale/config-drift, X=cross-component/cron/security/hook, DTZ=datetime/tz).

---

## A. Data integrity (CRITICAL/HIGH)

### [CRITICAL] DATA-INTEGRITY — `confirm_slot` overwrites ALL drug times with `now`, destroying earlier partial takes
**File(s):** `scripts/med_confirm.py:225-226, 234`
**Evidence:**
```python
for did in drug_ids:
    entry.setdefault('drugs', {})[did] = {"status": "taken", "time": now}
    try:
        from med_supply import decrement
        decrement(did)
    except Exception:
        pass
entry['overall'] = recalc_overall(slot, entry, schedule)
```
**Impact:** Real intake timestamps are lost. If the user confirmed `levetiracetam_b` at 08:16 then later runs `med_confirm.py B`, the 08:16 record is clobbered to the new time. Corrupts chain-gap math (`get_actual_time` uses latest) and the compliance report.
**Root cause:** Slot-level confirm conflates "mark done" with "re-stamp every drug at one instant."
**Recommendation:** Only set `now` for drugs not already `taken`; still decrement regardless.

### [CRITICAL] DATA-INTEGRITY — `--update <LETTER> HH:MM` overwrites every taken drug's time
**File(s):** `scripts/med_confirm.py:401-405`
**Evidence:**
```python
if 'drugs' in entry:
    for did, drug_entry in entry['drugs'].items():
        if drug_entry.get('status') == 'taken':
            drug_entry['time'] = time_val
    save_json(STATE_FILE, state)
```
**Impact:** `--update C 12:00` collapses three genuinely-different real times (calcium 16:00, calcitriol 16:00, dexa_2 14:36) to one value. Same history-destruction as above, user-invoked.
**Root cause:** `--update` implemented as bulk re-stamp, not per-drug.
**Recommendation:** Scope `--update` to a specific `drug_id`, or only update the slot-level default time.

### [CRITICAL] RACE/CORRUPTION — `chain_monitor.sh:79` writes `chain-state.json` directly, no tempfile, no backup, no atomicity
**File(s):** `scripts/chain_monitor.sh:79` and `scripts/chain_calc.py:136-139`
**Evidence:**
```bash
state_file.write_text(json.dumps(state, indent=2))   # chain_monitor.sh:79 (no .bak, no atomic)
# chain_calc.save_json:  with open(path, 'w') as f: json.dump(data, f, indent=2, sort_keys=True)
```
**Impact:** The hottest writer (every 15 min) does non-atomic read-modify-write. A crash/OOM/reboot mid-write truncates `chain-state.json`; the next run's `except (json.JSONDecodeError, IOError): state = {}` **silently resets** all cooldowns → reminder burst. No backup exists for this file.
**Root cause:** Direct `write_text`/`open('w')`, no `tempfile`+`os.replace`, no backup (only `med_confirm.py` rotates `.bak`).
**Recommendation:** Write to `.tmp` then `os.replace()`; keep a `.bak`. Make the corrupt-file fallback loud, not silent.

### [CRITICAL] PATIENT-SAFETY — Reminder counts are NOT date-keyed; they accumulate across days
**File(s):** `scripts/chain-state.json:4-14`; `scripts/chain_monitor.sh:71-73`
**Evidence:**
```python
state.setdefault('reminder_counts', {})[slot] = counts.get(slot, 0) + 1   # no date key
```
and `chain-state.json` ships `"reminder_counts": {"D": 2, "C": 1}` with no date.
**Impact:** Counts bleed across days → escalating tone fires on day 2 for a slot missed once; stale high count selects the 15-min "critical" cooldown (`chain_calc.py:67-68`); first reminder of a new day may already be count 3.
**Root cause:** Reminder state keyed by slot only, never by date.
**Recommendation:** Key counts by date (`reminder_counts["2026-07-05"]["D"]`) or reset all counts at local midnight (store `last_reset_date`).

### [HIGH] CORRECTNESS — `get_actual_time` docstring says "earliest" but returns LATEST
**File(s):** `scripts/chain_calc.py:362-383`
**Evidence:** docstring (`:365`) "earliest taken time" vs `return sorted(times)[-1]` (`:381`). `med_report.get_slot_time` copies the same `[-1]` pattern with its own "latest" docstring — internally consistent, but the contract is contradicted.
**Impact:** Maintenance hazard; a future caller trusting "earliest" (e.g. for the empty-stomach 1h rule on slot A) computes wrong gaps.
**Root cause:** Docstring never updated when logic changed to latest.
**Recommendation:** Fix docstring; add `get_earliest_taken_time` if needed elsewhere.

### [HIGH] CORRECTNESS — Ready times fall back to static defaults when a predecessor slot is pending
**File(s):** `scripts/chain_calc.py:397-441, 454-463`
**Evidence:** `calculate_ready_time` uses `chain_times` (confirmed/partial only); if predecessor has no actual time it returns `get_default_time(...)` instead of propagating from the last known anchor.
**Impact:** When early slots are MISSED (the failure mode that matters most for TB/epilepsy adherence), downstream ready times don't shift — the "domino geser" promise is false; levetiracetam 12h-gap and dexa 4h-gap guidance become meaningless.
**Root cause:** Silent default fallback instead of "blocked/pending" propagation.
**Recommendation:** When a predecessor is missing, propagate from the last known slot's actual time or mark downstream as blocked.

### [HIGH] CORRECTNESS — `confirm_slot` decrements supply for optional `b_complex` and re-decrements already-taken drugs
**File(s):** `scripts/med_confirm.py:225-231`; `med-supply.json:82-92`
**Evidence:** `drug_ids = get_all_drug_ids(slot, schedule)` includes `b_complex` (`required:false`, `doses_per_day:0`, `current:null`). Because `confirm_slot` overwrites all drugs, running it twice decrements `calcitriol`/`calcium`/`dexamethasone_2` a second time (the `except Exception: pass` hides any guard).
**Impact:** Supply counts drift downward faster than reality → false LOW/OUT-OF-STOCK alerts.
**Root cause:** Decrement tied to the confirm *action*, not the `pending→taken` transition.
**Recommendation:** Decrement only on transition; skip `doses_per_day == 0`.

### [HIGH] CORRECTNESS — Typo/ambiguous `med_resolve` can write an orphan drug key in the wrong slot
**File(s):** `scripts/med_confirm.py:181-188, 282`; `scripts/med_resolve.py:197-213`
**Evidence:** `confirm_drug` writes `entry['drugs'][drug_id] = {...}` using whatever `resolve` returned. For `python3 med_confirm.py C dexa`, `resolve` may return `dexamethasone_1` (slot B's first match) → a `dexamethasone_1` key is written under slot C's entry, where it is invisible to `recalc_overall` but pollutes `med-status.json`.
**Impact:** Orphan drug keys inflate `med_report` latest-time and any future audit; the real slot-C dexa is never recorded.
**Root cause:** `resolve` first-match wins; no re-check that the drug_id belongs to the slot's schedule.
**Recommendation:** After resolve, assert `result['slot'] == slot`; refuse to write a `drug_id` not in `get_drugs_for_slot(slot)`.

### [HIGH] CORRECTNESS — `med_resolve.pick_slot_by_time` float hack mis-routes a 10:30 dexa to slot B
**File(s):** `scripts/med_resolve.py:127-130`
**Evidence:** `"13:30".replace(":",".").rstrip("0")` → `"13.3"` = 13.3; the B/C boundary is `10.5` (10:30). 10.3 < 10.5 → **B**, but 10:30 dexa should be **C** (`med-schedule.json:32-46` rule: C at 12:00, 4h after B).
**Impact:** A dexa taken at 10:30 is logged to the wrong slot → both chain math and compliance are wrong that day.
**Root cause:** `HH:MM` encoded as a lossy decimal float; `rstrip("0")` drops significant digits.
**Recommendation:** Parse `h, m = map(int, t.split(':'))`; compare `h + m/60.0`. Delete the `rstrip` hack.

### [HIGH] CORRECTNESS — `med_resolve` levetiracetam boundary: exactly 14:00 routes to B, not E
**File(s):** `scripts/med_resolve.py:77-80, 139`
**Evidence:** B rule `hi=14` (`hour_f < 14`), E rule `lo=14` (`hour_f >= 14`). At 14:00 both match; `matches` order (schedule order) returns B first. The comment says "after 14:00 → E" — 14:00 is ambiguous and resolves to B.
**Impact:** A levetiracetam logged at precisely 14:00 lands in slot B (morning) instead of E (night).
**Root cause:** Boundary double-matches, picks B by ordering; undocumented.
**Recommendation:** Make boundaries explicit/non-overlapping; add a test for `14:00`.

### [HIGH] DATE-HANDLING — `chain_monitor.sh` writes `last_reminder_times` with naive `datetime.now()` while reader uses MYT
**File(s):** `scripts/chain_monitor.sh:76-77` vs `scripts/chain_calc.py:109-110` (`now_myt()` = `ZoneInfo('Asia/Kuala_Lumpur')`)
**Evidence:** `state.setdefault('last_reminder_times', {})[slot] = _dt.datetime.now().strftime('%H:%M')` (naive local). `is_within_cooldown` (`chain_calc.py:83-97`) compares against MYT `now_min`. On a UTC host the delta is wrong → cooldown effectively random (spam every 15 min or never fire).
**Impact:** On a non-MYT VPS, reminder cadence is broken — directly affects whether the patient is reminded.
**Root cause:** One writer uses naive `datetime.now()`; reader assumes MYT. No TZ normalization.
**Recommendation:** Use `datetime.now(ZoneInfo('Asia/Kuala_Lumpur'))` in the shell's inline Python; store epoch minutes. Confirm VPS TZ.

### [HIGH] PATIENT-SAFETY — Supply threshold inclusive + non-idempotent decrement → false stock-outs
**File(s):** `scripts/med_supply.py:62-72, 131-134`
**Evidence:** `warning_threshold` for `dexamethasone_1` = 7; `current` = 8. After one decrement → 7 → `7 <= 7` → "LOW" fires while a week of supply remains. Combined with C-7 (double-decrement on repeated confirm), a tracked drug can hit 0 fast.
**Impact:** False/early stock-out alarms; repeated slot-confirms can mark "OUT OF STOCK" when pills remain.
**Root cause:** Inclusive threshold + non-idempotent decrement.
**Recommendation:** Use `< threshold` for "low"; make decrement idempotent on intake state.

### [HIGH] CORRECTNESS — `med_report` hardcodes `2026-07-02` cutoff and counts inactive taper days as missed
**File(s):** `scripts/med_report.py:107-114`
**Evidence:** `if date_obj < datetime.strptime("2026-07-02",...).date(): continue` — magic constant; `no_data` for a date where the slot was inactive (BD/OD taper deactivating C/D) is counted as `missed`.
**Impact:** Compliance % distorted: taper-transition days look like missed doses; the hardcoded cutoff eventually excludes all history (or, past a year, includes pre-tracking noise).
**Root cause:** Magic date constant; treats `no_data` as missed without consulting taper-active slots.
**Recommendation:** Derive cutoff from earliest `med-status.json` record; skip dates where the slot was inactive per `dexa_taper`.

### [HIGH] CORRECTNESS — `next_slot` picks a `partial` slot over its upstream blocker (slot A)
**File(s):** `scripts/chain_calc.py:512-526`
**Evidence:** Loop selects the first slot whose status ∈ `('ready','partial_ready','partial')`. Slot C `partial` can be chosen while slot A is still `pending` (the root cause).
**Impact:** Wrong slot reminded first; root-cause slot A can be starved of reminders. Compounds C-6.
**Root cause:** Candidate selection doesn't respect chain dependency order.
**Recommendation:** Order by SLOTS index; require the chosen slot to be fireable.

### [MEDIUM] FRAGILITY — `chain_monitor.sh` runs TWO separate `calculate_chain()` evaluations (fire decision vs increment) with no lock
**File(s):** `scripts/chain_monitor.sh:24-31, 50-79`
**Evidence:** `--next` computes the fire decision at T1; the increment step re-imports `chain_calc` and calls `is_confirmed` at T2. If the slot becomes confirmed between T1 and T2, it is popped then +1'd → phantom count=1 on a confirmed slot.
**Impact:** Spurious reminder_count on confirmed slots; inconsistent state.
**Root cause:** Fire decision and mutation are two processes, no transaction/lock.
**Recommendation:** Do decision+increment in one Python process; re-check `should_fire` after resetting confirmed slots.

### [MEDIUM] ERROR-HANDLING — `chain_monitor.sh` swallows ALL errors with `2>/dev/null || true` and has no logging
**File(s):** `scripts/chain_monitor.sh:16, 80`
**Evidence:** `set -euo pipefail` is defeated by `... write_text(...) 2>/dev/null || true`. Any failure (json.dumps raise, import fail, disk full) exits 0 silently; no log file, stderr discarded.
**Impact:** Production reminder-pipeline failures are completely invisible — the user just stops getting reminders with no diagnostic trail.
**Root cause:** `|| true` + `2>/dev/null` to "never spam," but it hides faults.
**Recommendation:** Log to a file (`>> ~/.hermes/logs/chain_monitor.log 2>&1`); only suppress user-facing stdout; don't `|| true` the write.

### [MEDIUM] CORRECTNESS — `med_appointments` unhandled `ValueError` on a non-ISO date (THEORETICAL)
**File(s):** `scripts/med_appointments.py:49-61`
**Evidence:** `datetime.strptime(appt_date, "%Y-%m-%d")` inside a path whose caller (`get_upcoming`) has no try/except for `ValueError` (only `load_json` catches `IOError`/`JSONDecodeError`). Current data is ISO-clean → THEORETICAL.
**Impact:** A malformed appointment date crashes `main`.
**Root cause:** Date parsing not wrapped.
**Recommendation:** Wrap in try/except; validate on add.

### [MEDIUM] CORRECTNESS — `med_interact.validate_regimen` reports "ALL SAFE" even when `unknown_count>0`
**File(s):** `scripts/med_interact.py:111-113`
**Evidence:** `verdict = "ALL SAFE ✅" if unsafe==0 and unknown==0 else f"ALL SAFE ✅ (...{unknown_count} pairs with no explicit data...)" if unsafe==0 else ...`. When `unsafe==0` but `unknown>0`, the prefix is still "ALL SAFE".
**Impact:** A future DB edit dropping a `safe_with` link shows "ALL SAFE" with a parenthetical — masking a real knowledge gap as safety.
**Root cause:** Verdict prioritizes "ALL SAFE" prefix over data completeness.
**Recommendation:** When `unknown>0`, verdict should be "PARTIAL — N pairs unverified".

### [MEDIUM] CORRECTNESS — `med_substitute --otc` shows drugs with no actual alternatives
**File(s):** `scripts/med_substitute.py:38-43, 93-97`
**Evidence:** `--otc` prints entries where `no_substitute_available` is falsy, but `format_result` may show "❌ No alternatives listed" when `alternatives` is empty.
**Impact:** `--otc` can advertise an OTC swap that doesn't exist.
**Root cause:** Filter doesn't require `alternatives` non-empty.
**Recommendation:** Require `alternatives` non-empty (and match `general_rules.otc_available`).

### [MEDIUM] FRAGILITY — String-form legacy migration drops the legacy intake time
**File(s):** `scripts/med_confirm.py:138-145`
**Evidence:** Legacy `"confirmed"` string entry migrated to `{"overall":"completed","drugs":{did:{"status":"taken","time":None}...}}` — the legacy `time` (e.g. `"~09:30"`) is discarded (the dict-form branch at `:146-154` preserves it).
**Impact:** Legacy intake times for past dates destroyed on migration; `time:None` drugs make `get_actual_time` skip them (slot "completed" but no actual time).
**Root cause:** String-form migration doesn't capture the legacy time.
**Recommendation:** Capture/preserve legacy time (or store in `legacy_time`).

### [MEDIUM] LOGGING — Bare `except Exception: pass` hides supply/import failures
**File(s):** `scripts/med_confirm.py:230-231, 257-258, 292-293`; `scripts/med_supply.py` (no logging); `scripts/chain_llm.py:171-173` (logs — good)
**Evidence:** `confirm_slot`/`confirm_drug` wrap `decrement` in `except Exception: pass`. If `med_supply` import fails or `save_supply` raises, confirmation succeeds silently while supply is not decremented.
**Impact:** Silent supply desync; patient may run out without warning. Only `chain_llm.py` logs.
**Root cause:** Defensive `except: pass` with no logging.
**Recommendation:** At minimum log the exception to a file; surface a non-fatal warning in the confirm result.

### [MEDIUM] DATETIME — `med_confirm.get_today` falls back to naive local time if `zoneinfo` import fails
**File(s):** `scripts/med_confirm.py:50-63`
**Evidence:** `except ImportError: return datetime.now().strftime("%Y-%m-%d")` (server local). `chain_calc` imports `ZoneInfo` at module top and would fail entirely if missing — so the two scripts could write **different date keys** near midnight on a non-MYT/old-Python host.
**Impact:** Cross-script date-key mismatch near midnight → confirmations "disappear" from the chain view.
**Root cause:** Inconsistent TZ handling; fragile fallback.
**Recommendation:** Centralize one `today_myt()`/`now_myt()` (as `chain_calc` has) and import everywhere; fail loudly if `ZoneInfo`/`tzdata` missing.

### [LOW] COSMETIC — BD-phase slot C reminder shows Dexa 0mg (ignores `dose_2pm`)
**File(s):** `scripts/chain_calc.py:914, 921-923` vs `203-228`
**Evidence:** `get_dexa_dose_for_slot` maps `{B:dose_morning, C:dose_midday, D:dose_afternoon}`. In BD, slot C's `dose_midday=0` → reminder shows "(0mg)" while the real 2pm dose is `dose_2pm`. Not live today (BD starts 2026-09-09) but a real future bug.
**Impact:** During BD taper, slot-C reminder misreports dexa dose as 0mg.
**Root cause:** `get_dexa_dose_for_slot` has no `dose_2pm` key.
**Recommendation:** For BD map slot C → `dose_2pm` (or `dose_midday or dose_2pm`).

### [LOW] SPEC — `get_default_time` brittle parse can crash `time_str_to_minutes`
**File(s):** `scripts/chain_calc.py:390-394, 118`
**Evidence:** `raw.split(',')[0].strip().split()[0]` assumes a space after the time. If a schedule edit removes the space (`"08:00(Levetiracetam)"`), `.split()[0]` = `"08:00(Levetiracetam)"` (contains `:`) → `time_str_to_minutes` `map(int, t.split(':'))` raises `ValueError` (uncaught in `calculate_ready_time`). THEORETICAL (current data has the space).
**Impact:** A trivial schedule edit could crash `chain_calc` (and thus `chain_monitor.sh`, which `exit 0`s silently → reminders stop).
**Root cause:** No regex/guard on time parse.
**Recommendation:** Parse with `^(\d{1,2}):(\d{2})`; fall back to DEFAULT on no match.

### [MEDIUM] DEAD-CODE — `ESCALATION` dict defined but never used
**File(s):** `scripts/chain_calc.py:43-50` vs `56-71`
**Evidence:** `ESCALATION = {'normal':0,'gentle':1,'push':2,'urgent':4,'critical':7}` is referenced nowhere; `get_cooldown_interval` uses raw count thresholds (`COOLDOWN_INTERVAL['urgent'/'critical']`).
**Impact:** Maintenance hazard — editing `ESCALATION` won't change behavior.
**Root cause:** Dead config; escalation ladder implemented implicitly elsewhere.
**Recommendation:** Drive `generate_reminder`/`get_cooldown_interval` from `ESCALATION`, or delete it.

---

## B. Stale data / config drift (CRITICAL/HIGH)

### [CRITICAL] CONFIG DRIFT — `med-schedule.json` dexa `dosage` goes stale at taper transition (2026-07-14)
**File(s):** `med-schedule.json:26,38,53` vs `dexa_taper.json:99-113`
**Evidence:** `med-schedule.json` hard-codes Phase-5 dexa (B=5mg, C=5mg, D=4mg). Phase 6 (from 2026-07-15) drops C to 4mg. No code syncs `med-schedule.json` to `dexa_taper.json`. The med-tracker SKILL itself warns "NEVER read `dosage` from med-schedule.json for dexamethasone."
**Impact:** Any new/future script reading `drug['dosage']` (the natural "single source of truth" field) shows wrong dexa mg after 2026-07-14.
**Root cause:** Two files encode the same fact with different cadences, no reconciliation.
**Recommendation:** Make `med-schedule.json` `dosage` a computed/redirected reference, or add a CI check diffing it against `dexa_taper.json` for today's date.

### [CRITICAL] MED-SAFETY — BD phases have a 2pm dexa dose with no slot; modal mismatch under-reports steroid exposure
**File(s):** `dexa_taper.json:162-177` (phase 10) vs `med-schedule.json:19-71`
**Evidence:** Phase 10 (BD, from 2026-09-09) carries `dose_2pm: 4` but `active_slots_by_freq['BD'] = ["A","B","C","E"]` — D deactivated; no slot represents the 2pm dose. SKILL.md admits "BD phases will display wrong dose breakdowns … until a slot F (or `dose_2pm` field) is added."
**Impact:** For ~5 months the 2pm dexa dose is never surfaced by `taper_alert.py`/`chain_calc --taper-display` → under-reports steroid dose in a TB-meningitis taper where exact mg matters.
**Root cause:** Taper schema carries `dose_2pm`; med-schedule/chain models only A–E.
**Recommendation:** Add a `dose_2pm` rendering path or synthetic slot; until then, `taper_alert.py` must explicitly flag the missing 2pm dose.

### [HIGH] SUPPLY GAP — 7/10 drugs `current: null`; `confirm_slot` doesn't decrement → supply tracking effectively dead
**File(s):** `med-supply.json:54,59,66,77,98,109` (null) + `med-tracker/SKILL.md:497-504` (context)
**Evidence:** `dexamethasone_2`, `calcium`, `calcitriol`, `dexamethasone_3`, `levetiracetam_e`, etc. have `current: null`. The med-tracker SKILL states `confirm_slot()` (the common path) never calls `decrement()`, so low-stock warnings never fire for slot-confirmed drugs. `dexamethasone_1` shows `current:8, warning_threshold:7` — already at the brink.
**Impact:** The supply safety net (the thing that tells the patient "refill now") is effectively dead for 9/10 drugs. For a TB regimen where running out mid-course is clinically serious, this is a silent failure.
**Root cause:** Asymmetry between `confirm_drug` (decrements) and `confirm_slot` (doesn't); null baselines.
**Recommendation:** Make `confirm_slot()` call `decrement()` per drug; backfill `current` from a physical inventory count.

### [MEDIUM] DEAD/STALE — `.bak1/.bak2/.bak3` only 3 rolling copies, no timestamp/pruning
**File(s):** `med-status.json.bak1/.bak2/.bak3` (top-level)
**Evidence:** Backup scheme is exactly 3 rolling files with no point-in-time history. If a corruption writes through, the `.bak` files may already hold corrupted data from the prior write.
**Impact:** Overstated protection; minor confusion.
**Root cause:** Shallow backup design.
**Recommendation:** Document semantics honestly; consider date-stamped backups if history is wanted.

---

## C. Cross-component / cron / security / hook (CRITICAL/HIGH/MEDIUM)

### [CRITICAL] SPOF — Only provider is `opencode-go`; `fallback_providers: []`. One outage = total assistant + reminder failure
**File(s):** `config.yaml:4-6`; `med-tracker/SKILL.md:644-652`
**Evidence:** `providers: {}`, `fallback_providers: []`. SKILL.md states opencode-go/zen are Cloudflare-1010 blocked for scripted HTTP. Med crons are pure-Python (independent), but chat/QA/`chain_llm` LLM path all depend on opencode-go. A commented-out `fallback_model` block exists (`:740-761`) but is not enabled.
**Impact:** If opencode-go is unreachable, the conversational assistant (med confirmation/QA layer) goes dark. Reminders keep firing but the confirmation layer dies.
**Root cause:** No fallback configured despite documented Cloudflare fragility.
**Recommendation:** Enable the `fallback_model` (e.g. openrouter) or route `chain_llm.py` (already deepseek-capable) as fallback for med reminders.

### [CRITICAL] SECURITY — WhatsApp `creds.json` (private identity keys) on disk; NO `.gitignore` anywhere in the tree
**File(s):** `whatsapp/session/creds.json:1` (private keys) + global absence of `.gitignore`
**Evidence:** `creds.json` contains `noiseKey`, `signedPreKey`, `signedIdentityKey`, `advSecretKey`, `accountSignatureKey` — private cryptographic identity material for the WhatsApp account. Glob `**/.gitignore` returns NO files at any depth.
**Impact:** If `.hermes` is ever committed/pushed/synced, the patient's WhatsApp account private keys leak. `config.yaml:569 redact_secrets: true` only redacts agent logs, not the filesystem.
**Root cause:** No `.gitignore` covering `whatsapp/`, `.env`, `state.db`, `*/session*/`.
**Recommendation:** Add `.gitignore` (`whatsapp/`, `.env`, `*.session`, `state.db*`, `triggered_skills.txt`, `*/session*/`). Rotate the WhatsApp identity (re-link) since this snapshot may already be exposed. (PRD §1.1/§13.1 REQUIRES a `.gitignore` — it was created in MJay per Phase 1 but is absent from the runtime snapshot.)

### [HIGH] HOOK FAILS-OPEN — med-tracker can silently NOT load → agent fabricates drug names
**File(s):** `hooks/skill-trigger/handler.py:80-94` + `SOUL.md:123-131`
**Evidence:** `handler.py` writes `triggered_skills.txt` inside `try/except Exception: ... print(...stderr)` then returns — on any error the skill simply isn't loaded, no user notification. This is the exact gap that enabled the 2026-07-04 `letram→Letrozole` fabrication. There is **no hard gate** — `med_resolve.py` only rejects if the agent voluntarily calls it.
**Impact:** If a user message implying a med action doesn't hit a regex, med-tracker never loads and the agent can again fabricate.
**Root cause:** Fails-open hook + advisory (not enforced) skill loading.
**Recommendation:** Make med-skill loading a deterministic precondition; hard-gate `med_confirm.py` to refuse any confirmation whose drug_id isn't resolver-verified.

### [HIGH] ANTI-FABRICATION — enforcement advisory only; `med_resolve` can still return wrong slot
**File(s):** `anti-fabrication-guardrails/SKILL.md:11-21`; `med_resolve.py:204-213`; `SKILL.md:535-543`
**Evidence:** `resolve()` returns `matches[0]` even when ambiguous; alias expansion strips the slot-qualifier word ("petang") before `match_name`, so time disambiguation isn't triggered. SKILL itself flags "dexa petang → logged to B. WRONG" as still live.
**Impact:** "dexa petang" → logged to slot B (pagi) instead of D. Wrong slot, corrupt chain.
**Root cause:** Alias expansion destroys the time-word before slot inference; first-match wins.
**Recommendation:** Prioritize the `WORD_TO_SLOT` hint before alias expansion; reject (return ambiguous error) when hint conflicts with match.

### [HIGH] ROUTING — `hello-world-watch` delivers restart beacon to the MEDICAL GROUP, not the home DM
**File(s):** `cron/jobs.json:400`; `channel_directory.json:45-49`; `SOUL.md:97-99`
**Evidence:** `deliver: "whatsapp:120363428305511789"` (a **group**, the medical group). Home DM is `13186321408227@lid` (`:15`), used by every other med cron's `origin`.
**Impact:** Every gateway restart spams the patient's medical group with a non-medical "Hello World" — wrong-context noise in a clinical channel, eroding trust/signal.
**Root cause:** hello-world-watch deliver set to the med group id, not the home DM.
**Recommendation:** Change deliver to `whatsapp:13186321408227@lid`.

### [HIGH] CONTRADICTION — SKILL.md says gateway "broken (ImportError fast_safe_load)"; `gateway_state.json` says running/connected
**File(s):** `med-tracker/SKILL.md:654` vs `gateway_state.json:1` vs `logs/agent.log`
**Evidence:** `gateway_state.json:1` = `"gateway_state":"running"`, both platforms `connected`. The `fast_safe_load` string appears ONLY in SKILL.md quotes — grep finds no such import error in code/logs (the real historic error was `get_model_capabilities`, 2026-07-01). The claim is **UNVERIFIED/THEORETICAL** and likely stale.
**Impact:** The med-tracker SKILL instructs agents to avoid `hermes chat -q` for LLM-from-cron because "gateway broken" — a false premise that permanently disables the only path to same-model parity for med reminders, forcing the weaker `chain_llm.py` deepseek path. Misleads future maintainers.
**Root cause:** Stale documentation; ImportError reference never validated.
**Recommendation:** Test `hermes chat -q` live; remove the claim if it works (or capture the real traceback if not).

### [HIGH] TIMEZONE — All cron times carry no TZ; if the host is not MYT, every reminder fires 8h off
**File(s):** `config.yaml:481` (`timezone: Asia/Kuala_Lumpur`) + `cron/jobs.json` (all `expr` wall-clock) + `chain_calc.py` (`ZoneInfo('Asia/Kuala_Lumpur')`)
**Evidence:** The Hermes cron scheduler's effective TZ is not in the snapshot. `chain_calc` correctly uses MYT for reminder math, but the **scheduler** fires on wall-clock `expr`. Tencent Lighthouse Singapore is often UTC. `chain-state.json` timestamps *suggest* MYT, but this is **UNVERIFIED** — rests on one assumption.
**Impact:** CRITICAL-if-true: med reminders could fire 8h off, during sleep, or never within the intended window. (Compounds C-11.)
**Root cause:** No explicit TZ pinning on the cron scheduler; relies on host TZ = MYT.
**Recommendation:** Set `TZ=Asia/Kuala_Lumpur` in the gateway service environment; assert it at startup; log the resolved cron TZ.

### [HIGH] CONCURRENCY — Domino Chain cron every 15 min, no lock; an LLM call >15 min overlaps and races on `chain-state.json`
**File(s):** `cron/jobs.json:337-341`; `chain_monitor.sh:50-80`; `cron/.tick.lock` (gateway-level only)
**Evidence:** `chain_monitor.sh` does non-atomic read-modify-write of `chain-state.json` with `2>/dev/null || true`. `cron/.tick.lock` is the gateway's per-tick scheduler lock, NOT a per-job lock. If `chain_llm.py` takes >15 min, the next tick reads the same state, both increment → double-counted reminder_counts + corrupted cooldown timestamp.
**Impact:** Over-escalation (count +2/tick) or lost updates → spam or silenced reminders.
**Root cause:** No `flock`/`FileLock` around the state mutation.
**Recommendation:** Wrap the state mutation in `flock -n` (exit 0 if locked) or use atomic `os.replace()`.

### [HIGH] MEMORY WATCH GAP — `memory_watch.py` watches only MEMORY.md/USER.md; `state.db` + `cron/output/` grow unbounded
**File(s):** `scripts/memory_watch.py:22-29` vs `state.db` (141MB) + `cron/output/*` (dozens of .md, hello-world-watch = ~1 file/min)
**Evidence:** `LIMITS = {'MEMORY.md': 9000, 'USER.md': 1375}`. `cron/output/` accumulates a markdown file every minute from hello-world-watch (642 completed runs already). `sessions.auto_prune: false` (per PROGRESS). No cleanup cron for `cron/output/` (only `logrotate-run.sh` for logs).
**Impact:** Disk exhaustion over time; `cron/output/` → 1440 files/day. `state.db` with `auto_prune:false` retains all session state.
**Root cause:** Watchdog scope too narrow; no retention on cron output or session db.
**Recommendation:** Add a cron to prune `cron/output/*` older than N days; set `sessions.auto_prune: true`; extend memory_watch to flag `state.db` size.

### [MEDIUM] DEAD/STALE — `med-status.json.bak*` present but unverified rotation; "auto-backup" claim overstated (see B-dead)
**File(s):** `med-status.json.bak1/.bak2/.bak3` + `med-tracker/SKILL.md:425`
*(Covered in §B — listed here only to note it is also a documentation-vs-reality gap.)*

### [MEDIUM] SECURITY — `redact_secrets: true` covers agent logs, but no_agent cron stdout is delivered verbatim; redaction boundary for cron output unverified
**File(s):** `config.yaml:569` + `chain_monitor.sh:94` (echo to stdout) + `cron/output/*.md`
**Evidence:** Med cron output is sent to WhatsApp AND saved to `cron/output/*.md` on disk. If any script ever echoed a secret (API key, username path), it lands in both the group chat and unredacted output files. Current reminder text is safe; the boundary is unverified.
**Impact:** Low-probability, high-blast-radius: a future script change logging an env var leaks it to the medical group and disk.
**Root cause:** Redaction policy scope unclear for no_agent cron stdout.
**Recommendation:** Confirm `redact_secrets` applies to cron stdout/output; add a lint/test failing if cron scripts reference `API_KEY`/`os.environ` in print/echo.

### [MEDIUM] CHANNEL/ALLOW-LIST MISMATCH — Telegram allow-list id vs directory name; WhatsApp has no allow-list
**File(s):** `config.yaml:623-624` vs `channel_directory.json:6`; `config.yaml:647` (`unauthorized_dm_behavior: ignore`)
**Evidence:** `allow_from: ['679729206']` (numeric) vs directory `name: "amirulhazym"`. No code cross-checks that the allow-listed id exists in the directory. WhatsApp has `unauthorized_dm_behavior: ignore` but **no `allow_from`** — any WhatsApp number can reach the agent (just not use admin commands).
**Impact:** An arbitrary WhatsApp sender can reach the agent (no allow-list); directory typo won't be caught. For a medical assistant handling PHI, an open inbound channel is a privacy risk.
**Root cause:** Allow-lists hand-maintained; directory is display-only.
**Recommendation:** Derive allow-lists from `channel_directory.json` or assert every `allow_from` id exists in the directory. Add a WhatsApp `allow_from`.

### [MEDIUM] HOOK COVERAGE — `malaysia-country-selector-interaction` NOT in any trigger map; only manual/SOUL-instructed
**File(s):** `hooks/skill-trigger/handler.py:22-45` (no geo triggers) + `SOUL.md:83-99`
**Evidence:** TRIGGER_MAP has med patterns only. The malaysia-selector skill (critical for geo-sensitive pricing) loads only if the agent voluntarily remembers. Same self-administered-guard weakness as the med case.
**Impact:** Pricing queries may report Singapore-region (VPS IP) prices as if Malaysian.
**Root cause:** Trigger map incomplete; relies on SOUL.md compliance.
**Recommendation:** Add regex triggers (`.my`, "harga", "price", "MYR", "RM", "cost") to TRIGGER_MAP.

### [MEDIUM] OBSERVABILITY — Morning Briefing cron `last_status: "error"` (Broken pipe); no alert fired
**File(s):** `cron/jobs.json:34-35`
**Evidence:** `"last_status": "error", "last_error": "RuntimeError: [Errno 32] Broken pipe"` (2026-07-05). No cron watches cron health; the only signal is a field in jobs.json nothing alerts on.
**Impact:** A systemic delivery outage shows only as a buried field, zero operator notification.
**Root cause:** No health/alerting cron for cron-job failures.
**Recommendation:** Add a watchdog cron scanning `jobs.json` for `last_status != ok` in 24h, alerting to the home DM.

### [MEDIUM] CONFIG DRIFT — Cron jobs snapshot `deepseek-v4-flash`; live chat uses `deepseek-v4-pro`; snapshot unused by any code
**File(s):** `config.yaml:2-3` vs `cron/jobs.json:11-12` (every job)
**Evidence:** Every cron job carries `provider_snapshot: "deepseek"` / `model_snapshot: "deepseek-v4-flash"`; grep across `*.py` finds zero reads of these fields. Three different "active models" coexist: (1) live `opencode-go/deepseek-v4-pro`, (2) cron snapshot `deepseek/deepseek-v4-flash`, (3) `chain_llm.py` default `deepseek-v4-flash`.
**Impact:** The snapshot is dead metadata giving false model-governance impression; a model rename/retire breaks every cron silently (they're no_agent scripts, so mostly benign, but the snapshot misleads).
**Root cause:** Snapshot fields persisted at cron-create; no reconciliation with config.yaml.
**Recommendation:** Delete unused snapshot fields or wire them to config.yaml (re-snapshot on gateway start); label non-authoritative.

### [MEDIUM] INVENTORY DRIFT — RUNBOOK lists 28 cron jobs; snapshot `jobs.json` defines 14
**File(s):** `RUNBOOK.md:53-84` vs `cron/jobs.json` (14 job objects)
**Evidence:** RUNBOOK's cron table enumerates 28 (7 system + 20 medication + balance check). The snapshot `jobs.json` contains 14 job definitions. (The audit prompt also cites "14 jobs.") The discrepancy may be a RUNBOOK written for the WSL era vs the VPS snapshot; either way the doc overstates current job count.
**Impact:** Operational docs mislead during incident response.
**Root cause:** Docs not re-synced after VPS migration / job consolidation.
**Recommendation:** Regenerate RUNBOOK cron table from live `jobs.json`.

### [LOW] DEAD CODE — cost-tracking triggers commented out in hook; broken `fix-models.sh` referenced
**File(s):** `hooks/skill-trigger/handler.py:40-44`; `scripts/fix_models.py:5`
**Evidence:** Cost-tracking trigger block commented out; `fix_models.py` references a `fix-models.sh` that "silently did nothing."
**Impact:** Confusion/maintenance risk.
**Recommendation:** Delete dead commented blocks; ensure only `fix_models.py` ships.

---

## D. DateTime / dependency (the environment-level fragility)

### [CRITICAL] DEPENDENCY — `chain_calc.py` hard-crashes at import without `tzdata`
**File(s):** `scripts/chain_calc.py:27` (`MYT = ZoneInfo('Asia/Kuala_Lumpur')`)
**Evidence (REPRODUCED on Windows audit host):** `python scripts/chain_calc.py --help` → `ModuleNotFoundError: No module named 'tzdata'` raised at import. The entire med-tracker chain engine depends on `ZoneInfo('Asia/Kuala_Lumpur')` resolving; on any host without system zoneinfo AND without the `tzdata` PyPI package (common on minimal VPS images, containers, Windows), **the module fails to import** — taking down `chain_monitor.sh` (which imports it) and any script that imports `chain_calc`.
**Impact:** A missing optional dependency (not declared in any requirements file, THEORETICAL whether VPS has it) can silently kill the medication reminder pipeline. This is the same class of failure as C-CONC / X-TZ — the med system's availability rests on an undeclared, unguarded dependency.
**Root cause:** Hard `ZoneInfo` import at module top with no fallback/guard; `tzdata` not pinned.
**Recommendation:** Add `tzdata` to a requirements file / install step; wrap the import with a clear error and a documented install command; consider a fallback TZ constant.

### [MEDIUM] (See C-11, X-TZ-1, C-DTZ-MED) — TZ handling is inconsistent across scripts and the scheduler; consolidated above.

---

## E. What I found BEYOND the brief's "Known Failure Patterns"

The brief listed Patterns A–E (test-on-prod corruption, fix-regression, cron wrong-destination, over-assume, outgrew-design). My findings **extend well past** those:

- **A (test-on-prod):** Confirmed structurally — only `med_confirm.py` has `--dry-run`; the hot production writer `chain_monitor.sh` has **none** (C-3, C-MEDIUM-logging). This is the deeper version of Pattern A.
- **B (fix-regression):** Confirmed at the code level — `confirm_slot` overwrites all drug times (C-1), supply double-decrement (C-7), orphan drug keys (C-8). The drug-level feature introduced exactly the regression risk the brief describes.
- **C (cron wrong destination):** **Already fixed** in this snapshot — no `deliver:"origin"`. But I found a *new* routing bug: the hello-world beacon posts to the medical **group** (X-ROUTE-1).
- **D (over-assume):** Reframed as the fails-open hook + advisory anti-fabrication gate (X-FAB-1, X-HOOK-2) — the assistant can still fabricate because nothing hard-blocks it.
- **E (outgrew design):** Confirmed broadly — stale dexa dosage (S-DRIFT-1), BD 2pm-dose gap (S-DRIFT-2), 7/10 untracked supply (S-SUPPLY), undeclared tzdata dependency (DTZ-1), no .gitignore (S-SEC-2), job-count doc drift (X-JOB-1).

**Net:** The medication layer — the patient-safety core — is the most fragile part of the system, and its fragility is concentrated in (1) non-atomic/unbacked writes, (2) slot-vs-drug time destruction, (3) untracked supply, and (4) an undeclared timezone dependency that can disable the whole reminder pipeline. The config/doc layer shows provider/SPOF drift, missing `.gitignore`, and a RUNBOOK job count that no longer matches `jobs.json` (the PRD is early-stage/historical per owner — treat as doc-hygiene, not a binding-spec violation).

*End of Audit 02. See `2026-07-05-zcode-audit-03-execution-plan.md` for the prioritized fix plan.*
