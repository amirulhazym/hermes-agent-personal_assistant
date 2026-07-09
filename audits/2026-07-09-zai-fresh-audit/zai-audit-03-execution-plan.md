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

**End of zai-audit-03.** Findings above are evidence-first; UNVERIFIED items are flagged, not asserted. Ready for your phase-by-phase go-ahead.
