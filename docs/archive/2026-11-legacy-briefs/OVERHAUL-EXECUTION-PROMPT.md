# Hermes Agent Overhaul — Execution Prompt

> **Purpose:** Self-contained execution brief for a NEW AI agent (OpenCode / fresh context window).
> All context end-to-end: initial audit engagement → 3 independent audits complete → execution phase begins.
> **Author:** MJ (native agent, VPS) — verifier only, NOT executor.

---

## ⚠️ YOUR MODE — READ THIS FIRST

You are a **strategic advisor + executor**, in that order. Your job:

1. **FIRST — READ & ANALYSE:** Read ALL files listed in §5. Every single word. Jangan skip.
2. **SECOND — EXPAND & IMPROVE:** Jangan jadi robot ikut plan blindly. Based on your own research, analysis, verification, and findings — propose improvements, modifications, expansions to the execution plan. Luaskan mana yang patut. You have freedom to make it better.
3. **THIRD — ASK BEFORE EXECUTION:** You MUST ask the user for confirmation, agreement, and approval BEFORE any change hits the live system. **No proceed before asking.** This is not optional.
4. **Q&A IS WELCOME:** Jika tak clear, if you need more context, if you want a different approach — ask. Multiple rounds expected before any execution.

---

## 🔧 SKILLS & METHODOLOGY REQUIREMENT (MANDATORY)

You are REQUIRED to use the following structured methodologies at maximum capability. These are the user's explicit standards — not suggestions. If these skills exist in your environment, **load them before acting**. If your environment lacks the literal skill files, **follow the principles described below** — they are the contract.

### A. `using-superpowers` + `superpowers` (skill-first discipline)
- **Rule:** Before ANY response, clarifying question, exploration, or action — check if a skill applies. If it does, you MUST use it. Do not rationalize your way out.
- Process skills (investigation, debugging, planning) come **first** — they set the approach; implementation follows.
- Announce the skill you're using: *"Using [skill] to [purpose]."*
- When multiple skills apply: load process skills first, then implementation skills.

### B. `mattpocock` — Systematic Debugging & Planning (root-cause-first)
This is the user's preferred methodology for ALL investigation, debugging, and planning. Two parts:

**B1. Systematic Debugging (4-phase, Iron Law)**
- **IRON LAW:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST. Symptom fixes are failure.
- Phase 1 — Root Cause: read errors carefully, reproduce consistently, check recent changes, gather evidence, trace data flow. Understand WHY before proposing fixes.
- Phase 2 — Pattern Analysis: find working examples, compare, identify differences.
- Phase 3 — Hypothesis & Testing: form ONE hypothesis, test minimally (one variable), verify.
- Phase 4 — Implementation: create failing test, fix root cause (one change), verify, no scope creep.
- **Rule of Three:** If 3+ fixes fail, STOP and question the architecture — don't try fix #4.
- **Hard wall vs soft bug:** If ALL variations hit the SAME fundamental failure (platform constraint), abandon the approach entirely — pivot to a fundamentally different method.

**B2. Planning & Task Breakdown**
- Decompose work into SMALL, VERIFIABLE tasks with explicit acceptance criteria.
- Build the dependency graph. Implementation order follows it bottom-up (foundations first).
- Vertical slicing: build one complete feature path at a time, not all-database-then-all-API.
- Each task: description + acceptance criteria + verification + dependencies + files + scope.
- Add checkpoints after every 2-3 tasks. High-risk tasks early (fail fast).
- Red flag: jumping from problem statement to execution without Q&A. When given multiple open points, confirm understanding of EACH before executing.

### C. `evidence-first-feasibility-assessment` (live-test gatekeeping)
- **Core principle:** If you haven't tested it live, it's NOT VALIDATED. Design on paper is not evidence.
- Before committing implementation effort: map the exact failure mechanism `[trigger] → [component failure] → [symptom]`.
- Distinguish ROOT CAUSE (mechanism) from PROBLEM CLASS (category). Solutions addressing only the class → flag WEAK.
- For each candidate: label strictly — VALIDATED (live test passed + artifact) / UNTESTED (design only) / REJECTED (falsified) / PENDING (needs live test).
- NEVER call a design-only claim "VALIDATED."
- Subagent/adversarial output is evidence to be verified, NOT an oracle. Verify root-cause claims live before trusting.
- Stale snapshot trap: a file on disk may be outdated. VPS live state is source of truth. Verify recency (`stat` mtime) before relying.

### D. `incremental-implementation` (thin vertical slices)
- Build in thin slices: implement one piece → test → verify → commit → next slice.
- Each increment leaves the system in a working, testable state. Don't write 500 lines then test.
- One thing at a time. Separate concerns into separate commits.
- **User-per-step approval mode (ACTIVE here):** state WHAT + WHY → wait for explicit "go" → execute → SHOW EVIDENCE (raw output) → ask "proceed?" → WAIT. Do NOT auto-advance.
- "Proceed" on the plan ≠ approval for all execution steps. Each step needs its own gate.

### E. `gsd` — Get-Shit-Done (execution mindset) ⚠️ *Not a literal installed skill — required as mindset*
- Decisive execution. Ship working increments. No analysis paralysis.
- Verify, then MOVE. Don't over-deliberate when evidence is sufficient.
- When blocked, pivot fast — don't try 3 variations of a failing method (see B1 hard-wall rule).
- Balance with the freeze/approval gates: GSD means execute the APPROVED work efficiently, not bypass the gates.
- Report progress concretely. No filler, no reassurance padding.

### F. How to apply these when CREATING THE MASTER PLAN (§10)
When you produce the Master Implementation Plan, you MUST:
1. Use **`writing-plans` Master Execution Plan format** (11 sections: current state → architecture → roadmap → dependency graph → folder structure → module list → testing → logging/monitoring → priority → deliverables → completion checklist).
2. Use **`mattpocock` planning** to decompose each phase into verifiable tasks with acceptance criteria + checkpoints.
3. Use **`evidence-first`** to label every finding: VALIDATED (live-verified) / UNTESTED (from audit docs, not yet live-checked) / REJECTED.
4. Use **`systematic-debugging`** for any bug you personally investigate — root cause before fix.
5. Use **`incremental-implementation`** discipline when you start executing: thin slices, per-step approval, show evidence.
6. Use **`gsd`** to keep momentum: don't stall on analysis when the path is clear.

---

## 1. Current State Assessment

### Project Summary
- **System:** Hermes Agent (Nous Research) — personal AI assistant for amirulhazym
- **Host:** Tencent Lighthouse VPS, Singapore (Linux, ubuntu@119.28.119.151)
- **Working dir (VPS):** `~/mjay/` (git repo)
- **Working dir (PC — your environment):** `F:\AI Prep\OVIS\Hermes Agent\MJay\`
- **Goal:** Transform from generic chatbot → multi-agent expert system that acts like real humans across common + specialized tasks. Currently <5% of target.
- **User:** EEE grad, AI self-learner since 2025, Malaysian (Manglish), building production AI systems.

### Git State (VPS — MIXED)
| Item | Detail |
|------|--------|
| HEAD | `62729fc` (OpenCode reorg — `opencode-audits-1007/` + `archive/` committed) |
| Branch | `hermes-live` |
| Untracked | `antigravity-audits-1007/`, `zai-audits-0907/` (scp'd from PC, not committed in git) |
| Remote | `origin github.com/amirulhazym/hermes-agent-personal_assistant.git` |
| Push | NONE — all local only (user approval required) |
| Reorg commits | PC `main` HEAD `6116d64`; VPS `hermes-live` HEAD `62729fc`; histories NOT merged/pushed. (Z.ai `c7c40e2` does not resolve on VPS — likely stale/PC-only.) |

### 3 Auditors — Complete & File-Synced to VPS

| Auditor | PC Folder | VPS Folder | Verified? | Key Contents |
|---------|-----------|------------|-----------|-------------|
| **Gemini/Antigravity** | `\audits\antigravity-audits-1007\` | `~/mjay/audits/antigravity-audits-1007/` | ✅ byte-match 18001/27198/20964 | audit-01 (system-context), audit-02 (28 findings), audit-03 (execution-plan) |
| **OpenCode** | `\audits\opencode-audits-1007\` | `~/mjay/audits/opencode-audits-1007/` | ✅ 5 files | audit-01/02/03 + fresh-context-v2.2 + Pattern-G doc |
| **Z.ai** | `\audits\zai-audits-0907\` | `~/mjay/audits/zai-audits-0907/` | ✅ byte-match 20000/37148/22499 | zai-audit-01/02/03 (55 findings, target-state blueprint §8) |
| **Archive** | `\audits\archive\` (13 files, PC) | `~/mjay/audits/archive/` (8 files, VPS) | ⚠️ NOT byte-identical | Reference-only unless reconciled |

> **Sync nuance:** File contents/sizes ARE synced to VPS, BUT `antigravity-audits-1007/` and `zai-audits-0907/` are **untracked** on VPS `hermes-live` git (only OpenCode's `opencode-audits-1007/` is committed). They exist as files but are NOT in git — a fresh `git clone`/`pull` would drop them. Commit before relying on them.

### Cross-Audit Critical Findings (Highest Consensus)

| ID | Title | Severity | Convergence | Summary |
|----|-------|----------|-----------|---------|
| **Pattern G / F-22** | Med-auto-confirm false-positive | **CRITICAL** | ✅ All 3 | Loose regex matched "A" + "20:00" → created future timestamp → froze chain → 10 Jul silent lockout. Fix spec G-1…G-7. |
| **F-01** | Med-timing "blind-shift" logic | **CRITICAL** | ✅ OpenCode+Z.ai | Clinically incorrect shift logic. Redesign med-engine. **Depends on Pattern G fix first.** |
| **F-03** | Watchdog path broken | **CRITICAL** | ✅ Gemini | watchdog.sh uses `/home/amirul/` instead of `/home/ubuntu/`. |
| **25+ others** | hooks, cron, config, memory, state, security | HIGH/MED/LOW | — | Read individual audit docs. |

### Unverified Items (Z.ai flagged — you must check live)
1. GitHub repo PII exposure (med/personal data in committed files?)
2. Vision pipeline liveness (does it actually work?)
3. Daily Health Broken Pipe root cause

---

## 2. Architecture Snapshot

> **TO BE EXPANDED BY YOU** — use `mattpocock` planning + `evidence-first` to consolidate.
> - Z.ai `zai-audit-03-execution-plan.md` §8 — TARGET-STATE ARCHITECTURE: Overhaul Blueprint (KEEP/FIX/SIMPLIFY/ADD, phased Phase 0→4)
> - OpenCode `audit-03-execution-plan.md` — O1-O8 overhaul map + F-01 Final Remediation Spec
> - Gemini `audit-01-system-context.md` — system topology + runtime layers
>
> Read all 3. Compare. Find convergence + conflicts. Propose ONE consolidated architecture.

---

## 3–4. Implementation Roadmap (Starter — TO BE EXPANDED BY YOU)

### Phase 0: Synthesis & Verification (READ-ONLY, freeze-safe)
- Read ALL auditor files (every word)
- **Cross-auditor verification (CRITICAL):** For EVERY finding across all 3 auditors, verify against LIVE VPS. Classify each:
  - **CONFIRMED** — live-verified, real defect
  - **FALSE-POSITIVE** — auditor claimed it, live check proves wrong (flag it)
  - **CONFLICT** — auditors disagree on root cause/severity → investigate, decide
  - **SINGLE-SOURCE** — only 1 auditor found it → verify harder, don't assume consensus
  - **NEW** — you discover something NONE of the 3 found → pursue it
- Classify each finding by usefulness: helpful / critical / nice-to-have / not-needed / redundant.
- Verify 3 unverified items against live VPS (ask MJ)
- **Independent discovery:** Go BEYOND the 3 audits. The prompt is a FLOOR, not a ceiling — find what they missed, challenge their conclusions, expand scope.
- Propose Master Implementation Plan (use `writing-plans` 11-section format + `mattpocock` decomposition)

### Phase 1: Critical Quick Fix (Pattern G)
*Prerequisite for everything else — broken daily reminders*
- G-1: Tighten regex (anti-false-positive)
- G-2: Fix future-timestamp creation
- G-3: Fix chain freeze
- G-4: Fix day-roll gating
- Verify: no more silent lockout (test with actual reminder cycle)

### Phase 2: Foundation Fixes
- F-03: Fix watchdog.sh path (/home/amirul/ → /home/ubuntu/)
- F-01: Med-engine redesign START (design + test first, implement after)
- System-level bug cleanup (home dir, config paths)

### Phase 3: Core Overhaul
- Complete med-engine redesign (O8 / F-01 Spec)
- 3-way sync deployment (sync/ scaffold)
- Memory system cleanup & dedup
- Soul.md uniqueness fix (lowercase/uppercase orphan + root cause)
- (Add more based on your expanded analysis)

### Phase 4: Target-State Expansion
- Multi-agent expert system per Z.ai blueprint
- Obsidian integration
- Domain-specific expert agents
- Production hardening + monitoring

### Dependency Rules (VERIFY by reading audits — may expand)
- Pattern G fix → before med-engine redesign (all 3 converged)
- Med-engine redesign → before soul/memory restructure
- 3-way sync → after core fixes
- Git push/merge → after user approves

---

## 5. File Inventory (Your Accessible Files)

All paths relative to `F:\AI Prep\OVIS\Hermes Agent\MJay\`.

### Auditor Files
| Relative Path | Size | What it Contains |
|---------------|------|-----------------|
| `audits/antigravity-audits-1007/audit-01-system-context.md` | 18,001 | System topology, runtime layers |
| `audits/antigravity-audits-1007/audit-02-findings.md` | 27,198 | 28 findings (F-01..F-28) incl. F-03 watchdog |
| `audits/antigravity-audits-1007/audit-03-execution-plan.md` | 20,964 | Remediation phases O1-O8 |
| `audits/opencode-audits-1007/audit-01-system-context.md` | — | Deep architecture + overhaul dives (§7-14) |
| `audits/opencode-audits-1007/audit-02-findings.md` | — | F-01..F-24 + Pattern G (F-22 critical) |
| `audits/opencode-audits-1007/audit-03-execution-plan.md` | — | P0-P3 + O1-O8 + F-01 Final Remediation Spec |
| `audits/opencode-audits-1007/fresh-context-prompt-v2.2.md` | — | Phase 0 charter prompt |
| `audits/opencode-audits-1007/PATTERN-G-med-auto-confirm-false-positive.md` | — | Raw incident log + step trace + G-1..G-7 specs |
| `audits/zai-audits-0907/zai-audit-01-system-context.md` | 20,000 | Architecture atlas (16 dimensions D1-D16 + clinical) |
| `audits/zai-audits-0907/zai-audit-02-findings.md` | 37,148 | **55 findings** (11 CRIT / 17 HIGH / 16 MED / 11 LOW, 30 BEYOND baseline) |
| `audits/zai-audits-0907/zai-audit-03-execution-plan.md` | 22,499 | P1-P23 + 6 human gates + **target-state overhaul blueprint (§8)** |

### Other Key Files
| Relative Path | Contents |
|---------------|----------|
| `audit-prep/` (local 17 / VPS 12) | VPS mandatory-read docs. ⚠️ VPS copy PARTIAL — missing MED_CHAIN_ENGINE_SPEC_v3.md, med-status.json, soul_lowercase.md, soul_uppercase.md, VPS_AUDIT_STATE.md. Full set is on PC/local. |
| `sync/SYNC-MECHANISM.md` | 3-way sync design (PC↔VPS↔GitHub) — NOT yet deployed |
| `sync/pull-vps-to-wsl2.sh` | Sync script stub — NOT yet deployed |
| `sync/drift-check.sh` | Drift detection script stub — NOT yet deployed |

### VPS Runtime (Read-only reference — never modify)
| Path | What it Contains |
|------|-----------------|
| `~/.hermes/med-status.json` | Current medication state (PII — never commit/expose) |
| `~/.hermes/chain-state.json` | Chain state for cron reminders (PII — never commit) |
| `~/.hermes/med-schedule.json` | Medication schedule config |
| `~/.hermes/config.yaml` | Hermes config |
| `~/.hermes/cron/jobs.json` | Cron job definitions (verified path on VPS) |
| `~/.hermes/.env` | **API keys** — NEVER read or expose |

---

## 6–7. Execution Mandate

### Your Role
You are the **EXECUTION AGENT** for the overhaul. You drive the process — but you MUST ask before acting.

MJ (native VPS agent) is **VERIFIER ONLY**. For live-VPS truth checks you have two options: (a) self-verify via `ssh ubuntu@119.28.119.151` read-only commands (`wc -c`, `grep`, `git status`, `cat` non-PII) — same access the auditors used; or (b) ask the owner to relay to MJ for independent native verification. NEVER modify VPS without explicit user "go".

### Freeze Rule (ACTIVE)
Execution requires explicit user approval per phase/step. The user (amirulhazym) says "go" for each phase/step before any system change. No changes without that explicit "go".

| ✅ Allowed | ❌ Not Allowed |
|-----------|---------------|
| Read ALL audit files — every word | Create/modify/delete any system file on VPS |
| Analyse, compare, contrast, synthesize | Change any config on VPS |
| Verify against live VPS (read-only via MJ) | `git push` to GitHub |
| Propose execution phases — expand, improve, add | Restart gateway |
| Produce your own Master Implementation Plan | Deploy any change |
| Ask Q&A — clarification, deeper context, decisions | Run cron/med reminders manually |
| Suggest alternative approaches | Anything touching live system without "yes" |
| **Improve the plan — your ideas are welcome** | — |

### Working Discipline
1. **READ EVERY WORD** — all files in §5. Jangan skip. Jangan skim.
2. **LOAD SKILLS FIRST** — before any task, invoke `using-superpowers` + relevant skills (see §SKILLS).
3. **THEN Q&A** — if unclear, ask. Multiple rounds OK.
4. **THEN PROPOSE** — your expanded Master Implementation Plan (`writing-plans` 11-section + `mattpocock` tasks).
5. **THEN GET APPROVAL** — user confirms "go" Phase 1. Then execute with `incremental-implementation` + per-step gates.
6. **SEQUENTIAL** — selesai satu baru proceed next.
7. **VERIFY** — each step has a verification. Evidence-first (`evidence-first` labels).
8. **DEPENDENCY-ALERT** — if later work affects earlier done work, alert user immediately.
9. **STOP** for: login/OTP/payment/destructive actions.
10. **GSD** — when approved work is clear, execute decisively. No stalling.

### Communication
- User speaks **Manglish** (Malay-English mix). Match his language.
- User is technically capable (EEE grad, AI professional). Match depth accordingly.
- Direct, honest, grounded feedback. Don't sugarcoat. Don't fabricate.
- Don't over-explain basics unless asked.

---

## 🔒 WORKING METHOD — HARD RULES

> These govern **HOW you work** (context discipline, checkpoints, handoff). They do NOT restrict your analytical freedom — you may still improve, expand, and challenge the plan with your own judgment. Grounded in `incremental-implementation`, `planning-and-task-breakdown`, `subagent-driven-development`.

### R1 — Context-Window Monitoring (continuous)
- At every checkpoint, report context usage as **% of model limit**.
- Context **> 70%** of limit → STOP adding work to this window.
- ⚠️ **hy3-free SPECIFIC (256k limit):** This model **silently dies at the ceiling — no error, no response, just stops**. Auto-compaction is UNRELIABLE for it in OpenCode/zcode (works in Hermes, not there). Treat **60% (~150k tokens) as the HARD STOP**. NEVER rely on auto-compaction to save you. Manual context discipline (R2/R4) is the ONLY reliable safeguard.

### R2 — Checkpoint Discipline (after each task / every 2-3 tasks)
- After a task (or batch of 2-3): **STOP**. Report what was done + evidence + context %.
- **Ask owner (amirulhazym) to confirm before next task.**
- If context > 70% (or **> 60% for hy3-free**): signal owner to either (a) spawn subagent (if supported + under tolerance) to continue, or (b) start a FRESH context window for next phase. **For hy3-free: do NOT wait for 70% — at 60% request fresh context immediately. The model gives no warning before it dies.**

### R3 — File-Reading Discipline (never blow context on raw reads)
- NEVER load all 11 auditor files + audit-prep into one context.
- **Subagents available:** dispatch one per auditor folder (terminal/file) → return condensed summary (~3-5k tok). Main context uses summaries only.
- **Subagents NOT available:** read in targeted batches (grep findings, read sections). Spread across fresh contexts if needed.

### R4 — Per-Phase Fresh Context
- Each phase (Phase 0 synthesis, Phase 1 Pattern G, Phase 2 F-03, …) = own fresh context window. Don't carry full phase context forward.
- At phase boundary: summarize state → hand to new context → restart from summary.

### R5 — Q&A Gate Before Execution
- Multiple open points/feedback → don't execute. Understand each, confirm, get approval, then execute one at a time.
- Correction ≠ Approval: a corrected value isn't implicit approval for a full multi-step plan.

### R6 — VPS Read-Only Verification
- Live VPS truth checks: `ssh ubuntu@119.28.119.151` with **read-only** commands (`wc -c`, `grep`, `git status`, `cat` non-PII). Same access auditors used.
- NEVER modify VPS via SSH without explicit user "go".
- MJ (native Hermes) is verifier-of-record — for independent native check, ask owner to relay; self-verify read-only via SSH is acceptable.

### R7 — Freedom Preserved (Coverage UNBOUNDED)
- These rules constrain mechanics, not conclusions. You retain full freedom to improve the plan, propose alternatives, expand scope, challenge findings — while following R1-R6 for HOW you work.
- **Coverage is UNBOUNDED.** This prompt is a FLOOR, not a ceiling. The 3 audits + MJ's synthesis are baseline INPUT, NOT the limit. You are EXPECTED to find new issues, challenge auditor conclusions, expand scope beyond what's listed. Do NOT treat the listed findings as exhaustive. If you find something the auditors missed, pursue it.

---

## 8. Verification Strategy

| What | How | When |
|------|-----|------|
| Byte-verify synced files | Ask MJ: `wc -c` on VPS → compare to local | Before trusting sync claim |
| Verify config values | Ask MJ: `grep` of live config | Before changing config |
| Verify hook/script state | Ask MJ: `cat` live file + check path | Before code changes |
| Test Pattern G fix | `med_confirm.py --dry-run` with boundary inputs | After fix applied |
| Test med-engine | `chain_calc.py` with test data | After redesign |
| Test no regressions | Run cron cycle + check logs in **sandbox/copy/`--dry-run` ONLY** (no live run until user says "go") | After each phase (post-freeze) |
| `--dry-run` first | Test against copy/backup | EVERY change |
| Auto-backup | `.bak1/.bak2/.bak3` at `~/.hermes/scripts/` — USE IT | Before destructive changes |

> ⚠️ **Execution guard:** No live cron runs or live med tests without explicit user "go" for that phase. All testing must be sandbox / copy / `--dry-run` until the user approves the live run. Per-step approval (§6-7, R2) overrides any "run existing cycle" instruction.

**Evidence-first labels (use these in your plan + reports):**
- ✅ **VALIDATED** — live test passed + raw output shown
- 🔶 **UNTESTED** — from audit docs, not yet live-verified
- ❌ **REJECTED** — audit claim falsified by live check
- ⏳ **PENDING** — needs live test before claiming

---

## 9. Implementation Priority (Starter — validate + expand by you)

| Priority | Item | Why | Depends On |
|----------|------|-----|-----------|
| **P0** | **Pattern G hook fix** | Broken daily med reminders. Highest consensus CRITICAL. | None |
| **P1** | F-01 med-engine redesign | Clinically incorrect timing. Affects ALL med features. | Pattern G fix FIRST |
| **P2** | F-03 watchdog path fix | Broken monitoring. | None (parallel P1 after P0) |
| **P3** | All CRITICAL findings from all 3 audits | — | Depends on items |
| **P4** | HIGH findings | — | Depends on CRITICAL |
| **P5** | MEDIUM findings | — | Depends on HIGH |
| **P6** | LOW findings | — | Depends on HIGH/MED |
| **P7** | Overhaul O1-O8 (target-state blueprint) | Architecture redesign | All CRITICAL/HIGH |
| **P8** | Multi-agent expert system | User's ultimate goal | P7 complete |

> **YOUR JOB:** Validate this order using `evidence-first` + `mattpocock`. Read the audits. Do YOU agree? If not, propose changes WITH EVIDENCE. Expand gaps.

---

## 10–11. Deliverables & Completion Checklist

> **TO BE PRODUCED BY YOU** after reading all files. Use `writing-plans` 11-section format.

### After Phase 0 (Mandatory First Output)
1. ✅ **Master findings list** — consolidated from all 3 auditors, cross-referenced (converge / conflict / gap)
2. ✅ **Cross-auditor verification matrix** — per finding: CONFIRMED / FALSE-POSITIVE / CONFLICT / SINGLE-SOURCE / NEW + usefulness rating (helpful / critical / not-needed / redundant)
3. ✅ **Independent discovery list** — new issues YOU found that none of the 3 auditors caught (with evidence)
4. ✅ **All 3 unverified items checked** against live VPS — result per item (VALIDATED/REJECTED/UNTESTED)
5. ✅ **Your expanded Master Implementation Plan** — 11-section format + `mattpocock` task decomposition (acceptance criteria + checkpoints)
6. ✅ **Your recommendation on git merge strategy** — reconcile 2 reorg commits + 2 untracked folders
7. ✅ **Questions for the user** — what you need before proceeding (multiple Q&A rounds welcome)
8. ✅ **User approval on Phase 0 output** — THEN proceed to Phase 1

### Completion Checklist Template
| # | Finding | Auditor(s) | Severity | Status | Evidence Label |
|---|---------|-----------|----------|--------|----------------|
| 1 | Pattern G / F-22 | All 3 | CRITICAL | PENDING | — |
| 2 | F-01 med timing | OpenCode, Z.ai | CRITICAL | PENDING | — |
| 3 | F-03 watchdog path | Gemini | CRITICAL | PENDING | — |
| ... | (expand from all 3 audits) | | | | |

**Legend:** ✅ DONE | ❌ BLOCKED | ◐ IN PROGRESS | ⏳ PENDING | 🔶 UNTESTED

---

## Hard Constraints (From User — IMMUTABLE)

1. **Skills mandatory:** Use `using-superpowers` + `mattpocock` (debugging + planning) + `evidence-first` + `incremental-implementation` + `gsd` mindset at max capability. Load skills before acting.
2. **Evidence-first:** Every claim → verify against live VPS before repeating as fact. Label VALIDATED/UNTESTED/REJECTED.
3. **Single source = flagged:** If only ONE auditor found something, say so. Don't present as consensus.
4. **Partial ≠ Done:** Never round up. ◐ is ◐. Only ✅ when fully verified complete.
5. **No secrets in files:** API keys in `.env` ONLY. Never in `config.yaml`, never committed.
6. **MJ = VERIFIER ONLY:** Never delegate execution to her. She answers VPS truth queries.
7. **Sequential discipline:** Selesai satu, baru proceed next. Dependency-alert if later work affects earlier.
8. **Stop for destructive:** Gate on login/OTP/payment/destructive. Report before acting.
9. **Manglish OK:** User speaks Malaysian Manglish. Match his language.
10. **The freeze is real:** Phase 0 read-only work only. No system changes without explicit "go".
11. **Pattern G first? Validate yourself.** Read the audits. If you agree, great. If not, propose why with evidence.
12. **ASK BEFORE EXECUTION.** No proceed without user's explicit confirmation and agreement.

---

## YOUR FIRST INSTRUCTION

```
1. Load using-superpowers. Check for relevant skills. Announce what you're using.
2. Read EVERY file in §5 (all auditor docs + audit-prep/ + sync/). Every single word.
3. Using mattpocock + evidence-first:
   - Produce master synthesis (converge / conflict / gap across 3 auditors)
   - Check 3 unverified items against live VPS (ask MJ)
4. Using writing-plans (11-section) + mattpocock (task breakdown):
   - Propose YOUR Master Implementation Plan with phases, steps, substeps, acceptance criteria
   - Validate the P0-P8 priority (agree? if not, why, with evidence)
   - What you'd add/modify based on analysis
5. Ask the user any Q&A before proceeding. Multiple rounds welcome.
6. WAIT for user "go". Then execute Phase 1 with incremental-implementation + per-step gates.
```

**Good luck. The user wants quality — not speed, not shortcuts, not robot behaviour. Use the skills.**
