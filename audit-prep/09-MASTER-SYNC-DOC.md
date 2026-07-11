# MASTER SYNC DOC — VPS ↔ WSL2/Windows ↔ GitHub

> **PURPOSE:** Single unified handoff document for OpenCode to achieve 100% sync across all 3 platforms.
> **Combines:** `00-SYNC-UPDATE-2026-07-09.md` + `07-FULL-TIMELINE-0707-0709.md` + `08-EVIDENCE-APPENDIX.md`
> **Compiled:** 2026-07-09 11:30 MYT by Jane (MJ) on live VPS access.
> **For:** OpenCode (external auditor/executor) — has rsync + read-only SSH to VPS.

---

## 0. EXECUTIVE SUMMARY

The VPS (Singapore) is the **authoritative live system**. It has changes from 8/7-9/7 that are NOT in the Windows snapshot (`C:\Users\amiru\hermes-snapshot-20260707\`, dated 7/7, STALE) and NOT in GitHub (last commit Jul 1, stale 8 days).

**Two separate workstreams exist:**
1. **Audit/Sync** — config fixes, med system, audit-prep docs. → What OpenCode needs.
2. **Anti-bot research engine** — fragrantica scraping, fetcher/, AdaptiveRouter. → Already committed to git (hermes-live), separate concern.

**Critical user clarifications:**
- There is **NO "default" model** — user changes model ad-hoc via `/model`. config.yaml `default: hy3-free` is just fallback.
- Gemini's 2 "critical findings" (CVE-2026-48063, BD taper 4mg deficit) were **FABRICATED** — strike from any audit record.
- MiniMax API key issue = **IGNORED per user** (9/7 09:47).

---

## 1. PLATFORM STATE (verified 9/7)

| Platform | State | Last Sync | Action for OpenCode |
|----------|-------|-----------|---------------------|
| **VPS (live)** | Authoritative — has 9/7 fixes | NOW | Source of truth |
| **VPS git (`mjay/`)** | hermes-live branch, 7 commits 9/7 00:43-01:08 (anti-bot only) | 8 days behind for audit files | Commit 9/7 config fixes + audit-prep/ |
| **Windows PC / WSL2** | `C:\Users\amiru\hermes-snapshot-20260707\` | 7/7 (STALE) | Do NOT trust for current state; fresh rsync available at `~/hermes-snapshot-20260709/` on VPS |
| **GitHub** | `amirulhazym/hermes-agent-personal_assistant` main + hermes-live | Jul 1 (Phase 23) | Push hermes-live → main after audit |

---

## 2. FRESH SNAPSHOT (Phase B deliverable)

**Location on VPS:** `~/hermes-snapshot-20260709/` (3.2G)
**Excludes:** `.env`, `auth.json`, `whatsapp/session`, `*.db*`, `logs/`, `cache/`, `cron/output/`
**Contains:** config.yaml, hermes-agent/ (models.py, run.py), scripts/, skills/, audit-prep/, SOUL.md, med-*.json, dexa_taper.json, cron/jobs.json, vps-cron-list.txt, vps-git.txt, README-SNAPSHOT.md

OpenCode can rsync this folder or use read-only SSH to verify live.

---

## 3. CONFIG CHANGES (7/7 → 9/7, verified live)

| Setting | 7/7 baseline | 9/7 current | Changed by | Date |
|---------|-------------|-------------|------------|------|
| `model.default` | deepseek-v4-pro | hy3-free | Gemini Phase 1 | 7/7 23:58 |
| `model.provider` | opencode-go | opencode | Gemini Phase 1 | 7/7 23:58 |
| `model.base_url` | .../zen/go/v1 | .../zen/v1 | Gemini Phase 1 | 7/7 23:58 |
| `redact_pii` | false | true | Gemini Phase 1 | 7/7 23:58 |
| `mcp_servers` | cua-driver.exe | {} | Gemini Phase 1 | 7/7 23:58 |
| `providers` | {minimax block} | '{}' | Jane Fix #2 | 9/7 10:53 |
| `fallback_providers` | [] | [hy3-free, deepseek-v4-flash-free] | Jane Fix #3 | 9/7 10:55 |
| models.py hy3-free | absent | line 389 | Jane Fix #1 | 9/7 10:38 |
| run.py fallback warning | absent | [FALLBACK] @1637 | Jane Fix #3 | 9/7 10:55 |

**Raw config.yaml (verbatim, 9/7):**
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
redact_pii: true
mcp_servers: {}
```

---

## 4. FULL TIMELINE (7/7 evening → 9/7 10:38)

### 2026-07-07 (Night)
| Time | Event |
|------|-------|
| 20:18 | User frustrated about stale cron/med issues; pasted Gemini's first audit |
| 20:37 | User: "check balik kau dah fix betul2 ke belum!!" — demanded verification |
| 21:25 | Gemini read all audit-prep files + rsync VPS→WSL2 |
| 21:54 | Gateway confirmed running (PID 2400154, 8h uptime) |
| 23:25 | User pasted Gemini's full audit; assistant rated 4/10 (missed 8/11 dimensions) |
| 23:28 | **File 05-AGENT2-PROMPT.md created** (adversarial audit prompt) |
| 23:37 | User concerned .env exposed in snapshot; decided NOT to delete |
| 23:42 | **File 06-GEMINI-FOLLOWUP-PROMPT.md created**; Gemini claimed CVE-2026-48063 + BD 4mg deficit |
| 23:44 | User: "aku taknak kau hadam je, aku nak kau check, verify" |
| 23:58 | **Gemini deployed Phase 1 config fixes** (redact_pii, fallback, mcp_servers); gateway restarted (PID 2543798) |

### 2026-07-08
| Time | Event |
|------|-------|
| 00:03 | Dexa Reminder Cooldown Issue #4 (continuation) |
| 00:04 | **overhaul** session (main audit coordination) |
| 03:46 | Best Time to Take Akurit-4 — user wanted C~1pm not 2pm |
| 04:01 | **Default Model Misunderstanding Resolved** — user: "there is NO default model" |
| 04:03 | Clarifying 4am Medication Intent (116-msg, med timing flexibility) |
| 09:48 | Clarifying 4am Medication Intent #2 |
| 10:50 | Clarifying 4am Medication Intent #3 — "Dah makan dexa jam 4.30pm" |
| 12:28 | Failed image read auth error (vision tool) |
| 13:19 | Cron: vision-fix-gateway-restart |
| 21:31 | "E aku baru lepas makan, 9.30pm" (Letram confirmed) |
| 23:08 | **web-issues #1** — START anti-bot research (fragrantica CAPTCHA) |

### 2026-07-09 (Early)
| Time | Event |
|------|-------|
| 00:15-01:17 | web-issues #3-6 (anti-bot continued) |
| 00:43-01:08 | **GIT COMMITS** (hermes-live): Phase 1a→4+6 anti-bot engine (7 commits) |
| 06:03 | Pivot from RCA to capability benchmarking |
| 06:24 | Morning med confirmation (Slot A) |
| 07:00 | Cron: V2 Overnight Build Verify |
| 07:45 | Logging morning Dexa + Letram (B + E) |
| 08:55 | MiniMax M3 system setup — user asked model id/base_url/key |
| 09:38 | MiniMax #2 — user questioned why minimax→deepseek API |
| 09:47 | **User: ignore minimax entirely** |
| 10:17 | Recalling VPS audit setup context (alignment check with OpenCode's 3 Q) |
| 10:38 | MiniMax #3 — **Fix #1 applied** (hy3-free in models.py:389) |
| 10:53 | **Fix #2 applied** (providers: '{}') |
| 10:55 | **Fix #3 applied** (fallback chain + run.py warning) |
| 10:57 | Created 00-SYNC-UPDATE-2026-07-09.md |
| 10:58-11:07 | MiniMax #4 — user approved Phase A (full sweep), all phases approved, OpenCode = rsync + read-only SSH |

---

## 5. EVIDENCE APPENDIX (raw artifacts)

### A1. Cron List (6 active jobs, 9/7)
```
87d596fcfc0a  Log Rotate             0 6 * * 0     no-agent  local
c97c00f2fb46  Domino Chain Med Mon  */15 5-22 * *  no-agent  whatsapp
c8aa6f321848  Dexa Taper Alert       0 6 * * *     no-agent  whatsapp
91f561d0bbc7  Weekly Med Compliance  0 10 * * 0    no-agent  whatsapp
bd80225557d5  Appointment Reminder   0 20 * * *    no-agent  whatsapp
1bf7fcc00b60  V2 Overnight Build     0 7 * * *     whatsapp
```
Note: `hello-world-watch` (1m) from 7/7 GONE. LLM-driven jobs (Daily Health, etc.) also absent — terminated/migrated.

### A2. models.py:389
```python
        "deepseek-v4-flash-free",
        "mimo-v2.5-free",
        "nemotron-3-ultra-free",
        "hy3-free",          # ← ADDED 2026-07-09
```

### A3. run.py:1637
```python
        logger.warning("[FALLBACK] Primary provider auth failed: %s — trying fallback", auth_exc)
        fb_config = _try_resolve_fallback_provider()
        if fb_config is not None:
            fb_config["fallback_warning"] = f"⚠ Primary provider failed..."
```

### A4. .env VAR NAMES ONLY
```
DEEPSEEK_API_KEY, OPENCODE_ZEN_API_KEY, OPENCODE_GO_API_KEY, TELEGRAM_BOT_TOKEN,
TELEGRAM_ALLOWED_USERS, TELEGRAM_HOME_CHANNEL, WHATSAPP_ENABLED, WHATSAPP_ALLOWED_USERS,
WHATSAPP_MODE, WHATSAPP_HOME_CHANNEL, WHATSAPP_HOME_CHANNEL_THREAD_ID, OBSIDIAN_VAULT_PATH,
MINIMAX_API_KEY (UNUSED)
```

### A5. med-schedule.json (current)
```
A: 06:00  Akurit-4
B: 08:00  Levetiracetam + Dexamethasone
C: 12:00  Dexamethasone     ← user wanted ~1pm (8/7 discussion, NOT implemented)
D: 16:00  Dexamethasone
E: 20:00  Levetiracetam
extras: Pantoprazole (PRN)
```

### A6. Session IDs (8/7-9/7) — 27 total
Full list in `08-EVIDENCE-APPENDIX.md` A7. Key ones:
- `20260708_000411_fefbdf` overhaul
- `20260708_040109_1391fedc` Default Model Misunderstanding
- `20260708_230855_5e406fdd` web-issues #1 (anti-bot start)
- `20260709_110739_a017a3` MiniMax #4 (current, approved Phase A)

### A7. Git State
```
Branch: hermes-live
Last commits: 9/7 00:43-01:08 (anti-bot, 7 commits)
Uncommitted: audit-prep/, 10-solutions-anti-bot.md, build_overnight.*, fetcher/RCA_*, pending-tasks-*
NOT in repo: 9/7 config fixes (config.yaml, models.py, run.py) — live on VPS only
```

---

## 6. OPEN ITEMS FOR OPENCODE

- [ ] Commit 9/7 config fixes to git (config.yaml, models.py, run.py)
- [ ] Commit audit-prep/ (00-08 + FULL-GUIDE)
- [ ] Verify Windows snapshot stale — use fresh rsync instead
- [ ] B→C gap timing NOT implemented in dexa_taper.json (user wanted ~1pm)
- [ ] Strike Gemini's fabricated CVE + BD claims from any audit record
- [ ] Gateway stale-state bug still unfixed (known P0, manual rm workaround)
- [ ] Daily Health cron Broken Pipe — was it fixed? (Need verification)
- [ ] Med names in cron system — PII exposure (redact_pii:true helps logs, not job names)

---

## 7. ROLE AFTER HANDOFF

- **OpenCode:** Executor — deep audit + overhaul end-to-end. Has rsync + read-only SSH.
- **Jane (native agent):** Verifier — checks live VPS state, confirms OpenCode's changes are correct. Does NOT execute fixes.

---

*End of Master Sync Doc. All claims verified against live VPS config, git log, session DB. No memory-based assertions.*
