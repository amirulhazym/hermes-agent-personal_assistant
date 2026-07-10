<!-- ===== OVERHAUL ADDENDUM — 2026-07-09 (OpenCode deep-audit extension) =====
This document was extended with a full overhaul-level deep audit. The original
v2.2-baseline content (Sections 0-6) is preserved verbatim below. New material
is appended as clearly-labelled Sections 7-14 (deep-dives across orchestration,
integration, automation, state, memory, security, observability, cost). No prior
text was removed or altered. Every new claim cites live VPS file:line evidence
gathered read-only on 2026-07-09.
============================================================================= -->

# audit-01-system-context.md — Hermes Agent (MarryJane / MJ) System Context

> Auditor: OpenCode (external, read-only SSH + rsync snapshot)
> Date: 2026-07-09 | VPS: 119.28.119.151 (Tencent, Singapore) — AUTHORITATIVE
> Method: Live VPS read-only verification. Prior AI reports (Zhipu/Qwen/Sakana/Claude/Gemini) re-verified, not trusted blindly.

---

## 0. One-line verdict
VPS is the only live source of truth; Windows snapshot and GitHub are stale. The system is **functionally running but architecturally fragile**: the medication "Domino Chain" encodes a clinically-wrong *blind-shift* model, the gateway watchdog is silently broken by a hardcoded wrong home directory, and the audit handoff docs themselves contain stale/incorrect evidence.

---

## 1. Architecture (should vs actual)

### 1.1 Layers
| Layer | What it is | Reality |
|---|---|---|
| Gateway | `hermes-agent/gateway/run.py` long-running daemon; Telegram + WhatsApp (Baileys) bridges | Single process, PID 3010901, healthy, both platforms connected (gateway_state.json) |
| Cron | Hermes cron engine (`cron/jobs.json`) + Linux system cron (watchdog.sh) | 6 Hermes jobs active; 1 Linux watchdog |
| Scripts | `~/.hermes/scripts/*.py` + `*.sh` (med chain, taper, supply, reports, billing, watchdog, restarts) | 27 files, mixed quality, **some reference a nonexistent home dir** |
| State | JSON files (`med-status`, `med-schedule`, `chain-state`, `dexa_taper`, `gateway_state`, etc.) | Plain JSON, no schema validation, no transactions |
| Persona | `SOUL.md` (132 lines) + `memories/MEMORY.md` (90% full) + `USER.md` | Works but MEMORY.md at capacity |

### 1.2 Should vs actual
- **Should:** 3-way sync (VPS ↔ WSL2 ↔ GitHub) auto-aligned. **Actual:** VPS ahead; Windows snapshot 7/7 (stale); GitHub ~Jun 28/Jul 1 (stale). No automated sync mechanism exists (only a *proposed* one in `09-MASTER-SYNC-DOC.md`).
- **Should:** med reminders model independent drug clocks (Akurit empty-stomach wait; Dexa's own 8/12/4pm; Levetiracetam 12h). **Actual:** everything is chained off Slot A's actual intake time (`chain_calc.py:416-460`).
- **Should:** watchdog cleans stale `gateway_state.json` so restarts never block. **Actual:** watchdog targets `/home/amirul/...` which does not exist here (`watchdog.sh:9-13`) → mitigation is a no-op.

---

## 2. Data flow (medication reminder path)

```
[Hermes cron] c97c00f2fb46  */15 5-22 * * *  ──no-agent──▶  scripts/chain_monitor.sh
        │
        ├─ calls chain_calc.py --next  → computes "ready time" per slot
        │        └─ calculate_ready_time()  anchors B→A, C→B, D→C, E→B (chain_calc.py:416-460)
        ├─ increments chain-state.json (BUG: last_reminder_sent overwritten, line 85)
        └─ calls chain_llm.py → LLM-generated Manglish reminder → WhatsApp
[med_confirm.py] user replies → writes med-status.json (drug-level)
[taper_alert.py] daily 06:00 → reads dexa_taper.json → Dexa phase alert
[med_report.py] weekly → compliance report
```

Critical: `chain_calc.py` reads `med-status.json` actual times and **propagates A's lateness downstream**. There is no branch that says "Dexa #1 stays ~08:00 regardless of A."

---

## 3. Dependencies & external surface
- **Providers:** opencode-zen (free, primary+fallback), deepseek-v4-flash-free (fallback). NVIDIA/DeepSeek referenced in scripts but config `providers: '{}'`.
- **MiniMax:** provider block deleted from config 9/7, but `scripts/minimax_proxy.py` and `fix_models.py:36,61` still reference it → dead code.
- **WhatsApp:** Baileys bridge; allowed-users gated. **Telegram:** allowlist `679729206`.
- **Secrets:** `.env` on VPS (not in this audit). `MINIMAX_API_KEY` present but unused. `redact_pii: true` (config.yaml:382) helps logs, NOT job names (med drug names visible in `hermes cron list`).

---

## 4. Confusing / undocumented / contradictory
1. **`config.yaml:5` `providers: '{}'`** — a *quoted string*, not a YAML mapping. Inconsistent with `credential_pool_strategies: {}` (proper mapping). Risk: a consumer doing `config["providers"].get(...)` throws AttributeError. (THEORETICAL — needs runtime confirmation; system currently runs, so it may be coerced.)
2. **`med-schedule.json:85` `shift_logic`** says *"Jika A lambat, semua meds shift accordingly"* — directly contradicts the clinically-correct model the user/charter insists on. The schedule JSON encodes the wrong mental model.
3. **GAPS vs nominal times:** `chain_calc.py:38` `A_to_B: 1.0` (1h) but `med-schedule.json` Slot B nominal time is `08:00` (2h after A=06:00). On a normal on-time day the chain engine computes B ready ≈ 07:00–07:15, **one hour earlier than the slot's own scheduled time**. The engine and the schedule disagree by 1h for every downstream slot.
4. **`V2 Overnight Build Verify + Report` cron (1bf7fcc00b60)** is an **agent-driven LLM job** (long `prompt`, no `script`) that verifies the *anti-bot fragrantica build* — a SEPARATE workstream from the med/audit system. It runs daily 07:00 and costs LLM tokens, yet sits inside the "medication/personal assistant" cron set. Scope contamination.
5. **Audit handoff docs are themselves stale/inaccurate** — see Finding F-12. The `08-EVIDENCE-APPENDIX.md A6` med-schedule.json snippet shows a *simplified* schedule (Slot A = Akurit-4 only, Slot C = Dexa only) that does **not** match the live file. Trusting that snippet would produce a false finding.

---

## 5. What is actually working (credit where due)
- Gateway stable, both platforms connected, 8+ days uptime across restarts.
- 9/7 config hygiene: free-model default, free-only fallback chain, `redact_pii`, dead minimax provider block removed.
- LLM-driven cron jobs that were erroring (`Daily Health` Broken pipe) or unauthorized (`Morning Briefing`) have been **removed** — only 6 jobs remain, 5 no-agent.
- `med_confirm.py` does drug-level tracking with `--dry-run` + auto-backup (`.bak1-3`) — good safety pattern.
- `dexa_taper.json` structure is sound (TDS→BD→OD phases, correct 5/5/4 mg split in BD) — Gemini's "4mg deficit" claim is false.

---

## 6. User end-goals context (for Doc 3)
- **Side-income:** user is a solo AI-consulting builder; the *anti-bot fragrantica research engine* (separate workstream) is the income experiment. MJ should eventually help, not just chat.
- **ADHD compensation:** needs reliable external memory + non-judgmental nudges. MEMORY.md at 98% capacity is a ticking failure for this goal.

---

## 7. DEEP-DIVE — Orchestration & Runtime (Overhaul Audit, 2026-07-09)

**Source of truth:** `hermes-agent/gateway/run.py` = **17,594 lines**, a single monolithic gateway daemon (PID 3010901, healthy). Earlier audit-01 §1.1 called it "single process" — this section goes deeper.

- **Agent lifecycle & session model:** `run.py:5105 start()` boots adapters, then `_kanban_dispatcher_watcher` (`:5694`) spawns an in-gateway background kanban worker; `_handoff_watcher` (`:5721`) re-dispatches handoff notices through the normal gateway path. Sessions are per-profile scoped via `_profile_runtime_scope` (`:1279`), isolating config/skills/memory/credentials per `MultiplexConfigError` profile (`:1269`).
- **Concurrency:** `max_concurrent_sessions` resolved at `run.py:3938-3949`; when the cap is hit, new sessions are rejected (`:8337`). **But `config.yaml:16` sets it to `null`** → unbounded concurrent sessions (see F-15).
- **Reasoning:** `run.py:3712-3721` reads `agent.reasoning_effort` from config. `config.yaml:36` = `high` → every agent turn requests high reasoning effort (see F-14).
- **Tool/MCP wiring:** platform toolsets resolved at `run.py:11017-11053` (`enabled_toolsets`/`disabled_toolsets`); MCP servers discovered/shutdown at `run.py:11624` (`discover_mcp_tools`, `shutdown_mcp_servers`). `config.yaml` `mcp_servers: {}` (no MCP servers configured) — the MCP plumbing exists but is unused.
- **Secret hygiene in-process:** `_redact_gateway_user_facing_secrets` (`run.py:290`) scrubs secrets from gateway-facing output — good, but only covers *gateway* output, not logs/jobs (see F-17).
- **Takeaway:** architecturally competent monolith with profile isolation and redaction, but two config values (`reasoning_effort: high`, `max_concurrent_sessions: null`) impose real cost/reliability risk, and the kanban subsystem is *embedded inside* the gateway process (single point of failure for both chat and task dispatch).

## 8. DEEP-DIVE — Integration Layer (Overhaul Audit, 2026-07-09)

- **Bridges:** WhatsApp (Baileys) + Telegram (Bot API) enabled via toolsets `hermes-whatsapp` / `hermes-telegram` (`config.yaml:12-14`). Allowlist `TELEGRAM_ALLOWED_USERS` / `WHATSAPP_ALLOWED_USERS` in `.env`.
- **Channel directory (PII):** `channel_directory.json` (1.6 KB) enumerates Telegram id `679729206` and WhatsApp id `13186321408227@lid` + **2 WhatsApp groups**, with names. This is health-adjacent PII sitting in plaintext runtime state (see F-17).
- **Redundant restart scripts:** THREE gateway-restart scripts coexist — `gw_restart.sh`, `restart_gateway.sh`, `hermes_gateway_restart.sh` (in `scripts/`). Divergence risk: a fix to one is easily missed in the others (see F-23).
- **Hooks (undocumented automation):** `hooks/` contains `med-auto-confirm`, `skill-trigger`, `hello-world`. **`med-auto-confirm`** (`HOOK.yaml`: "Auto-log medication confirmations from inbound messages BEFORE the agent processes them, so med-status.json is always correct… Fail-open") auto-writes med state pre-agent — an automation the prior audit never mapped, and one that can interact with `med_confirm.py` (see F-22). `skill-trigger` auto-detects med/message patterns and writes a trigger file for skill auto-loading.
  - **POST-AUDIT (2026-07-10, Pattern G):** this hook caused a CRITICAL false-positive — a chat discussion of "20:00" was misread as intake, corrupting med-state and freezing `chain-state.json` on 2026-07-09. See **F-22 / Pattern G** for the verified incident + fix plan.
- **WhatsApp session store:** `pairing/` exists but is **empty** (verified 2026-07-09) — the Baileys auth store lives elsewhere (location UNVERIFIED); no exposure observed in `pairing/`.

## 9. DEEP-DIVE — Automation & Cron Engine (Overhaul Audit, 2026-07-09)

- **Job inventory (`cron/jobs.json`):** **15 jobs total** — 6 `scheduled` (active) + 9 `paused`.
  - Active (5 `no_agent` scripts + 1 LLM): `Log Rotate`, `Domino Chain Medication Monitor` (`*/15 5-22`), `Dexa Taper Alert`, `Weekly Med Compliance Report`, `Appointment Reminder (day-before)` — all `no_agent` — **plus `V2 Overnight Build Verify + Report` (`0 7 * * *`, LLM, anti-bot workstream) = the only active LLM cron job** (confirms F-05).
  - Paused LLM jobs: `Evening Check-in`, `Daily Usage Report`, `Goal Check-in`, `Weekly Review`, `Daily Health`, `DeepSeek Balance Check`, `Memory Watchdog`, `Routine Analysis Start Weekend`, `hello-world-watch`.
- **Correction to prior audit:** audit-01 §5 stated erroring LLM jobs "have been removed." They are actually **paused, not deleted** — still present in `jobs.json` (9 paused jobs). Not critical, but the prior doc overstated the cleanup (see F-20).
- **Execution model:** `no_agent` jobs run a script; LLM jobs (`prompt` set, `script` null) spin an agent. The anti-bot daily LLM job is the sole standing LLM cost in the cron set (separate workstream — scope contamination, F-05).

## 10. DEEP-DIVE — State & Data Model (Overhaul Audit, 2026-07-09)

- **15 JSON state files** (no schema validation, no transactions): `med-schedule.json`, `med-status.json` (+3 `.bak`), `chain-state.json` (250 B — the F-04-clobbered state), `dexa_taper.json`, `med-interactions.json`, `substitutions.json`, `med-supply.json`, `appointments.json`, `gateway_state.json`, `auth.json`, `channel_directory.json`, `processes.json` (2 B), plus caches `models_dev_cache.json` (**2.98 MB** full provider catalog), `provider_models_cache.json` (740 B), `ollama_cloud_models_cache.json` (735 B), and hidden `.skills_prompt_snapshot.json` (**68 KB** skill prompt cache, unaccounted).
- **kanban.db (SQLite, ACID):** 8 tables — `tasks` (30 cols: `claim_lock`, `worker_pid`, `consecutive_failures`, `model_override`, `goal_mode`, `session_id`…), `task_links`, `task_comments`, `task_events`, `task_runs`, `task_attachments`, `kanban_notify_subs`, `sqlite_sequence`. **All 0 rows** currently. Driven by the in-gateway dispatcher (`run.py:5694`).
- **Architectural inconsistency (key finding):** the **medication** subsystem — the most safety-critical data in the whole system — uses **flat JSON with no ACID/transactions**, while the **kanban** subsystem uses **proper SQLite**. The F-04 `chain-state.json` clobber is a direct symptom of the JSON-no-transaction design. Recommend unifying med state onto a transactional store (see F-16).

## 11. DEEP-DIVE — Memory Subsystem (Overhaul Audit, 2026-07-09)

- **Files:** `memories/MEMORY.md` (9,105 B, F-09 98% of 9,000 limit), `USER.md` (1,388 B), `SOUL.md` (132 lines live vs 61 in repo — stale, F-? repo drift), `.memory_watch_alerted` flag.
- **Curation is an LLM aux role:** `config.yaml:278-280` `curator` (`provider: auto`, `timeout: 600`) runs periodic memory curation on the **main model** (see F-19). So memory upkeep itself costs LLM tokens on hy3-free.
- **Token cost of memory loading:** MEMORY.md + USER.md + SOUL.md are injected every turn; at 9,105 B MEMORY.md alone is ~2.3K tokens per turn, every turn — a silent, permanent per-turn cost that grows as memory fills.
- **ADHD implication:** a full/near-full flat memory with no vector retrieval means the "external brain" degrades exactly when the user needs it most; curation (an LLM job) is the only relief valve (see F-09, audit-02).

## 12. DEEP-DIVE — Security & Privacy (Overhaul Audit, 2026-07-09)

- **Secrets:** `.env` holds `DEEPSEEK_API_KEY`, `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY`, `TELEGRAM_BOT_TOKEN`, `WHATSAPP_ALLOWED_USERS`, `OBSIDIAN_VAULT_PATH`, `MINIMAX_API_KEY` (still present though minimax provider deleted 9/7 — dead secret, F-18), plus WhatsApp/Telegram home-channel threading vars. `auth.json` top-level keys: `credential_pool`, `providers`, `updated_at`, `version` (values not inspected — var names only, per constraints).
- **`redact_pii: true` (`config.yaml:382`)** covers **logs only** — not `jobs.json`, `channel_directory.json`, or `med-*.json` filenames/content. Drug names remain visible in `hermes cron list`/jobs.json (F-10) and phone numbers in `channel_directory.json` (F-17).
- **PDPA exposure if synced:** audit-03 already says VPS runtime state must not hit GitHub. Confirmed necessary — `channel_directory.json` (phone numbers) + med JSON are the concrete PII that would leak.
- **Obsidian integration:** `OBSIDIAN_VAULT_PATH` in `.env` implies a notes integration the prior audit never mapped (UNVERIFIED what it does).

## 13. DEEP-DIVE — Observability & Recovery (Overhaul Audit, 2026-07-09)

- **Health monitor:** `scripts/health_check.py` is an *independent* Linux-cron monitor (not Hermes cron) that alerts via WhatsApp→Telegram fallback. Good redundancy — but it is separate from the gateway's own stale-state handling.
- **Log rotation:** `scripts/logrotate-run.sh` + the `Log Rotate` cron job.
- **Watchdog (F-03):** broken by hardcoded `/home/amirul/` on a `/home/ubuntu` box → the gateway stale-state P0 is unmitigated.
- **No DLQ / central alerting:** failures in cron jobs or the kanban dispatcher have no dead-letter queue or aggregated alerting observed; `health_check.py` is the only out-of-band signal.
- **3 redundant restart scripts (F-23)** compound recovery confusion.

## 14. DEEP-DIVE — Cost Model (Overhaul Audit, 2026-07-09)

- **Always-on high reasoning:** `config.yaml:36 reasoning_effort: high` on every agent turn (F-14).
- **Unbounded concurrency:** `config.yaml:16 max_concurrent_sessions: null` (F-15) → cost & overload risk under load.
- **Auxiliary roles on main model:** `auxiliary_client.py:1704/1734` (`_read_main_model`/`_read_main_provider`) → background roles (`curator` timeout 600, `kanban_decomposer` timeout 180, `compression`, `skills_hub`, `approval`, `mcp`, `title_generation`, `tts`, `triage_specifier`, `profile_describer`, `monitor`, `background_review`, `extraction`) run on **hy3-free** (the main capable model). Real, recurring background LLM spend (F-19). `reasoning_effort` propagation to aux is **UNVERIFIED** (not referenced in `auxiliary_client.py`).
- **Standing LLM cron:** `V2 Overnight Build Verify + Report` (anti-bot) daily LLM cost (F-05).
- **Per-turn memory injection** (~2.3K tokens/turn from MEMORY.md alone) is a permanent, growing cost (§11).
- **Net:** the system's default posture is "max reasoning + unbounded sessions + main-model background tasks" — the opposite of a cost-conscious config. Tuning these is the highest-leverage cost reduction available without touching features.
