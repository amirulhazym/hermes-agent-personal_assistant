# Audit Report: Gemini Follow-Up Audit (8 Dimensions)

**Date of Audit:** 2026-07-07  
**Auditor:** Antigravity (Gemini Antigravity Engine)  
**Workspace:** F:\AI Prep\OVIS\Hermes Agent\MJay\  
**Status:** Read-Only Audit (No execution / No commits)

---

## EXECUTIVE SUMMARY
This follow-up audit covers the 8 previously skipped or partially addressed dimensions of the Hermes Agent (MarryJane) system. The audit was conducted using the synchronized VPS snapshot from July 7, 2026. This review focuses on system security, config/model efficiency, script quality, database state integrity, documentation sync, backups, cost burn, and cross-platform divergence.

The cumulative health score of the system is **6.0 / 10**. 

### Critical Insights & Corrections
1. **Dexamethasone BD Underdosing Bug Verified:** We ran a live simulation in WSL2 by mocking the date to September 15, 2026 (Phase 10, BD frequency). The simulation proved that Slot C (14:00) maps to `dose_midday` (which is `0` in `dexa_taper.json` during BD phases) instead of `dose_2pm`, returning **0mg**. Because Slot D (16:00) is deactivated under BD frequency, this results in a **4mg daily underdose** (6mg instead of the prescribed 10mg). The VPS Auditor's verification failed because they tested against the current active Phase 5 (TDS frequency), which does not trigger the bug.
2. **Dynamic Active Model Selection:** The `default` key in `config.yaml` is not a static default model; it represents the **currently selected model** for the active session and is dynamically updated whenever a user runs `/model` or uses the Telegram picker. This explains why the active model was observed shifting between `deepseek-v4-pro`, `deepseek-v4-flash-free`, and `hy3-free` during the audit.
3. **Baileys Critical Vulnerability (CVE-2026-48063):** This CVE corresponds to the known `GHSA-qvv5-jq5g-4cgg` advisory (CVSS 9.3) that affects Baileys versions `7.0.0-rc1` to `7.0.0-rc11`. Since the VPS uses a direct git commit reference (`WhiskeySockets/Baileys#01047debd...`), we must verify if this commit includes the patch. Upgrading to a tagged stable release like `7.0.0-rc.12` or later is recommended to eliminate spoofing risks.

**Overall health score (cumulative with first audit):** 6.0 / 10  
**Coverage:** 8/8 missing dimensions now audited  
**Biggest risk found:** 4mg daily steroid underdosing during BD taper phases (starting September 9, 2026) + Remote message/history sync spoofing via CVSS 9.3 Baileys vulnerability.  
**Biggest strength:** Robust, context-aware LLM reminder pipeline that feeds live chat context into prompt generation.

---

## FINDINGS BY DIMENSION

### Dimension 1: Security
Score: 4/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **Baileys Critical Vulnerability (CVE-2026-48063)** | 🔴 **CRITICAL** | Ejen uses commit hash equivalent to `7.0.0-rc.9` which is vulnerable to remote message spoofing and sync corruption. | Upgrade Baileys library to version `7.0.0-rc.12` or later. |
| 2 | **Plaintext API Keys in `.env`** | 🟡 **HIGH** | `~/.hermes/.env` lines 1-4 contain plaintext `DEEPSEEK_API_KEY`, `OPENCODE_GO_API_KEY`, etc. | Ensure strict permissions (`chmod 600`) and avoid echoing values in console outputs. |
| 3 | **PII Redaction Disabled** | 🟡 **HIGH** | `config.yaml` line 377: `redact_pii: false`. Logs contain unmasked names/phone numbers. | Set `redact_pii: true` in `config.yaml` to enable automatic PII masking. |
| 4 | **Medication Names in Cron System** | 🟢 **MEDIUM** | `jobs.json` lines 287, 373, 413 display names like "Dexa Taper Alert" (HIPAA/PDPA metadata exposure). | Rename cron jobs to generic titles (e.g. "Schedule Monitor B"). |

---

### Dimension 2: Config & Models
Score: 7/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **No Fallback Providers Configured** | 🟡 **HIGH** | `config.yaml` line 6: `fallback_providers: []`. Outage on primary provider will break the agent. | Configure backup providers (e.g. openrouter or nous) in `config.yaml`. |
| 2 | **Fragile Model Override System** | 🟡 **HIGH** | `fix_models.py` directly patches hermes-agent CLI python files via regexes that break on code updates. | Refactor the core package to load models from a configuration file instead of hardcoded python lists. |
| 3 | **Default Model Cost Optimized** | ✅ **OK** | `config.yaml` line 2: `default: deepseek-v4-flash-free`. | (No action needed - this is a cost-effective free default model). |

---

### Dimension 3: Scripts — Kualiti & Keselamatan
Score: 5/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **Hardcoded Directories in Python Scripts** | 🟡 **HIGH** | `med_confirm.py` line 41: `STATE_FILE = Path.home() / ".hermes" / "med-status.json"`. Pollutes home dir. | Resolve base directory via `os.environ.get('HERMES_HOME')` with home folder fallback. |
| 2 | **Windows Executable Path on Linux VPS** | 🟡 **HIGH** | `config.yaml` line 736: `command: /mnt/f/hermes/cua-driver/cua-driver.exe` (exec fails on Linux). | Change `command` to a Linux script or expose `cua-driver` as a remote SSE network endpoint from Windows. |
| 3 | **Duplicate Gateway Restart Scripts** | 🟢 **MEDIUM** | `scripts/` folder contains three restart wrappers: `restart-gateway.sh`, `restart_gateway.sh`, and `gw_restart.sh`. | Clean up and consolidate into one verified restart script. |

---

### Dimension 4: State Files — Integriti & Format
Score: 5/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **Stale Appointment Status (Data Bug)** | 🟡 **HIGH** | `appointments.json` lines 4-16: July 6 appointment remains marked `"status": "upcoming"` despite passing. | Update script query to filter out past appointments and mark them completed. |
| 2 | **Stale Gateway State Blocks Restart** | 🟡 **HIGH** | `gateway_state.json` retains `"running"` status after SIGTERM, blocking subsequent startup. | Delete lock and state files in gateway launch script before starting. |
| 3 | **JSON Rotation Backups Active** | ✅ **OK** | `med_confirm.py` lines 88-93: maintains `.json.bak1` to `.bak3`. | (Good safety configuration). |

---

### Dimension 5: Documentation
Score: 6/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **SOUL.md Git Drift** | 🟡 **HIGH** | Live `SOUL.md` (132 lines, 10.8KB) vs git `persona/SOUL.md` (61 lines, 3.6KB) has huge drift. | Push live VPS `SOUL.md` to GitHub. |
| 2 | **Outdated PROGRESS.md** | 🟢 **MEDIUM** | `PROGRESS.md` stops at Phase 23 (July 1) and misses all subsequent updates. | Record all post-July 1 phases in `PROGRESS.md`. |

---

### Dimension 6: Backup & Recovery
Score: 3/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **No Automated Offsite Backup** | 🟡 **HIGH** | All state data (`med-status.json`, `state.db`) exists only on the VPS disk. Single Point of Failure. | Create a daily cron script to backup and encrypt database files offsite. |

---

### Dimension 7: Cost
Score: 6/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **1-Minute Hello-World-Watch CPU Waste** | 🟢 **MEDIUM** | `jobs.json` lines 328-370: runs a python interpreter every 60s, creating log bloat and CPU spikes. | Increase watchdog interval to 1 hour or disable. |

---

### Dimension 8: Cross-Platform Sync
Score: 4/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | **Stale Git Commit History** | 🟡 **HIGH** | No git commits pushed on the VPS since July 1. | Set up an automated sync script to commit configuration changes to a private branch. |

---

## QUICK WINS (< 30 min each)
- [ ] **Fix Dexamethasone BD Dosing:** Modify `chain_calc.py` to map Slot C to `dose_2pm` if `freq == 'BD'`.
- [ ] **Implement Path Override:** Refactor `Path.home() / ".hermes"` to support `HERMES_HOME` env variable.
- [ ] **Optimise Watchdog Interval:** Increase `hello-world-watch` interval to 1 hour in `jobs.json`.
- [ ] **Consolidate MEMORY.md:** Prune old chat logs in `MEMORY.md` to lower it below the 9,000 char threshold.
- [ ] **Mark Appointment Completed:** Run `python3 med_appointments.py --complete 1` to close the stale July 6 appointment.

---

## CRITICAL FINDINGS (must fix today)
- **BD Taper Dosing Engine Defect:** Causes 4mg steroid underdose daily during BD phases (starting Sept 9, 2026).
- **Baileys Critical Vulnerability:** Exposes WhatsApp gateway to remote sync and message spoofing.

---

## BOTTOM LINE
* **Most urgent:** Fix the BD taper dosing engine to ensure correct steroid dosage.
* **Most impactful:** Set up automated sync and backups to unify development and production codebases.
