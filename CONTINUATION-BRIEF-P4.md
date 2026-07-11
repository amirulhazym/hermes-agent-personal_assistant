# Hermes Agent Overhaul — CONTINUATION BRIEF P4 (fresh session handoff)

> **Attach BOTH this file AND `OVERHAUL-EXECUTION-PROMPT.md` to the new session.**
> Also attach (or open):
> - `docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md`
> - `docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md`
>
> **Naming rule:** this file is P4 only. Do not edit P2/P3 briefs for P4 work.
> When P5 (if any) starts, create `CONTINUATION-BRIEF-P5.md`.

---

## 0. ROLE & MANDATE

You are strategic advisor + executor for the Hermes Agent overhaul for user
`amirulhazym`. Critical path: medication reminders (TB) on VPS + Telegram/WhatsApp.

**Mandate:** `OVERHAUL-EXECUTION-PROMPT.md` (skills, freeze, R1–R7).

**Phase status:**
- Phase 0 / P0 / P1 / P2 / **P3 (incl. cleanup) = DONE & VERIFIED**
- **P4 = DRAFTED (design + plan + this brief). NOT EXECUTED until user go.**

**Q5 (locked):** Split but **partially** build multi-agent setup; document for later full build.

## 1. HARD CONSTRAINTS

- Skills mandatory: using-superpowers, evidence-first, incremental-implementation,
  systematic-debugging, verification-before-completion, writing-plans / executing-plans
  as needed; mattpocock-style task breakdown.
- Freeze: do not break live med logic. Per-step approval for VPS changes.
- MJ = VERIFIER ONLY. OpenCode = only executor.
- Local git commits yes; **git push NO**.
- No paid service without explicit yes.
- Language: **current selected model** via `/model` — never “default model”.
- Design skills (gsap/creative/UI) — **do not delete** (user interest area).
- hy3-free: **60% HARD STOP** — fresh session before stall.

## 2. ENVIRONMENT

- **VPS:** `ubuntu@119.28.119.151` · `ssh -o ConnectTimeout=10 ubuntu@119.28.119.151`
- **Hermes:** `~/.hermes/` · agent `~/.hermes/hermes-agent/`
- **Gateway:** `systemd --user` `hermes-gateway.service` · `Restart=always`
  OC restart: `systemctl --user restart hermes-gateway`
- **Tests:** stdlib unittest · 21 med_chain tests expected green
- **Local git:** Windows branch `overhaul/exec` · VPS `~/.hermes` branch `hermes-local`
- **Backups:** `~/hermes-overhaul-backup/` (pre-p2, pre-p3, skills-dropped, …)

## 3. AUTHORIZATION

User authorized overhaul live changes with per-step gates. P4 execution requires
**new explicit go** after reviewing design/plan (drafting was requested; execute was not).

## 4. DECISIONS ALREADY MADE (do not re-litigate)

| ID | Decision | Status |
|---|---|---|
| Q1–Q2 | Akurit-2 + med-status date rule | DONE P2 |
| Q3 | Med chain engine v3 | DONE P1 |
| Q4 | MiniMax standalone remove | DONE P0 (+ env key removed P3 cleanup) |
| Q5 | Partial multi-agent + document | **P4 scope** |
| Q7 | whatsapp session 700 | DONE P0 |
| Restart | clean-restart-gateway only; hello-world-watch 30s | DONE P3 |
| Daily Health | leave paused | DONE P3 |
| Memory | trimmed healthy 46%/67% + policy | DONE P3 |
| Skills cleanup | niche platforms + gateway-restart + morning-briefing note dropped | DONE P3 |
| Push | blocked | ongoing |

## 5. COMPLETED WORK SUMMARY (P0–P3)

### P0
Pattern G hook, G-5 freeze, paths/supervisor, session perms, MiniMax plugin remove, PII gitignore (Windows).

### P1
`scripts/med_chain/` solver + 21 tests; T10 chain_calc freeze-safe; T11 hook consistency; T12 review.

### P2
Akurit-2 propagation; med-status ≥2026-07-09 → akurit_2; pre-swap history kept.

### P3
- Local versioning (VPS hermes-local + Windows overhaul/exec)
- Cost audit; gateway restart reliability (A–D)
- Memory R1–R11 + thin R12 + R14
- S4 skill report; S5 verify 21/21
- Cleanup: apple/smart-home/social-media/yuanbao/morning-briefing-removal-note/gateway-restart; MINIMAX_API_KEY line removed from .env

## 6. P4 — PARTIAL MULTI-AGENT (PLAN READY, NOT EXECUTED)

### Goal
Connect existing Hermes foundations (delegate, kanban, skills, hooks) into a
**usable partial multi-agent expert system** (Med / Research / Ops) + documentation.
Target: ~5% → ~20–25% of user vision. Full product later.

### Approach (recommended)
**Wire on existing platform (Approach C)** — not a new orchestrator service.

### Experts
| Expert | Skill pack | Core skill |
|---|---|---|
| Med | `skills/experts/med-expert/` | med-tracker + med_chain SSOT |
| Research | `skills/experts/research-expert/` | medication-safety-research |
| Ops | `skills/experts/ops-expert/` | clean-restart-gateway |

### Router
Thin: MEMORY pins + `multi-agent-router` skill + optional skill-trigger keywords.
No separate LLM router process.

### Tasks (see plan for full steps)
| Task | Name | Risk |
|---|---|---|
| P4-S0 | Orient / inventory | none |
| P4-S1 | multi-agent-patterns skill | low |
| P4-S2 | Expert packs | low |
| P4-S3 | MEMORY pins + multi-agent-router | low–med |
| P4-S4 | skill-trigger expand (optional) | med |
| P4-S5 | Delegate recipes + supervised dry-run | med |
| P4-S6 | Kanban docs (cards optional) | low |
| P4-S7 | Verify 21 tests + gateway + Hello World | low |

### Hard boundaries
- Med math = deterministic engine only (LLM explains).
- No delegate restarts gateway; no delegate writes med-status.
- `max_spawn_depth: 1`, `subagent_auto_approve: false` stay.
- Do not delete design skills.

### Live foundation (for orient)
```
orchestrator_enabled: true
max_concurrent_children: 3
max_spawn_depth: 1
subagent_auto_approve: false
kanban: configured
delegate_tool.py + async_delegation.py exist
```

### Open questions (user — before execute)
1. Expert packs as `skills/experts/*` vs docs-only? **Default: experts/**  
2. Expand skill-trigger for ops/research? **Default: MEMORY first; trigger only high-confidence**  
3. Kanban backlog cards now? **Default: document-only**

## 7. REORIENTATION COMMANDS

```bash
# Local
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" branch
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -8

# Open
# OVERHAUL-EXECUTION-PROMPT.md
# CONTINUATION-BRIEF-P4.md
# docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md
# docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md

# VPS
ssh ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 'grep -nE "orchestrat|max_spawn|max_concurrent|kanban|subagent" ~/.hermes/config.yaml | head -30'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/skills/experts 2>&1; ls ~/.hermes/skills/devops/multi-agent-patterns 2>&1'
ssh ubuntu@119.28.119.151 '~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s ~/.hermes/scripts/med_chain/tests -p "test_*.py" 2>&1 | tail -5'
ssh ubuntu@119.28.119.151 'python3 -c "from pathlib import Path;m=Path.home()/\" .hermes/memories/MEMORY.md\".replace(\" \",\"\"); print(len((Path.home()/\"hermes\").read_text()) if False else len((Path(\"/home/ubuntu/.hermes/memories/MEMORY.md\")).read_text()), \"/9000\")"'
```

## 8. NEXT AFTER P4

- Full multi-agent productization (deeper kanban product, more experts).
- Obsidian integration (`OBSIDIAN_VAULT_PATH` already in env names).
- Fetcher as product asset (Z.ai).
- Git push only when user explicitly allows.
- Optional: skill MAYBE DROP for more bulk design archive (user said keep design).

## 9. KEY FILES

**Local**
- `CONTINUATION-BRIEF-P4.md` — this file
- `docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md`
- `docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md`
- `CONTINUATION-BRIEF-P3.md` — prior phase (do not edit for P4)
- `OVERHAUL-EXECUTION-PROMPT.md`
- `audits/zai-audits-0907/zai-audit-03-execution-plan.md` §8 — target-state blueprint

**VPS (post-execute targets)**
- `skills/devops/multi-agent-patterns/SKILL.md`
- `skills/experts/{med,research,ops}-expert/SKILL.md`
- `skills/devops/multi-agent-router/SKILL.md`
- `hooks/skill-trigger/handler.py` (if S4 approved)
- `scripts/med_chain/` — must stay green
- `skills/devops/clean-restart-gateway/`
- `memories/MEMORY.md`

## 10. SESSION DISCIPLINE

- One task → evidence → stop → user go.
- No push.
- Med regression tests after any hook/skill wiring that could affect runtime.
- If context >60% on hy3-free: hand off with this brief, do not continue silently.

## 11. DRAFT STATUS

| Artifact | Status |
|---|---|
| Design spec | **WRITTEN** (UNTESTED — not executed) |
| Implementation plan | **WRITTEN** (UNTESTED) |
| This brief | **WRITTEN** |
| VPS expert skills | **NOT CREATED** until execute go |
| skill-trigger changes | **NOT APPLIED** until execute go |

**To execute P4:** user says e.g. `go execute P4` (optionally with answers to open questions).
Start at Task 0 orient, then Task 1 with per-task gates unless user grants broader approval.

---

*End of CONTINUATION-BRIEF-P4.md*
