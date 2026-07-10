# Comprehensive Audit Report: Hermes Agent (MarryJane)

**Date of Audit:** 2026-07-07  
**Auditor:** Antigravity (Gemini Antigravity Engine)  
**System:** Hermes Agent v0.17.0 on Tencent Lighthouse VPS (Singapore)  
**Status:** Read-Only Audit (No execution / No commits)

---

## 1. Executive Summary

This audit report represents a complete, evidence-first review of the Hermes Agent (MarryJane) system, utilizing the live VPS snapshot synchronized on July 7, 2026. The assistant manages a safety-critical medical routine for TB Meningitis and epilepsy. Consequently, logic errors in the medication engine present severe risks to the patient's health.

Our analysis has identified **12 key findings** categorized by severity. The most severe is a **CRITICAL** dosing engine error that causes a 40% underdose of Dexamethasone (steroid) during all BD (twice-daily) tapering phases. In addition, we found significant architectural issues including hardcoded directories that pollute production state, inventory tracker decay due to static decrement quantities, and cron performance issues (CPU spikes and log bloat) caused by a 1-minute interval watchdog script.

The system is highly customized and demonstrates excellent integration of ADHD safety nets, Manglish personality, and natural LLM-driven reminders. However, code quality debt and configuration drift between Windows, WSL2, and the VPS must be resolved to ensure long-term stability and clinical safety.

---

## 2. Severity Breakdown

| Severity | Count | Primary Impact |
|---|---|---|
| 🔴 **CRITICAL** | 1 | Clinical Safety (Steroid Underdosing) |
| 🟡 **HIGH** | 6 | Data Integrity, Cron Failures, Config Errors, System Pollution |
| 🟢 **MEDIUM** | 4 | Timestamp Corruption, Resolution Errors, Validation Noise |
| 🔵 **LOW** | 1 | Resource Exhaustion (Log Bloat / CPU spikes) |
| **TOTAL** | **12** | |

**System Health Score:** **6.5 / 10**  
* **Biggest Risk:** Adrenal crisis or TB Meningitis relapse due to the 4mg steroid underdosing defect during BD taper phases.  
* **Biggest Strength:** Exceptionally rich, context-aware LLM reminder engine (`chain_llm.py`) that integrates live WhatsApp chat context to personalize reminders.

---

## 3. Findings Catalog

### 🔴 CRITICAL — Dexamethasone Taper Phase 10-16 (BD Phase) Dosing Underdose Defect
* **File(s):** 
  * [chain_calc.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/chain_calc.py#L203-L228) (`get_dexa_dose_for_slot`)
  * [dexa_taper.json](file:///C:/Users/amiru/hermes-snapshot-20260707/dexa_taper.json#L163-L273) (Phases 10-16)
* **Evidence:**
  In `chain_calc.py`, the mapping of slots to tapering fields is hardcoded:
  ```python
  mapping = {
      'B': 'dose_morning',
      'C': 'dose_midday',
      'D': 'dose_afternoon',
  }
  dose_key = mapping.get(slot)
  ...
  return phase.get(dose_key, 0)
  ```
  In `dexa_taper.json` Phase 10 (BD frequency):
  ```json
  "freq": "BD",
  "dose_morning": 6,
  "dose_midday": 0,
  "dose_afternoon": 4,
  "dose_2pm": 4
  ```
* **Impact:** In the BD tapering phases, Slot D is deactivated. The morning dose (6mg) is taken at 08:00 (Slot B), and the second dose (4mg) is taken at 14:00 (Slot C). Because `chain_calc.py` statically maps Slot C to `dose_midday` (which is defined as `0` in all BD phases), the system calculates the Slot C dose as `0mg`. The daily total is reported as 6mg instead of 10mg. If the user follows this calculated dose, they are underdosed by 4mg (40% of their daily requirement), which risks disease relapse.
* **Root Cause:** The dosing engine uses a static lookup mapping that is not aware of changes in tapering frequency (TDS → BD → OD).
* **Fix Recommendation:** Modify `get_dexa_dose_for_slot` to map Slot C to `dose_2pm` (or `dose_afternoon`) if the active taper phase frequency is `BD`.

---

### 🟡 HIGH — Hardcoded Paths Prevent Test Isolation & Cause DB Pollution
* **File(s):** 
  * [chain_calc.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/chain_calc.py#L22-L26)
  * [med_confirm.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_confirm.py#L41-L42)
  * [med_resolve.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_resolve.py#L22-L23)
  * [med_supply.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_supply.py)
* **Evidence:**
  In `med_confirm.py`:
  ```python
  STATE_FILE = Path.home() / ".hermes" / "med-status.json"
  SCHEDULE_FILE = Path.home() / ".hermes" / "med-schedule.json"
  ```
  In `med_resolve.py`:
  ```python
  HERMES_HOME = Path.home() / ".hermes"
  ```
* **Impact:** Development, dry-runs, and auditing cannot be executed locally without modifying the user's live database files. Running verification commands on Windows/WSL2 edits the real home directory files. This directly caused the minimax review agent to pollute the live database on the VPS.
* **Root Cause:** System home directory is hardcoded instead of checking for environment variables.
* **Fix Recommendation:** Resolve the directory path using `Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))` in all scripts.

---

### 🟡 HIGH — Pills-per-Dose Supply Decrement Defect
* **File(s):** 
  * [med_confirm.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_confirm.py#L267-L268) (`confirm_slot`)
  * [med_confirm.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_confirm.py#L331-L332) (`confirm_drug`)
  * [med_supply.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_supply.py)
* **Evidence:**
  In `med_confirm.py`:
  ```python
  from med_supply import decrement
  decrement(did)  # No quantity argument passed
  ```
  In `med_supply.py`:
  ```python
  def decrement(drug_id: str, amount: int = 1) -> dict:
  ```
* **Impact:** Confirmation always decrements the supply database by exactly `1` pill. However, a single dose of Akurit-4 requires `4` pills, and Pyridoxine requires `3` pills. The inventory counts quickly fall out of sync, showing hundreds of pills in stock when the actual box is empty, rendering low-stock alerts useless.
* **Root Cause:** `med_confirm.py` does not load the drug's `pills_per_dose` array from `med-supply.json` or `med-schedule.json` to pass it to the decrement function.
* **Fix Recommendation:** Load the medication's `pills_per_dose` array in `med_confirm.py` and pass the correct quantity to `decrement()`.

---

### 🟡 HIGH — Double-Decrementing on Slot Confirmation
* **File(s):** 
  * [med_confirm.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_confirm.py#L264-L270) (`confirm_slot`)
* **Evidence:**
  ```python
  for did in drug_ids:
      entry.setdefault('drugs', {})[did] = {"status": "taken", "time": now}
      try:
          from med_supply import decrement
          decrement(did)
      except Exception:
          pass
  ```
* **Impact:** In a partially confirmed slot (e.g. user took Akurit-4 at 07:30, Pyridoxine pending), running slot-level confirmation later to complete the slot decrements the supply of Akurit-4 a second time, corrupting inventory state.
* **Root Cause:** `confirm_slot` loops over all drugs in the slot and calls `decrement(did)` without checking if the drug was already marked `taken` earlier.
* **Fix Recommendation:** Add a check `if entry.get('drugs', {}).get(did, {}).get('status') == 'taken': continue` to skip already completed drugs.

---

### 🟡 HIGH — Time-Based Resolver Taper-Unawareness
* **File(s):** 
  * [med_resolve.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_resolve.py#L81-L91)
* **Evidence:**
  ```python
  TIME_RULES = {
      "dexamethasone": {
          "B": (None, 10.5),  # Before 10:30 → B
          "C": (10.5, 16),    # 10:30-16:00 → C
          "D": (16, None),    # After 16:00 → D
      },
  }
  ```
* **Impact:** During BD tapering phases, Slot D is inactive. If a user takes their afternoon dose late (e.g. at 17:00), the resolver maps the intake to Slot D. This confirms an inactive slot, leaving the active Slot C marked as pending. Reminders for Slot C continue to fire, resulting in duplicate intake warnings.
* **Root Cause:** The resolver relies on static hour bounds and is unaware of which slots are currently active in `dexa_taper.json`.
* **Fix Recommendation:** Integrate `chain_calc` inside the resolver to filter out slots that are inactive under the current taper phase before matching rules.

---

### 🟡 HIGH — Invalid Executable Path for Cua-Driver on Linux VPS
* **File(s):** 
  * [config.yaml](file:///C:/Users/amiru/hermes-snapshot-20260707/config.yaml#L734-L738)
* **Evidence:**
  ```yaml
  mcp_servers:
    cua-driver:
      command: /mnt/f/hermes/cua-driver/cua-driver.exe
  ```
* **Impact:** The `cua-driver` MCP server fails to start on the Linux VPS because it is pointing to a Windows `.exe` path. This breaks the `qwen` and `sakana` quick commands that depend on it.
* **Root Cause:** Environmental configuration divergence; the local Windows development path was copied to the Linux production VPS.
* **Fix Recommendation:** Change the command path on the VPS to point to the Linux binary or direct node launcher, or disable it if it's only meant for local PC development runs.

---

### 🟡 HIGH — Broken Daily Health Telegram Cron Job
* **File(s):** 
  * [jobs.json](file:///C:/Users/amiru/hermes-snapshot-20260707/cron/jobs.json#L166-L204)
* **Evidence:**
  ```json
  "name": "Daily Health",
  "deliver": "telegram",
  "last_status": "error",
  "last_error": "RuntimeError: [Errno 32] Broken pipe",
  "last_run_at": "2026-07-07T09:10:15.120414+08:00"
  ```
* **Impact:** The Daily Health check fails to deliver every day at 09:00 MYT, leaving the user without system status updates.
* **Root Cause:** Connection failure or missing chat configuration/auth keys for Telegram delivery in the background cron worker.
* **Fix Recommendation:** Inspect the cron logs to isolate the Telegram broken pipe issue and verify gateway credentials.

---

### 🟢 MEDIUM — Slot-Level Timestamp Overwrite
* **File(s):** 
  * [med_confirm.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_confirm.py#L265) (`confirm_slot`)
* **Evidence:**
  ```python
  for did in drug_ids:
      entry.setdefault('drugs', {})[did] = {"status": "taken", "time": now}
  ```
* **Impact:** Overwrites earlier, accurate intake times with the slot-level confirmation timestamp, destroying history.
* **Root Cause:** Destructive write logic that does not preserve pre-existing drug entries.
* **Fix Recommendation:** If a drug is already marked `taken`, preserve its `"time"` field instead of setting it to `now`.

---

### 🟢 MEDIUM — Float-String Precision Loss in Time Parsing
* **File(s):** 
  * [med_resolve.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_resolve.py#L141-L143)
* **Evidence:**
  ```python
  hour_f = float(time_24h.replace(":", ".").rstrip("0").rstrip("."))
  ```
* **Impact:** Converting `"10:30"` yields `10.3`, which is less than the `10.5` boundary for Slot C. Consequently, 10:30pm maps to Slot B rather than Slot C.
* **Root Cause:** String replacement math that does not parse minutes correctly.
* **Fix Recommendation:** Parse using `datetime.strptime(t, "%H:%M").time()` for clean comparisons.

---

### 🟢 MEDIUM — Unknown Interaction Pairs for Same-Drug Matches
* **File(s):** 
  * [med_interact.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/med_interact.py)
  * [med-interactions.json](file:///C:/Users/amiru/hermes-snapshot-20260707/med-interactions.json)
* **Evidence:**
  Same-drug pairs across slots (e.g. `levetiracetam_b` and `levetiracetam_e`) return `UNKNOWN` status because they are not safe-listed with themselves in `med-interactions.json`.
* **Impact:** Noisy compliance validation reports with 4 false-positives (`UNKNOWN`).
* **Root Cause:** Strict pair-checking that has no concept of drug equivalence or self-interaction safety.
* **Fix Recommendation:** Modify the checking logic in `med_interact.py` to automatically skip or mark as safe any drug IDs that resolve to the same base drug.

---

### 🟢 MEDIUM — Stale Taper Display String Formatting
* **File(s):** 
  * [chain_calc.py](file:///C:/Users/amiru/hermes-snapshot-20260707/scripts/chain_calc.py#L628)
* **Evidence:**
  Inside `chain_calc.py` line 628:
  ```python
  'dose_afternoon': current_phase.get('dose_afternoon', 0) or current_phase.get('dose_evening', 0),
  ```
  But inside `dexa_taper.json` Phase 10, the 2pm dose is defined under `"dose_2pm": 4`.
* **Impact:** Because `dose_2pm` is not fetched or mapped in `taper_info` inside `calculate_chain()`, the `--taper-display` outputs `Doses: 6mg (8am) + 0mg (2pm)` for BD phases instead of `4mg`.
* **Root Cause:** `dose_2pm` field is omitted from the fallback chain.
* **Fix Recommendation:** Map `dose_2pm` as an active dose lookup candidate for afternoon dose calculation inside `calculate_chain()`.

---

### 🔵 LOW — hello-world-watch Excessive Execution and Log Bloat
* **File(s):** 
  * [jobs.json](file:///C:/Users/amiru/hermes-snapshot-20260707/cron/jobs.json#L328-L370)
* **Evidence:**
  In `jobs.json`:
  ```json
  "name": "hello-world-watch",
  "schedule": {
    "kind": "interval",
    "minutes": 1
  },
  "repeat": {
    "completed": 2204
  }
  ```
* **Impact:** Running a Python script every 1 minute creates unnecessary CPU load spikes and produces thousands of output files under `cron/output/67efe5d502bc/`, leading to disk space bloat and slowing down directory transfers.
* **Root Cause:** A test interval watchdog left running in production.
* **Fix Recommendation:** Increase the interval to 15 minutes or 1 hour, or disable it if the gateway stability is verified.

---

## 4. Prioritized Remediation Plan

We suggest executing these fixes in the following order to ensure safety and prevent regression:

### Phase 1: Clinical Safety & Directory Decoupling
1. **Fix Dexamethasone BD Dosing:** Modify `chain_calc.py` to correctly map Slot C to `dose_2pm` if `freq == 'BD'`.
2. **Implement Path Environment Override:** Refactor all scripts to read `HERMES_HOME` with fallback to `Path.home() / '.hermes'`.
3. **Optimise hello-world-watch Interval:** Change the interval in `jobs.json` to 1 hour or disable it to clean up log bloat.

### Phase 2: Inventory & Log Integrity
4. **Fix Pills-per-Dose Decrementing:** Update `med_confirm.py` to pass the correct dose amount to `decrement()`.
5. **Fix Double-Decrementing and Overwrite on Slot Confirm:** Skip already completed drugs during slot confirmations and preserve their original intake timestamps.
6. **Taper-Aware Shorthand Resolver:** Integrate active taper phase slot checks in `med_resolve.py`.

### Phase 3: Cleanup & Integration
7. **Fix Time parsing float math:** Replace the float-string replacement parse logic with `datetime.time` calculations.
8. **Resolve Same-Drug Interaction Noise:** Add same-base-name checks to `med_interact.py`.
9. **Fix cua-driver Executable Path:** Change `/mnt/f/...cua-driver.exe` to a network-based MCP endpoint or remove it from the VPS config.
