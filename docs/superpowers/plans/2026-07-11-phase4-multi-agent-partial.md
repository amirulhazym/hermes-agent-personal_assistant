# Phase 4 — Partial Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Partially wire Hermes into a multi-agent expert system (Med / Research / Ops)
using existing delegation + skills + hooks — document patterns and thin router; do not
rebuild the platform.

**Architecture:** Three expert roles as skill packs + routing rules (MEMORY/SOUL +
optional skill-trigger). Med math stays in `med_chain`. Delegate depth 1 only.
Kanban optional documentation/backlog only.

**Tech Stack:** Hermes VPS (`~/.hermes`), skills (SKILL.md), hooks (skill-trigger),
config.yaml orchestrator flags, stdlib unittest for med regression, local git only.

## Global Constraints

- Q5: partial multi-agent only; full product later.
- Freeze: do not break med logic; per-step user go for live VPS changes.
- MJ = verifier only; OpenCode = executor.
- Local commits yes; **git push NO**.
- `subagent_auto_approve: false`; `max_spawn_depth: 1`; `max_concurrent_children: 3`.
- No paid provider enable without yes.
- Design skills (gsap/creative/UI) must not be deleted.
- Evidence labels: VALIDATED / UNTESTED / REJECTED.
- hy3-free: 60% context hard stop; fresh session if needed.

**Spec:** `docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md`  
**Handoff:** `CONTINUATION-BRIEF-P4.md`

---

### Task 0: Orient (read-only)

**Files:** none (read only)

- [ ] **Step 1:** Attach `OVERHAUL-EXECUTION-PROMPT.md` + `CONTINUATION-BRIEF-P4.md` + design + this plan.
- [ ] **Step 2:** Live inventory:

```bash
ssh ubuntu@119.28.119.151 'grep -nE "orchestrat|max_spawn|max_concurrent|kanban|subagent" ~/.hermes/config.yaml | head -40'
ssh ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 '~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s ~/.hermes/scripts/med_chain/tests -p "test_*.py" 2>&1 | tail -5'
```

Expected: orchestrator_enabled true; gateway active; 21 tests OK (or note regression).

- [ ] **Step 3:** STOP — report inventory; ask go for Task 1.

---

### Task 1: Multi-agent patterns skill (documentation product)

**Files:**
- Create (VPS): `~/.hermes/skills/devops/multi-agent-patterns/SKILL.md`
- Create (local mirror optional): `docs/superpowers/specs/` already has design

**Interfaces:**
- Produces: skill MJ can `skill_view("multi-agent-patterns")`
- Consumes: design §5–§7

- [ ] **Step 1:** Backup:

```bash
ssh ubuntu@119.28.119.151 'mkdir -p ~/hermes-overhaul-backup/pre-p4 && ls ~/hermes-overhaul-backup/pre-p4'
```

- [ ] **Step 2:** Write SKILL.md covering: architecture diagram (text), E1/E2/E3, D1–D3
  delegate patterns, forbidden actions, when to use kanban vs delegate vs no_agent cron,
  clean-restart-only for ops.

- [ ] **Step 3:** Verify file exists and is valid markdown (readable by `skill_view`).

- [ ] **Step 4:** Commit VPS local git:

```bash
cd ~/.hermes && git add skills/devops/multi-agent-patterns/SKILL.md
git commit -m "overhaul(P4-S1): multi-agent-patterns skill [VALIDATED]"
```

- [ ] **Step 5:** STOP — show path + excerpt; ask go for Task 2.

---

### Task 2: Expert skill packs (thin wrappers)

**Files:**
- Create: `~/.hermes/skills/experts/med-expert/SKILL.md`
- Create: `~/.hermes/skills/experts/research-expert/SKILL.md`
- Create: `~/.hermes/skills/experts/ops-expert/SKILL.md`

**Interfaces:**
- Each expert skill: description triggers + must-load skills + hard rules + tools allowed
- Med expert MUST reference med-tracker + med_chain; MUST NOT replace solver

- [ ] **Step 1:** Write three SKILL.md files (short, <150 lines each). Include:

```markdown
# Med Expert
## When to use
## Must load
- med-tracker
## Hard rules
- SSOT: med-schedule.json, med_chain/rules.json
- Never invent drug_id; never rewrite pre-2026-07-09 history
- Partial≠Done; dry-run / no prod clobber
## Tools
- chain_calc.py --display (read)
- med scripts only with user go for writes
```

(Similar for Research / Ops.)

- [ ] **Step 2:** Verify dirs exist; `find ~/.hermes/skills/experts -name SKILL.md`

- [ ] **Step 3:** Commit:

```bash
git add skills/experts && git commit -m "overhaul(P4-S2): expert packs Med/Research/Ops [VALIDATED]"
```

- [ ] **Step 4:** STOP — ask go for Task 3.

---

### Task 3: Router pins (MEMORY + optional skill)

**Files:**
- Modify (VPS): `~/.hermes/memories/MEMORY.md` (add ≤3 short entries; stay under 75% chars)
- Create: `~/.hermes/skills/devops/multi-agent-router/SKILL.md` (decision table)

**Interfaces:**
- MEMORY pins: durable routing facts
- multi-agent-router: if X then load Y

- [ ] **Step 1:** Measure MEMORY chars before edit:

```bash
python3 -c "from pathlib import Path;p=Path.home()/'.hermes/memories/MEMORY.md';print(len(p.read_text()))"
```

Must stay under 6750 after edit (75% of 9000).

- [ ] **Step 2:** Add entries (examples):

```
Multi-agent: domains Med→experts/med-expert+med-tracker; Research→experts/research-expert; Ops/restart→experts/ops-expert+clean-restart-gateway. Patterns: multi-agent-patterns skill.
```

- [ ] **Step 3:** Write multi-agent-router SKILL.md decision table (no code).

- [ ] **Step 4:** Commit memory + skill; re-check char %.

- [ ] **Step 5:** STOP — ask go for Task 4.

---

### Task 4: skill-trigger expansion (optional, freeze-safe)

**Files:**
- Modify: `~/.hermes/hooks/skill-trigger/handler.py` TRIGGER_MAP
- Backup: `~/hermes-overhaul-backup/pre-p4/skill-trigger-handler.py.bak`

**Interfaces:**
- Consumes: message text
- Produces: `triggered_skills.txt` lines (skill names)

- [ ] **Step 1:** Backup handler.

- [ ] **Step 2:** Add **high-confidence only** patterns, e.g.:

```python
(r"\brestart\s+gateway\b", "experts/ops-expert"),  # or clean-restart-gateway
(r"\bclean\s+restart\b", "experts/ops-expert"),
(r"\bdrug\s+interaction\b", "experts/research-expert"),
```

Do **not** steal med keywords from med-tracker (keep med-tracker first).

- [ ] **Step 3:** `python3 -m py_compile hooks/skill-trigger/handler.py`

- [ ] **Step 4:** Restart gateway once; verify hooks load; no traceback.

- [ ] **Step 5:** Commit + STOP.

If user declined skill-trigger changes: skip Task 4 entirely; MEMORY+router skill is enough.

---

### Task 5: Delegate recipe dry-run (supervised)

**Files:**
- Create: `~/.hermes/skills/devops/multi-agent-patterns/references/delegate-recipes.md`

- [ ] **Step 1:** Write D1–D3 recipes with exact constraints (no med writes, no restart).

- [ ] **Step 2:** With user go only: one supervised non-med parallel research via
  Hermes delegate tools (or document manual dry-run checklist if tool unavailable from OC).

- [ ] **Step 3:** Record VALIDATED/UNTESTED in brief.

- [ ] **Step 4:** Commit docs.

---

### Task 6: Kanban (document-only default)

**Files:**
- Create: section in multi-agent-patterns OR `references/kanban-usage.md`

- [ ] **Step 1:** Read live `kanban:` config; note max_in_progress if missing.

- [ ] **Step 2:** Document: use kanban for multi-day non-med builds; not for med confirms.

- [ ] **Step 3:** Only if user go: create backlog cards for Obsidian / fetcher / skill archive.

- [ ] **Step 4:** Commit.

---

### Task 7: Live verification (mandatory)

**Files:** none (commands)

- [ ] **Step 1:** Med tests:

```bash
~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s ~/.hermes/scripts/med_chain/tests -p "test_*.py"
```

Expected: Ran 21 tests … OK

- [ ] **Step 2:** Gateway + hooks + WA bridge + hello-world-watch scheduled.

- [ ] **Step 3:** `python3 chain_calc.py --display` clean.

- [ ] **Step 4:** Confirm experts dirs + multi-agent-patterns exist.

- [ ] **Step 5:** Update `CONTINUATION-BRIEF-P4.md` actuals; local commit Windows + VPS; **no push**.

- [ ] **Step 6:** Report P4 DONE / partial with evidence.

---

### Task 8: Windows docs commit

**Files:**
- `CONTINUATION-BRIEF-P4.md`
- `docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md`
- `docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md`

```bash
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" checkout overhaul/exec
git add CONTINUATION-BRIEF-P4.md docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md
git commit -m "overhaul(P4): draft multi-agent partial design + plan + brief [UNTESTED until execute]"
# NO PUSH
```

---

## Execution order summary

| Task | Risk | Needs user go |
|---|---|---|
| 0 Orient | none | no |
| 1 Patterns skill | low | yes |
| 2 Expert packs | low | yes |
| 3 MEMORY + router | low–med | yes (memory) |
| 4 skill-trigger | med | yes (explicit) |
| 5 Delegate dry-run | med | yes |
| 6 Kanban docs | low | optional |
| 7 Verify | low | after changes |
| 8 Windows commit | none | after docs |

---

## Self-review

1. **Spec coverage:** design §5 experts → Task 2; §6 router → Task 3–4; §7 delegate → Task 5; §8 kanban → Task 6; §10 success → Task 7.
2. **Placeholders:** none intentional; open questions listed in design §13.
3. **Consistency:** expert paths `skills/experts/*` used throughout.

---

*End of plan. Do not execute Tasks 1–7 until user approves after reviewing design + brief.*
