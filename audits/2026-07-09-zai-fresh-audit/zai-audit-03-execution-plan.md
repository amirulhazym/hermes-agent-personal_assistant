# zai-audit-03 — Execution Plan (Hermes Agent / MJ)

> **Auditor:** Z.ai (GLM-5.2) · **Date:** 2026-07-09
> **Principle:** brutal honesty, evidence-first, fix root cause not symptom, simplify where possible.
> **Hard constraint reminder:** nothing here is executed without your explicit "yes" per item. Med-changing scripts ONLY with `--dry-run` first. No git/commit/push without separate approval.

---

## 0. Guiding thesis

Most CRITICALs share ONE root cause: **there is no single durable, secret-safe, version-controlled source of truth.** The live system lives in `~/.hermes/` (uncommitted runtime edits), a stale Windows copy (with `.env`!), and a stale public GitHub repo. Until that is fixed, every other fix is fragile and unreproducible — and your side-income goal (replicate/sell the med-intelligence or fetcher IP) is unreachable.

**So Phase 1 (below) is the keystone.** Do it first; everything else becomes reproducible after.

---

## 1. Prioritized fix list

Ranked by **impact × fix-complexity × safety**. `Indep` = can be done alone; `Seq` = depends on a prior item.

| # | Severity | Dim | Fix | Complexity | Dep |
|---|----------|-----|-----|-----------|-----|
| P1 | CRITICAL | D2/D16/C1 | Establish durable source: commit 9/7 runtime edits + define git as source of truth; automate VPS→git; exclude secrets | Med | Indep |
| P2 | CRITICAL | D14 | `chmod 700 ~/.hermes/whatsapp/session` (+ parent chain) | Low | Indep |
| P3 | CRITICAL | D12/clin | Reflect Akurit-2 swap in all med JSON + scripts (`akurit_4`→`akurit_2`) | Med | Indep |
| P4 | CRITICAL | D12 | Atomic `chain-state.json` write (`os.replace` + `.bak` + loud fallback) | Low | Indep |
| P5 | HIGH | D1 | Fix `gateway_state.json` stale-state bug in launch sequence | Low | Indep |
| P6 | HIGH | D4/clin | Implement med constraint engine Spec v3 (deterministic, not LLM-linearized) | High | Seq(P3) |
| P7 | CRITICAL | D14 | Purge `.env` from Windows snapshot; verify GitHub has no PII/med JSON | Low | Indep |
| P8 | HIGH | D14 | Verify + lock GitHub repo (pre-push PII/secret scan) | Low | Seq(P1) |
| P9 | HIGH | D12 | Fix `med_confirm.py` clobber + re-decrement (transition-guarded) | Med | Seq(P3) |
| P10 | HIGH | D13 | Fix `med_resolve.py` float hack + 14:00 boundary | Low | Indep |
| P11 | HIGH | D6 | Root-cause + fix `Daily Health` Broken Pipe (then re-enable) | Med | Indep |
| P12 | MED | D15 | External dead-man alert (gateway down → Telegram) | Med | Seq(P5) |
| P13 | MED | D1/TZ | Use `ZoneInfo('Asia/Kuala_Lumpur')` in `chain_monitor.sh:88`; verify host TZ | Low | Indep |
| P14 | MED | D4/D5 | Wire or delete orphan drivers (qwen/sakana/minimax); decide MCP | Low | Indep |
| P15 | MED | D7 | Wire 2-3 ADVANCED-IDEAS automations (memory-contradiction detective, weekly retrospective) | Med | Indep |
| P16 | MED | D8 | Curate skills → personal-assistant core; archive rest | Low | Indep |
| P17 | MED | D9 | Add pre-write guard on med state mutations (covers Pattern D) | Med | Seq(P9) |
| P18 | MED | D10 | Enable safe memory-consistency scan | Low | Indep |
| P19 | MED | D13 | Replace `except Exception: pass` with specific + logged | Med | Indep |
| P20 | MED | integ | Fold `fetcher/` into durable-source + sync; document as separable product | Med | Seq(P1) |
| P21 | LOW | D6 | Point `V2 Overnight Build` cron to `build_overnight.py` or rename | Low | Indep |
| P22 | LOW | D3 | Hide non-functional `minimax` from model picker | Low | Indep |
| P23 | LOW | D13 | Scope `--update` to specific drug_id | Low | Seq(P9) |

---

## 2. Human-input gates (require YOUR decision/approval)

- **G1 (P1):** where does durable truth live? Recommend: `~/mjay` git `hermes-live` tracks `~/.hermes/hermes-agent/` + `audit-prep/` + `fetcher/` code; runtime state (`med-*`, `chain-state`, `gateway_*`) stays VPS-only and is EXCLUDED from git (PII). Confirm before I draft the sync mechanism.
- **G2 (P3):** confirm the exact Akurit-2 drug_id naming + that NO other drug changed 9/7 (charter says Akurit-4→Akurit-2 only; Pyridoxine/B6, Dexa, Letra, Calcium, Calcitriol unchanged). I will not rename beyond what you confirm.
- **G3 (P6):** approve implementing Spec v3 as-is, or simplify first? Spec is rated 9.95/10 but is 7 layers; a minimal v1 (rules.json + solve + trace + validate) may be enough to kill the E-follows-C bug. Your call.
- **G4 (P7/P8):** if Windows PC may be compromised, **rotate DEEPSEEK/OPENCODE_ZEN/GO/TELEGRAM keys** (I can never see values; you do the rotate). Confirm need.
- **G5 (P20):** is `fetcher/` a product you want to productize (anti-bot data acquisition service) or keep internal? Affects how much to invest.
- **G6 (git):** every commit/push is a separate "yes" — I will ask per item, never batch.

---

## 3. Per-fix detail (key items)

**P1 — Durable source (keystone).**
- Files: `~/.hermes/hermes-agent/{hermes_cli/models.py, gateway/run.py}`, `~/mjay/audit-prep/`, `~/mjay/fetcher/`.
- Change: add a VPS→git commit step (cron or post-edit hook); `.gitignore` `.env`, `auth.json`, `whatsapp/session`, `*.db`, `logs/`, `cache/`, `med-*`, `chain-state.json`, `gateway_state.json`. Verify drift via Jane (native agent) daily.
- Verify: `git -C ~/mjay status` clean after a known edit; `git clone` on a fresh box reproduces runtime.
- Simplify: do NOT try to sync Windows↔VPS bidirectionally yet; one-way VPS→git is enough to stop data loss.

**P2 — session perms.**
- `chmod 700 ~/.hermes/whatsapp/session && chmod 711 ~/.hermes/whatsapp` (read-only SSH can't do this; needs your approval + a 1-line command). Verify `stat`.
- Risk: none (tightening). Re-pair WhatsApp only if session breaks (unlikely from chmod).

**P3 — Akurit-2 drift.**
- Files: `med-schedule.json`, `med-status.json`, `chain-state.json`, `med-supply.json`, all `med_*.py` referencing `akurit_4`.
- Change: rename `akurit_4`→`akurit_2`, `Akurit-4`→`Akurit-2`. Do NOT touch other drugs (G2).
- Verify: `grep -rn akurit_4` returns nothing in med files; spot-check one historical `med-status.json` entry still parses.

**P4 — atomic chain-state.**
- Files: `chain_monitor.sh` + `chain_calc.save_json`.
- Change: write to `chain-state.json.tmp` then `os.replace()`; keep `chain-state.json.bak`; on JSON error, LOG loudly + load `.bak` instead of `{}`.
- Verify: simulate corruption, confirm fallback uses `.bak` and alerts.

**P6 — med engine (highest clinical value).**
- Files: new `scripts/med_chain/{rules.json,solve.py,resolve_conflict.py,trace.py,validate_semantic.py,route.py,why.py}` + patch `chain_calc.py` to call solver.
- Change: per Spec v3, but consider minimal v1 (G3). Must encode: (a) ~1h empty-stomach gate after A, (b) Dexa 4h-gap independence, (c) E = B+12h invariant, (d) regression test Bug #17 ("E ikut C" → fail).
- Verify: `test_solver` C=1pm → D=5pm, E untouched; `test_conflicts` user vs rule priority; `test_regression` permanent fail on E-follows-C.

**P9 — confirm clobber.**
- Files: `med_confirm.py:264-269`.
- Change: only set `now` for drugs not `taken`; `decrement` only on pending→taken transition; skip `doses_per_day==0`.
- Verify: confirm B twice → second run does NOT re-decrement; partial times preserved.

---

## 4. Simplify vs keep

**Keep:** the deterministic-engine approach (Spec v3), the no_agent cron discipline, the fallback chain (free-only rule), SOUL.md epistemic standard.
**Simplify:** drop bidirectional Windows↔VPS sync (one-way VPS→git for now); delete orphan drivers (qwen/sakana/minimax_proxy); curate 60→~15 skills; collapse aspirational ADVANCED-IDEAS to 2-3 shipped.
**Remove:** `.env` from Windows snapshot; world-readable session perms; `except pass` swallowers.

---

## 5. End-goals section (side-income, ADHD compensation, med-intelligence)

Your stated goal: *"unexpected, maintainable side income"* + *ADHD compensation* + *go beyond a basic assistant.* The audit shows the raw material exists but is trapped by the no-durable-source problem. Concrete path:

1. **Med-intelligence as a product (highest leverage).** Finish Spec v3 → you have a *clinically-correct, adaptive* med-adherence engine (the "2026 not 2010" system you described). That is sellable: ADHD/med-adherence assistant for chronic-disease patients, or a white-label rule-engine. Blocked only by P6 + P1.
2. **Fetcher as a product (already real IP).** `fetcher/` is a capability-routed anti-bot scraper with cost optimizer — genuinely useful for price/competitor intelligence. Productize as a data-acquisition service (G5). Blocked by P20 + P1.
3. **MJ agent-loop as a consulting demo.** Once reproducible (P1), the whole assistant is a portable demo for your solo AI-consulting business — show, don't tell.
4. **ADHD compensation is already designed** (escalating reminders, flexible timing, Manglish SOUL). It fails only when the reminder PATH fails silently (C3: disabled heartbeat + stale-state bug). Fix P5+P12 and ADHD-compensation actually works.

**The throughline:** P1 (durable source) is what unlocks ALL three income paths. It is the first thing to do.

---

## 6. Proposed execution order (phases)

- **Phase 1 — Stop the bleeding (safety/security):** P2, P4, P5, P7, P13. (Low complexity, high safety.) All Indep.
- **Phase 2 — Durable source (unlocks everything):** P1, then P8, P20. (G1, G4.)
- **Phase 3 — Med correctness (clinical):** P3, P9, P10, P6. (G2, G3.) P6 highest effort.
- **Phase 4 — Reliability/observability:** P11, P12, P17, P18.
- **Phase 5 — Tidy/productize:** P14, P15, P16, P19, P21, P22, P23.

Each phase ends with a verification step and your sign-off before the next.

---

## 7. What I will NOT do without explicit "yes"

- Modify any file on VPS (all above are proposed; I'll show the exact diff/command first).
- Run `med_confirm.py` without `--dry-run`.
- `git add/commit/push/rebase/force`, key rotation, `chmod` on live paths, restart gateway.
- Anything in G1–G6 until you decide.

---

## 8 — TARGET-STATE ARCHITECTURE: Overhaul Blueprint (FROM L2 DEEP DIVE)

> **Preface:** The L2 expansion (hooks, plugins, config-deep, kanban, delegation, curator, fetcher, gateway-internal, memory) revealed that the SYSTEM ALREADY HAS MUCH OF THE FOUNDATION the user's "multi-agent expert system" vision needs. Kanban, subagent delegation, curator, fetcher, med-auto-confirm hook, Spec v3 design — these are REAL capabilities, not aspirational. The gap is: (1) they're SILOED, (2) several have DATA-DRIFT bugs, (3) they're not WIRED toward a coherent target state, (4) they're UNDOCUMENTED so nobody uses them. The overhaul should CONNECT AND CLEAN, not rebuild from scratch.

### 8.1 — Target State Architecture Diagram

```
                         ┌─── USER (WhatsApp/Telegram) ─────────────────────┐
                         │                                                   │
                         ▼                                                   │
              ┌──────────────────────┐                                       │
              │  GATEWAY (systemd)    │  cron_mode: deny                     │
              │  agent loop/enrich    │  approvals: manual                    │
              │  redundancy: stub     │                                       │
              ├──────────────────────┤                                       │
              │  CANARY: dead-man     │◄─── New: simple external ping        │
              │  alert (Tel/WA)      │      (no meds → alert)               │
              ├──────────────────────┤                                       │
              │  med-auto-confirm     │─── auto-run med_confirm.py (fix drift)│
              │  skill-trigger       │─── inject med-tracker on keywords     │
              └──────────┬───────────┘                                       │
                         │                                                   │
          ┌──────────────┼──────────────────┬─────────────────────┐          │
          ▼              ▼                  ▼                     ▼          │
   ┌──────────┐  ┌──────────┐  ┌──────────────────┐  ┌───────────────────┐  │
   │ CRON     │  │ KANBAN   │  │ SUBAGENT         │  │ CURATOR           │  │
   │ 6 active │  │ dispatch │  │ delegation        │  │ self-clean        │  │
   │ no-agent │  │ auto-dec │  │ max_children:3    │  │ weekly, 30d stale │  │
   │ scripts  │  │ (fix cap)│  │ depth:1           │  │ auto-backup       │  │
   └──────────┘  └──────────┘  └──────────────────┘  └───────────────────┘  │
                         │                                                   │
          ┌──────────────┴──────────────────┐                                │
          ▼                                 ▼                                │
   ┌──────────┐                     ┌──────────────┐                        │
   │ MED-SYS  │                     │ FETCHER      │                        │
   │ Spec v3  │                     │ adaptive     │                        │
   │ solver   │                     │ scraper      │                        │
   │ (BUILD)  │                     │ (PRODUCT)    │                        │
   │ clean    │                     │ cost-opt     │                        │
   └──────────┘                     └──────────────┘                        │
                         │                                                   │
                         └───────────────────────────────────────────────────┘
```

### 8.2 — Keep: What's already working and should stay

| Layer | Why Keep | Condition |
|-------|----------|-----------|
| Cron no_agent discipline | Cost control. 6 jobs, script-only, no LLM burn. | Keep all 6 active; decide on 9 disabled ones. |
| med-auto-confirm hook | Pattern D countermeasure — auto-state BEFORE agent. | Fix DRUG_MAP drift + dexa redundancy. |
| chain_calc.py deterministic engine | Right approach (Python, no LLM for math). | Enhance with floor/independence guards OR implement Spec v3. |
| Spec v3 constraint engine design | 9.95/10 rated. Clean architecture. | Execute: rules.json → solve → trace → why. |
| fallback_providers chain | Free-only. Correctly wired. Properly logged [FALLBACK]. | Keep. |
| Kanban dispatch + auto-decompose | Task orchestration activated. | Only fix: set max_in_progress limit. Wire to overhaul. |
| Subagent delegation | Multi-agent foundation exists. | Document patterns; wire to kanban for overhaul. |
| Memory curator | Self-cleaning, weekly, auto-backup. ACTIVE. | Wire contradiction-detection report. |
| hybrid-web plugin | Working custom extraction. | Document as asset; address its paid-model dep. |
| privacy.redact_pii | True. | Keep. |
| approvals.mode: manual | Human-gate for dangerous ops. | Keep. |

### 8.3 — Fix: Known bugs that must be resolved

From Doc 2 findings (P1–P23), but here grouped by overhaul phase order:

**Phase 1 — Safety-critical (immediate)**  
- P2: `chmod 700 whatsapp/session/` — 775→700  
- P3: Akurit-4→Akurit-2 across ALL med JSON + scripts + hooks (incl. med-auto-confirm DRUG_MAP)  
- P4: chain-state.json atomic write (tmpfile+os.replace)  
- P5: gateway_state stale-state bug  
- P7: Purge `.env` from Windows snapshot; GitHub PII check  
- Corr: Fix med-auto-confirm dexa boundary  

**Phase 2 — Clinical correctness**  
- P9: med_confirm.py clobber + re-decrement guard  
- P10: med_resolve float hack + 14:00 boundary  
- P6: Implement Spec v3 (constraint solver ≥ linear chain) — with floor/independence rules  
- P13: Add `now_myt()` to chain_monitor.sh for portability (LOW now, still good practice)

**Phase 3 — Orchestration + reliability**  
- P11: Fix Daily Health Broken Pipe or decide to keep disabled  
- P12: External dead-man alert (whatsapp/telegram when gateway dies)  
- P14: Qwen/Sakana/minimax orphan drivers — quarantine or delete  
- P17: Add pre-write state guard (Pattern D residual — agent can override after hook)  
- P9: Session reset awareness for med context (suppress reset 5am-10pm)

### 8.4 — Simplify: What to remove or consolidate

| Item | Action | Rationale |
|------|--------|-----------|
| hello-world hook + cron pipeline | DELETE both hook + script | Dead pipeline — hook writes, cron doesn't read |
| lightclawbot plugin | QUARANTINE (or delete) | Third-party, inactive, unverified code quality |
| qwen_driver.py, sakana_driver.py, minimax_proxy.py | DELETE | Orphaned, dead endpoints, misleading capability |
| 9 disabled LLM cron jobs | DECIDE: delete or fix | Currently `active=False` — neither removed nor repaired. Either fix or clean up. |
| 60→~15 skills | CURATE | Keep: med-tracker, anti-fabrication, malaysia-selector, auto-skill-suggester, hermes-no-agent-cron, agent-methodology, agent-best-practices, life-management, research, github, devops, data-science, note-taking, productivity. Archive/delete the rest (gsap-*, design-*, brand-guidelines, apple, etc.) |
| Async: ADVANCED-IDEAS list | CONDENSE to top 3 shipped | Currently 11 aspirational ideas. Pick: memory-contradiction detective, weekly retrospective, chained cron pipeline. Wire don't just document. |
| `mcp_servers: {}` + `computer_use.enabled: true` | CONSISTENCY — disable flag if MCP empty | Currently contradictory (flag on, runtime absent) |

### 8.5 — Add: What to build for overhaul target state

| Addition | Priority | Why | Depends on |
|----------|----------|-----|------------|
| Spec v3 constraint engine | P0-clinical | Kills the E-follows-C bug + adds floor/independence. 9.95/10 design ready. | P3 (Akurit-2 fix) |
| Durable source sync (one-way VPS→git) | P0-system | Unlocks reproducibility & all 3 income paths. | G1 decision |
| Kanban wired to overhaul tasks | P1-orchestration | Track overhaul progress; existing system unused | Kanban cap fix |
| Multi-agent delegation patterns documented | P2-vision | User's explicit "multi-agent expert system" goal | None (documentation) |
| Session med-context survival across reset | P2-reliability | Prevents med context loss mid-day | Session_reset config |
| Weekly curator contradiction report | P2-memory | Turns existing curator into active "memory detective" | None (add report generation) |
| Fetcher as documented product asset | P3-product | Second sellable asset (after med engine) | P1 (sync) + G5 decision |
| Med-intelligence framework (sellable) | P3-product | Complete Spec v3 → white-label ADHD/med-adherence engine | Spec v3 built |
| GitHub pre-push PII/secret scan | P1-security | Prevents accidental secret exposure | P1 (sync) |

### 8.6 — Phased execution order (revised from v1)

```
Phase 0: Safety/security (immediate actions, all independent)
   P2, P4, P5, P7, P13 + Corr fix (dexa boundary) + session perms

Phase 1: Durable source (unlocks reproducibility)
   P1 (commit 9/7 fixes, establish one-way VPS→git)
   P8 (GitHub PII check + pre-push scan)
   → Git commit audit docs
   → Decide G1, G4

Phase 2: Med correctness (clinical safety, highest value)
   P3 (Akurit-2 everywhere)
   P9 (confirm clobber fix)
   P10 (med_resolve fixes)
   P6 (Spec v3 — implement constraint solver)
   → Decide G2, G3

Phase 3: Orchestration wiring (build target state)
   P11 (Daily Health fix/decide)
   P12 (dead-man alert)
   P14 (orphan drivers)
   P17 (state-write guard)
   Wire kanban → overhaul tasks
   Wire curator → contradiction report
   Session med-context survival
   → Decide G5 (fetcher product)

Phase 4: Tidy + productize
   P15 (wire 2-3 ADVANCED-IDEAS)
   P16 (curate skills 60→15)
   P19 (except pass → specific + log)
   P20 (fetcher sync discipline)
   P21 (V2 Overnight Build→build_overnight.py)
   P22 (hide minimax from picker)
   P23 (scope --update to drug_id)
   hello-world pipeline cleanup
   lightclawbot quarantine
   Skills curation
   Document multi-agent patterns
```

### 8.7 — User's multi-agent expert system vision vs current reality

| Vision (USER.md) | Current Reality | Gap |
|------------------|----------------|-----|
| Multi-agent system: agents that "act/execute like real humans" | Subagent delegation exists (`max_concurrent_children: 3`, `max_spawn_depth: 1`) but pattern UNDOCUMENTED — no one uses it | Document + wire use cases |
| "Not just chat answers" — agents do real work | Kanban auto-decomposes work items, cron runs scripts, hooks auto-confirm meds — FOUNDATION EXISTS | No integration between kanban, delegation, and user-facing workflows |
| "Helpful, meaningful, profitable" | 3 clear product seeds: med-intelligence engine, fetcher anti-bot scraper, MJ consulting demo | All blocked by no-durable-source (P1). All need Spec v3 complete. |
| "Current <5% of reality" | User's own assessment. I agree: the platform components are there but disconnected. The 5% is cron+med-tracker working. The 95% is kanban+delegation+fetcher+curator sitting idle. | Goal: 5% → 25% in this overhaul. Full 100% is post-overhaul iteration. |
| "Obsidian not integrated" | Confirmed — no Obsidian configuration in config.yaml despite `OBSIDIAN_VAULT_PATH` in .env | Wire Obsidian read/write after overhaul stabilizes |

**End of zai-audit-03.** Findings evidence-first; UNVERIFIED items flagged. The L2 deep dive expanded scope from ~4 layers to 16+ and produced 13 new findings (54 total). Ready for phase-by-phase execution — starting with your signal on G1–G6 and Phase 0.
