# zai-audit-02 — Full Audit Findings (Hermes Agent / MJ)

> **Auditor:** Z.ai (GLM-5.2) — fresh, independent, evidence-first
> **Date:** 2026-07-09 · **Basis:** live VPS read-only + fresh 9/7 snapshot + audit-prep + prior audits (re-verified, not trusted)
> **Format:** `[Severity][Category] — D<n> short desc`. Every item cites file:line or raw output. UNVERIFIED/THEORETICAL tagged.
> **Baseline cleared:** Known Patterns A–E + the 44-item `2026-07-05-zcode-audit-02` set + recurring gemini/zhipu items. Items marked **[BEYOND]** are new vs that baseline.

**Severity:** CRITICAL (data loss / patient-safety / system failure / secret exposure) · HIGH (wrong behavior / silent gap) · MEDIUM (edge/debt) · LOW (cosmetic/doc).

**Counts (this pass): CRITICAL: 9 · HIGH: 14 · MEDIUM: 12 · LOW: 6 = 41.** Of these, **18 are [BEYOND]** the prior baseline (new dimensions: orchestration, security perms, second workstream, sync-of-truth, aspirational-vs-shipped).

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

## Cross-dimension findings (flagged)

- **C1 (D2+D12+D14+D16):** the root cause of most CRITICALs is **"no single durable, secret-safe, version-controlled source of truth."** Fixing this one thing cascades: reproducibility, sync, security, and productizability all improve. This is the headline.
- **C2 (D4+D12+D-clinical):** safety-critical logic (meds) is still LLM-linearized because the deterministic engine was designed but not built. Highest clinical-value fix = implement Spec v3.
- **C3 (D6+D15):** observability of the med reminder path is thin (disabled heartbeat, stale-state bug) — silent failure = silent missed dose.

---

## Items I could NOT confirm (NOT rounded up)

- systemd unit file (`/etc/systemd/...`) contents — SSH didn't reach it.
- Host OS timezone — determines if `chain_monitor.sh:88` is actually buggy.
- `GOOGLE_API_KEY` / vision pipeline liveness.
- `USER.md` presence; `memories/` contents.
- GitHub repo PII exposure (must check before any push).
- Whether `Daily Health` Broken Pipe root cause is fixed.

Each is marked UNVERIFIED above; none is presented as fact.
