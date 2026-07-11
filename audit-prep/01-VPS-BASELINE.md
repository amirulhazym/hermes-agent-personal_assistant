# VPS Baseline — Complete Hermes Agent System Inventory

> **Generated:** Tuesday, July 7, 2026 — 12:15 MYT  
> **Server:** Tencent Lighthouse, Singapore (119.28.119.151)  
> **Purpose:** Full inventory for external AI agent cross-platform audit  
> **Profile:** default

---

## 1. System Overview

| Metric | Value |
|---|---|
| Hostname | VM-0-17-ubuntu |
| OS | Ubuntu 24.04.4 LTS (x86_64) |
| Kernel | 6.8.0-124-generic |
| Python | 3.11.15 (default), 3.12 via pip mismatch |
| Uptime | 6 days 18:40 |
| Disk | 40G total — 16G used (43%) — 22G free |
| RAM | 1.9G total — 756M used — 149M free — 1.2G avail |
| Load Avg | 0.10 / 0.05 / 0.01 |
| IP | 119.28.119.151 (Singapore — datacenter IP) |
| Hermes Version | v0.17.0 |
| Config Version | v31 |

---

## 2. Model & Provider Configuration

```yaml
model:
  default: deepseek-v4-pro
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
agent:
  reasoning_effort: xhigh
  max_turns: 60
  gateway_timeout: 1800
auxiliary:
  vision:
    provider: opencode-zen
    model: mimo-v2.5-free
    base_url: https://opencode.ai/zen/v1
```

**Provider Setup (from .env):**
- `OPENCODE_GO_API_KEY` — paid subscription ($5 first month → $10/month)
- `OPENCODE_ZEN_API_KEY` — free tier (vision + fallback)
- `NVIDIA_API_KEY` — free tier (5 curated models)
- `DEEPSEEK_API_KEY` — pay-per-use (CNY balance, ~RM2-3/month)

**Model Override System:**
- `fix_models.py` / `fix-models.sh` — runs after `hermes update` to restore curated model lists
- NVIDIA: 5 curated models (minimaxai/minimax-m3, moonshotai/kimi-k2.6, deepseek-ai/deepseek-v4-flash, deepseek-ai/deepseek-v4-pro, z-ai/glm-5.1)
- OpenCode Zen: 3 curated models (deepseek-v4-flash-free, mimo-v2.5-free, nemotron-3-ultra-free) — 3 dead models removed after live API verification
- OpenCode Go: 13 curated models
- Google Gemini: Fully removed (code + plugin renamed to `_gemini/`)
- MoA (Mixture of Agents): Removed from picker

**Prompt Caching:** 5-minute TTL, enabled

---

## 3. Cron Jobs — Complete Inventory (14 Active)

### System Jobs (LLM-Driven)

| ID | Name | Schedule | Provider | Deliver | Last Status |
|---|---|---|---|---|---|
| 4c0b50c379d6 | **Evening Check-in** | 0 21 * * * | deepseek-v4-flash | whatsapp | ✅ ok |
| 5913f13f40c7 | **Daily Usage Report** | 0 8 * * * | deepseek-v4-flash | telegram | ✅ ok |
| 36a78c55962e | **Goal Check-in** | 0 20 * * 1,3,5 | deepseek-v4-flash | whatsapp | ✅ ok |
| 1353eafcddb2 | **Weekly Review** | 0 10 * * 0 | deepseek-v4-flash | telegram | ✅ ok |
| c2d0ddc1371e | **Daily Health** | 0 9 * * * | deepseek-v4-flash | telegram | 🔴 error: Broken pipe |
| e5df4a1384c0 | **DeepSeek Balance Check** | 0 9 * * 1,5 | deepseek-v4-flash | telegram | ✅ ok |

### Script Jobs (No-Agent — stdout delivered directly)

| ID | Name | Schedule | Script | Deliver | Last Status |
|---|---|---|---|---|---|
| 87d596fcfc0a | **Log Rotate** | 0 6 * * 0 | logrotate-run.sh | local | ✅ ok |
| c97c00f2fb46 | **Domino Chain Medication Monitor** | */15 5-22 * * * | chain_monitor.sh | whatsapp:120363428305511789 | ✅ ok (318 completed) |
| 67efe5d502bc | **hello-world-watch** | every 1m | hello_watch.py | whatsapp:120363428305511789 | ✅ ok (1873 completed) |
| c8aa6f321848 | **Dexa Taper Alert** | 0 6 * * * | taper_alert.py | whatsapp | ✅ ok (2 completed) |
| 91f561d0bbc7 | **Weekly Med Compliance Report** | 0 10 * * 0 | med_report.py | whatsapp | ✅ ok |
| bd80225557d5 | **Appointment Reminder (day-before)** | 0 20 * * * | med_appt_daybefore.sh | whatsapp | ✅ ok |
| 4dedd0e5bbbe | **Memory Watchdog** | 0 9 * * * | memory_watch.py | telegram | ✅ ok |

### One-Shot Jobs

| ID | Name | Schedule | Deliver | Status |
|---|---|---|---|---|
| cb2f4b5bb3ba | **2pm Medical Update Reminder** | once at 2026-07-07 14:00 | origin | pending |

### ❌ Terminated Jobs

| Original ID | Name | Terminated | Reason |
|---|---|---|---|
| 618dceeabcaa | **Morning Briefing** | 2026-07-07 11:09 | User never requested — agent self-initiated without consent. Ran 7 times. |

---

## 4. Scripts Directory (`~/.hermes/scripts/`)

All scripts live in `/home/ubuntu/.hermes/scripts/`. 27 files total.

| Script | Type | Purpose | Modified |
|---|---|---|---|
| `chain_monitor.sh` | Shell (no_agent cron) | Domino Chain Medication Monitor — reads chain_calc.py output, calls chain_llm.py for context-aware reminders | Jul 4 |
| `chain_calc.py` (38KB) | Python | Calculates medication chain state, ready times, escalation levels, drug-level tracking v2 | Jul 5 |
| `chain_llm.py` (15KB) | Python | Generates medication reminders using SAME LLM model as chat session (reads config.yaml for active provider) | Jul 7 |
| `med_confirm.py` (21KB) | Python | Drug-level medication confirmation with --dry-run, --reset, auto-backup (.bak1-3) | Jul 7 |
| `med_resolve.py` (10KB) | Python | Resolves drug name shorthands to drug_id + slot (alias table) | Jul 7 |
| `med_report.py` (8KB) | Python | Weekly medication compliance report generation | Jul 5 |
| `med_supply.py` (8KB) | Python | Medication supply tracking, decrement, refill, low-stock warnings | Jul 5 |
| `med_interact.py` (6KB) | Python | Drug interaction checker for current regimen | Jul 5 |
| `med_substitute.py` (4KB) | Python | Medication substitution database query | Jul 5 |
| `med_appointments.py` (7KB) | Python | Medical appointment tracker, tomorrow-check | Jul 5 |
| `med_appt_daybefore.sh` | Shell | Wrapper for Appointment Reminder cron | Jul 5 |
| `taper_alert.py` (7KB) | Python | Dexamethasone tapering phase transition alert | Jul 5 |
| `billing.py` (17KB) | Python | Unified API billing checker (DeepSeek + OpenCode Go + self-tracked) | Jul 3 |
| `fix_models.py` (16KB) | Python | Post-hermes-update model override restoration (replaces broken fix-models.sh heredoc) | Jul 5 |
| `fix-models.sh` | Shell | Thin wrapper → exec fix_models.py | Jul 3 |
| `health_check.py` (9KB) | Python | Independent health monitor via Linux system cron (not Hermes cron) | Jul 5 |
| `health_state.json` | JSON | Health monitor state file | Jul 7 |
| `hello_watch.py` (1.5KB) | Python | Hello World delivery watchdog — delivers on gateway restart | Jul 4 |
| `hello-world.sh` | Shell | Cross-platform sync update message (Option A fixes notification) | Jul 1 |
| `memory_watch.py` (4KB) | Python | Memory usage watchdog — alerts when MEMORY.md/USER.md near limit | Jul 5 |
| `watchdog.sh` (2KB) | Shell | Gateway watchdog v3 — detects stale-but-alive, cleans gateway_state.json | Jun 30 |
| `logrotate-run.sh` | Shell | Hermes log rotation (no_agent cron) | Jun 30 |
| `check_ds_balance.sh` | Shell | DeepSeek API balance check | Jun 30 |
| `restart-gateway.sh` | Shell | Gateway restart via systemctl | Jul 3 |
| `restart_gateway.sh` | Shell | Gateway kill + auto-restart | Jul 2 |
| `gw_restart.sh` | Shell | systemctl restart wrapper | Jul 2 |
| `qwen_driver.py` | Python | Qwen LM driver via cua-driver MCP (Brave browser automation) | Jun 30 |
| `sakana_driver.py` | Python | Sakana AI driver via cua-driver MCP | Jun 30 |

---

## 5. Active Plugins

| Plugin | Type | Purpose |
|---|---|---|
| `hybrid-web` | User Plugin | Intelligent web extraction routing — static (Trafilatura) vs JS-heavy (Crawl4AI) |
| `lightclawbot` | Platform Plugin | WhatsApp bridge (Baileys-based, 14 source files) |

**Disabled Plugins:**
- `_gemini/` — Google Gemini provider (physically renamed to prevent auto-extend from resurrecting via .pyc)

---

## 6. State Files — Complete Inventory

All state files live in `/home/ubuntu/.hermes/`.

| File | Size | Modified | Purpose |
|---|---|---|---|
| `med-status.json` | 6.7KB | Jul 7 08:20 | Drug-level medication intake log (today's entries) |
| `med-schedule.json` | 4.5KB | Jul 7 10:03 | Medication schedule v1.3 — drug per slot with drug_id, timing, dosage |
| `med-supply.json` | 3.3KB | Jul 7 10:05 | Drug supply tracking (quantity, refill dates) |
| `med-interactions.json` | 5.5KB | Jul 5 09:16 | Drug interaction database |
| `substitutions.json` | 4.3KB | Jul 5 09:14 | Drug substitution database |
| `dexa_taper.json` | 7.2KB | Jul 5 10:01 | Dexamethasone tapering schedule (3 phases: TDS → BD → OD) |
| `chain-state.json` | 244B | Jul 7 12:00 | Domino Chain medication reminder state |
| `appointments.json` | 449B | Jul 5 20:11 | Medical appointment records |
| `gateway_state.json` | 532B | Jul 7 10:36 | Gateway PID and platform status (known stale-state bug) |
| `channel_directory.json` | 1.6KB | Jul 7 12:15 | Platform channel directory |
| `auth.json` | 1.7KB | Jul 4 15:09 | Hermes platform auth credentials |
| `processes.json` | 2B | Jul 7 10:36 | Process state |
| `provider_models_cache.json` | 587B | Jul 5 20:06 | Cached provider models |
| `models_dev_cache.json` | 2.9MB | Jul 7 12:12 | Development model cache |
| `state.db` | ~50MB | — | SQLite session store (119 sessions) |
| `kanban.db` | ~1MB | — | Kanban task board |

---

## 7. Skills Library — 110 Skills

**67 builtin + 43 local = 110 enabled, 0 disabled**

### Key Local Skills (User-Created / User-Installed)

| Category | Skills |
|---|---|
| **agent-best-practices** | context-engineering, debugging-and-error-recovery, doubt-driven-development, incremental-implementation, planning-and-task-breakdown |
| **agent-methodology** | brainstorming, dispatching-parallel-agents, evidence-first-feasibility-assessment, executing-plans, subagent-driven-development, using-superpowers, verification-before-completion, writing-plans |
| **software-development** | anti-fabrication-guardrails, codebase-design, diagnosing-bugs, domain-modeling, finishing-a-development-branch, malaysia-country-selector-interaction, prototype, receiving-code-review, system-verification-qa, writing-great-skills, writing-skills |
| **devops** | cost-tracking, system-self-monitor, using-git-worktrees |
| **med-tracker** | Auto-detect medication confirmations and trigger med_confirm.py |
| **research** | malaysia-telco-research, medication-safety-research |
| **productivity** | handoff, petdex, teach, to-issues, to-prd |
| **design** | ai-design-workflow, taste-skill, ui-ux-pro-max |
| **other** | auto-skill-suggester, hermes-no-agent-cron-pattern, morning-briefing-removal-note, adhd-daily-planning |

---

## 8. Persona Files

### SOUL.md (Live System Prompt)
- **Path:** `/home/ubuntu/.hermes/SOUL.md`
- **Size:** 10.8KB, 132 lines
- **Modified:** July 7 (today's systemprompt-update session)
- **Full content is the system prompt injected into every session** — see file on disk for complete text
- Contains: communication style rules, epistemic standards (9-point), geo-sensitive query protocol, skill trigger system, tool-use enforcement, parallel tool calling, memory management, DND mode, infrastructure context

### MEMORY.md
- **Path:** `/home/ubuntu/.hermes/memories/MEMORY.md`
- **Char limit:** 9,000
- **Current usage:** ~8,855 chars (98%)
- Contains: medical tracking prefs, medication defaults, med system v2 drug-level details, MJ persona, cron times, ADHD safety net, user preferences/lessons learned

### USER.md
- **Path:** `/home/ubuntu/.hermes/memories/USER.md`
- **Char limit:** 1,375
- **Current usage:** ~1,170 chars (85%)
- Contains: user profile (Amirulhazym), education, health info, preferences

---

## 9. Gateway Status

- **State:** Running
- **PID in gateway_state.json:** Present
- **WhatsApp bridge:** node bridge.js (PID varies) on port 3000
- **cua-driver MCP:** Subprocess of gateway
- **Stale-state bug:** Known — after SIGTERM, gateway_state.json persists "running", blocks restart. Fix: `rm ~/.hermes/gateway_state.json`

---

## 10. mjay/ Git Repository

**Path:** `/home/ubuntu/mjay/`  
**Branch:** `hermes-live`  
**Remote:** `origin/main` → `github.com/amirulhazym/hermes-agent-personal_assistant`  
**Status:** Working tree clean, no uncommitted changes  
**Last commits (none since Phase 23 era):**

| Commit | Date | Description |
|---|---|---|
| a48fda5 | 2026-07-01 04:42 | hermes: git workflow setup (.gitignore, workflow doc) |
| e570aaf | 2026-07-01 04:42 | Update scripts: line-ending fixes + gateway backup |
| 0f49c2a | 2026-07-01 04:42 | Option C build start |
| 31f11a8 | 2026-07-01 04:42 | Phase 23: Design Methodology skill |
| 1a3a398 | 2026-07-01 04:42 | Phase 22: Install 13 design skills |

**Key Documentation Files in Repo:**

| File | Last Modified | Purpose |
|---|---|---|
| PROGRESS.md | Jul 1 04:42 | Phase tracking (Phase 0-23) |
| DECISIONS.md | Jul 1 04:42 | Decision log with verified facts |
| README.md | Jul 1 04:42 | Project overview |
| RUNBOOK.md | Jul 1 04:42 | Operational documentation |
| AUDIT.md | Jul 1 04:42 | System snapshot for external audit |
| CLAUDE_AUDIT_PROMPT.md | Jul 1 04:42 | Structured audit prompt template |
| NEW_AUDIT_PROMPT.md | Jul 1 04:42 | Free-form audit prompt for exploration |
| AGENTS.md | Jul 1 04:42 | Agent safety rules + commit policy |
| persona/SOUL.md | Jul 1 04:42 | OLD SOUL.md (61 lines — OUTDATED) |
| persona/MEMORY.md | Jul 1 04:42 | Archived memory snapshot |
| persona/USER.md | Jul 1 04:42 | Archived user profile |

**⚠️ NOTE:** All timestamps in the repo are Jul 1 04:42 because they were committed in one batch. Real modification dates before this are unknown. These files may be OUTDATED compared to the live system.

---

## 11. Existing Audit Trail

**Location:** `/home/ubuntu/mjay/audits/`

| File | Auditor | Date | Size | Status |
|---|---|---|---|---|
| zhipu1-audit.md | Zhipu Chat | Jun 28 | 30KB | COMPLETE |
| zhipu2-audit.md | Zhipu Agent | Jun 28 | 90KB | COMPLETE |
| zhipu-exploration-audit.md | Zhipu (free-form) | Jun 28 | 30KB | COMPLETE |
| qwen-audit.md | Qwen | Jun 28 | 10KB | COMPLETE |
| sakana-audit.md | Sakana | Jun 28 | 75B | NOT STARTED |
| claude-audit.md | Claude | Jun 28 | 13KB | COMPLETE |
| opencode-go-addendum.md | MJ | Jun 28 | 4KB | COMPLETE |

**Consensus Findings Across All Auditors:**
1. Baileys critical vulnerability (GHSA-qvv5-jq5g-4cgg)
2. API keys exposed in plaintext — need rotation
3. gateway_state.json stale-state bug blocks restart
4. No automated backup / DR — single F: drive SPOF
5. Model overrides via source patching — fragile on hermes update
6. No provider fallback — OpenCode Zen was SPOF (now partially addressed by OpenCode Go paid subscription)
7. Medication names in cron system — health data exposure risk

---

## 12. File Age Map — Key Files by Last Modified

| File | Modified | Category |
|---|---|---|
| `chain-state.json` | Jul 7 12:00 | State |
| `skills_prompt_snapshot.json` | Jul 7 11:35 | Skills |
| `channel_directory.json` | Jul 7 12:15 | Platform |
| `chain_llm.py` | Jul 7 10:06 | Script |
| `med_confirm.py` | Jul 7 10:07 | Script |
| `med_resolve.py` | Jul 7 10:06 | Script |
| `med-schedule.json` | Jul 7 10:03 | State |
| `med-supply.json` | Jul 7 10:05 | State |
| `SOUL.md` | Jul 7 ~09:00 | Persona |
| `gateway_state.json` | Jul 7 10:36 | Gateway |
| `health_state.json` | Jul 7 12:15 | Health |
| `med-status.json` | Jul 7 08:20 | State |
| `med-interactions.json` | Jul 5 09:16 | State |
| `substitutions.json` | Jul 5 09:14 | State |
| `dexa_taper.json` | Jul 5 10:01 | State |
| `taper_alert.py` | Jul 5 10:02 | Script |
| `med_report.py` | Jul 5 09:18 | Script |
| `med_supply.py` | Jul 5 09:13 | Script |
| `med_interact.py` | Jul 5 10:02 | Script |
| `med_substitute.py` | Jul 5 09:14 | Script |
| `med_appointments.py` | Jul 5 09:27 | Script |
| `fix_models.py` | Jul 5 11:15 | Script |
| `memory_watch.py` | Jul 5 11:44 | Script |
| `health_check.py` | Jul 5 03:12 | Script |
| `chain_calc.py` | Jul 5 10:01 | Script |
| `billing.py` | Jul 3 19:29 | Script |
| `hello_watch.py` | Jul 4 21:51 | Script |
| `chain_monitor.sh` | Jul 4 16:52 | Script |
| `watchdog.sh` | Jun 30 12:07 | Script |
| `appointments.json` | Jul 5 20:11 | State |
| `config.yaml` | — | Config |

---

## 13. Session Database Summary

| Metric | Value |
|---|---|
| Active sessions | ~119 in state.db |
| Recent WhatsApp sessions (Jul 4-7) | ~20 with meaningful content |
| Recent Telegram sessions (Jul 3-5) | Billing fixes, design skills, audit reviews |
| Total session data | ~50MB with WAL/SHM |

**Key Recent Sessions:**
- `systemprompt-update -0707` (Jul 7, 170 msgs) — SOUL.md overhaul, med system fixes
- `Morning Medication Logged` (Jul 7, 98 msgs) — Daily medication tracking
- `Reviewing Reports with Installed Skills #1-4` (Jul 5, Telegram) — Cross-referencing audit reports
- `Med System V3 Adversarial Review` (Jul 5, 84 msgs) — External AI review of med system
- `Morning Wake-Up Plans` (Jul 5, 394 msgs) — Systematic debugging, massive analysis

---

## 14. Known Issues & Gaps (Live on VPS)

| # | Issue | Status | Priority |
|---|---|---|---|
| 1 | **gateway_state.json stale-state bug** — blocks restart after SIGTERM | UNFIXED | P0 |
| 2 | **Daily Health cron error** — "[Errno 32] Broken pipe" on last run (Jul 7 09:10) | ACTIVE ERROR | P0 |
| 3 | **Baileys critical vulnerability** (GHSA-qvv5) — check if fix exists in newer version | UNCHECKED | P0 |
| 4 | **No automated backup** — only manual, no offsite | UNFIXED | P1 |
| 5 | **Model overrides via source patching** — fragile on `hermes update` | DESIGN ISSUE | P1 |
| 6 | **SOUL.md in git repo is OUTDATED** — live version (132 lines) vs committed (61 lines) | SYNC GAP | P1 |
| 7 | **Morning Briefing was running unapproved** — terminated, but similar jobs may exist | RESOLVED | P1 |
| 8 | **API keys not rotated** — exposed in plaintext during conversations | PENDING | P1 |
| 9 | **Medication names in cron system** — visible in `hermes cron list` | PENDING | P2 |
| 10 | **Cross-platform sync** — VPS vs WSL2 vs GitHub all out of sync | IN PROGRESS | P0 |
| 11 | **config.yaml model.default** uses `deepseek-v4-pro` (expensive) — should default to Flash, reserve Pro for hard tasks | COST INEFFICIENCY | P2 |
| 12 | **No provider fallback configured** in config.yaml — `fallback_providers: []` | GAP | P1 |
| 13 | **Git repo mjay/ commits are stale** — no commits since Jul 1, live changes not tracked | SYNC GAP | P0 |
| 14 | **hello-world-watch fires every 1 minute** — 1,873 completed runs, may be excessive | QUESTIONABLE | P3 |
| 15 | **cua-driver MCP** — installed but unclear if actually used | QUESTIONABLE | P3 |
| 16 | **memory_watch.py** at 95% CRITICAL level on MEMORY.md — needs investigation | MONITOR | P2 |

---

*End of VPS Baseline. This document captures everything accessible from the Singapore VPS as of July 7, 2026 12:15 MYT.*
