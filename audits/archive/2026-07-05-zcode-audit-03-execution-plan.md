# Hermes Agent — Execution Plan (Audit 03)

> **Auditor:** ZCode · **Date:** 2026-07-05
> **Basis:** Findings in `2026-07-05-zcode-audit-02-findings.md` (7 CRITICAL / 14 HIGH / 18 MEDIUM / 5 LOW).
> **Owner intent (clarified this session):** The PRD is early-stage/historical — the snapshot is the evolved reality. `DECISIONS.md` is the living decisions log. The user wants this to eventually become a productive/profit-capable personal agent, not just a cost sink — but patient safety (the medication layer) is the stated priority.
> **Safety stance:** Every fix below is staged so the patient-safety core is hardened first, with no destructive change going unverified.

This plan is organized in **priority tiers**, not a single linear sequence. Within a tier, items are grouped as **independent** (can be done in any order / in parallel) or **sequential** (depend on a prior item). Each item cites the Doc 2 finding, the exact files, the change, and how to verify.

---

## Tier 0 — Patient-safety blockers (do first, before anything else)

These are the issues that can corrupt real intake data, silently lose reminders, or expose credentials. **Do not start Tier 1+ until T0-A/T0-B/T0-C are in.**

### T0-A · Hard-stop data corruption: atomic + backed-up writes [CRITICAL] (findings C-3, C-CONC, X-MEM)
- **Independent** of other fixes; touches the write path only.
- **Files:** `scripts/chain_calc.py:136-139` (`save_json`), `scripts/chain_monitor.sh:79`, and add a shared atomic helper (e.g. `scripts/med_io.py` with `atomic_write_json(path, data)` = write `path.with_suffix('.tmp')` then `os.replace(tmp, path)` + optional `.bak` copy).
- **Change:**
  1. Add `med_io.atomic_write_json` and use it everywhere a JSON state file is written: `chain_calc.save_json`, `chain_monitor.sh` (replace the inline `write_text` with a call to a small Python helper that imports `med_io`), `med_supply.save_supply`, `med_appointments.save_json`, `med_confirm.save_json`.
  2. Make the corrupt-read fallback **loud**: in the read paths, on `json.JSONDecodeError`, log to `~/.hermes/logs/state_recovery.log` and return the last `.bak` (not silently `{}`).
  3. Add a `flock -n` guard at the top of `chain_monitor.sh` so overlapping 15-min runs don't race (exit 0 if locked).
- **Verify (read-only on VPS):**
  - Unit test `atomic_write_json` with a simulated kill mid-write (truncate the `.tmp`); confirm the target file is unchanged and the `.bak` is intact.
  - Simulate a corrupted `chain-state.json` (write garbage) and confirm the read path logs + falls back instead of resetting to `{}`.
- **Needs human input:** none — pure hardening.

### T0-B · Stop silent destruction of real intake times [CRITICAL] (findings C-1, C-2)
- **Sequential after T0-A** (same file, `med_confirm.py`).
- **Files:** `scripts/med_confirm.py:225-231` (`confirm_slot`), `:401-405` (`update_time`).
- **Change:**
  1. `confirm_slot`: only set `{status:"taken", time: now}` for drugs whose existing status ≠ `taken`; preserve earlier real times. Still decrement supply (see T1-D for idempotent decrement).
  2. `update_time`: scope to a single `drug_id` argument; if no drug_id given, only update a slot-level default time field (don't flatten per-drug times). Print a warning when bulk-updating.
- **Verify:** `python scripts/med_confirm.py --dry-run B` after a partial confirm shows the earlier time preserved (note: requires `tzdata` — see T1-A). Confirm with a `--dry-run` so no live write happens.
- **Needs human input:** confirm the desired `--update` semantics (per-drug vs slot-level default).

### T0-C · Credential hygiene: add `.gitignore` + assess exposure [CRITICAL] (finding S-SEC-2)
- **Independent.**
- **Files:** create `C:/Users/amiru/hermes-snapshot-20260705/.gitignore` (and mirror on VPS `~/.hermes/.gitignore`).
- **Change:** add `whatsapp/`, `platforms/whatsapp/`, `.env`, `*.key`, `*.pem`, `auth.json`, `*.session`, `state.db*`, `triggered_skills.txt`, `*/session*/`, `logs/`. (The MJay repo's Phase-1 `.gitignore` exists for the docs repo — this is for the runtime tree.)
- **Verify:** `git status --ignored` (if the runtime tree ever becomes a repo) shows the sensitive paths ignored.
- **Needs human input (IMPORTANT):** The snapshot was taken to a Windows folder and may have been handled by sync tools. **Ask the owner: has `~/.hermes/` or this snapshot ever been committed/pushed/backed-up to a non-local destination?** If yes, the WhatsApp identity keys should be rotated (re-link) — that's a human decision, not an automated one.

### T0-D · Pin timezone + declare `tzdata` [CRITICAL] (findings X-TZ-1, C-11, DTZ-1)
- **Sequential: needs the VPS, not just the snapshot.**
- **Files:** VPS systemd unit `~/.config/systemd/user/hermes-gateway.service` (add `Environment=TZ=Asia/Kuala_Lumpur`); `scripts/chain_monitor.sh:76-77` (replace `_dt.datetime.now()` with `datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))`); add `tzdata` to a `~/.hermes/scripts/requirements.txt` (or confirm it's installed: `python3 -c "import tzdata"`).
- **Change:**
  1. Confirm the VPS host TZ and the cron scheduler's effective TZ (log `time.tzname` / `datetime.now().astimezone()` at gateway startup). PROVES or REFUTES X-TZ-1.
  2. Pin `TZ=Asia/Kuala_Lumpur` in the service env regardless (belt + suspenders).
  3. Fix the naive `datetime.now()` in `chain_monitor.sh`.
  4. Pin `tzdata` so DTZ-1 can't recur on a minimal/containerized host.
- **Verify:** add a one-shot cron that prints `datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))` and compares to `datetime.now()`; they must match. Check the gateway log prints the resolved TZ.
- **Needs human input:** SSH access to the VPS is required for steps 1–2. **Ask the owner** whether to proceed on-VPS (per AGENTS.md, I won't SSH without explicit approval).

---

## Tier 1 — Correctness of the medication layer (do after T0)

### T1-A · Date-keyed reminder counts [CRITICAL] (finding C-4)
- **Sequential after T0-A** (touches `chain-state.json` schema).
- **Files:** `scripts/chain_monitor.sh:71-73`, `scripts/chain_calc.py:550`.
- **Change:** store `reminder_counts` as `{date: {slot: n}}` OR add a `last_reset_date` field; reset all counts when the date changes (use MYT). Migrate the existing flat dict on first read.
- **Verify:** simulate two consecutive days with an unconfirmed slot; confirm count resets at midnight, not accumulates.
- **Needs human input:** none.

### T1-B · Make the domino chain actually shift when A is late [HIGH] (findings C-6, C-14)
- **Files:** `scripts/chain_calc.py:397-441` (`calculate_ready_time`), `:454-463` (`chain_times`), `:512-526` (`next_slot`).
- **Change:** when a predecessor slot is pending/missing, propagate the ready time from the last *known* actual time + cumulative gaps, OR mark downstream slots as `blocked` (a new status) rather than returning an optimistic default. In `next_slot`, order candidates by SLOTS index and ensure slot A is surfaced first when it's the blocker.
- **Verify:** construct a test `med-status.json` where A is pending and B's default is 08:00; confirm C/D/E ready times shift (or are marked blocked), not stay static.
- **Needs human input:** confirm the desired behavior when A is missed entirely — "shift everything" vs "block + alert loudly." I recommend the latter for a TB regimen.

### T1-C · Fix `med_resolve` routing bugs [HIGH] (findings C-9, C-10, X-FAB-2)
- **Files:** `scripts/med_resolve.py:127-130` (float time hack), `:77-80, 139` (levetiracetam boundary), `:204-213` (first-match / alias-expansion-order).
- **Change:**
  1. Replace the float hack with `h, m = map(int, t.split(':')); hour_f = h + m/60.0`.
  2. Make slot boundaries explicit and non-overlapping; add a test for 10:30 and 14:00.
  3. Prioritize `WORD_TO_SLOT` hints ("petang"→D, "pagi"→B) *before* alias expansion; return an `ambiguous` error (not `matches[0]`) when the hint conflicts with the resolved match.
- **Verify:** unit tests: `resolve("dexa", time="10:30")` → slot C; `resolve("dexa petang")` → slot D; `resolve("letram", time="14:00")` → slot E.
- **Needs human input:** none.

### T1-D · Idempotent supply decrement + backfill [HIGH] (findings C-7, C-12, S-SUPPLY)
- **Files:** `scripts/med_confirm.py:225-231` (decrement loop), `scripts/med_supply.py:58-72`.
- **Change:**
  1. Decrement only on the `pending→taken` transition (capture `prev_status` before overwriting).
  2. Skip drugs with `doses_per_day == 0` or `current is None`.
  3. Change the threshold comparison to `< warning_threshold` for "low" (or redefine threshold semantics explicitly).
- **Verify:** `confirm_slot C` twice in `--dry-run` should show decrement happening once per drug.
- **Needs human input:** **ask the owner to do a physical pill count** so `current` can be backfilled for the 7/10 null entries — this is the only way to make supply tracking actually work. The code fix alone won't help if the baseline is `null`.

### T1-E · Sync `med-schedule.json` dexa dosage from the taper engine [CRITICAL] (findings S-DRIFT-1, S-DRIFT-2, LOW-1)
- **Files:** `med-schedule.json:26,38,53`; `dexa_taper.json`; add a small `scripts/sync_taper_to_schedule.py`.
- **Change:**
  1. Add `sync_taper_to_schedule.py` that reads the *current* phase from `dexa_taper.json` and rewrites the dexa `dosage` fields in `med-schedule.json`. Run it from a daily cron (after `taper_alert.py`) so it stays correct on every phase change.
  2. Surface `dose_2pm` for BD phases (the 2pm dose that currently has no slot): either add a synthetic slot F, or have `taper_alert.py` explicitly print the 2pm dose when `freq == "BD"`.
  3. Fix `get_dexa_dose_for_slot` (`chain_calc.py:203-228`) so BD-phase slot C maps to `dose_2pm` (not `dose_midday=0`).
- **Verify:** set the test date to a BD-phase date and confirm `taper_alert.py` shows the 2pm dose and slot-C reminder shows the correct mg.
- **Needs human input:** confirm the synthetic-slot-F approach vs a "2pm dose" rendering in reminders. This is a real schedule-model decision.

### T1-F · Hard-gate anti-fabrication [HIGH] (findings X-FAB-1, X-HOOK-2, X-HOOK-3)
- **Files:** `scripts/med_confirm.py` (add a hard check at entry), `hooks/skill-trigger/handler.py:80-94`.
- **Change:**
  1. In `med_confirm.py`, refuse any confirm whose `drug_id` is not in `get_all_drug_ids(slot, schedule)` (this kills orphan-key writes, finding C-8, and makes the resolver a hard gate).
  2. In `handler.py`, on failure to write `triggered_skills.txt`, write a fallback marker the agent must acknowledge (fail-loud, not fail-open).
  3. Add `malaysia-country-selector` triggers to `TRIGGER_MAP` (`.my`, "harga", "RM", "MYR", "price", "cost").
- **Verify:** `med_confirm.py X bogus_drug` returns an error, not a silent write. A message that doesn't match any regex leaves a visible marker.
- **Needs human input:** none.

---

## Tier 2 — Reliability & observability (do after T1, can be parallelized)

### T2-A · Give `chain_monitor.sh` dry-run + logging [HIGH/MEDIUM] (findings C-MEDIUM-LOG, C-MEDIUM-RACE)
- **Independent.**
- **Files:** `scripts/chain_monitor.sh:16, 80, 94`.
- **Change:** add `--dry-run` (skip write + skip LLM call); replace `2>/dev/null || true` with `>> ~/.hermes/logs/chain_monitor.log 2>&1` (only stdout to the user-facing message). Keep `set -euo pipefail` honest.
- **Verify:** run `chain_monitor.sh --dry-run` against the snapshot state; confirm no write and a log entry.

### T2-B · Cron health watchdog [MEDIUM] (finding X-OBS-1)
- **Independent.**
- **Files:** new `scripts/cron_health_watch.py`; register as a daily cron to the home DM.
- **Change:** scan `cron/jobs.json` for `last_status != "ok"` in the last 24h; alert the home DM (`whatsapp:13186321408227@lid`), not the medical group.
- **Verify:** flip a job's `last_status` to `error` and confirm the alert fires.

### T2-C · Retention for `cron/output/` + `state.db` [HIGH] (finding X-MEM-1)
- **Independent.**
- **Files:** new `scripts/prune_cron_output.sh` (weekly cron); `config.yaml` `sessions.auto_prune: true`.
- **Change:** delete `cron/output/*` older than N days (default 14); enable session auto-prune; extend `memory_watch.py` to flag `state.db` size.
- **Verify:** run the prune against the existing 642+ hello-world outputs; confirm disk freed and nothing live breaks.

### T2-D · Fix `hello-world-watch` routing [HIGH] (finding X-ROUTE-1)
- **Independent.**
- **Files:** `cron/jobs.json:400`.
- **Change:** `deliver: "whatsapp:13186321408227@lid"` (home DM), not the medical group.
- **Verify:** restart gateway; confirm the beacon lands in the DM, not the group.

### T2-E · Reconcile docs with reality [MEDIUM] (findings X-JOB-1, X-GOV-doc, X-MODEL-1)
- **Independent (doc-only).**
- **Files:** `RUNBOOK.md` (cron table), `DECISIONS.md` (provider/fallback rationale), `med-tracker/SKILL.md:654` (remove/verify the "gateway broken" claim), `cron/jobs.json` (remove or relabel unused `provider_snapshot`/`model_snapshot`).
- **Change:** regenerate the RUNBOOK cron table from live `jobs.json`; add a dated `DECISIONS.md` entry for the current provider posture; test `hermes chat -q` live and remove the stale ImportError claim if it works.
- **Verify:** RUNBOOK count matches `jobs.json`; `DECISIONS.md` has a dated entry; grep for `fast_safe_load` returns nothing actionable.

---

## Tier 3 — Code quality & minor (opportunistic)

- **T3-A** Delete dead `ESCALATION` dict or wire it up (LOW).
- **T3-B** Fix `med_interact` verdict to "PARTIAL" when `unknown_count>0` (MEDIUM).
- **T3-C** Fix `med_substitute --otc` to require non-empty `alternatives` (MEDIUM).
- **T3-D** Wrap `med_appointments` date parsing in try/except (MEDIUM, THEORETICAL).
- **T3-E** Preserve legacy time in string-form migration (`med_confirm.py:138-145`) (MEDIUM).
- **T3-F** Add a regex guard to `get_default_time` parse (`chain_calc.py:390-394`) (LOW).
- **T3-G** Remove commented cost-tracking block in `handler.py:40-44`; ensure only `fix_models.py` ships (LOW).
- **T3-H** Centralize `today_myt()`/`now_myt()` in one module; import everywhere; fail loudly on missing `ZoneInfo` (MEDIUM, pairs with T0-D).

These are independent and low-risk; batch them whenever you touch the relevant file.

---

## Independent vs sequential — at a glance

```
T0-A (atomic writes) ──┬──> T0-B (preserve times)
                      ├──> T1-A (date-keyed counts)
                      ├──> T1-D (idempotent decrement)
                      └──> T1-F (hard-gate)

T0-C (.gitignore)           [independent — do immediately]
T0-D (TZ + tzdata)          [needs VPS — needs human approval]

T1-B (domino shift)         [independent of T0-A, but test after]
T1-C (med_resolve)          [independent]
T1-E (taper→schedule sync)  [independent; needs human on slot-F decision]

T2-*                        [all independent of each other and of T1]
T3-*                        [opportunistic]
```

**Safe parallel tracks once T0-A is in:** T1-C, T1-E, T2-A/B/C/D/E can proceed in parallel; T0-B/T1-A/T1-D/T1-F share `med_confirm.py`/`chain_calc.py` and should be sequenced.

---

## What needs human input before proceeding

| Decision | Why it matters | Where |
|---|---|---|
| **Has `~/.hermes/` or this snapshot ever been pushed/committed/backed-up remotely?** | If yes, WhatsApp identity keys may be exposed → rotate (re-link). | T0-C |
| **Approve SSH work on the VPS for TZ pinning + `tzdata`?** | Can't fully fix X-TZ-1 / DTZ-1 without VPS access. | T0-D |
| **Physical pill count to backfill supply baselines?** | 7/10 drugs have `current: null`; supply tracking is dead without it. | T1-D |
| **When slot A is missed: "shift everything" vs "block + alert loudly"?** | Real schedule-model decision; I recommend block+alert for a TB regimen. | T1-B |
| **BD-phase 2pm dose: synthetic slot F vs reminder rendering?** | Schedule-model decision for taper phases 10+. | T1-E |
| **`--update` semantics: per-drug vs slot-level default?** | Affects how the owner corrects times. | T0-B |

---

## Simplify vs keep

**Simplify / consolidate:**
- The dual `calculate_chain()` evaluation in `chain_monitor.sh` (T2-A moves it into one process).
- The two time representations (naive `datetime.now()` in shell vs MYT in Python) → one `med_io.now_myt()`.
- Dead `ESCALATION` dict, dead `fix-models.sh`, commented cost-tracking triggers.
- The `.bak1/.bak2/.bak3` scheme → consolidate behind `atomic_write_json` + a date-stamped backup when history is wanted.

**Keep (do NOT remove):**
- The drug-level tracking model itself — it's the right design; only its write path is buggy.
- The taper engine (`dexa_taper.json`) as the single dexa authority — extend it, don't replace it.
- The `--dry-run` flag and `.bak` rotation in `med_confirm.py` — extend to other writers.
- The 14-job cron structure (it's coherent; only the doc count is wrong).

---

## Forward-looking: productive → side-income path (per stated end-goal)

> You said the assistant should eventually "gain some unexpected maintainable profits/side income per month." The current system is a pure cost sink (DeepSeek/VPS/domain) and a personal medical assistant. Below is an honest, grounded ideation — not a promise. Every item is free/low-cost to prototype and reversible. None of this should be started before Tier 0–1 are done: **a profit path built on a fragile, corrupting medication layer inherits that fragility.**

**What's already in place that has leverage value:**
- A working multi-platform (WhatsApp + Telegram) proactive agent with cron, memory, skills, and a vision pipeline (Phase 18–23 design skills + MiMo-V2.5 vision).
- A documented, repeatable "build a Hermes personal agent" workflow (PRD/PROGRESS/DECISIONS/RUNBOOK are genuinely useful as a template).
- A real, clinically-serious medication-tracking system — which, once hardened, is a compelling portfolio piece and a credible domain.

**Three realistic directions (ranked by leverage × low-cost):**

1. **"Personal AI assistant as a service" — done-for-you builds for individuals (highest leverage).**
   - Productize the exact stack you built: Hermes + DeepSeek + WhatsApp + a custom cron/skill layer. Offer it to other busy professionals (clinicians, founders, ADHD-friendly personal CRM).
   - Low cost: it's the system you already run; each client is a cloned VPS + config. Marginal cost ≈ one VPS + their DeepSeek usage.
   - Asset to build first (after hardening): a clean, documented "recipe" (`provision.sh` + the skills + a setup runbook) you can deliver. The current MJay repo is 60% of this.

2. **Niche clinical-quality medication adherence tooling (highest credibility, matches your domain).**
   - Your Domino Chain (chain-dependent reminders, taper engine, interaction matrix) is genuinely novel for a personal system. Hardened + generalized, it's a credible open-source project or a paid tool for chronic-disease patients (TB, epilepsy, steroid tapers).
   - Caveat: medical software has real liability. The safe framing is "adherence companion, not medical advice" and open-source-first to build trust.
   - Asset to build first: the hardening in Tier 0–1 IS the product work. The audit findings (Doc 2) are effectively your pre-launch bug list.

3. **Content + templates (lowest risk, slowest payoff).**
   - The PRD/DECISIONS/PROGRESS/RUNBOOK pattern and the phase-by-phase build log are valuable as a paid guide or newsletter for people building personal agents. Low cost, but requires consistency (hard with ADHD + treatment).
   - This pairs with direction 1 as marketing, not a standalone income.

**Honest reconciliation with cost reality:**
- The current opencode-go + deepseek-v4-pro setup is a paid subscription. For a personal tool that's fine; for a productized service, per-client cost matters. **T0-SPOF/C-SPOF is not just reliability — it's also the unit-economics question.** Fixing the fallback (enable a real fallback, or route cheap paths to a free tier like opencode-zen) is both a reliability fix and a margin fix.

**Concrete first step (after Tier 0–1):** pick ONE direction above, and the next deliverable is a one-page `DECISIONS.md` entry capturing: target user, what they pay for, monthly cost per client, and which existing asset (Hermes stack / Domino Chain / docs) is the foundation. Don't build anything new until that one page exists — it prevents the "built a thing nobody asked for" failure mode.

---

## Verification before completion (per the audit's quality standard)

After implementing any tier, verify on the **VPS** (not just the snapshot):
- [ ] `med_confirm.py --dry-run` for each slot shows correct preservation of times.
- [ ] `chain_monitor.sh --dry-run` logs without writing.
- [ ] Corrupted `chain-state.json` → logged + `.bak` fallback, not silent reset.
- [ ] `taper_alert.py` on a BD-phase test date shows the 2pm dose.
- [ ] `med_resolve` returns C for 10:30 dexa, D for "dexa petang", E for 14:00 levetiracetam.
- [ ] Gateway log prints resolved TZ = Asia/Kuala_Lumpur.
- [ ] `.gitignore` present; `git status --ignored` covers session/creds/env.
- [ ] RUNBOOK cron count == `jobs.json` count.
- [ ] No secrets in any new file or log.

---

## What I did NOT do (honesty)

- I did not run the med scripts live — the audit host is Windows without `tzdata`, and `chain_calc.py` hard-crashes at import there (PROVEN — see DTZ-1). Behavioral dry-runs of confirm/chain-calc are therefore UNVERIFIED in this audit; the Tier 0–1 changes should be verified on the VPS where `tzdata` exists.
- I did not read any prior audit document (unbiased stance, per your instruction).
- I did not SSH to the VPS or modify any runtime file — everything above is a plan for you to approve and execute (or direct me to execute on-VPS with explicit approval).
- The "side-income" section is grounded ideation from PROGRESS/DECISIONS/RUNBOOK, not market research — validate with real users before building.

*End of Audit 03. Full set: `audit-01-system-context.md` · `audit-02-findings.md` · `audit-03-execution-plan.md` (all prefixed `2026-07-05-zcode-`).*
