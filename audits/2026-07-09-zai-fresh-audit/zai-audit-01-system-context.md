# zai-audit-01 — System Context & Architecture Atlas (Hermes Agent / MJ)

> **Auditor:** Z.ai (GLM-5.2) — fresh, independent, evidence-first pass
> **Date:** 2026-07-09
> **Basis:** Read-only SSH to live VPS `ubuntu@119.28.119.151` (~/.hermes/), the fresh `~/hermes-snapshot-20260709/` (1157 files), `~/mjay/audit-prep/`, and the locally-available prior audits. No file on the VPS was modified.
> **Stance:** Unbiased. Prior audits (zcode 44-finding set, gemini, zhipu, qwen, sakana, claude) treated as leads only — every claim re-verified against live files. Gemini's CVE-2026-48063 + BD taper 4mg deficit claims are FABRICATED per the user/evidence and are struck (not reproduced).
> **Epistemic rule applied throughout:** every claim cites file:line or raw output; unverifiable claims are tagged UNVERIFIED / THEORETICAL.

---

## 0. How to read this doc

This is the **architecture atlas** for a 16-dimension agentic-system audit. Doc 2 (findings) is grouped by those same dimensions (D1–D16 + clinical). Doc 3 (plan) prioritizes across them and ties to your end-goals (side-income, ADHD compensation, smart med-intelligence).

The system is **not** a medication tracker. It is a self-hosted, always-on **agentic platform**: a gateway that bridges WhatsApp + Telegram to an LLM agent loop, with a cron scheduler, a skills/hooks system, a memory store, a fleet of state-JSON-backed domain scripts, and — separately committed — a multi-executor web-fetching "anti-bot research engine." All of that sits on one Tencent SG VPS as the single source of truth, with a Windows/WSL2 copy and a public GitHub repo both badly stale.

---

## 1. Topology (verified)

```
                         ┌─────────────────────────────────────────────┐
                         │  TENCENT LIGHTHOUSE VPS (Singapore)          │
                         │  ubuntu@119.28.119.151  — AUTHORITATIVE      │
                         │                                             │
   WhatsApp ◄──Baileys──►│  hermes gateway (systemd, Restart=always)    │
   Telegram ◄────────────│      │                                      │
                         │      ▼                                      │
                         │  agent loop (opencode runtime, max_turns=60) │
                         │      │ tool/skill/hook injection            │
                         │      ├── toolsets: hermes-cli, telegram,    │
                         │      │            whatsapp (config.yaml:12) │
                         │      ├── skills/ (60+ synced)               │
                         │      └── hooks/ (skill-trigger, guardrails) │
                         │                                             │
                         │  cron scheduler (6 ACTIVE jobs)             │
                         │      │ no_agent=true scripts (chain_*, etc) │
                         │                                             │
                         │  state JSON (med-*, chain-state, gateway_)  │
                         │  scripts/ (med_*, fetcher drivers)          │
                         │  fetcher/ anti-bot engine (git: hermes-live)│
                         └──────────────┬──────────────────┬───────────┘
                                        │ rsync (proposed) │ git push
                                        ▼                  ▼
                          Windows/WSL2 snapshot      GitHub repo (public)
                          (STALE 7/7, contains .env!) (STALE ~Jun28/Jul1)
```

**Verified facts:**
- Live config `model.default: hy3-free`, `provider: opencode`, `base_url: https://opencode.ai/zen/v1`, `providers: '{}'`, `fallback_providers: [opencode-zen/hy3-free, opencode-zen/deepseek-v4-flash-free]`, `redact_pii: true`, `mcp_servers: {}`, `toolsets: [hermes-cli, hermes-telegram, hermes-whatsapp]`, `max_turns: 60`, `reasoning_effort: high`. Source: `~/.hermes/config.yaml:1-12` (read live 2026-07-09).
- Cron: 15 jobs defined in `cron/jobs.json`, **6 active** (Log Rotate, Domino Chain Med Monitor, Dexa Taper Alert, Weekly Med Compliance, Appointment Reminder, V2 Overnight Build). Source: `python3 -c` over live `cron/jobs.json` (2026-07-09).
- The other 9 jobs (Evening Check-in, Daily Health, Daily Usage Report, Memory Watchdog, Goal Check-in, Weekly Review, DeepSeek Balance Check, hello-world-watch, Routine Analysis Start Weekend) are **present but `active=False`** — disabled, not deleted.

---

## 2. Dimension-by-dimension context (what it IS, should-vs-actual)

### D1 — Infrastructure & runtime reliability
**What it is:** One Tencent Lighthouse SG VPS, Ubuntu, user `ubuntu`. Gateway runs as a systemd service (`Restart=always`, `RestartSec=10` per VPS-MIGRATION-GUIDE). 
**Should:** documented restart/monitor, disk headroom, OOM guard on the 15-min `chain_monitor.sh` writer.
**Actual:** `systemd` unit presence UNVERIFIED (could not read `/etc/systemd` over read-only SSH in this pass — flagged UNVERIFIED). `gateway_state.json` has a known stale-state bug: after SIGTERM it persists `"running": true` and blocks restart; only manual `rm` fixes it (09-MASTER-SYNC-DOC §6, A10). This is a P0 availability gap, unfixed.
**TZ:** `chain_calc.py` uses `now_myt()` = `ZoneInfo('Asia/Kuala_Lumpur')` (verified line 109-110). But `chain_monitor.sh:88` writes `last_reminder_times` with naive `_dt.datetime.now().strftime('%H:%M')` — TZ-fragile if host is not MYT. Host TZ UNVERIFIED.

### D2 — Runtime & versioning
**What it is:** Python venv under `~/.hermes/hermes-agent/`, Node/Baileys for WhatsApp, the Hermes Agent core.
**Actual:** The 9/7 config fixes live as **uncommitted edits** to `~/.hermes/hermes-agent/hermes_cli/models.py` (hy3-free @ line 389) and `~/.hermes/hermes-agent/gateway/run.py` ([FALLBACK] @ line 1637). These are NOT in git (`mjay/` repo does not track `~/.hermes/hermes-agent/`). So a `git pull` on another machine would NOT reproduce the current runtime. **Reproducibility gap.**
**Should:** package edits versioned/committed.

### D3 — Model / provider / cost layer
**What it is:** OpenCode Zen/Go free-tier routing. `default: hy3-free` (fallback only — user switches ad-hoc via `/model`, there is NO fixed default model per user 2026-07-08 04:01). `fallback_providers` free-only by user rule.
**Actual:** `providers: '{}'` — the `minimax` block was deleted 9/7 (it pointed to `api.minimax.com` which is NXDOMAIN; built-in plugin still resolves `api.minimax.io/anthropic`). MiniMax issue IGNORED per user (9/7 09:47). Minimax key still in `.env` (unused).
**Cost discipline:** active cron jobs are `no_agent=true` (script-only). LLM-driven jobs are disabled (`active=False`), so they don't burn tokens — but they're not removed, so re-enabling is one flag flip away from cost risk.
**Drift in v2.2:** the handoff's `fallback_providers: [hy3-free, deepseek-v4-flash-free]` is WRONG — live is `[{opencode-zen, hy3-free}, {opencode-zen, deepseek-v4-flash-free}]`. I report the live truth.

### D4 — Orchestration & agent-loop design
**What it is:** message → intent → agent loop (max_turns 60, gateway_timeout 1800s) → tool/skill/hook injection → response. `context_from` chaining and `/background` exist (per ADVANCED-IDEAS).
**Should:** deterministic sub-systems for safety-critical logic (meds), LLM for explanation only.
**Actual:** The med chain is the textbook case. There is a **fully-specified deterministic constraint engine (`med_chain/` Spec v3, rated 9.95/10) that is NOT implemented** — `scripts/med_chain/` does not exist (verified `ls`: No such file or directory). Today the med timing is computed by `chain_calc.py` (1040 lines) which *interacts* with the LLM. The LLM "auto-linearizes a branched dependency graph" (the E-follows-C bug) — this is the core orchestration defect the spec was meant to fix but hasn't.

### D5 — Tool-calling & MCP architecture
**What it is:** `toolsets: [hermes-cli, hermes-telegram, hermes-whatsapp]`. `mcp_servers: {}` (cua-driver.exe removed 9/7 because it crashed on VPS — no Windows paths).
**Actual:** No MCP servers active. Auxiliary model drivers exist as loose scripts: `scripts/qwen_driver.py`, `scripts/sakana_driver.py`, `scripts/minimax_proxy.py` — these are ORPHANED/experimental drivers not referenced by live config (minimax proxy points at a dead endpoint). They're dead weight + a misleading signal of capability.
**Vision pipeline:** `gemini` wired for screenshot analysis per ADVANCED-IDEAS, but `mcp_servers:{}` and `GOOGLE_API_KEY` status UNVERIFIED this pass.

### D6 — Cron & automation reliability
**What it is:** 6 active jobs. Med monitor every 15min 5-22, taper alert daily 06:00, weekly compliance Sun 10:00, appt reminder 20:00, log rotate Sun 06:00, V2 overnight build 07:00.
**Should:** delivery target explicit, idempotent, error-visible.
**Actual:** Med monitor delivers to `whatsapp:120363428305511789` (explicit — good, fixes old `deliver:"origin"` bug). But `chain_monitor.sh` writes `chain-state.json` non-atomically (no tempfile/os.replace, no per-write backup) — crash mid-write truncates it; the JSON-decode fallback silently resets cooldowns → reminder burst (baseline CRITICAL, still live, see Doc 2 D12).
**Open question:** `Daily Health` cron had a "Broken Pipe" error pre-9/7 (09-MASTER-SYNC-DOC §6) — was it fixed? It's now `active=False`, so it can't error, but the root cause is UNVERIFIED.

### D7 — Workflow & pipeline design
**What it is:** ADVANCED-IDEAS lists 11+ automation ideas (self-improvement loop, chained fetch→rank→brief, memory-contradiction detective, weekly retrospective).
**Actual:** **Almost entirely aspirational.** None are wired as standing automations. The only real "pipeline" is the `fetcher/` anti-bot engine (separate workstream). The `V2 Overnight Build Verify` cron exists but its `script` field is null (delivers a message, doesn't run a build). **Gap between documented ambition and shipped reality is large** — itself a finding (the user explicitly wants to go "beyond basic assistant").

### D8 — Skills system
**What it is:** 60+ synced skills: `med-tracker`, `anti-fabrication-guardrails`, `malaysia-selector-interaction`, plus design (gsap-*, shadcn, material-3, frontend-design), `agent-methodology`, `github`, `devops`, `life-management`, `auto-skill-suggester`, etc.
**Should:** each skill correct, activated by relevant keywords, no bloat.
**Actual:** `med-tracker` is the med knowledge skill. `auto-skill-suggester` suggests skills — but there is no evidence of a curation/retirement process. Many skills (e.g. `gsap-*`, `canvas-design`, `brand-guidelines`, `apple`) are irrelevant to a personal/med assistant and add load + attack surface. Skill bloat UNVERIFIED for impact but noted.

### D9 — Hooks & guardrails
**What it is:** `hooks/` with `skill-trigger/` (auto-injects med-tracker on med keywords) and `anti-fabrication-guardrails/` (prevents AI fabricating drug names).
**Should:** guardrails cover the failure modes — esp. Pattern D (assistant resets med data without checking history).
**Actual:** The anti-fabrication hook guards *output text*, not *state writes*. Pattern D (over-assume reset) is a **state-mutation** failure, not a text-fabrication failure — so the existing hook does NOT cover it. Gap.
**POST-AUDIT (2026-07-10):** the `med-auto-confirm` hook (not in original D9 text) caused Pattern G — false-positive slot match on conversational message, corrupt A/07-10 @20:00 entry, suppressed all morning reminders. See `zai-audit-02-findings.md` Z-F-G [CRITICAL].

### D10 — Memory & context architecture
**What it is:** `memories/`, `SOUL.md` (live 131 lines vs repo 61 — drift), `USER.md` (referenced in charter, presence UNVERIFIED this pass), compression, `memory_watch.py` (cron, active=False).
**Should:** clean separation of long-term user facts vs working session state; contradiction detection.
**Actual:** SOUL.md is strong (explicit brutal-honesty epistemic standard — I am following it). But `memory_watch.py` is disabled, so the "memory contradiction detective" idea is not running. No evidence of automated contradiction detection. Med/state history lives in `med-status.json` keyed by date (good) but is mutable by `med_confirm.py` in lossy ways (Doc 2).

### D11 — Persona & behavioral design
**What it is:** MJ — warm, Manglish, ADHD-aware, escalation on missed meds.
**Actual:** SOUL.md encodes this well, including "escalating tone" logic implicitly via cron. BUT the escalation is driven by `chain_calc.py` cooldown counters, and the counting logic had the cross-day bleed bug — which is **now fixed** (day-reset at `chain_monitor.sh:61`). So persona behavior is more correct than prior audits claimed. Persona drift across platforms: not separately verified; the same SOUL drives both WhatsApp + Telegram.

### D12 — State / data integrity (system-wide)
**What it is:** ALL mutable state as JSON: med-*, chain-state, dexa_taper, gateway_state, channel_directory, processes, kanban.db, health_state, appointments.
**Should:** atomic writes, backup rotation, schema consistency, migration path.
**Actual:**
- `chain-state.json` non-atomic write (D6).
- `med-schedule.json` is **stale vs reality**: version 1.3, `last_updated: 2026-07-05`, still says `Akurit-4`/`akurit_4` — the **real 9/7 pharmacy swap to Akurit-2 was NEVER reflected** (CRITICAL data-integrity drift; see Doc 2 D-clinical). NOTE: v2.2 claimed Pyridoxine/Calcium/Calcitriol were "ABSENT" from live JSON — that is STALE; the live file DOES include them (verified). I correct v2.2 here.
- `gateway_state.json` stale-state bug (D1).
- Test-on-prod isolation gap (Pattern A) still structurally present: scripts write directly to prod state; `--dry-run` exists on `med_confirm.py` but discipline, not enforcement.

### D13 — Script correctness (system-wide)
**What it is:** ~28 scripts in `scripts/`.
**Should:** error-handled, exit-coded, dry-run-covered, no silent `except Exception: pass`.
**Actual:** Confirmed live defects (Doc 2 D13):
- `med_confirm.py:264-269` — `confirm_slot` sets `{"status":"taken","time":now}` for ALL drugs in slot, clobbering earlier partial real times; `decrement(did)` runs every confirm (re-decrement on re-run).
- `med_resolve.py:141` — `float(time.replace(":",".").rstrip("0"))` lossy (e.g. `13:30`→`13.3`); mis-routes a 10:30 dexa to slot B.
- `med_resolve.py` boundary `14:00` double-matches B/E (returns B by order).
- `chain_monitor.sh:88` naive datetime (D1 TZ).
- `except Exception: pass` pattern present (e.g. `med_confirm.py:238,268,298,333`) — swallows errors.

### D14 — Security & secrets
**What it is:** `.env` (600), `auth.json` (600), WhatsApp `session/` (BAILEYS auth), public GitHub repo.
**Actual:**
- `.env` and `auth.json` are `600` ✓ (verified `stat`).
- **`whatsapp/session/` is `drwxrwxr-x` (775) — group/world readable** (verified). Baileys session = full account takeover secret. Real exposure. (Doc 2 D14-CRITICAL)
- The Windows `hermes-snapshot-20260707/` **contains a copy of `.env`** (user chose not to delete, 2026-07-07 23:39). If that PC is compromised, secrets leak. And GitHub repo is PUBLIC — need to confirm no med/PII is pushed there (channel `120363428305511789` is a WhatsApp group ID, not secret, but med-status.json is PII).
- `minimax_proxy.py` references a dead endpoint; harmless but dead code.

### D15 — Observability & ops
**What it is:** `health_check.py`, `hello_watch.py` (heartbeat), `logrotate-run.sh`, logs in `logs/`.
**Should:** alert when gateway dies; debuggable.
**Actual:** `hello-world-watch` exists but `active=False`. `health_check.py` presence confirmed but its alerting path UNVERIFIED. **No evidence of an external dead-man's-switch alert** (e.g. if gateway dies at 3am, who knows?). `gateway_state.json` stale-state bug means even an internal restart can silently fail. Observability is thin.

### D16 — End-goal & product architecture
**What it is:** personal assistant → revenue-generating, ADHD-compensating, med-intelligence product.
**Actual:** Today it is a **well-built personal tool**, not a product. The `fetcher/` engine is the closest thing to a reusable asset (a capability-routed anti-bot scraper — genuinely useful IP). The med-intelligence engine (Spec v3) is designed but unbuilt. Path to "unexpected side income": (a) finish + productize the med-intelligence engine as a sellable ADHD/med-adherence assistant, (b) productize the fetcher as an anti-bot data-acquisition service, (c) use MJ's agent-loop + skills as a consulting demo. All three are blocked by the same root cause: **no sync/discipline between the 3 environments, and uncommitted runtime state** (D2). You can't sell or replicate what you can't reproduce.

---

## 3. The second workstream (the audit-prep docs under-weighted this)

`~/mjay/` (git `hermes-live`) contains a committed **anti-bot research engine** — `fetcher/` with `router.py` (AdaptiveRouter, capability-based executor selection), `capability_registry.py`, `cost_optimizer.py`, `analytics.py`, `domain_memory.py`, and executors: `crawl4ai_executor.py`, `flaresolverr_executor.py`, `browseract_executor.py`, `cloudscraper_executor.py`, `curl_cffi_executor.py`. 7 commits 2026-07-09 00:43-01:08. Plus `build_overnight.py` (11KB, uncommitted).

This is a **real, substantial integration** — a multi-provider web-fetching system with cost optimization and analytics — running beside the assistant. It is entirely absent from v2.2's scope. Its data dirs (`analytics.db`, `cookies.db`, `domain_memory.db`) live in `~/.hermes/fetcher/`; its code in `~/mjay/`. Another split-source-of-truth instance.

---

## 4. Should-vs-actual summary table

| Dimension | Should be | Actual (verified) | Verdict |
|---|---|---|---|
| D1 Infra | monitored, TZ-safe, restart-safe | stale-state bug, TZ-fragile writer, monitor UNVERIFIED | GAP |
| D2 Versioning | committed runtime | 9/7 fixes uncommitted, not in git | GAP (CRITICAL for repro) |
| D3 Model/cost | free-only, no waste | correct; LLM jobs disabled not deleted | OK (minor) |
| D4 Orchestration | deterministic med engine | Spec v3 unbuilt; LLM linearizes deps | GAP |
| D5 Tools/MCP | MCP or clean drivers | MCP empty; 3 orphan drivers | GAP |
| D6 Cron | atomic, visible errors | non-atomic chain-state write | GAP (CRITICAL) |
| D7 Workflows | ideas shipped | ~all aspirational | GAP |
| D8 Skills | curated | 60+, bloat, no retirement | MINOR |
| D9 Hooks | cover state writes | only cover text output | GAP |
| D10 Memory | clean, contradiction-detect | mem-watch disabled | GAP |
| D11 Persona | consistent, ADHD-aware | good; cross-day bug FIXED | OK |
| D12 Data integrity | atomic, synced | akurit_4 drift, non-atomic | GAP (CRITICAL) |
| D13 Scripts | safe, dry-run | confirm clobber, float hack live | GAP |
| D14 Security | locked secrets | session/ 775, .env on PC snap | GAP (CRITICAL) |
| D15 Ops | dead-man alert | none verified | GAP |
| D16 Product | reproducible asset | uncommitted, unsynced | GAP (blocks goal) |

---

## 5. What I could NOT verify this pass (tagged UNVERIFIED)

- systemd unit file contents (`/etc/systemd/...`) — read-only SSH didn't reach it.
- Host OS timezone (MYT vs UTC) — determines if `chain_monitor.sh:88` is actually buggy in prod.
- `GOOGLE_API_KEY` / vision pipeline liveness.
- `USER.md` presence and `memories/` contents (not read this pass).
- Whether `Daily Health` "Broken Pipe" root cause was fixed before disable.
- GitHub repo contents (are med/PII files public?).

These are called out so nothing is rounded up to "confirmed." Doc 2 lists the findings that depend on them as UNVERIFIED.
