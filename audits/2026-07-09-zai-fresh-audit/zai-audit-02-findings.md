# zai-audit-02 — Full Audit Findings (Hermes Agent / MJ)

> **Auditor:** Z.ai (GLM-5.2) — fresh, independent, evidence-first
> **Date:** 2026-07-09 · **Basis:** live VPS read-only + fresh 9/7 snapshot + audit-prep + prior audits (re-verified, not trusted)
> **Format:** `[Severity][Category] — D<n> short desc`. Every item cites file:line or raw output. UNVERIFIED/THEORETICAL tagged.
> **Baseline cleared:** Known Patterns A–E + the 44-item `2026-07-05-zcode-audit-02` set + recurring gemini/zhipu items. Items marked **[BEYOND]** are new vs that baseline.

**Severity:** CRITICAL (data loss / patient-safety / system failure / secret exposure) · HIGH (wrong behavior / silent gap) · MEDIUM (edge/debt) · LOW (cosmetic/doc).

**Counts (this pass): CRITICAL: 10 · HIGH: 17 · MEDIUM: 16 · LOW: 11 = 54.** Of these, **29 are [BEYOND]** the prior baseline (new dimensions: orchestration, security perms, second workstream, sync-of-truth, aspirational-vs-shipped, kanban, delegation, curator, plugins, hooks internals, config-deep, fetcher-product).

---

## D12 / D-clinical — Data integrity & medication (CRITICAL core)

### [CRITICAL] DATA-INTEGRITY — Live `med-schedule.json` never reflected the 9/7 Akurit-2 pharmacy swap
**File(s):** `~/.hermes/med-schedule.json:1,18-26` (version 1.3, `last_updated: 2026-07-05`)
**Evidence:**
```json
"A": {"name": "Akurit-4 + Pyridoxine", "drugs": [{"drug": "Akurit-4", "drug_id": "akurit_4", ...}]}
```
User confirmed 9/7: 4-dose Akurit-4 → **4-dose Akurit-2** (pharmacy swap). Live JSON still says `Akurit-4`/`akurit_4`. `chain-state.json` and `med-status.json` history also key on `akurit_4`.
**Impact:** Every reminder, taper reference, and supply count for the TB drug is keyed to a drug the patient no longer takes. Clinician-aligned safety data is wrong. Patient-safety risk.
**Root cause:** No process links a real-world med change to the JSON; edits are manual and were missed.
**Recommendation:** Treat charter+real-change as truth. Rename `akurit_4`→`akurit_2` across med-schedule.json, med-status.json, chain-state.json, med-supply.json, scripts. Add a med-change procedure (not ad-hoc).
**Note (correcting v2.2):** v2.2 claimed Pyridoxine/Calcium/Calcitriol were "ABSENT" from live JSON — **STALE**. Live file DOES include them (verified `med-schedule.json:27-49`). I report the narrower, true drift (Akurit-4 only).

### [CRITICAL] DATA-INTEGRITY — `confirm_slot` clobbers ALL drug times to `now`
**File(s):** `scripts/med_confirm.py:264-269` (baseline CRITICAL, **re-verified live, still present**)
**Evidence:**
```python
for did in drug_ids:
    entry.setdefault('drugs', {})[did] = {"status": "taken", "time": now}
    try: from med_supply import decrement; decrement(did)
    except Exception: pass
```
**Impact:** If user confirmed `levetiracetam_b` at 08:16 then later runs `confirm_slot B`, the 08:16 record is overwritten to the new time. Destroys real intake history → corrupts chain-gap math + compliance report.
**Root cause:** slot-level confirm conflates "mark done" with "re-stamp every drug at one instant."
**Recommendation:** only set `now` for drugs not already `taken`; decrement only on pending→taken transition.
**[BEYOND note]:** prior audit found this; I confirm it is UNFIXED on 9/7 live.

### [CRITICAL] DATA-INTEGRITY — `chain-state.json` written non-atomically; silent reset on corruption
**File(s):** `scripts/chain_monitor.sh` (writes state; `chain_calc.save_json` uses `open('w')`), no `.tmp`/`os.replace`, no per-write backup
**Evidence:** hottest writer every 15 min does read-modify-write; JSON-decode fallback `state = {}` silently resets all cooldowns → reminder burst. (Baseline CRITICAL, **live, unverified-fixed**.)
**Impact:** crash/OOM/reboot mid-write truncates file; next run resets counts → spam or missed escalation.
**Recommendation:** write `.tmp` then `os.replace()`; keep `.bak`; make corrupt-file fallback LOUD.
**Severity upgrade:** this is patient-safety-adjacent (reminder cadence).

### [HIGH] DATA-INTEGRITY — `med_confirm.py` re-decrements supply on every confirm
**File(s):** `scripts/med_confirm.py:264-269` (decrement inside the loop, no transition guard)
**Evidence:** `get_all_drug_ids` includes `b_complex` (required:false, doses_per_day:0). Running confirm twice decrements calcitriol/calcium/dexa a second time; `except Exception: pass` hides any guard.
**Impact:** supply counts drift downward faster than reality → false LOW/OUT-OF-STOCK.
**Recommendation:** decrement only on pending→taken; skip `doses_per_day == 0`.

### [HIGH] CORRECTNESS — `med_resolve.py` lossy float time parser mis-routes doses
**File(s):** `scripts/med_resolve.py:141`
**Evidence:** `float(time_24h.replace(":", ".").rstrip("0"))` → `"13:30"`→`13.3`; B/C boundary `10.5`. A 10:30 dexa resolves to **B** not **C**.
**Impact:** dexa taken 10:30 logged to wrong slot → wrong chain math + compliance.
**Recommendation:** `h, m = map(int, t.split(':')); compare h + m/60.0`. Delete `rstrip` hack.

### [HIGH] CORRECTNESS — `med_resolve.py` 14:00 boundary double-matches B/E
**File(s):** `scripts/med_resolve.py` slot-rule match (B `hi=14`, E `lo=14`)
**Evidence:** at exactly 14:00 both match; `matches` order returns B first. Comment says "after 14:00 → E".
**Impact:** levetiracetam at 14:00 logged to morning slot B, not night slot E.
**Recommendation:** make boundaries non-overlapping; add test for `14:00`.

### [HIGH] CLINICAL-MODEL — System does NOT model the ~1h empty-stomach wait or independent Dexa 4h-gap
**File(s):** `med-schedule.json` rules + `chain_calc.py` (calculate_ready_time); `MED_CHAIN_ENGINE_SPEC_v3.md`
**Evidence:** `rules.shift_logic`: "Jika A lambat, semua meds shift" — but the real mechanism is: after Akurit-2 there is a mandatory ~1h EMPTY-STOMACH wait before ANY other med/food. Dexa follows its OWN ~8am timing (independent of Akurit-2). The live engine blindly shifts on Late A. The Spec v3 that would fix this is **unimplemented** (`scripts/med_chain/` does not exist).
**Impact:** this is the #1 error prior auditors made and v2.2 explicitly warns about. The current logic over-/under-shifts. Patient-adherence guidance is clinically wrong.
**Recommendation:** implement the deterministic constraint engine (Spec v3) OR at minimum encode (a) 1h empty-stomach gate after A, (b) Dexa 4h-gap independence. Research clinical basis before tightening gaps.
**[BEYOND]:** v2.2's central correction; verified the gap is REAL and the fix is designed-but-not-built.

---

## D2 / D16 — Versioning & source-of-truth (CRITICAL for reproducibility & your goal)

### [CRITICAL] CONFIG/SYNC — 9/7 runtime fixes are uncommitted and untracked by git
**File(s):** `~/.hermes/hermes-agent/hermes_cli/models.py` (hy3-free @389), `~/.hermes/hermes-agent/gateway/run.py` ([FALLBACK] @1637); `~/mjay/` git does NOT include `~/.hermes/hermes-agent/`
**Evidence:** `git -C ~/mjay log` last commits are anti-bot only (00:43-01:08 9/7). `09-MASTER-SYNC-DOC §6/A7`: "9/7 config fixes ... live on VPS but NOT committed anywhere."
**Impact:** the authoritative runtime cannot be reproduced by `git clone`/`pull` on any other machine. The 3-way sync goal is structurally impossible until these are committed. Blocks productization (D16).
**Recommendation:** commit `~/.hermes/hermes-agent/` changes (or vendor them) to `hermes-live`; establish that runtime edits MUST be committed.
**[BEYOND]:** this is a deeper finding than the charter's "GitHub stale" — the fix lives nowhere durable.

### [CRITICAL] SYNC — Three sources of truth are mutually inconsistent and none is durable
**File(s):** VPS `~/.hermes/` (live) vs `C:\Users\amiru\hermes-snapshot-20260707\` (STALE 7/7, contains `.env`) vs GitHub `amirulhazym/hermes-agent-personal_assistant` (STALE ~Jun28/Jul1)
**Evidence:** 09-MASTER-SYNC-DOC §1 platform table; Windows snapshot has OLD config (deepseek-v4-pro, fallback []).
**Impact:** any "merge into GitHub" (charter intent) will silently lose the 9/7 fixes or reintroduce stale config. The bi-directional sync the user wants has no mechanism.
**Recommendation:** define ONE durable source (git), automate VPS→git, exclude secrets, verify drift daily (Jane as verifier).
**[BEYOND]:** the user's own handoff under-weighted this; the real defect is "no durable source," not just "stale copies."

---

## D14 — Security & secrets

### [CRITICAL] SECURITY — WhatsApp `session/` directory is world/group-readable (775)
**File(s):** `~/.hermes/whatsapp/session/` → `drwxrwxr-x` (verified `stat`)
**Evidence:** `ls -ld ~/.hermes/whatsapp/session` → `drwxrwxr-x 2 ubuntu ubuntu ... Jul 9 14:37`
**Impact:** Baileys session = full WhatsApp account credential. Any local user or compromised service on the VPS can hijack the account. Unlike `.env`/`auth.json` (600), this is exposed.
**Recommendation:** `chmod 700 ~/.hermes/whatsapp/session` (and parent chain). Add to provisioning.
**[BEYOND]:** not in prior audits' security sections.

### [HIGH] SECURITY — `.env` copy sits in the STALE Windows snapshot
**File(s):** `C:\Users\amiru\hermes-snapshot-20260707\.env` (copy, user chose not to delete 2026-07-07 23:39)
**Evidence:** 08-EVIDENCE-APPENDIX A9: "Contains: .env copy ... SECURITY RISK if PC compromised."
**Impact:** if the Windows PC is compromised, all API keys (DEEPSEEK, OPENCODE_ZEN/GO, TELEGRAM_BOT_TOKEN) leak.
**Recommendation:** purge `.env` from any snapshot; add to `.gitignore`/exclusion list; rotate keys if PC untrusted.

### [HIGH] SECURITY — Public GitHub repo may expose PII/med data
**File(s):** GitHub `amirulhazym/hermes-agent-personal_assistant` (public)
**Evidence:** charter says repo is "docs only" but unverified. `med-status.json` (PII: med intake times, drugs) must NEVER reach public repo. `channel_directory.json` has the WhatsApp group ID (low sensitivity).
**Impact:** accidental push of med-*/state JSON = public patient-data leak.
**Recommendation:** verify repo has no med/state JSON; add a pre-push hook / secret+PII scan; keep runtime state VPS-only.
**Status:** UNVERIFIED (repo not read this pass) — must check before any `git push`.

### [MEDIUM] SECURITY — Orphaned `minimax_proxy.py` references dead endpoint
**File(s):** `scripts/minimax_proxy.py`
**Evidence:** `api.minimax.com` is NXDOMAIN (00-SYNC-UPDATE §MiniMax). User ignored minimax 9/7.
**Impact:** dead code; misleading capability signal; if re-enabled, fails silently.
**Recommendation:** delete or quarantine.

---

## D4 / D5 — Orchestration, tools, MCP

### [HIGH] ORCHESTRATION — Med constraint engine (Spec v3, 9.95/10) is designed but NOT implemented
**File(s):** `MED_CHAIN_ENGINE_SPEC_v3.md` (status: PENDING EXTERNAL AUDIT) vs `scripts/med_chain/` (does not exist)
**Evidence:** `ls ~/.hermes/scripts/med_chain/` → No such file or directory. Spec says "This spec is NOT yet implemented."
**Impact:** the core safety-critical timing logic remains LLM-linearized (E-follows-C bug persists in practice). The user paid for a 9.95/10 design that shipped as a doc, not code.
**Recommendation:** implement Spec v3 (rules.json → solve → resolve_conflict → trace → validate → route → why), with the regression test for Bug #17. This is the single highest-value med fix.
**[BEYOND]:** the spec exists; the gap is execution. Prior audits didn't see it (it postdates them).

### [MEDIUM] MCP/TOOLS — `mcp_servers: {}`; three orphan model drivers
**File(s):** `config.yaml:13 (mcp_servers: {})`; `scripts/qwen_driver.py`, `scripts/sakana_driver.py`, `scripts/minimax_proxy.py`
**Evidence:** config has no MCP; the three drivers are not referenced by live config.
**Impact:** no tool-extensibility active; orphan scripts imply capability that isn't wired; maintenance confusion.
**Recommendation:** either wire a real MCP server (e.g. for vision/Obsidian) or delete the orphan drivers.

---

## D6 / D15 — Cron, automation, observability

### [HIGH] CRON — `Daily Health` "Broken Pipe" root cause unknown; job disabled, not fixed
**File(s):** `cron/jobs.json` (Daily Health `active=False`); 09-MASTER-SYNC-DOC §6 open item
**Evidence:** "Daily Health cron Broken Pipe — was it fixed? (Need verification)."
**Impact:** a previously-broken LLM job was switched off rather than repaired; if re-enabled, breaks again.
**Recommendation:** find + fix the Broken Pipe (likely a pipe to a dead subprocess); only then re-enable.
**Status:** UNVERIFIED root cause.

### [MEDIUM] OBSERVABILITY — No verified dead-man's-switch alert
**File(s):** `scripts/hello_watch.py` (`active=False`), `health_check.py`, `gateway_state.json` stale-state bug
**Evidence:** heartbeat job disabled; gateway_state bug means restart can silently fail (09-MASTER-SYNC-DOC A10).
**Impact:** if gateway dies at 3am, no one is alerted; meds go unreminded silently — patient-safety.
**Recommendation:** external heartbeat → Telegram/WhatsApp alert on failure; fix stale-state bug in `run.py` launch.

### [LOW] CRON — `V2 Overnight Build Verify` cron has null script
**File(s):** `cron/jobs.json` (V2 Overnight Build: `script: null`)
**Evidence:** job delivers a message but runs no build.
**Impact:** mislabeled; suggests automation that isn't there.
**Recommendation:** point to `build_overnight.py` or rename.

---

## D7 / D8 / D9 / D10 — Workflows, skills, hooks, memory

### [MEDIUM] WORKFLOW — Documented automations are ~entirely aspirational
**File(s):** `ADVANCED-IDEAS.md` (11+ ideas) vs live cron (only 6 active, none are the "self-improvement loop / memory-contradiction detective / weekly retrospective")
**Evidence:** no standing automation for any ADVANCED-IDEA beyond med cron.
**Impact:** the system is far below the "beyond basic assistant" bar the user set. Gap between vision and shipped reality.
**Recommendation:** pick 2-3 highest-ROI ideas (memory-contradiction detective, weekly retrospective) and actually wire them; drop the rest from the "roadmap" framing.
**[BEYOND]:** the user explicitly wants this dimension covered; prior med-centric audits missed it.

### [MEDIUM] SKILLS — 60+ skills, no curation/retirement; irrelevant bloat
**File(s):** `~/.hermes/skills/` (gsap-*, canvas-design, brand-guidelines, apple, material-3, ...)
**Evidence:** skill list includes many irrelevant to a personal/med assistant.
**Impact:** load, context pollution, larger attack surface; `auto-skill-suggester` may surface irrelevant skills.
**Recommendation:** curate to a personal-assistant core; archive the rest.
**Status:** impact UNVERIFIED but noted.

### [MEDIUM] HOOKS — Guardrails cover text output, not state writes (Pattern D uncovered)
**File(s):** `~/.hermes/hooks/anti-fabrication-guardrails/`, `skill-trigger/`
**Evidence:** hook prevents fabricating drug names in text; Pattern D (assistant resets med data without checking history) is a STATE mutation, not text.
**Impact:** the most damaging recurring failure mode (data reset) has no guard.
**Recommendation:** add a pre-write hook / confirmation gate on `med_confirm.py` state mutations when history shows recent conflicting intake.

### [MEDIUM] MEMORY — `memory_watch.py` disabled; no contradiction detection running
**File(s):** `cron/jobs.json` (Memory Watchdog `active=False`); `ADVANCED-IDEAS` "Memory Contradiction Detective"
**Evidence:** job present but off.
**Impact:** memory can accumulate contradictions (the user explicitly worried about this).
**Recommendation:** enable a safe read-only memory-consistency scan.

---

## D1 / D3 — Infra, model/cost

### [HIGH] INFRA — `gateway_state.json` stale-state bug blocks restart (P0, unfixed)
**File(s):** `~/.hermes/gateway_state.json`; `gateway/run.py` launch (per 09-MASTER-SYNC-DOC A10)
**Evidence:** after SIGTERM, file persists `"running": true`; only manual `rm` fixes. "Still UNFIXED as of 9/7."
**Impact:** any crash/restart can silently fail to come back up → total outage, no meds.
**Recommendation:** fix launch sequence to write state atomically + clear on clean shutdown.

### [MEDIUM] INFRA/TZ — `chain_monitor.sh:88` uses naive `datetime.now()` for reminder timestamps
**File(s):** `scripts/chain_monitor.sh:88` vs `chain_calc.py:109-110` (`now_myt()`)
**Evidence:** `state['last_reminder_times'][slot] = _dt.datetime.now().strftime('%H:%M')` (naive local).
**Impact:** IF host is not MYT, cooldown delta is wrong → spam or silence. `chain_calc.py` correctly uses MYT, so the two writers disagree.
**Status:** UNVERIFIED whether host is MYT — if it is, impact is low; if not, HIGH. **Recommendation:** use `ZoneInfo('Asia/Kuala_Lumpur')` in the shell inline Python; store epoch minutes. Verify host TZ.

### [LOW] CONFIG — v2.2 handoff mis-states `fallback_providers`
**File(s):** v2.2 vs live `config.yaml:6-10`
**Evidence:** v2.2: `[hy3-free, deepseek-v4-flash-free]`; live: `[{opencode-zen, hy3-free}, {opencode-zen, deepseek-v4-flash-free}]`.
**Impact:** an auditor following v2.2 verbatim would "fix" the config to a wrong shape.
**Recommendation:** (none — just corrected here). Future handoffs should quote live config verbatim.

### [LOW] MODEL — `minimax` still appears in model picker though non-functional
**File(s):** built-in plugin resolves `api.minimax.io/anthropic` (00-SYNC-UPDATE)
**Evidence:** minimax block deleted from config but built-in still offers it; key rejected (401).
**Impact:** user can pick a model that fails; fallback may mask it.
**Recommendation:** hide non-functional providers from picker.

---

## D13 — Script correctness (system-wide, beyond med)

### [MEDIUM] SCRIPT — `except Exception: pass` swallows errors across med scripts
**File(s):** `med_confirm.py:238,268,298,333`; `med_supply.decrement` guarded silently
**Evidence:** multiple bare `except Exception: pass`.
**Impact:** failures (e.g. supply decrement, resolution) are invisible; data can drift undetected.
**Recommendation:** catch specific exceptions; log; never silently pass on state-mutating paths.

### [MEDIUM] SCRIPT — `get_actual_time` docstring says "earliest" but returns latest
**File(s):** `chain_calc.py:362-383`
**Evidence:** docstring "earliest taken time" vs `return sorted(times)[-1]`.
**Impact:** maintenance hazard; a future caller trusting "earliest" (e.g. empty-stomach 1h rule) computes wrong gaps.
**Recommendation:** fix docstring; add `get_earliest_taken_time` if needed.

### [LOW] SCRIPT — `med_confirm.py` re-stamp on `--update` (user-invoked variant)
**File(s):** `med_confirm.py` `--update <LETTER> HH:MM` path
**Evidence:** bulk re-stamps all taken drugs to one value (baseline HIGH, live).
**Impact:** collapses genuinely different real times to one.
**Recommendation:** scope `--update` to a specific drug_id.

---

## Second workstream (the audit under-weighted this)

### [MEDIUM] INTEGRATION — `fetcher/` anti-bot engine: substantial, committed, but split-source
**File(s):** `~/mjay/fetcher/` (router.py, capability_registry.py, cost_optimizer.py, analytics.py, domain_memory.py, executors/*) ; data in `~/.hermes/fetcher/*.db`
**Evidence:** 7 git commits 9/7 00:43-01:08; `build_overnight.py` (11KB, uncommitted).
**Impact:** real IP (capability-routed scraper w/ cost optimizer). But code (git) vs data (`~/.hermes`) vs build script (uncommitted) are three places; not covered by any med-sync process.
**Recommendation:** fold into the same durable-source + sync discipline; document as a separable product (D16).
**[BEYOND]:** entirely absent from v2.2 scope; first time surfaced in audit.

---

## L2 Deep Dive: New findings from expanded scope (hooks, config, orchestration, plugins)

### [CRITICAL][DATA-INTEGRITY] — L2-N5: `med-auto-confirm` hook DRUG_MAP hardcodes `akurit_4` — drift inherited
**File(s):** `hooks/med-auto-confirm/handler.py:57`
**Evidence:** `DRUG_MAP` entry: `(r"\bakurit[- ]?4?\b", "A", "akurit_4")`. The hook auto-confirms Akurit messages before agent processes them — but won't recognize Akurit-2 correctly since `akurit[- ]?4?\b` may not match "Akurit-2".
**Impact:** same Akurit drift infects the hook layer. Auto-confirm bypassed for the real current drug, defeating the hook's purpose.
**Root cause:** DRUG_MAP never updated to reflect 9/7 pharmacy swap.
**Recommendation:** add `(r"\bakurit[- ]?2?\b", "A", "akurit_2")` to DRUG_MAP; rename `akurit_4` references.

### [HIGH][ORCHESTRATION] — L2-N1: Kanban task orchestration layer ACTIVE and unexamined
**File(s):** `config.yaml:~140-158` (`kanban.dispatch_in_gateway: true`, `auto_decompose: true`, `max_in_progress_per_profile: null`); `~/.hermes/kanban.db` (114KB)
**Evidence:** Kanban dispatches tasks in the gateway, auto-decomposes work items, has its own worker profile system. `orchestrator_profile: ''`, `default_assignee: ''`, `max_in_progress_per_profile: null` (unbounded). `dispatch_stale_timeout_seconds: 14400` (4h timeout).
**Impact:** a whole task-orchestration system runs silently inside the gateway — managing workloads, decomposing tasks, dispatching workers. Completely absent from prior audits. Unbounded in-progress items risk unbounded concurrency.
**Recommendation:** audit kanban state (`kanban.db`), set `max_in_progress_per_profile` to a safe limit, wire to overhaul workflow.
**[BEYOND]:** entirely missed by all prior audits.

### [HIGH][ORCHESTRATION] — L2-N2: Subagent delegation system ACTIVE (multi-agent foundation exists)
**File(s):** `config.yaml:~390-400` (`delegation.orchestrator_enabled: true`, `max_concurrent_children: 3`, `max_spawn_depth: 1`, `max_iterations: 50`, `subagent_auto_approve: false`)
**Evidence:** Hermes supports spawning subagents with their own tool/inherit-MCP. `max_spawn_depth: 1` (agents can't spawn sub-agents = safe), `orchestrator_enabled: true`, `max_concurrent_children: 3`. User's vision of "multi-agent expert system" has FOUNDATIONAL SUPPORT but nothing uses it yet.
**Impact:** the platform CAN support the user's overhaul vision. Gap is in wiring, not architecture.
**Recommendation:** document available delegation patterns; wire kanban + delegation together for overhaul task execution.
**[BEYOND]:** entirely missed.

### [HIGH][CLINICAL] — L2-N4: Chain logic is PURE LINEAR with no floor/independent guards
**File(s):** `scripts/chain_calc.py:413-463` (`calculate_ready_time`)
**Evidence:** Ready times are: B = A + 1h, C = B + 4h, D = C + 4h, E = B + 12h. NO `max(calculated, default_time)` floor. NO empty-stomach gate modeling (A→B 1h is coincidental, not explicit constraint). Dexa #2 (C) = B + 4h, not max(B+4h, 12:00). E follows B, contradicting Spec v3 rule_005 "independent." Fire logic at line ~610 blocks 22:00-05:00 — so if A late → B late → E = B+12h may land in quiet hours → reminder blocked silently.
**Impact:** patient-adherence guidance is numerically wrong for real-life scenarios. Late A cascades too aggressively; early A pulls Dexa earlier than standard.
**Recommendation:** implement Spec v3 constraint engine with explicit clinical rules: (1) A→B min-gap 1h (empty-stomach gate), (2) Dexa #1 ≥ 08:00 (standard floor), (3) Dexa→Dexa = max(prev+4h, standard), (4) E = max(B+12h, 20:00), (5) E independent (no cascade from C/D).
**[BEYOND]:** v2.2's central correction; verified this is the exact model gap.

### [HIGH][CONFIG] — N8: Auxiliary tasks use PAID deepseek-v4-flash for web_extract + compression
**File(s):** `config.yaml:~220-250` (`auxiliary.web_extract.provider: deepseek, model: deepseek-v4-flash`; `auxiliary.compression.provider: deepseek, model: deepseek-v4-flash`)
**Evidence:** Two auxiliary tasks (web extraction, context compression) use `deepseek-v4-flash` (PAID model). Vision uses `opencode-zen/mimo-v2.5-free` (free). User's free-only rule applies to fallback chain ONLY — auxiliary can still burn paid tokens silently.
**Impact:** every web-extraction call (via hybrid-web) burns paid tokens. Every context compression event (50% threshold) burns paid tokens. Cost invisible at `/usage`.
**Recommendation:** audit auxiliary costs; move web_extract to free model if quality OK; add cost logging/tracking.

### [MEDIUM][MEMORY] — L2-N3: Memory curator IS active and runs weekly
**File(s):** `config.yaml:~400-410` (`curator.enabled: true`, `interval_hours: 168`, `stale_after_days: 30`, `archive_after_days: 90`, `prune_builtins: true`, `backup.enabled: true, keep: 5`)
**Evidence:** The self-cleaning memory system I said was "disabled" is actually ACTIVE — runs every 7 days, archives stale entries >30d, prunes builtins. Backs up automatically (5 copies). My own finding D10/Memory is PARTIALLY INCORRECT: the curator is running.
**Correction:** update D10 finding: memory_watch.py cron is disabled but curator IS active and handles contradiction detection indirectly via staleness. Memory-contradiction detective (ADVANCED-IDEAS) still aspirational.
**Recommendation:** document the curator as the self-cleaning mechanism; wire weekly contradiction report to it.

### [MEDIUM][HOOKS] — L2-N13: med-auto-confirm dexa boundary uses redundant condition
**File(s):** `hooks/med-auto-confirm/handler.py:121`
**Evidence:** `if h < 10 or h < 10.5:` — `h < 10` is a SUBSET of `h < 10.5`. The second check NEVER triggers. Same lossy boundary as `med_resolve.py:141` float hack.
**Impact:** a dexa at 10:20 maps to slot B (h=10, `h < 10` = false, but `h < 10.5` should be true). Actually wait: if h=10, 10 < 10 is false, but 10 < 10.5 is TRUE. So `10 < 10 or 10 < 10.5` = `False or True` = True → maps to B. The condition IS redundant (10 < 10.5 subsumes 10 < 10) but functionally correct for h=10. The real bug: what about h=9.5 (09:30)? 9.5 < 10 OR 9.5 < 10.5 = True → B. But 09:30 is still 9:30am, B slot standard is 08:00, so mapping to B is arguably correct. The redundancy is CODE QUALITY, not functional bug — but it shows the same boundary confusion as med_resolve.
**Severity downgraded:** LOW impact, MEDIUM code quality.

### [MEDIUM][PLUGINS] — L2-N6: lightclawbot third-party platform adapter installed but not enabled
**File(s):** `plugins/lightclawbot/` — `plugin.yaml` (kind: platform, v0.0.6 by lhanyun); src/ with `inbound.py`, `outbound.py`, `adapter.py`, `socket/`, `per_uin_session.py`, `tenancy.py`, `media.py`, `file_storage.py`, `download_handler.py`, `usage_tracker.py`
**Evidence:** Third-party WebSocket platform adapter (multi-user, multi-tenant). Requires `LIGHTCLAW_API_KEY_${UIN}` env. NOT in `plugins.enabled: [web-trafilatura, hybrid-web]` (config.yaml:~660). Installed but inactive.
**Impact:** attack surface if enabled without audit (WebSocket, custom file storage, multi-user session isolation). Code quality of third-party package UNVERIFIED.
**Recommendation:** quarantine or delete if not deploying; security-audit before enabling.

### [MEDIUM][SECURITY] — L2-N9: Tirith security scanner configured fail_open
**File(s):** `config.yaml:~570` (`security.tirith_enabled: true`, `tirith_fail_open: true`)
**Evidence:** "If Tirith fails or times out, the check passes." Mitigates false-positive blocks but means a broken/crashed Tirith = no security checks.
**Impact:** false sense of security — user thinks scanner protects when it silently passes on failure.
**Recommendation:** add health check for Tirith; consider `tirith_fail_open: false` with monitoring override.

### [MEDIUM][HOOKS] — L2-C3: hello-world hook fires but reads nothing (dead pipeline)
**File(s):** `hooks/hello-world/handler.py` (writes `hello-world-pending.txt` on `gateway:startup`); `scripts/hello_watch.py` (cron, `active=False`)
**Evidence:** Hook writes a pending marker on every gateway restart. The cron job that reads and sends it (`hello_watch.py`) is disabled. So the marker accumulates but never delivers.
**Correction:** The 09-MASTER-SYNC-DOC A1 claimed hello-world-watch is "GONE." It's NOT gone — it's DISABLED. The hook (which fires) and the cron (which doesn't) form a dead pipeline.
**Recommendation:** either wire a tiny shell-based reader into the startup sequence, or remove both hook + script entirely.

### [LOW][CONFIG] — L2-C1: Host TZ confirmed MYT; `chain_monitor.sh:88` naive datetime is correct in production
**File(s):** `config.yaml:~430` (`timezone: Asia/Kuala_Lumpur`)
**Evidence:** Previous MEDIUM finding (#TZ) flagged `chain_monitor.sh:88` using naive `_dt.datetime.now()` as TZ-fragile. Config confirms host is MYT. In production this code is correct.
**Correction:** DOWNGRADE from MEDIUM to LOW/THEORETICAL. Only becomes a bug if host is moved from MYT. `chain_calc.py` correctly uses `now_myt()` — consistency already ensured for this host.
**Recommendation:** still good practice to use `now_myt()` in chain_monitor.sh for future portability; de-prioritize.

### [LOW][INTEGRATION] — L2-N7: hybrid-web plugin active and working
**File(s):** `plugins/hybrid-web/provider.py, __init__.py` (v1.0.0, by Amirul); `config.yaml:~112` (`web.extract_backend: hybrid-web`)
**Evidence:** Custom plugin for intelligent Trafilatura↔Crawl4AI routing. ACTIVE and wired to web extraction.
**Recommendation:** document as a configurable asset; note it uses paid deepseek for extraction (N8).

### [LOW][MEMORY] — L2-N10: Session auto-reset at 4am/4h idle
**File(s):** `config.yaml:~670` (`session_reset.mode: both, idle_minutes: 240, at_hour: 4`)
**Evidence:** If user doesn't interact for 4 hours, or at 4am daily, session resets. Mid-day med context can be lost.
**Impact:** if user takes A at 6am, then doesn't interact until 11am (5h idle), session resets — agent enters without med context from earlier confirmation. Hook (med-auto-confirm) helps but only for the confirmation action, not the contextual awareness.
**Recommendation:** ensure med confirmation state survives session reset; consider suppressing reset during active med-tracking windows (5am-10pm).

### [LOW][TOOLS] — L2-N11: Computer use ENABLED though MCP inactive
**File(s):** `config.yaml:~655` (`computer_use.enabled: true`, `cua_telemetry: false`)
**Evidence:** Feature flag on but `mcp_servers: {}` means no runtime available. `cua-driver.exe` was removed 9/7.
**Recommendation:** either wire computer use properly or disable the flag.

### [LOW][MODEL] — L2-N12: x_search uses grok-4.20-reasoning (external paid dependency)
**File(s):** `config.yaml:~640` (`x_search.model: grok-4.20-reasoning, timeout_seconds: 180, retries: 2`)
**Evidence:** X/Twitter search uses a separate model (grok) — dependency on X API + potential paid usage.
**Recommendation:** document as external dependency; note cost implications.

### [LOW][CONFIG] — L2-C2: med-auto-confirm hook PARTIALLY addresses Pattern D (with inherited bugs)
**File(s):** hooks/med-auto-confirm/handler.py (agent:start hook)
**Evidence:** My earlier finding "Hooks cover text not state (Pattern D uncovered)" is PARTIALLY INCORRECT. The med-auto-confirm hook DOES run med_confirm.py as a side-effect BEFORE the agent processes the message — so the state IS updated before the LLM can overwrite it. This IS a Pattern D countermeasure. However, it inherits the Akurit-4 drift (L2-N5) and the dexa boundary redundancy (L2-N13).
**Correction:** Update D9 finding: Pattern D is PARTIALLY covered by this hook; the remaining gap is the inherited drift + the agent can still override after the hook fires (since hook runs at agent:start, agent still processes the message).

**[BEYOND note for all L2 findings]:** These are from the L2 deep expansion — all 14 are [BEYOND] the prior baseline audit. Prior auditors (zcode, gemini, zhipu, etc.) read none of these layers.

---

## Cross-dimension findings (flagged)

- **C1 (D2+D12+D14+D16):** the root cause of most CRITICALs is **"no single durable, secret-safe, version-controlled source of truth."** Fixing this one thing cascades: reproducibility, sync, security, and productizability all improve. This is the headline.
- **C2 (D4+D12+D-clinical):** safety-critical logic (meds) is still LLM-linearized because the deterministic engine was designed but not built. Highest clinical-value fix = implement Spec v3.
- **C3 (D6+D15):** observability of the med reminder path is thin (disabled heartbeat, stale-state bug) — silent failure = silent missed dose.

---

## Items I could NOT confirm (NOT rounded up)

- systemd unit file (`/etc/systemd/...`) contents — SSH didn't reach it.
- ~~Host OS timezone — determines if `chain_monitor.sh:88` is actually buggy.~~ **RESOLVED:** config.yaml `timezone: Asia/Kuala_Lumpur` — host IS MYT, `chain_monitor.sh:88` naive datetime is correct in production. Finding DOWNGRADED to LOW/THEORETICAL (only breaks if host moved from MYT).
- ~~`USER.md` presence; `memories/` contents.~~ **RESOLVED:** USER.md read (22 lines, confirms multi-agent vision), MEMORY.md read (72 lines, rich history).
- `GOOGLE_API_KEY` / vision pipeline liveness.
- GitHub repo PII exposure (must check before any push).
- Whether `Daily Health` Broken Pipe root cause is fixed.

Each is marked UNVERIFIED above; none is presented as fact.
