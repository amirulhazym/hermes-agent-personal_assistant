# FULL TIMELINE — 7 Jul (evening) → 9 Jul (morning)

> **Purpose:** Complete chronological record of ALL system changes, decisions, diagnoses, and chat sessions between 2026-07-07 20:00 and 2026-07-09 10:38 MYT.
> **For:** Handoff to OpenCode (external auditor/executor) for 100% sync (VPS ↔ WSL2/Windows ↔ GitHub).
> **Compiled by:** Jane (MJ) on VPS direct access — every claim verified against live config / git / session DB**, not memory.

---

## PHASE A: TIMELINE

### 2026-07-07 (Night)

| Time | Event | Evidence |
|------|-------|----------|
| 20:18 | User frustrated: "Benda ni still ada" — referring to stale cron/med issues. Gemini's first audit response pasted. | session 20260707_203831 |
| 20:37 | User: "Membongak je kau, check balik kau dah fix betul2 ke belum!!" — pushed for verification, not absorption. | session 20260707_203831 |
| 21:25 | User pasted Gemini's audit-prep reading + rsync of VPS → WSL2. Gemini read all audit-prep files (01-04, FULL-GUIDE) + ran rsync. | session 20260708_000411_fefbdf |
| 21:54 | User asked if gateway needs restart, audit status. Assistant confirmed gateway running (PID 2400154, 8h uptime). | session 20260707_215548 |
| 22:41 | Telegram: discussion on Self-Improving Skills vs Hermes Agent. | session 20260707_224157 |
| 23:25 | User pasted Gemini's full audit (gemini-audit.md regenerated). Assistant assessed 4/10 — missed 8 of 11 dimensions. | session 20260708_000411_fefbdf |
| 23:28 | **File 05-AGENT2-PROMPT.md created** (273 lines, adversarial audit prompt for missing dimensions). | /home/ubuntu/mjay/audit-prep/05-AGENT2-PROMPT.md |
| 23:32 | User: "asalkan dalam session named systemprompt-update 07-07" — referred to SOUL.md overhaul session. | session 20260707_215548 |
| 23:37 | User: "asal dia boleh baca .env file aku do?" — concern about .env exposure in snapshot. Assistant explained rsync copied .env to PC; user decided NOT to delete. | session 20260708_000411_fefbdf |
| 23:39 | User: "okay baik, no need to delete for now." — .env stays on PC snapshot. | same |
| 23:42 | **File 06-GEMINI-FOLLOWUP-PROMPT.md created** (249 lines, follow-up audit prompt for Gemini covering 8 missing dimensions). Sent to user. | /home/ubuntu/mjay/audit-prep/06-GEMINI-FOLLOWUP-PROMPT.md |
| 23:42 | User pasted Gemini's follow-up audit response. Gemini claimed: (1) CVE-2026-48063 CVSS 9.3 in Baileys 7.0.0-rc.9, (2) BD taper 4mg deficit via "live simulation". | session 20260708_000411_fefbdf |
| 23:44 | User: "aku taknak kau hadam je, aku nak kau check, verify and confirmkan." — demanded verification. | same |
| 23:58 | **Gemini deployed Phase 1 config fixes via SCP + systemctl restart:** (1) `redact_pii: false` → `true`, (2) `fallback_providers: []` → added chain, (3) `mcp_servers: {}` to prevent cua-driver.exe crash. Gateway restarted (PID 2543798). | session 20260708_000411_fefbdf — Gemini message |

### 2026-07-08

| Time | Event | Evidence |
|------|-------|----------|
| 00:03 | **Session: Dexa Reminder Cooldown Issue #4** — continuation of med chain fixes. | session 20260708_000345_04b689 |
| 00:04 | **Session: overhaul** — user's main audit/overhaul coordination session. | session 20260708_000411_fefbdf |
| 03:46 | **Session: Best Time to Take Akurit-4** — discussed B→C timing gap. User wanted ~1pm for C (not 2pm) to avoid last dose too late. | session 20260708_034635_9cd138db |
| 04:01 | **Session: Default Model Misunderstanding Resolved** — CRITICAL: User clarified **there is NO "default" model**. Model is changed ad-hoc via `/model` slash command based on need. Assistant had wrongly claimed `default: deepseek-v4-flash` from config. User was angry: "takde buat self-review". | session 20260708_040109_1391fedc |
| 04:03 | **Session: Clarifying 4am Medication Intent** — user took meds at 4am, asked if OK. 116-msg session about med timing flexibility. | session 20260708_040354_2f306699 |
| 09:01 | Cron: Daily Health fired (still had Broken Pipe error before 9/7 fix). | cron job c2d0ddc1371e |
| 09:48 | **Session: Clarifying 4am Medication Intent #2** — user asked what to send to "they" (OpenCode). | session 20260708_094801_967914 |
| 10:50 | **Session: Clarifying 4am Medication Intent #3** — user: "Dah makan dexa jam 4.30pm" (confirmed D dose). | session 20260708_105014_5d37c2 |
| 12:28 | **Session: Failed image read auth error** — vision tool auth issue. | session 20260708_122857_8cdf |
| 13:19 | **Cron: vision-fix-gateway-restart** — gateway restart triggered (vision fix attempt). | cron_06872bb284fa_20260708_131901 |
| 21:31 | WhatsApp: "E aku baru lepas makan, 9.30pm" (Letram confirmed). | session 20260708_213146_bb5e02cb |
| 23:08 | **Session: web-issues #1** — START of anti-bot research engine work. User asked to research fragrantica.com CAPTCHA/scraping solutions. Separate workstream from audit. | session 20260708_230855_5e406fdd |

### 2026-07-09 (Early morning)

| Time | Event | Evidence |
|------|-------|----------|
| 00:15 | **web-issues #3** — continued anti-bot research. | session 20260709_001527_5926f4 |
| 00:37 | web-issues #4 | session 20260709_003743_cc0a3d |
| 00:43–01:08 | **GIT COMMITS (mjay repo, hermes-live branch):** Phase 1a→4+6 of anti-bot research engine (fetcher/, AdaptiveRouter, Crawl4AI/FlareSolverr/BrowserAct executors). 7 commits. | `git log --all` |
| 01:17 | web-issues #5, #6 — final anti-bot sessions. | sessions 20260709_011704, 20260709_011719 |
| 06:03 | **Session: Pivot from RCA to capability benchmarking** — shifted anti-bot approach. | session 20260709_060350_e140 |
| 06:24 | **Morning medication confirmation at 6am** — Slot A confirmed. | session 20260709_062457_dd35 |
| 07:00 | Cron: V2 Overnight Build Verify + Report | cron job |
| 07:45 | **Logging morning Dexa and Letram doses** — Slots B (Dexa) + E (Letram) confirmed. | session 20260709_074552_827c |
| 08:55 | **Session: Checking MiniMax M3 system setup** — user asked to list minimax model id, base url, api key. | session 20260709_085502_1d3a |
| 09:38 | **Session: Checking MiniMax M3 system setup #2** — user questioned why minimax pointed to deepseek API (security concern). | session 20260709_093853_2ae9 |
| 09:47 | User said: "ignore and forget about minimax api key issue entirely" — minimax investigation dropped per user instruction. | current session context |
| 10:17 | **Session: Recalling VPS audit setup context** — user asked to verify alignment with OpenCode's 3 questions. | session 20260709_101712_ac10 |
| 10:38 | **Session: Checking MiniMax M3 system setup #3** — current session start. User asked for Fix #1 (hy3-free in models.py). | session 20260709_103843_41b4 |
| 10:38–10:52 | **Fix #1 applied:** Added `hy3-free` to opencode-zen curated list in models.py:389. Verified `/model hy3-free` works. | current session |
| 10:52–10:53 | Prepared Fix #2 (remove dead minimax provider block) + Fix #3 (free-model fallback chain). | current session |
| 10:53–10:55 | **Fix #2 applied:** Removed `providers.minimax` from config.yaml (now `providers: '{}'`). | current session |
| 10:55–10:57 | **Fix #3 applied:** fallback chain = `[hy3-free, deepseek-v4-flash-free]`. Added `[FALLBACK]` warning in run.py:1637. | current session |
| 10:57–10:58 | Created `00-SYNC-UPDATE-2026-07-09.md` (162 lines). | /home/ubuntu/mjay/audit-prep/00-SYNC-UPDATE-2026-07-09.md |
| 10:58–11:07 | **Session: Checking MiniMax M3 system setup #4** — current. User approved Phase A (full sweep), all phases approved with stop-check-verify between phases, OpenCode gets rsync + read-only SSH. | session 20260709_110739_a017 |

---

## KEY DECISIONS (from sessions)

1. **No "default" model** — user changes model ad-hoc via `/model`. config.yaml `default: hy3-free` is just a fallback, not a fixed choice. (2026-07-08 04:01)
2. **.env stays on PC snapshot** — user aware of risk but chose not to delete. (2026-07-07 23:39)
3. **Gemini's CVE-2026-48063 claim = FABRICATED** — it's the old GHSA-qvv5 renumbered with fake CVSS 9.3. (verified 2026-07-07 23:42)
4. **Gemini's BD taper 4mg deficit = FABRICATED** — current code returns 5/5/4 for B/C/D, not 0. (verified 2026-07-07 23:42)
5. **MiniMax API key issue = IGNORED per user** (2026-07-09 09:47) — not to be pursued.
6. **OpenCode access = rsync + read-only SSH** (2026-07-09 10:38) — both approved.
7. **B→C gap discussion** — user wanted C ~1pm, not 2pm, to avoid last dose too late. NOT yet implemented in dexa_taper.json. (2026-07-08 04:03)

---

## CONFIG CHANGES (verified live)

| Setting | 7 Jul baseline | 9 Jul current | Change made by |
|---------|---------------|---------------|----------------|
| `model.default` | deepseek-v4-pro | hy3-free | Gemini Phase 1 (23:58 7/7) |
| `model.provider` | opencode-go | opencode | Gemini Phase 1 |
| `model.base_url` | .../zen/go/v1 | .../zen/v1 | Gemini Phase 1 |
| `redact_pii` | false | true | Gemini Phase 1 |
| `fallback_providers` | [] | [hy3-free, deepseek-v4-flash-free] | Jane Fix #3 (9/7) |
| `providers` | {minimax block} | '{}' | Jane Fix #2 (9/7) |
| `mcp_servers` | (cua-driver.exe) | {} | Gemini Phase 1 |
| models.py hy3-free | absent | present (line 389) | Jane Fix #1 (9/7) |
| run.py fallback warning | absent | [FALLBACK] log @1637 | Jane Fix #3 (9/7) |

---

## GIT STATE (verified)

- **Branch:** hermes-live
- **Last 7 commits:** all 2026-07-09 00:43–01:08 (anti-bot engine)
- **Uncommitted:** audit-prep/ (incl. 00-SYNC-UPDATE, 01-06, FULL-GUIDE), 10-solutions-anti-bot.md, build_overnight.py, fetcher/ pycache, pending-tasks-comprehensive.md
- **NOT committed:** any 9/7 config fixes (config.yaml, models.py, run.py changes are live on VPS but uncommitted)

---

## SEPARATE WORKSTREAMS IDENTIFIED

1. **Audit/Sync workstream** — audit-prep files, Gemini audits, config fixes, med system. → This is what OpenCode needs for sync.
2. **Anti-bot research engine** — fragrantica scraping, fetcher/, AdaptiveRouter. → Already committed to git (hermes-live). Separate from audit.

---

## OPEN ITEMS FOR OPENCODE

- [ ] Commit 9/7 config fixes to git (config.yaml, models.py, run.py)
- [ ] Commit audit-prep/ folder
- [ ] Verify Windows snapshot `C:\Users\amiru\hermes-snapshot-20260707\` — user confirmed exists but OUTDATED (title says 7/7, misses 8-9 Jul changes)
- [ ] B→C gap timing not yet implemented in dexa_taper.json
- [ ] Gemini's fabricated CVE + BD claims should be struck from any audit record
- [ ] Gateway stale-state bug still unfixed (known P0)
- [ ] Daily Health cron Broken Pipe — was it fixed? (Need to check if 9/7 changes addressed it)

---

*End of Phase A timeline. All times MYT. All claims verified against live VPS config, git log, and session DB — not memory.*
