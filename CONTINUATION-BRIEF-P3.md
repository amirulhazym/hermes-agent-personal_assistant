# Hermes Agent Overhaul — CONTINUATION BRIEF P3 (fresh session handoff)

> **Attach BOTH this file AND `OVERHAUL-EXECUTION-PROMPT.md` to the new session.**
> `OVERHAUL-EXECUTION-PROMPT.md` = immutable mandate (skills, freeze rule, R1–R7).
> This file = live progress through P0/P1/P2 + the FULL P3 execution plan (approved).
>
> Paste both into a NEW OpenCode session pointed at workspace
> `F:\AI Prep\OVIS\Hermes Agent\MJay`. Read both fully before acting.
>
> **Naming convention (user rule):** each phase gets its OWN brief file suffixed
> with the phase. **Do NOT edit a prior phase's brief for later work.** When P4
> starts, create `CONTINUATION-BRIEF-P4.md` — do not modify this P3 file for P4.

---

## 0. ROLE & MANDATE

You are the user's strategic advisor + executor for a full overhaul of the
**Hermes Agent** — personal AI for `amirulhazym` (Malaysian, Manglish, EEE grad).
VPS + Telegram + WhatsApp; medication-reminder (TB) is the most critical feature.

Authoritative mandate: **`OVERHAUL-EXECUTION-PROMPT.md`**. Key rules:
- Skills first: `using-superpowers`, `evidence-first`, `incremental-implementation`,
  `systematic-debugging`, `verification-before-completion`, `gsd`.
- Freeze is real: do not break live med logic. Per-step user approval.
- R1: hy3-free **60% (~150k) HARD STOP** — request fresh context before stall.
- R2: after each task, STOP, show evidence, ask before next.
- MJ (native Hermes) = **VERIFIER ONLY**. Only OpenCode (you) changes the VPS.
- **Local git commits YES; git push NO** (user rule — avoid auditor merge conflicts).

**Phase 0/P0/P1/P2 = DONE. P3-S0 through S5 = DONE (2026-07-11).
P3 COMPLETE under bounded full approval (S4 report-only, no skill deletes).
Next phase: Phase 4 → create `CONTINUATION-BRIEF-P4.md` when starting.**

## 1. HARD CONSTRAINTS

- Evidence labels: VALIDATED / UNTESTED / REJECTED.
- No secrets in files/commits. Reference ENV VAR NAMES only.
- No paid service without explicit "yes".
- **Language:** Hermes has **current selected model** (via `/model`), NOT a
  "default model". Never report config.yaml fallback as the user's model.
- Sequential: one step → verify → next.
- STOP and ask before destructive/irreversible/paid/deploy.

## 2. ENVIRONMENT

- **VPS**: `ubuntu@119.28.119.151`, home `/home/ubuntu`.
  SSH: `ssh -o ConnectTimeout=10 ubuntu@119.28.119.151`.
- **Hermes**: `~/.hermes/` (config, hooks, scripts, whatsapp/session).
  Agent: `~/.hermes/hermes-agent/` (venv).
- **Gateway**: `systemd --user` `hermes-gateway.service`, **`Restart=always`**,
  `RestartSec=5`, `StartLimitIntervalSec=0`.
  External restart (OC): `systemctl --user restart hermes-gateway`.
- **Timezone**: Asia/Shanghai (UTC+8) = MYT.
- **Local workspace**: `F:\AI Prep\OVIS\Hermes Agent\MJay` (docs/audits only).
- **Tests**: stdlib `unittest` (pytest not in venv).
  `~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s ~/.hermes/scripts/med_chain/tests -p "test_*.py"`.

## 3. USER-PHASE AUTHORIZATION

Live VPS changes authorized for overhaul, WITH:
- gateway-restart + verify after each step;
- only OpenCode changes VPS;
- per-step approval for riskier steps;
- **commits local only; no push to GitHub**.

## 4. Q&A DECISIONS (do not re-litigate)

- **Q1 Akurit-4→Akurit-2**: DONE P2 (4 biji, note Rifampicin+Isoniazid).
- **Q2 med-status**: ≥2026-07-09 = `akurit_2`; &lt; that = `akurit_4` historical. DONE P2-S5.
- **Q3 med-chain v3**: DONE P1 (21 tests).
- **Q4 MiniMax standalone remove**: DONE P0-S5 (cache has zero minimax keys).
- **Q5 multi-agent**: Phase 4 later.
- **Q7 whatsapp session 700**: DONE P0-S3.
- **P3 versioning Q1**: (a) `git init` local-only in `~/.hermes`, strict `.gitignore`
  BEFORE first commit. Windows docs on branch `overhaul/exec`. No push.
- **P3 timestamps Q2**: (A) backdate P0/P1/P2 catch-up; (B) real-date for new P3 work.
- **hello-world-watch**: **RE-ENABLE**, interval **30s** (see platform note). NOT remove.
- **Daily Health**: **LEAVE PAUSED** (do not resume).
- **Memory trim**: GATED — show proposed list, user approves each entry.
- **Canonical restart skill**: **`clean-restart-gateway` only** (not `gateway-restart`).
- **Model language**: current selected model via `/model` only.

## 5. COMPLETED WORK — P0, P1, P2 (all verified)

### P0 — DONE
PII gitignore (Windows), Pattern G hook fix, G-5 freeze, session 700, path/supervisor,
MiniMax standalone removal. Backups in `~/hermes-overhaul-backup/`.

### P1 — DONE
`~/.hermes/scripts/med_chain/` engine + 21 unittest tests. T10 chain_calc freeze-safe
patch; T11 hook consistency check; T12 chain_review. Deviations: unittest not pytest;
`chain_trace.py` not `trace.py`.

### P2 — DONE
Akurit-2 everywhere from 9/7; pre-swap history kept; gateway restarted; WA connected.
Backups: `~/hermes-overhaul-backup/pre-p2/`.

## 6. P3 — APPROVED PLAN (READY / IN PROGRESS)

**Goal:** Version the live system (local git), restore gateway-restart reliability
(Problems A–D), cost/provider hygiene, gated memory trim, skill curation — without
regressing med logic or pushing to GitHub.

### Team-verified findings (2026-07-11, OC + 2× MJ verifiers)

| Claim | Verdict |
|---|---|
| `~/.hermes` not a git repo | ✅ |
| `~/hermes-overhaul-backup/` exists (pre-p2, minimax backups) | ✅ |
| Windows `.gitignore` excludes med PII | ✅ |
| `memories/MEMORY.md` exists (path `~/.hermes/memories/`, not root) | ✅ |
| hello-world-watch **paused** since 2026-07-08 bulk pause; 2672 prior OK runs | ✅ |
| Hook still writes `hello-world-pending.txt` on every restart | ✅ |
| Pending from 07:17 still unconsumed (watch paused) | ✅ |
| systemd `Restart=always` (not merely on-failure) | ✅ |
| Skills `clean-restart-gateway` vs `gateway-restart` **contradict** | ✅ |
| Cascade kill loop: no auto-signal + re-kill after respawn | ✅ |
| MiniMax standalone removed (cache empty) | ✅ |
| Daily Health paused (not actively erroring) | ✅ |

### Platform note — 30s interval
Hermes `parse_duration` only accepts integer minutes via CLI. Runtime uses
`period_seconds = minutes * 60`. Plan: hand-set `"minutes": 0.5` in jobs.json
for 30s; verify tick; fallback to 1m if broken.

### Better design than state-file alone (user-approved freedom)

| Layer | Artifact | Role |
|---|---|---|
| L1 Signal | hello-world-watch @ 30s | Automatic WA "Hello World! Gateway restarted successfully" |
| L2 Latch | `~/.hermes/restart-state.json` | New session: if restart in-flight → VERIFY ONLY, never re-kill |
| L3 History | `logs/gateway-restart-history.jsonl` | Cross-session learning |
| L4 SOP | `clean-restart-gateway` only | One skill; redirect/deprecate `gateway-restart` |
| L5 Outside | OC SSH `systemctl --user restart` | No in-process cascade |

**Anti-cascade hard rule:** one SIGTERM (or one systemctl restart) → STOP.
Success = Hello World on WA **or** new PID + pending cleared + bridge :3000.
Never second kill within 2 min if latch says `killed|respawning`.

### Execution steps

#### P3-S0 — Backup + versioning (FIRST)
- [ ] Create `~/hermes-overhaul-backup/pre-p3/` (cron, config, skills, hooks, scripts, memories).
- [ ] Write strict `~/.hermes/.gitignore` BEFORE any git add (secrets, PII, runtime, cache, bak).
- [ ] `git init` local-only in `~/.hermes` (no remote).
- [ ] Initial commit of non-PII code.
- [ ] Windows: branch `overhaul/exec`, commit briefs/plans — **no push**.
- VERIFY: git status shows no PII; backup dir lists files.

#### P3-S0b — Catch-up commits (backdated)
- [ ] Logical commits for P0/P1/P2 with `--date` ≈ real completion.
- Message style: `overhaul(Pn): <step> [VALIDATED]`.

#### P3-S1 — Cost / provider audit (READ-ONLY)
- [ ] Report **current selected model** posture (not config.yaml "default").
- [ ] Confirm no paid provider re-enabled; MiniMax standalone still absent.
- ENV names only.

#### P3-S2 — Gateway restart reliability (A–D) CRITICAL
- [ ] **S2a**: Re-enable hello-world-watch; set 30s (`minutes: 0.5`); Daily Health stays paused.
- [ ] **S2b**: Controlled OC systemctl restart → prove Hello World delivers on WA.
- [ ] **S2c**: Unify skills → `clean-restart-gateway` canonical; redirect `gateway-restart`.
- [ ] **S2d**: Add restart-state latch + history jsonl; ban SIGKILL in leftover scripts.
- [ ] **S2e**: Additive MEMORY note (signal purpose + anti-cascade) — not a trim.
- VERIFY each substep with raw evidence.

#### P3-S3 — Memory trim (GATED)
- [ ] Backup `memories/MEMORY.md` + USER.md.
- [ ] Show proposed removal list → **user approves each** → apply.
- KEEP: preferences, corrections, med rules, env, restart/hello-world lessons.

#### P3-S4 — Skill curation
- [ ] Flag obsolete skills; delete only with user OK.
- Keep methodology + clean-restart + med-tracker.

#### P3-S5 — Live verify
- [ ] Gateway active, hooks loaded (hello-world + med-auto-confirm + skill-trigger).
- [ ] Hello World path works.
- [ ] Med-chain tests green (expect 21).
- [ ] `chain_calc --display` clean.
- [ ] No cascade on single OC restart.

### Strict `.gitignore` for `~/.hermes` (mandatory before first commit)

```
# Secrets
.env

# PII — never version
med-status.json
chain-state.json
med-schedule.json
med-supply.json
med-interactions.json
substitutions.json
dexa_taper.json
appointments.json
channel_directory.json
whatsapp/session/

# Runtime state
*.db
*.db-wal
*.db-shm
logs/
cron/output/
hello-world-pending.txt
hello-world-sent.txt
restart-state.json
gateway.pid
clean_restart_result.txt

# Cache
__pycache__/
*.pyc
provider_models_cache.json
ollama_cloud_models_cache.json
cache/

# Backups
*.bak
*.bak1
*.bak2
*.bak3
```

## 7. REORIENTATION COMMANDS

```
# Local
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" branch

# Mandate + brief
# open: OVERHAUL-EXECUTION-PROMPT.md, CONTINUATION-BRIEF-P3.md

# VPS
ssh ubuntu@119.28.119.151 'systemctl --user status hermes-gateway --no-pager | head -8'
ssh ubuntu@119.28.119.151 'ls -la ~/hermes-overhaul-backup/pre-p3/ 2>&1 | head'
ssh ubuntu@119.28.119.151 'test -d ~/.hermes/.git && echo "git:yes" || echo "git:no"'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/scripts/med_chain/tests/'
ssh ubuntu@119.28.119.151 'python3 -c "import json;d=json.load(open(\"/home/ubuntu/.hermes/cron/jobs.json\"));j=[x for x in d[\"jobs\"] if x[\"name\"]==\"hello-world-watch\"][0];print(j[\"state\"], j[\"schedule\"])"'
```

## 7b. P3 COMPLETION ACTUALS (2026-07-11)

### S4 Skill curation — REPORT ONLY (no deletes) [VALIDATED]
- 125 SKILL.md files inventoried.
- KEEP: med-tracker, clean-restart-gateway, hermes-no-agent-cron-pattern,
  agent-methodology/*, cost-tracking, system-self-monitor, adhd-daily-planning, etc.
- MAYBE DROP later (user decision): morning-briefing-removal-note, unused gsap/*,
  niche platform skills; gateway-restart only after name fully unused (already DEPRECATED).
- Full report: VPS `~/hermes-overhaul-backup/pre-p3/P3-S4-SKILL-CURATION-REPORT.md`

### S5 Live verify [VALIDATED]
| Check | Result |
|---|---|
| gateway | **active** PID 3896725, WA bridge :3000 |
| hooks | hello-world + med-auto-confirm + skill-trigger |
| hello-world-watch | **scheduled** every 30s, last ok |
| Daily Health | **paused** (as ordered) |
| MEMORY / USER | **46.1% / 67.1%** (healthy) |
| chain_calc --display | A06:15→B08→C12→D17→E~20 clean |
| med_chain tests | **21/21 OK** |
| Extra restart | skipped (healthy; S2 already proved Hello World) |
| git push | **NONE** |

### Local commits (no push)
- VPS `hermes-local`: through `18140d3` (S4/S5 empty commit marker)
- Windows `overhaul/exec`: brief updates committed locally

## 8. NEXT AFTER P3

- Phase 4: partial multi-agent → create `CONTINUATION-BRIEF-P4.md`.
- Optional later: skill deletes from S4 MAYBE DROP list (needs explicit go).
- Keep med tests green; no push until user explicitly allows.

## 9. KEY FILES

Local: this brief, `OVERHAUL-EXECUTION-PROMPT.md`, `CONTINUATION-BRIEF-P2.md` (do not edit),
`docs/superpowers/plans/`, `audit-prep/`.

VPS:
- `scripts/med_chain/` (P1), `scripts/hello_watch.py`, `hooks/hello-world/`,
  `hooks/med-auto-confirm/handler.py`, `cron/jobs.json`,
  `skills/devops/clean-restart-gateway/`, `skills/devops/gateway-restart/`,
  `memories/MEMORY.md`, `~/.config/systemd/user/hermes-gateway.service`,
  `~/hermes-overhaul-backup/`.

## 10. SESSION DISCIPLINE

- One step, verify, next. Evidence labels.
- Ask before destructive/paid.
- 60% hard stop for hy3-free.
- Med logic post-P2 is correct — P3 must not regress (S5 re-runs 21 tests).
- Naming: next phase = new `-P4` file, never edit this for P4 content.
