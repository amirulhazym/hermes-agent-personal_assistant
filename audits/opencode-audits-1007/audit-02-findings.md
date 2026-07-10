<!-- ===== OVERHAUL ADDENDUM — 2026-07-09 (OpenCode deep-audit extension) =====
Original v2.2-baseline findings F-01..F-13 (above) are preserved verbatim.
New deep-audit findings F-14..F-24 are appended below, each citing live VPS
file:line evidence. No prior text removed or altered.
============================================================================= -->

# audit-02-findings.md — Hermes Agent (MarryJane / MJ) Findings

> Auditor: OpenCode (read-only SSH, live VPS). Every finding cites `file:line` or raw command output.
> Label rule: CONFIRMED (live-verified) | THEORETICAL (inferred from code, not runtime-tested) | UNVERIFIED (could not test).
> Prior AI reports (Zhipu/Qwen/Sakana/Claude/Gemini) were RE-VERIFIED; claims not reproducible are struck, not echoed.

---

## TOP-LINE
- **Med "Domino Chain" encodes a clinically-wrong blind-shift model** (chain_calc.py:416-460) — the exact mistake the charter warns about.
- **Gateway watchdog is silently dead** because it hardcodes `/home/amirul/` on a `/home/ubuntu` box (watchdog.sh:9-13) → the gateway stale-state "P0" is REAL and UNMITIGATED here.
- **The audit handoff's med-schedule drift claim was partially wrong**: the live file DOES contain Pyridoxine (Slot A) and Calcium+Calcitriol (Slot C); only the drug *name* "Akurit-4" is stale. Trusting the prep-doc snippet would have produced a false CRITICAL.

---

## CRITICAL

### F-01 [CRITICAL][Health/Script correctness] Med chain blindly shifts ALL slots when A is late
- **File:** `scripts/chain_calc.py:416-460` (`calculate_ready_time`); `med-schedule.json:85` (`shift_logic` rule); `scripts/chain_calc.py:735` (reminder text "A lambat = B,C,D,E semua akan geser").
- **Evidence:**
  ```
  chain_calc.py:432   b_min = a_min + int(GAPS['A_to_B'] * 60)   # B anchored to A
  chain_calc.py:440   c_min = b_min + int(GAPS['B_to_C'] * 60)   # C anchored to B
  chain_calc.py:448   d_min = c_min + int(GAPS['C_to_D'] * 60)   # D anchored to C
  chain_calc.py:456   e_min = b_min + int(GAPS['B_to_E'] * 60)   # E anchored to B
  med-schedule.json:85  "shift_logic": "Jika A lambat, semua meds shift accordingly. Gap minimum A→B = 1h."
  ```
- **Impact:** If A (Akurit-2) is taken at 09:00 (3h late), the engine pushes B→10:00, C→14:00, D→18:00, E→22:00. But Dexamethasone #1 should hold ~08:00 and its own 4h doses (12:00/16:00); Levetiracetam B/E keep a 12h clock. The system does NOT model the ~1h empty-stomach wait *only*, nor Dexa's independence. This is the #1 error prior audits made and the live code repeats it.
- **Root cause:** Design assumed a single linear chain; pharmacology treated as one dependency graph.
- **Recommendation:** Re-model as independent clocks: Dexa doses anchored to fixed 08/12/16; Levetiracetam B/E = 12h pair; A only gates B's *earliest* time via the empty-stomach wait (min 1h after A, but not "B = A+1h"). Keep 4h Dexa→Dexa gaps as a hard clinical constraint, not a side-effect of A.

### F-02 [CRITICAL][Data integrity / Health] Akurit-2 pharmacy swap (9/7) NOT tracked anywhere
- **File:** `med-schedule.json:13-22` (`"Akurit-4"`, `"akurit_4"`); `med-status.json` (7× "akurit_4" historical); `med-interactions.json:6-7` (`"akurit_4": "Akurit-4 (INH+RIF+PZA+ETB)"`); `substitutions.json` (akurit_4).
- **Evidence:** `grep -c akurit_4 med-schedule.json → 1`; `med-status.json` today's A entry: `{'akurit_4': {'status':'taken','time':'06:00'}}`. Live `med-schedule.json:13` still `"Akurit-4"`. No `akurit_2` anywhere.
- **Impact:** The real 9/7 swap to 4-dose Akurit-2 is invisible to the system. Dose-count, interaction checks, and reports all reference the wrong drug. Clinically the regimen composition changed; the assistant would give wrong advice if asked.
- **Root cause:** State files edited by hand/ad-hoc; no single source-of-truth update path; swap done in real life but never propagated.
- **Recommendation:** Rename `akurit_4`→`akurit_2` across all state + interaction + substitution files; re-verify INH/RIF/PZA/ETB composition against the new product; update `med-interactions.json` name. (Use `--dry-run`/backup first per FULL-GUIDE Phase 5.)

### F-03 [CRITICAL][Cross-component / Reliability] Gateway watchdog is broken by wrong hardcoded home dir → stale-state P0 UNMITIGATED
- **File:** `scripts/watchdog.sh:9-13` (`/home/amirul/.hermes/...`); `gateway/run.py:6716` (persists `gateway_state="running"` on unexpected SIGTERM); `hermes_cli/gateway.py:918` (treats `gateway_state=="running"` as alive).
- **Evidence:**
  ```
  watchdog.sh:12   STATE_FILE="/home/amirul/.hermes/gateway_state.json"
  $HOME on VPS = /home/ubuntu   (verified: echo $HOME → /home/ubuntu)
  run.py:6716      self._update_runtime_status("running", self._exit_reason)  # on unexpected signal
  gateway.py:918   if gateway_state == "running": ... return True  # restart gate
  ```
  The watchdog's `restart_gateway()` does `rm -f "$STATE_FILE"` (watchdog.sh:22) but against `/home/amirul/...` which does not exist → real `/home/ubuntu/.hermes/gateway_state.json` is never cleaned.
- **Impact:** If the gateway dies via bare `kill -TERM`/OOM/s6 SIGTERM, `gateway_state.json` persists `"running"` (by design, issue #42675), the watchdog's cleanup is a no-op, and a subsequent start is blocked because the gate sees "running". Messaging channels go dark until manual `rm`. This is the exact "blocks restart" P0 — and on THIS VPS it has no working mitigation.
- **Root cause:** Scripts written for a different machine (`amirul` user); never ported when deployed on `ubuntu` VPS. The run.py "running-on-signal" behavior is intentional for containers but harmful on a bare systemd box without a working watchdog.
- **Recommendation:** (a) Replace hardcoded `/home/amirul` with `$HOME`/`$HERMES_HOME` in watchdog.sh + check_ds_balance.sh. (b) Until then, the stale-state risk is live — document the manual `rm ~/.hermes/gateway_state.json` workaround in RUNBOOK. (c) Consider making run.py persist `running` only under s6/container detection, not bare-systemd.

---

## HIGH

### F-04 [HIGH][Script correctness / Data integrity] chain-state.json only retains the LAST processed slot
- **File:** `scripts/chain_monitor.sh:85` `state['last_reminder_sent'] = {slot: counts[slot]}`.
- **Evidence:** chain-state.json today shows only `"C"` under `last_reminder_sent`/`last_reminder_times`/`reminder_counts` despite A/B having fired earlier. Line 85 **replaces** the whole dict with a single key each run; only `reminder_counts` (cumulative `counts` dict) survives, the other two are clobbered.
- **Impact:** Any tool/diagnostic reading `last_reminder_sent`/`last_reminder_times` sees only the most-recent slot — misleading state, breaks cooldown/audit logic that assumes per-slot history.
- **Root cause:** assignment instead of `state['last_reminder_sent'][slot] = ...` (merge).
- **Recommendation:** Use `state.setdefault('last_reminder_sent', {})[slot] = counts[slot]` (same pattern as line 89).

### F-05 [HIGH][Script correctness / Cost] V2 Overnight Build cron is an agent-driven LLM job in the wrong workstream
- **File:** `cron/jobs.json` job `1bf7fcc00b60` (name "V2 Overnight Build Verify + Report", schedule `0 7 * * *`, `prompt:`=long LLM prompt, no `script:`, delivers WhatsApp).
- **Evidence:** `hermes cron list` shows it as the only non-`no-agent` active job; its prompt verifies the *anti-bot fragrantica build* (separate research workstream), not the med/personal-assistant system.
- **Impact:** (1) Daily LLM token cost for an unrelated experiment. (2) Scope contamination — pollutes the medication/audit cron set and confuses future auditors. (3) If the anti-bot build is abandoned, this job keeps running forever.
- **Root cause:** Two workstreams (audit vs anti-bot) were developed in parallel without separation.
- **Recommendation:** Move anti-bot crons to a separate命名/tag or repo; or convert to `no-agent` + a static report script. Confirm with user before touching (separate workstream).

### F-06 [HIGH][Config] `providers: '{}'` is a quoted STRING, not a mapping
- **File:** `config.yaml:5`.
- **Evidence:** `config.yaml:5  providers: '{}'` (single-quoted). Compare `config.yaml` `credential_pool_strategies: {}` (proper mapping at line ~). Syntax-valid YAML but the value is the *string* `"{}"`.
- **Impact:** THEORETICAL — any code path doing `config["providers"].get("minimax")` would raise `AttributeError: 'str' object has no attribute 'get'`. System currently runs, so it may be coerced somewhere, but this is a latent landmine and inconsistent with the rest of the config.
- **Root cause:** Manual edit 9/7 set it as a quoted literal (likely to "empty it out" without valid empty-map YAML).
- **Recommendation:** Change to `providers: {}` (unquoted). Verify gateway still starts. (Low-risk, but verify.)

---

## MEDIUM

### F-07 [MEDIUM][Script correctness] check_ds_balance.sh sources wrong .env path → DeepSeek balance check silently fails
- **File:** `scripts/check_ds_balance.sh:3` `source /home/amirul/.hermes/.env 2>/dev/null`.
- **Evidence:** same wrong-home issue as F-03; `2>/dev/null` hides the failure. The `Daily Usage Report`/`DeepSeek Balance Check` jobs (now removed) and any manual run of this script cannot load keys.
- **Impact:** Billing visibility broken; cost tracking gaps.
- **Recommendation:** Use `$HOME/.hermes/.env` and fail loudly (remove `2>/dev/null` or log the miss).

### F-08 [MEDIUM][Data integrity / Clinical] GAPS dict disagrees with nominal schedule by 1h
- **File:** `chain_calc.py:38` `A_to_B: 1.0`; `med-schedule.json` Slot B nominal `08:00`.
- **Evidence:** A=06:00, `A_to_B=1.0h` → engine computes B ready ≈ 07:00–07:15, but the slot's own `time` is `08:00` and window `07:30–08:30`. Cascades: C engine≈11:00 vs nominal 12:00; D≈15:00 vs 16:00; E≈19:00 vs 20:00.
- **Impact:** On a normal on-time day, every downstream reminder fires ~1h early vs the displayed schedule. Either the GAPS or the nominal times are wrong; users get inconsistent signals.
- **Recommendation:** Reconcile: set `A_to_B` to the intended gap (2h if B should be 08:00) OR change nominal times to match the 1h model. Pick one source of truth.

### F-09 [MEDIUM][Reliability / Memory] MEMORY.md at ~98% of 9000-char limit
- **File:** `memories/MEMORY.md` (9105 bytes vs 9000 limit); `config.yaml` `memory_char_limit: 9000`.
- **Evidence:** `wc -c memories/MEMORY.md → 9105`. Baseline flagged memory_watch.py at 95% CRITICAL.
- **Impact:** For an ADHD-compensation system, a full memory is a ticking failure — new lessons get dropped/compressed, exactly when the user needs the safety net most.
- **Recommendation:** Run curator/prune (config has `curator.enabled: true`, 168h interval); split stable facts to USER.md/SOUL.md; raise limit if storage allows; verify the 98% isn't already silently truncating writes.

### F-10 [MEDIUM][Security / Privacy] Med drug names visible in `hermes cron list` and job names
- **File:** `cron/jobs.json` job names + `scripts/chain_*.py` output; `config.yaml:382 redact_pii: true` (logs only).
- **Evidence:** `hermes cron list` shows "Domino Chain Medication Monitor", "Dexa Taper Alert", "Weekly Med Compliance Report" — drug names exposed in job metadata. `redact_pii` covers message logs, not cron/job definitions.
- **Impact:** PDPA/health-data exposure if cron list or jobs.json is shared/synced to GitHub (the sync plan pushes config but VPS runtime state should NOT go to GitHub — see Doc 3).
- **Recommendation:** Keep med JSON + jobs.json OUT of GitHub (already the plan); consider generic job names.

---

## LOW

### F-11 [LOW][Code quality] Orphan/dead scripts after provider & cron changes
- **File:** `scripts/hello_watch.py`, `scripts/hello-world.sh` (cron `hello-world-watch` removed — confirmed absent from `hermes cron list`); `scripts/minimax_proxy.py` (provider block deleted 9/7); `fix_models.py:36,61` still lists `minimax-m3`.
- **Evidence:** `hermes cron list` grep "hello" → NONE; `minimax_proxy.py` header "Minimax OpenAI-compatible API proxy"; `grep minimax config.yaml` → only commented fallback docs.
- **Impact:** Dead code/confusion; minimax_proxy implies a working integration that isn't configured.
- **Recommendation:** Delete or clearly mark deprecated; remove minimax from fix_models curated list if provider truly gone.

### F-12 [LOW][Docs / Meta] Audit handoff evidence was itself stale/inaccurate
- **File:** `audit-prep/08-EVIDENCE-APPENDIX.md A6` (med-schedule.json snippet) vs live `med-schedule.json`.
- **Evidence:** A6 shows `A: {"drugs":["Akurit-4 (akurit_4)"]}` and `C: {"drugs":["Dexamethasone (dexamethasone_3)"]}` (no Pyridoxine, no Calcium/Calcitriol). Live file (read 2026-07-09) shows Slot A = Akurit-4 **+ Pyridoxine**, Slot C = Dexa **+ Calcium + Calcitriol + B-Complex**. The prompt's "Data-Integrity Drift Rule" repeated A6's claim that these drugs are missing — they are NOT missing in the live file.
- **Impact:** Demonstrates the exact "don't trust prior AI / stale snapshot" risk. An auditor who trusted A6 would file a false CRITICAL. This audit corrects it: only the *name* "Akurit-4" is stale (F-02); the concomitant drugs are correctly present.
- **Recommendation:** Treat all prep-doc JSON snippets as point-in-time; always diff against live before citing.

### F-13 [LOW][Config] `fallback_providers` uses `opencode-zen` directly while default `provider: opencode`
- **File:** `config.yaml:3` `provider: opencode`; `config.yaml:6-9` fallback entries `provider: opencode-zen`.
- **Evidence:** `models.py:1174` maps `opencode`→`opencode-zen` alias, so both resolve; consistent. Minor note only — no action needed, but worth a comment that `opencode` is an alias.
- **Impact:** None currently. Documented for clarity.

---

## STRUCK / NOT REPRODUCED (do NOT carry forward)
- **Gemini CVE-2026-48063** (claimed Baileys RCE, CVSS 9.3): FABRICATED — renumbered old GHSA-qvv5. No evidence in live code. STRUCK.
- **Gemini "BD taper 4mg deficit"** (claimed code returns 0 instead of 5/5/4): FABRICATED. Live `dexa_taper.json` BD phase = 15mg with 5/5/4 split; `med-schedule.json` C=5mg, D=4mg. STRUCK.
- **"14/28 cron jobs"**: FALSE — live = 6 active (`hermes cron list`). The 14/28 figures are from the 7/7 baseline, since reduced.
- **"hello-world-watch (1m) still firing"**: FALSE — confirmed GONE from `hermes cron list`.

---

## UNVERIFIED / THEORETICAL items
- **F-06** `providers: '{}'` string parsing — THEORETICAL; system runs, so likely coerced, but unconfirmed at runtime.
- **Baileys library CVE status** (GHSA-qvv5) — NOT re-checked against installed Baileys version; prior audits flagged it P0 but provided no version proof. UNVERIFIED.
- **Whether a bare `kill -TERM` actually leaves a blocking stale state today** — inferred from run.py:6716 + gateway.py:918 + broken watchdog; not reproduced live (would require killing the gateway). THEORETICAL but high-confidence given code + wrong-path watchdog.
- **Session `started_at` corruption (returns 1970)** — noted in 08-APPENDIX A7; not independently verified. UNVERIFIED.

---

## OVERHAUL ADDENDUM — Deep Findings F-14…F-24 (2026-07-09, read-only VPS)

> New findings from the full overhaul deep-dive (orchestration, integration,
> automation, state, memory, security, observability, cost). Same labelling
> rules: CONFIRMED | THEORETICAL | UNVERIFIED. All cite live file:line.

### F-14 [HIGH][Config/Cost] `reasoning_effort: high` is always-on for every agent turn
- **File:** `config.yaml:36`; `hermes-agent/gateway/run.py:3712-3721`.
- **Evidence:** `config.yaml:36  reasoning_effort: high`. `run.py:3718` reads `agent.reasoning_effort` and applies it to the session; warning only on *unknown* values (`:3721`), so `high` is accepted silently.
- **Impact:** Every conversational turn requests maximum reasoning tokens on hy3-free. For a personal assistant doing reminders, scheduling, and chit-chat, this is a large, permanent, unnecessary token tax.
- **Root cause:** default config chose `high` for "best quality" without cost consideration.
- **Recommendation:** default `medium` (or `low` for routine turns); reserve `high`/`xhigh` for explicit reasoning-heavy tasks via per-request override. Quick, high-leverage cost win.

### F-15 [HIGH][Reliability/Cost] `max_concurrent_sessions: null` = unbounded concurrency
- **File:** `config.yaml:16`; `hermes-agent/gateway/run.py:3938-3949`, `:8337`.
- **Evidence:** `config.yaml:16  max_concurrent_sessions: null`. `run.py:3938` `_get_max_concurrent_sessions()`; `:8337` rejects new sessions only *when a limit is set* — with `null`, no cap.
- **Impact:** Under load (or a stuck session loop), unbounded sessions multiply LLM calls → cost spikes and gateway overload / OOM risk on a small Tencent Lighthouse VPS.
- **Root cause:** unset concurrency limit.
- **Recommendation:** set an explicit cap (e.g. 4–8) sized to VPS RAM. Pair with F-14 for combined cost/reliability control.

### F-16 [MEDIUM][Architecture/Data-integrity] Medication state uses fragile JSON while kanban uses ACID SQLite
- **File:** `med-status.json`/`chain-state.json`/`med-schedule.json` (flat JSON, no transactions); `kanban.db` (SQLite, 8 tables, ACID).
- **Evidence:** `kanban.db` schema (`tasks` 30 cols, `task_runs`, `task_events`…) is transactional; med JSON files have no schema/transactions. F-04 (`chain-state.json` clobber, `chain_monitor.sh:85`) is a direct symptom of the no-transaction design.
- **Impact:** the **most safety-critical** data (meds) is the *least* protected. Concurrent cron + manual `med_confirm.py` writes can race/corrupt med state with no rollback.
- **Root cause:** med subsystem predates the SQLite-based kanban subsystem; no unified storage layer.
- **Recommendation:** migrate med state to a transactional store (SQLite or the existing kanban.db pattern) with atomic writes + backups; or at minimum add write-locking/atomic-rename to JSON writes.

### F-17 [MEDIUM][Privacy/PDPA] PII in `channel_directory.json` + `jobs.json`; `redact_pii` covers logs only
- **File:** `channel_directory.json` (1.6 KB); `cron/jobs.json`; `config.yaml:382`.
- **Evidence:** `channel_directory.json` lists Telegram `679729206` and WhatsApp `13186321408227@lid` + **2 group ids** with names. `config.yaml:382 redact_pii: true` — but audit-01 §12 shows it scrubs *gateway output/logs* only, not job defs or state files. Drug names remain in `jobs.json`/`hermes cron list` (F-10).
- **Impact:** phone numbers + health context are plaintext PII in runtime state. If ever synced to GitHub or backed up off-box, this is a PDPA breach.
- **Root cause:** PII scattered across state files; `redact_pii` scope too narrow.
- **Recommendation:** keep `channel_directory.json` + med JSON + `jobs.json` strictly off GitHub (audit-03 already requires this); use generic job names; consider encrypting `channel_directory.json` at rest.

### F-18 [LOW][Config/Security] `MINIMAX_API_KEY` still present in `.env` after minimax provider deletion
- **File:** `~/.hermes/.env` (var name only, value never printed).
- **Evidence:** `.env` grep shows `MINIMAX_API_KEY=` present, yet `config.yaml` minimax provider block was deleted 9/7 and `scripts/minimax_proxy.py` is orphaned (F-11).
- **Impact:** dead secret = unnecessary attack surface; suggests other stale secrets may linger.
- **Root cause:** provider removed but `.env` not cleaned.
- **Recommendation:** remove `MINIMAX_API_KEY` (and audit other `.env` vars for staleness) after confirming no script references it.

### F-19 [MEDIUM][Cost] Auxiliary roles resolve to the MAIN model (hy3-free) → background LLM spend
- **File:** `hermes-agent/agent/auxiliary_client.py:1704` (`_read_main_model`), `:1734` (`_read_main_provider`); `config.yaml:195-308` (auxiliary block).
- **Evidence:** `auxiliary_client.py:177 main_prov = (_read_main_provider() or "").strip().lower()`; `:1920 model = _read_main_model() or "gpt-4o-mini"`. So `provider: auto`/`model: ''` aux roles (curator timeout 600, kanban_decomposer timeout 180, compression, skills_hub, approval, mcp, title_generation, tts, triage_specifier, profile_describer, monitor, background_review, extraction) run on **hy3-free**.
- **Impact:** recurring background LLM calls on a capable model — memory curation (F-09 relief), kanban decomposition, compression all bill tokens. `reasoning_effort` propagation to aux is **UNVERIFIED** (not referenced in `auxiliary_client.py`), but model/provider cost is confirmed.
- **Root cause:** aux roles default to main model when unset.
- **Recommendation:** assign cheaper/faster models (or `reasoning_effort: none`) to aux roles; verify reasoning propagation; quantify monthly aux spend.

### F-20 [LOW][Maintainability] 9 paused cron jobs clutter; prior audit overstated "removed"
- **File:** `cron/jobs.json`.
- **Evidence:** 15 jobs total, 9 `paused` (Evening Check-in, Daily Usage Report, Goal Check-in, Weekly Review, Daily Health, DeepSeek Balance Check, Memory Watchdog, Routine Analysis, hello-world-watch). audit-01 §5 claimed erroring LLM jobs "have been removed."
- **Impact:** dead config noise; a future auditor (or the user) may assume 6 jobs when 15 exist; `hello-world-watch` still present contradicts the "GONE" claim in F-11.
- **Root cause:** jobs paused, not deleted.
- **Recommendation:** delete obsolete paused jobs (esp. `hello-world-watch`, and `Routine Analysis` if abandoned); correct audit-01 §5 wording.

### F-21 [LOW][State] Unaccounted caches & snapshots
- **File:** `.skills_prompt_snapshot.json` (68 KB), `provider_models_cache.json` (740 B), `ollama_cloud_models_cache.json` (735 B), `models_dev_cache.json` (2.98 MB).
- **Evidence:** `ls -la ~/.hermes/*.json` (Phase A). Hidden `.skills_prompt_snapshot.json` not in prior inventory.
- **Impact:** unmonitored disk growth; if synced, leaks model/provider metadata.
- **Root cause:** caches never enumerated in prior audit.
- **Recommendation:** document each cache's purpose + rotation; ensure all excluded from any GitHub sync.

### F-22 [CRITICAL][Automation/Data-integrity] `med-auto-confirm` hook silently auto-writes med state pre-agent
- **File:** `hooks/med-auto-confirm/HOOK.yaml` + `handler.py`; interacts with `scripts/med_confirm.py`.
- **Evidence:** `HOOK.yaml`: "Auto-log medication confirmations from inbound messages BEFORE the agent processes them, so med-status.json is always correct and the reminder cron stops. Fail-open."
- **Impact:** undocumented automation that writes `med-status.json` outside the documented `med_confirm.py` path. Possible double-write / race / conflict if both the hook and `med_confirm.py` act on the same message; fail-open means errors are silent.
- **Root cause:** hook added without auditing against the existing med pipeline.
- **Recommendation:** document the hook's exact write path; make it idempotent and consistent with `med_confirm.py`; verify no conflicting writes during Phase C med work.

> **POST-AUDIT ADDENDUM (2026-07-10, Pattern G):** Runtime failure on 2026-07-10 — the hook's loose `SLOT_RE = \b(slot\s*)?([A-Ea-e])\b` (handler.py:53) false-positively matched a chat message where the user *discussed* yesterday's "20:00" timing. `TIME_RE` extracted "20:00" from conversation context (not intake), so the hook ran `med_confirm.py A --at 20:00`, creating a corrupt `med-status` entry `A/2026-07-10 @ 20:00` (future time). **Verified live:** `med-status.json` contains `A → 2026-07-10 → time "20:00"`; `chain-state.json` `"today"` is frozen on `2026-07-09` (day-roll never ran). Effect: `is_confirmed('A')`→True suppressed the A reminder; B ready_time = 21:00 suppressed B; silent exit → no morning TB-Meningitis reminders. **Severity raised MEDIUM→CRITICAL (patient-safety adjacent).** Fix per PATTERN-G analysis doc: tighten `SLOT_RE` (require med context), validate timestamp (reject future), add context guard, fix `_already_logged`, move day-roll outside the `should_fire` gate, add audit log, regression tests.
>
> *Added per Pattern G aligned-auditor instruction (2026-07-10); F-22 original body unchanged.*

### F-23 [LOW][Integration/Maintainability] Three redundant gateway-restart scripts
- **File:** `scripts/gw_restart.sh`, `scripts/restart_gateway.sh`, `scripts/hermes_gateway_restart.sh`.
- **Evidence:** all three present in `scripts/` (Phase A listing).
- **Impact:** a watchdog/fix applied to one can be missed in the others → divergence; increases chance the wrong (still-broken `/home/amirul`) variant is used (see F-03).
- **Root cause:** accumulated scripts across migrations.
- **Recommendation:** consolidate to one canonical restart script; delete the other two.

### F-24 [CRITICAL][Med/Design] Adopt `MED_CHAIN_ENGINE_SPEC_v3.md` deterministic engine as the F-01 fix (evaluate + refine in Phase C)
- **File:** `~/.hermes/MED_CHAIN_ENGINE_SPEC_v3.md`; relates to audit-02 F-01 + F-08.
- **Evidence:** spec (last updated 2026-07-08, author MJ native agent, "PENDING EXTERNAL AUDIT") proposes a deterministic rule engine: `Intent Classifier (route.py) → Constraint Solver (solve.py) → Conflict Resolver (resolve_conflict.py)`, explicitly to fix the LLM auto-linearization bug (E wrongly chained to B→C→D). This is a **pre-drafted redesign** for the #1 clinical-timing defect — the prior audit (F-01) recommended a redesign without discovering this spec exists.
- **Impact:** adopting the v3 deterministic engine is the correct, lowest-risk path to fix F-01 (no blind-shift). It also resolves the LLM-confusion root cause identified in the spec.
- **Root cause:** the fix was drafted but never evaluated/integrated; the audit independently re-derived the need.
- **Recommendation:** in **Phase C**, read the full spec, verify its model matches the clinically-correct timing (A gates only B's earliest via 1h empty-stomach wait; Dexa fixed 08/12/16; Levetiracetam 12h pair), reconcile its GAPS with F-08, refine any gaps, and produce a final F-01 remediation spec. This is the user-approved disposition for F-01.

---

## OVERHAUL ADDENDUM — Resolved / still-UNVERIFIED (2026-07-09)
- **kanban.db schema:** VERIFIED — SQLite, 8 tables, all 0 rows, ACID. Contrast with med JSON (F-16).
- **pairing/ WhatsApp session store:** VERIFIED empty (no Baileys session there); actual store location UNVERIFIED, but no exposure observed.
- **Auxiliary model resolution:** CONFIRMED aux roles use main model/provider (`auxiliary_client.py:1704/1734`). `reasoning_effort` propagation to aux = UNVERIFIED (not referenced in that file).
- **Obsidian integration:** `OBSIDIAN_VAULT_PATH` in `.env` implies a notes integration — purpose UNVERIFIED.
