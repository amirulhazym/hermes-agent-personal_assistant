# Hermes Agent Overhaul — CONTINUATION BRIEF (fresh session handoff)

> **Attach BOTH this file AND `OVERHAUL-EXECUTION-PROMPT.md` to the new session.**
> `OVERHAUL-EXECUTION-PROMPT.md` = immutable mandate (skills, freeze rule, R1–R7).
> This file = live progress + P1 plan. Together a fresh agent has full context
> without re-deriving anything — which is what prevents the context-limit stall.
>
> Paste both into a NEW OpenCode session pointed at workspace
> `F:\AI Prep\OVIS\Hermes Agent\MJay`. Read both fully before acting.

---

## 0. ROLE & MANDATE

You are the user's strategic advisor + executor for a full overhaul of the
**Hermes Agent** — a personal AI assistant for user `amirulhazym` (Malaysian,
Manglish, EEE grad, self-taught AI). It runs on a VPS and bridges Telegram +
WhatsApp, with medication-reminder (TB treatment) logic as its most critical
feature.

The authoritative execution brief is **`OVERHAUL-EXECUTION-PROMPT.md`** in this
workspace. READ IT FULLY before any implementation work. Key points it sets:
- Mandatory skills: `using-superpowers`, `mattpocock`, `evidence-first`,
  `incremental-implementation`, `gsd` mindset. Load skills before acting.
- "Freeze is real" rule: do NOT break live med logic. Per-step user approval.
- R1: context-window monitoring — for hy3-free model, **60% (~150k tokens) is a
  HARD STOP**; request a fresh context before it dies silently. Use subagents or
  a new session per phase.
- R2 checkpoint discipline: after each task, STOP, report evidence, ask owner to
  confirm before next.
- MJ (native OpenCode agent) = VERIFIER ONLY, never executor. Only OpenCode (you)
  makes changes.

**Phase 0 (read-only synthesis) = DONE. P0 (critical quick fixes) = DONE.
Execution is now at P1 (med-chain engine build).**

## 1. HARD CONSTRAINTS (non-negotiable)

- **Skills mandatory** before any action (see §0).
- **Evidence-first labels**: VALIDATED / UNTESTED / REJECTED. Never claim success
  without raw command output as proof.
- **Single-source findings**: flag if only one source claims something.
- **No secrets in files**: never print/commit `.env`, bot tokens, API keys,
  WhatsApp session folders. Reference secrets by ENV VAR NAME only.
- **MJ = verifier ONLY**. Only OpenCode (you) changes the VPS.
- **Sequential discipline**: one step, verify, then next.
- **STOP and ask before** destructive / irreversible / paid / deploy / external.
- **Manglish OK** in user comms.
- **Per-step approval**: riskier steps need explicit user "yes".

## 2. ENVIRONMENT

- **VPS**: Tencent Lighthouse SG, `ubuntu@119.28.119.151`, home `/home/ubuntu`.
  SSH: `ssh -o ConnectTimeout=10 ubuntu@119.28.119.151`.
- **Hermes install**: `~/.hermes/` (config, hooks, scripts, whatsapp/session).
  Agent code: `~/.hermes/hermes-agent/` (venv at `hermes-agent/venv/bin/hermes`).
- **Gateway supervision**: `systemd --user` service `hermes-gateway.service`
  (enabled, `Restart=always`).
  Restart: `ssh ubuntu@119.28.119.151 'systemctl --user restart hermes-gateway'`.
  Health check (cron `*/15`): `health_check.py` only ALERTS, does not restart.
- **VPS timezone**: `Asia/Shanghai` (UTC+8) = MYT — time-based med logic works.
- **Local workspace (this repo)**: `F:\AI Prep\OVIS\Hermes Agent\MJay` (git repo;
  mirrors docs/audits only — NEVER med PII JSON).
- **Pytest on VPS**: run with `~/.hermes/hermes-agent/venv/bin/python -m pytest`.

## 3. USER-PHASE AUTHORIZATION (still in effect)

User authorized **live VPS changes for this overhaul phase**, WITH:
- gateway-restart + immediate verification after EACH step;
- only OpenCode (you) makes changes — never the Hermes agent/Jane.
- Per-step approval still required for riskier steps.

## 4. Q&A DECISIONS ALREADY MADE (do not re-litigate)

- **Q1**: Akurit-4 → **Akurit-2** swap CONFIRMED. Full intake (4 biji) started
  **9/7/2026**. Latest appointment **6/7/2026**. (Propagate in P2.)
- **Q2**: Pattern G hook = disable-then-fix, fix perfectly. (**DONE** P0-S2.)
- **Q3**: Full v3 build of `MED_CHAIN_ENGINE_SPEC_v3` (deterministic engine,
  preserve original purpose). (**P1 — planned, ready to execute.**)
- **Q4**: **TOTALLY remove** standalone MiniMax provider + built-in plugin +
  leftovers; **keep** minimax models via `opencode-zen`/`opencode-go`.
  (**DONE** P0-S5 — verified `/model` clean, opencode minimax preserved.)
- **Q5**: Split but partially build multi-agent setup; document for later. (Phase 4.)
- **Q6**: Approve all verification methods; check deeply every file/word.
- **Q7**: Approve `chmod 700 whatsapp/session`. (**DONE** P0-S3.)

## 5. COMPLETED WORK — **P0 FULLY DONE (S1–S5), ALL VERIFIED**

- **P0-S1 (PII leak)**: Fixed `.gitignore` (exclude med-status.json,
  chain-state.json, med-schedule.json, med-supply.json, med-interactions.json,
  dexa_taper.json, substitutions.json, appointments.json, channel_directory.json,
  audit-prep/med-status.json, `*.db*`). Fixed `sync/SYNC-MECHANISM.md` PII
  contradiction. VERIFIED: `git check-ignore` excludes PII files.
- **P0-S2a**: Disabled `med-auto-confirm` hook (`HOOK.yaml` → `events: []`),
  restarted. VERIFIED: `Skipping med-auto-confirm: no events declared`; gateway
  running, TG+WA connected.
- **P0-S2b (Pattern G fix)**: Rewrote `hooks/med-auto-confirm/handler.py` with
  G-1..G-7, DRUG_MAP `akurit_4`→`akurit_2`, dexa fix. Re-enabled
  (`events: [agent:start]`). Extended `test_med_auto_confirm.py` (**14/14 PASS**).
  VERIFIED hook loaded; gateway running.
- **P0-S2c (G-5 freeze fix)**: Rewrote `scripts/chain_monitor.sh` — G-5
  housekeeping EVERY tick; F-04 merge fix. VERIFIED `bash -n` OK; `today`
  `2026-07-10`→`2026-07-11` advanced, silent.
- **P0-S3 (session perms)**: `chmod 700 ~/.hermes/whatsapp/session` + parent.
  VERIFIED 700; gateway alive.
- **P0-S4 (paths + supervisor)**: Fixed `/home/amirul`→`/home/ubuntu` in
  `watchdog.sh`, `check_ds_balance.sh`, `restart_gateway.sh`; rewrote `watchdog.sh`
  to delegate to `systemctl --user restart hermes-gateway`. VERIFIED restart
  works; gateway running, TG+WA connected, hook loaded. `.bak` kept.
- **P0-S5 (MiniMax removal) — DONE & VERIFIED**:
  - Root cause: `provider_models_cache.json` had a top-level `minimax` key (5
    standalone models: `MiniMax-M3/M2.7/M2.5/M2.1/M2`) fed by static
    `_PROVIDER_MODELS` blocks in `hermes_cli/models.py` (lines 316–333) +
    `ProviderEntry` (1001–1003) + `PROVIDER_GROUPS` (1063) + aliases (1166–1170).
  - Fix: removed those four registrations in `models.py` (kept ALL
    `opencode-go/zen` minimax + third-party OpenRouter/NVIDIA/Alibaba/Novita/
    HuggingFace minimax). Ran `hermes plugins disable minimax-provider`, then
    **physically moved** `plugins/model-providers/minimax/` off disk to
    `~/hermes-overhaul-backup/minimax-plugin-removed`. Removed orphan
    `scripts/minimax_proxy.py` (F-11). Cleared + rebuilt cache.
  - VERIFIED: `provider_model_ids("minimax"|"minimax-oauth"|"minimax-cn")` → 0
    models; cache keys = `['deepseek','opencode-go','opencode-zen']`;
    `opencode-go` still returns `minimax-m3`, `minimax-m2.7`; `MiniMax-M*`
    standalone grep = NONE; plugin `disabled` + not listed; gateway active;
    `med-auto-confirm` hook still loaded; TG/WA connected. All backups in
    `~/hermes-overhaul-backup/`.

**CORRECTION to earlier audits**: the 3 restart scripts
(`gw_restart.sh`, `hermes_gateway_restart.sh`, `restart-gateway.sh`) calling
`systemctl --user restart hermes-gateway` are CORRECT (`--user` scope exists).
Gateway IS supervised by systemd (not a bare process). `watchdog.sh` was NOT in
cron and its regex wouldn't match launch `hermes_cli.main gateway run` (was
ineffective) — fixed.

## 6. P1 — MEDICATION CHAIN ENGINE v3 (PLANNED, READY TO EXECUTE)

**Spec**: `audit-prep/MED_CHAIN_ENGINE_SPEC_v3.md` (124 lines; status was
"PENDING EXTERNAL AUDIT"). **Full implementation plan written** →
`docs/superpowers/plans/2026-07-11-med-chain-engine-v3.md` (12 TDD tasks,
freeze-safe integration). **Read that plan file first** in the new session.

**Goal**: Replace LLM auto-linearizing chain logic (the "E dependent on B→C→D"
confusion bug) with a deterministic constraint-solver engine as source of truth;
LLM only explains.

**Build order (from plan)**: rules.json → solve.py → resolve_conflict.py →
tests/ → validate_semantic.py → route.py → why.py → patch chain_calc.py →
med-keyword hook → optional chain_review.py.

**External-audit finding (RESOLVED in plan)**: the spec example "C at 1pm →
E=9:43pm" is self-contradictory (`rule_005` independent vs `rule_004` needing B
which is unknown). Resolved semantics — solver propagates **forward only**; an
`independent` slot is never overridden; `E` depends only on `B` (when known) or
is independent; **E must NEVER derive from C** (regression #17). So "C at 1pm" →
`D=17:00`, `E` untouched.

**Critical integration facts (verified live)**:
- `~/.hermes/scripts/med_chain/` does **NOT exist yet** — build it fresh.
- `chain_calc.py` and `chain_llm.py` **already exist** — current med logic; the
  bug lives in `chain_llm.py`'s auto-linearization. P1 patches `chain_calc.py` to
  call the solver.
- Other med scripts: `med_*.py`, `chain_monitor.sh` — the live reminder
  pipeline. Integration MUST be freeze-safe (engine behind a fallback).

**Execution guidance for the new session**:
1. Load skills first (`using-superpowers`, `writing-plans`, `test-driven-development`,
   `verification-before-completion`, `systematic-debugging` as needed).
2. Implement **directly on VPS** (spec: NO PC→VPS copy). Tests via venv pytest.
3. Follow the plan's TDD tasks exactly: failing test → verify fail → minimal
   implementation → verify pass → checkpoint.
4. **Freeze-safe integration**: `chain_calc.py` patch keeps existing logic as a
   fallback (engine returns `None` on any error → existing path runs). Never break
   live med reminders.
5. At each task boundary: STOP, report evidence, ask owner to confirm next task
   (R2). Watch context % (R1) — if approaching 60%, request a fresh session.

## 7. REORIENTATION COMMANDS (run first in new session)

```
# Local repo
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -5

# Mandate + this brief + P1 plan
# open: OVERHAUL-EXECUTION-PROMPT.md, CONTINUATION-BRIEF.md,
#       docs/superpowers/plans/2026-07-11-med-chain-engine-v3.md,
#       audit-prep/MED_CHAIN_ENGINE_SPEC_v3.md

# VPS orientation
ssh ubuntu@119.28.119.151 'systemctl --user status hermes-gateway --no-pager | head -6'
ssh ubuntu@119.28.119.151 'cat ~/.hermes/chain-state.json | head -20'
ssh ubuntu@119.28.119.151 'ls -la ~/.hermes/scripts/med_chain/ 2>&1 | head'   # expect: not found
ssh ubuntu@119.28.119.151 'ls -la ~/hermes-overhaul-backup/'
```

## 8. NEXT MOVES (after P1)

- **P2**: Propagate Akurit-4 → Akurit-2 swap across state JSON + scripts + hooks.
- **P3**: Cost/config hygiene (F-14/15/19/06, memory headroom, cron scope,
  skill curation).
- **Phase 4**: Partial multi-agent setup, documented for later full build.

## 9. KEY FILES

Local workspace:
- `OVERHAUL-EXECUTION-PROMPT.md` — mandate (authority). **Attach to new session.**
- `CONTINUATION-BRIEF.md` — this file. **Attach to new session.**
- `docs/superpowers/plans/2026-07-11-med-chain-engine-v3.md` — **P1 plan (read first).**
- `audit-prep/MED_CHAIN_ENGINE_SPEC_v3.md` — P1 design reference.
- `.gitignore`, `sync/SYNC-MECHANISM.md` — P0-S1 PII fixes.

VPS (`~/.hermes/...`):
- `hooks/med-auto-confirm/handler.py` (+`.bak`), `HOOK.yaml` (`events:[agent:start]`),
  `test_med_auto_confirm.py` (+`.bak`) — G fix (P0-S2).
- `scripts/chain_monitor.sh` (+`.bak`) — G-5 fix (P0-S2c).
- `whatsapp/session` — chmod 700 (P0-S3).
- `scripts/watchdog.sh`(+`.bak`), `check_ds_balance.sh`(+`.bak`), `restart_gateway.sh`(+`.bak`) — path fix (P0-S4).
- `hermes-agent/hermes_cli/models.py` — MiniMax registrations REMOVED (P0-S5);
  opencode minimax preserved. Backup: `~/hermes-overhaul-backup/models.py.bak`.
- `hermes-agent/plugins/model-providers/minimax/` — MOVED to
  `~/hermes-overhaul-backup/minimax-plugin-removed` (P0-S5).
- `scripts/minimax_proxy.py` — REMOVED (P0-S5).
- `scripts/chain_calc.py`, `scripts/chain_llm.py` — existing med logic;
  `chain_calc.py` is the P1 integration target.
- `config.yaml` — `providers: '{}'`.
- `~/.config/systemd/user/hermes-gateway.service` — gateway supervisor.
- `chain-state.json` — `today` = 2026-07-11 (freeze broken).
- `logs/med-auto-confirm-audit.log` — hook audit trail.
- `~/hermes-overhaul-backup/` — all P0 backups (reversible).

## 10. SESSION DISCIPLINE REMINDER

- One step, verify, then next. Never batch unverified changes.
- Tag evidence: VALIDATED/UNTESTED/REJECTED.
- Ask before destructive/irreversible/paid actions.
- **Context: 60% hard stop for hy3-free** — request fresh session before stall.
- Keep the user informed concisely; preserve Manglish tone in user-facing text.
