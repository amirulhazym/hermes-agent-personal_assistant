# EVIDENCE APPENDIX — Phase A (Raw Artifacts for OpenCode)

> **Purpose:** Raw, copy-pasteable artifacts so OpenCode can VERIFY every claim in `07-FULL-TIMELINE-0707-0709.md` without re-deriving from scratch.
> **All values captured live from VPS on 2026-07-09 11:20 MYT.**
> **Secrets:** Only `.env` VAR NAMES listed. No values. Ever.

---

## A1. HERMES CRON LIST (raw output, 6 active jobs)

```
  87d596fcfc0a [active]
    Name:      Log Rotate
    Schedule:  0 6 * * 0
    Script:    logrotate-run.sh
    Mode:      no-agent
    Deliver:   local
    Last run:  2026-07-05T06:00:31 ok

  c97c00f2fb46 [active]
    Name:      Domino Chain Medication Monitor
    Schedule:  */15 5-22 * * *
    Script:    chain_monitor.sh
    Mode:      no-agent
    Deliver:   whatsapp:120363428305511789
    Last run:  2026-07-09T11:15:33 ok

  c8aa6f321848 [active]
    Name:      Dexa Taper Alert
    Schedule:  0 6 * * *
    Script:    taper_alert.py
    Mode:      no-agent
    Deliver:   whatsapp
    Last run:  2026-07-09T06:00:25 ok

  91f561d0bbc7 [active]
    Name:      Weekly Med Compliance Report
    Schedule:  0 10 * * 0
    Script:    med_report.py
    Mode:      no-agent
    Deliver:   whatsapp
    Last run:  2026-07-05T10:00:34 ok

  bd80225557d5 [active]
    Name:      Appointment Reminder (day-before)
    Schedule:  0 20 * * *
    Script:    med_appt_daybefore.sh
    Mode:      no-agent
    Deliver:   whatsapp
    Last run:  2026-07-08T20:00:22 ok

  1bf7fcc00b60 [active]
    Name:      V2 Overnight Build Verify + Report
    Schedule:  0 7 * * *
    Deliver:   whatsapp
    Last run:  2026-07-09T07:01:24 ok
```

**Note:** `hello-world-watch` (every 1m) from 7/7 baseline is GONE — terminated between 7/7 and 9/7. `Daily Health` / `Daily Usage Report` / `Evening Check-in` / `Goal Check-in` / `Weekly Review` / `DeepSeek Balance Check` (LLM-driven jobs from 7/7) also absent — either terminated or migrated. OpenCode should diff against `01-VPS-BASELINE.md` (14 jobs) vs current (6 jobs).

---

## A2. CONFIG.YAML — Live Relevant Sections (verbatim)

```yaml
model:
  default: hy3-free
  provider: opencode
  base_url: https://opencode.ai/zen/v1
providers: '{}'
fallback_providers:
- provider: opencode-zen
  model: hy3-free
- provider: opencode-zen
  model: deepseek-v4-flash-free
credential_pool_strategies: {}
toolsets:
  # ... (rest unchanged)
redact_pii: true
mcp_servers: {}
```

**Compared to 7/7 baseline (01-VPS-BASELINE.md):**
| Key | 7/7 | 9/7 |
|-----|-----|-----|
| model.default | deepseek-v4-pro | hy3-free |
| model.provider | opencode-go | opencode |
| model.base_url | .../zen/go/v1 | .../zen/v1 |
| providers | {minimax block} | '{}' |
| fallback_providers | [] | [hy3-free, deepseek-v4-flash-free] |
| redact_pii | false | true |
| mcp_servers | (cua-driver.exe path) | {} |

---

## A3. MODELS.PY — hy3-free Addition (line 389)

File: `/home/ubuntu/.hermes/hermes-agent/hermes_cli/models.py`

```python
        # model disappears between audits.
        "deepseek-v4-flash-free",
        "mimo-v2.5-free",
        "nemotron-3-ultra-free",
        "hy3-free",          # ← ADDED 2026-07-09 (Fix #1)
    ],
    "opencode-go": [
```

Verify: `grep -n '"hy3-free"' /home/ubuntu/.hermes/hermes-agent/hermes_cli/models.py` → line 389

---

## A4. RUN.PY — Fallback Warning (line 1637)

File: `/home/ubuntu/.hermes/hermes-agent/gateway/run.py`

```python
        if is_rate_limited_auth_error(auth_exc):
            logger.warning("[FALLBACK] Primary provider rate-limited (429): %s — trying fallback", auth_exc)
        else:
            logger.warning("[FALLBACK] Primary provider auth failed: %s — trying fallback", auth_exc)
        fb_config = _try_resolve_fallback_provider()
        if fb_config is not None:
            fb_config = dict(fb_config)
            fb_config["fallback_warning"] = (
                f"⚠ Primary provider failed ({type(auth_exc).__name__}). "
                f"Using fallback: {fb_config.get('provider')}/{fb_config.get('model')}"
```

Verify: `grep -n '\[FALLBACK\]' /home/ubuntu/.hermes/hermes-agent/gateway/run.py` → lines 1637, 1639

---

## A5. .ENV — Variable Names Only (NO values)

```
DEEPSEEK_API_KEY
OPENCODE_ZEN_API_KEY
OPENCODE_GO_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_ALLOWED_USERS
TELEGRAM_HOME_CHANNEL
WHATSAPP_ENABLED
WHATSAPP_ALLOWED_USERS
WHATSAPP_MODE
WHATSAPP_HOME_CHANNEL
WHATSAPP_HOME_CHANNEL_THREAD_ID
OBSIDIAN_VAULT_PATH
MINIMAX_API_KEY
```

**Note:** `MINIMAX_API_KEY` exists but is UNUSED (provider block removed 9/7). User instructed to ignore minimax entirely (2026-07-09 09:47).

---

## A6. MED-SCHEDULE.JSON — Current Slot Structure

```json
{
  "version": "1.3",
  "meds": {
    "A": {"time": "06:00", "drugs": ["Akurit-4 (akurit_4)"]},
    "B": {"time": "08:00", "drugs": ["Levetiracetam (levetiracetam)", "Dexamethasone (dexamethasone_3)"]},
    "C": {"time": "12:00", "drugs": ["Dexamethasone (dexamethasone_3)"]},
    "D": {"time": "16:00", "drugs": ["Dexamethasone (dexamethasone_3)"]},
    "E": {"time": "20:00", "drugs": ["Levetiracetam (levetiracetam)"]}
  },
  "extras": ["Pantoprazole (PRN)"],
  "rules": ["akurit_empty_stomach", "dexamethasone_split", "levetiracetam_12h_gap", "shift_logic", "calcium_calcitriol_midday", "pantoprazole_prn"]
}
```

**B→C gap issue (from 8/7 session):** User wanted C ~1pm (not 12:00) to avoid last dose too late. NOT yet changed in this file. OpenCode should check if dexa_taper.json BD phase expects 2pm for C.

---

## A7. SESSION IDs — Full List (8/7 – 9/7) for Cross-Reference

| Session ID | Title | Date |
|------------|-------|------|
| 20260708_000345_04b689 | Dexa Reminder Cooldown Issue #4 | 8/7 |
| 20260708_000411_fefbdf | overhaul | 8/7 |
| 20260708_034635_9cd138db | Best Time to Take Akurit-4 | 8/7 |
| 20260708_040109_1391fedc | Default Model Misunderstanding Resolved | 8/7 |
| 20260708_040354_2f306699 | Clarifying 4am Medication Intent | 8/7 |
| 20260708_094801_967914 | Clarifying 4am Medication Intent #2 | 8/7 |
| 20260708_105014_5d37c2 | Clarifying 4am Medication Intent #3 | 8/7 |
| 20260708_122857_8cdfc954 | Failed image read auth error | 8/7 |
| 20260708_123849_2df1baa2 | untitled | 8/7 |
| 20260708_140201_78705a74 | untitled | 8/7 |
| 20260708_141747_393d31bb | untitled | 8/7 |
| 20260708_192310_e61d1971 | untitled | 8/7 |
| 20260708_213146_bb5e02cb | untitled (E confirmed 9.30pm) | 8/7 |
| 20260708_230855_5e406fdd | web-issues #1 | 8/7 |
| 20260708_234313_47445f | web-issues #2 | 8/7 |
| 20260709_001527_5926f4 | web-issues #3 | 9/7 |
| 20260709_003743_cc0a3d | web-issues #4 | 9/7 |
| 20260709_011704_88fc18 | web-issues #5 | 9/7 |
| 20260709_011719_89a31b | web-issues #6 | 9/7 |
| 20260709_060350_e1409420 | Pivot from RCA to capability benchmarking | 9/7 |
| 20260709_062457_dd35aa7e | Morning medication confirmation at 6am | 9/7 |
| 20260709_074552_827c4a58 | Logging morning Dexa and Letram doses | 9/7 |
| 20260709_085502_1d3a7949 | Checking MiniMax M3 system setup | 9/7 |
| 20260709_093853_2ae930 | Checking MiniMax M3 system setup #2 | 9/7 |
| 20260709_101712_ac1057a9 | Recalling VPS audit setup context | 9/7 |
| 20260709_103843_41b494 | Checking MiniMax M3 system setup #3 | 9/7 |
| 20260709_110739_a017a3 | Checking MiniMax M3 system setup #4 | 9/7 |

**Note:** `started_at` column in state.db is corrupted (returns 1970). Use ID prefix for date.

---

## A8. GIT STATE — mjay repo

```bash
Branch: hermes-live
Last commits (all 2026-07-09 00:43–01:08):
  ece3de5 Phase 4+6: BrowserAct stub, ContentCache, CLI, DeliveryLog
  1cc6b19 AdaptiveRouter: capability-based executor selection + cost optimizer
  12f5c77 Phase 2 (best-effort): Adaptive Router + Capability Registry
  b1915bb Phase 1c: Crawl4AI executor live-verified
  e651b21 Phase 1c: Crawl4AI executor (BrowserExecutor impl)
  439e93f Phase 1b: FlareSolverr executor + Parfumo bypass verified
  497c36e Phase 1a: foundation — executor interface, Document contract

Uncommitted (untracked):
  audit-prep/          ← ALL audit files (00-08, FULL-GUIDE)
  10-solutions-anti-bot.md
  build_overnight.py
  build_overnight.stdout
  build_overnight_STATUS.json
  fetcher/RCA_FRAGRANTICA_NETWORK_IDENTITY.md
  pending-tasks-comprehensive.md
  fetcher/__pycache__/*.pyc

Modified (tracked):
  fetcher/__pycache__/router.cpython-312.pyc  (binary, ignore)
```

**CRITICAL:** The 9/7 config fixes (config.yaml, models.py, run.py) are in `~/.hermes/hermes-agent/` — NOT in mjay/ repo. They are live on VPS but NOT committed anywhere. OpenCode must rsync `~/.hermes/` to capture them.

---

## A9. WINDOWS SNAPSHOT — Known Stale State

Path: `C:\Users\amiru\hermes-snapshot-20260707\` (user confirmed exists, title = 7/7)

Stale because:
- Captured 2026-07-07 evening (before 8/7-9/7 sessions)
- Missing: 9/7 config.yaml changes, models.py:389, run.py:1637
- Missing: 8/7 med timing discussions (B→C gap)
- Has: OLD config (deepseek-v4-pro, opencode-go, fallback_providers: [])
- Contains: `.env` copy (user chose not to delete — SECURITY RISK if PC compromised)

OpenCode should NOT trust this snapshot for current state. Use fresh rsync (Phase B).

---

## A10. GATEWAY STALE-STATE BUG — Evidence Pointer

- File: `~/.hermes/gateway_state.json`
- Known bug: after SIGTERM, file persists `"running": true`, blocks restart
- Fix: `rm ~/.hermes/gateway_state.json` before restart
- Still UNFIXED as of 9/7 (no code change, only manual workaround)
- OpenCode should check `gateway/run.py` launch sequence for where state is written

---

## A11. ANTI-BOT WORKSTREAM — Separate from Audit

Commits on hermes-live (9/7 00:43-01:08):
- `fetcher/` — anti-bot research engine (AdaptiveRouter, executors)
- `build_overnight.py` — overnight build script
- Not related to audit/sync. OpenCode can ignore for sync purposes unless asked.

---

*End of Evidence Appendix. All artifacts captured live 2026-07-09 11:20 MYT.*
