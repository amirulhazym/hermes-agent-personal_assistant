---
name: self-improving-agent
description: Use when facing repeated corrections, discovering recurring failure patterns, or needing a systematic way to compound learning across sessions. Not for one-off fixes or single corrections. Also use when comparing your self-improvement architecture against other systems (OpenClaw skills, etc.) to identify gaps and adopt missing patterns.
---

# Self-Improving Agent

## Overview

An agent that doesn't learn from corrections will repeat the same mistake twice. This skill provides a structured methodology for capturing, deduplicating, promoting, and reviewing learnings — synthesised from patterns across the AI agent ecosystem (Iván's self-improving + proactive agent, pskoett's self-improving-agent, and the Hermes Agent memory/skills/curator system).

The core principle: **corrections are data, not failures.** Each user correction is a signal to improve — but only if you capture it, deduplicate it, and promote it to permanent knowledge.

## The Learning Pyramid (Tiered Knowledge)

```
HOT (always available in current session)
  ├── Memory store — user profile, env facts, preferences (injected every turn)
  ├── Loaded skills — procedural memory for task types (skill_view)
  └── Session state — current task context

WARM (available via tool on next session)
  ├── session_search — FTS5 retrieval over all past transcripts
  ├── Skill library — 110+ curated skills (skills_list + skill_view)
  └── Project learnings — optional per-project .learnings/ dir

COLD (automatically decayed, still retrievable)
  ├── Curator archive — stale skills auto-archived after inactivity
  └── Old session transcripts — searchable via session_search
```

## Learning Signals

Capture learnings automatically on these triggers:

| Signal | Example | Action | Storage |
|--------|---------|--------|---------|
| User correction | "No, that's wrong..." | Log correction + evaluate for permanent rule | Memory (fact) or skill (procedure) |
| Tool/API failure | Command fails unexpectedly | Log error + fix pattern | Skill reference |
| Outdated knowledge | "That's old info, it's now X" | Research + correct + log | Memory update |
| Better approach | "Actually do X instead of Y" | Codify as skill if recurring | skill_manage('create') |
| Missing capability | "Can you do X?" | Log feature request | Memory |
| Repeated same mistake 2+ times | Same correction twice | Promote to hardened skill with pitfalls | skill_manage + pitfall section |

## Pattern-Key Dedup (from pskoett/self-improving-agent)

**The core anti-duplication technique.** Before persisting a new learning:

1. **Extract a stable Pattern-Key** — a noun-phrase identifying the core lesson (e.g. `med-confirm-source-text`, `partial-state-rounding`, `report-stale-issues`)
2. **Check existing knowledge** — `session_search(query)` for past occurrences + `skills_list()` + scan current memory
3. **If exists** — add **See Also** link to the occurrence, bump recurrence count mentally. Do NOT create duplicate entries.
4. **If new** — create with the Pattern-Key as anchor for future dedup

**When to skip dedup:** First occurrence of a novel correction. Dedup triggers on 2nd+ occurrence.

### Dedup in Practice

```python
# Mental checklist before saving anything:
# 1. session_search(query="partial+done+rounding") — any past session?
# 2. skills_list() — already a skill for this?
# 3. memory recall — already saved as fact?
# If yes → See Also, don't duplicate
# If no → save as new
```

## Heartbeat Self-Review (from ivangdavila/self-improving)

Periodic reflection on accumulated corrections and learnings. Not a cron job — a **mental trigger** that fires at natural breakpoints:

### When to Heartbeat

- **After task completion** — user says "selesai" on a 3+ tool-call task
- **Session start** — especially after a long gap (>24h)
- **Accumulation threshold** — 3+ corrections received in one session
- **Weekly rhythm** — scan memory + recent skills for stale entries

### Heartbeat Protocol

```
1. SCAN — review last N corrections in memory
2. PATTERN CHECK — any forming a repeated pattern? → promote to skill
3. STALE CHECK — any skill grown outdated? → patch or archive
4. DEDUP CHECK — any Pattern-Key duplicate across memory/skills? → consolidate
```

### Implementation

This is not a separate script or cron job. It's a judgment call you make at the natural breakpoints above. When triggered:

```bash
# Quick scan of recent corrections
session_search(query="correction", limit=5, sort="newest")

# Check if a pattern exists
skills_list()
# → if gap found, skill_manage(action='create')

# Check stale skills (via curator)
# → hermes curator status (manual check)
```

## Promotion Pipeline

```
Correction (raw, in memory)
    ↓ heartbeat review
Pattern identified (2+ occurrences)
    ↓
Skill candidate (stable, reusable procedure)
    ↓
Class-level umbrella skill (with references/ directory)
    ↓
Canonical knowledge (curator-managed, auto-archived when stale, pinned if evergreen)
```

### Promotion Thresholds

| Occurrence | Action |
|------------|--------|
| 1st correction | Log to memory only. Do NOT create a skill. |
| 2nd similar correction | Promote to skill — pattern is confirmed. Include pitfall section. |
| 3rd+ | Harden the skill — add rationalization table + red flags. Ensure dedup with existing. |

## Per-Project Scoping (from pskoett)

Some learnings are project-specific, not global:

| Scope | Examples | Storage |
|-------|----------|---------|
| **Global** | Tone preferences, formatting rules, epistemic standards, general Hermes usage patterns | Memory + skills (~/.hermes/skills/) |
| **Per-project** | Codebase conventions, specific API quirks, dependency workarounds | `.learnings/` in project root: LEARNINGS.md, ERRORS.md, FEATURE_REQUESTS.md |

For per-project learnings structure:
```markdown
# Learnings — <project-name>
**Categories**: correction | insight | knowledge_gap | best_practice

## YYYY-MM-DD: Short title [correction]
- **Pattern-Key:** `<stable-key>`
- **Source:** <session context>
- **Detail:** What happened, what was corrected, why
- **Recurrence-Count:** 1
- **See Also:** <link to related>
```

## External Skill-Repository Adoption Pattern

When importing skills from another agent ecosystem, treat the task as a reproducible adoption workflow, not a file-copy shortcut. Pattern-Key: `external-skill-adoption-discovery`.

1. **Verify the source first** — confirm the repository URL, README, selected skill paths, and pinned source commit before copying anything. A remembered repository name or URL is only a search hint.
2. **Discover Hermes from local ground truth** — locate the active local skills root and configured external directories; inspect one known-working skill's absolute path, complete package tree, and raw `SKILL.md` before choosing the destination.
3. **Check the runtime contract** — use the target's authoritative loader/scanner or skill APIs to determine frontmatter parsing, platform/environment filtering, duplicate precedence, core-command collisions, and slash-command registration. Do not add persistent routing rules until native routing has been tested.
4. **Compare exact names before copying** — classify every selected skill as `INSTALL`, `PRESERVE EXISTING`, or `REVIEW`. Never overwrite an exact-name skill silently, and never flatten a package that contains support files.
5. **Preserve source bytes by default** — copy the complete selected package without mass-rewriting descriptions or metadata. If source-platform metadata differs, flag it and test target behavior before adapting it.
6. **Verify three boundaries separately** — (a) package file-set and per-file hashes, (b) target parser + `skill_view()` readiness, and (c) generated slash-command/scanner registration. These prove installation/discovery only; interactive end-to-end behavior remains a separate status.
7. **Discard malformed checker output** — if a custom verifier is wrong, rerun with the target runtime's parser/API and keep invalid-checker output separate from actual skill failures.

Do not claim "auto-routing works" from a file existing or a skill-list entry alone. Report each boundary as `PROVEN`, `PARTIAL`, or `UNTESTED`, and keep persistent prompt/config changes as a separate approval and verification surface.


| Need | Tool/Method |
|------|-------------|
| Save a single fact/correction | `memory(action='add', target='user' or 'memory')` |
| Save a reusable procedure | `skill_manage(action='create')` |
| Search past learnings | `session_search(query)` — FTS5 over all transcripts |
| List existing skills for dedup | `skills_list()` |
| View a skill's content | `skill_view(name)` |
| Update an existing skill | `skill_manage(action='patch')` |
| Check for past occurrences | `session_search(query, limit=5)` before creating |
| Consolidate overlapping skills | Note in output — background curator handles bulk consolidation |
| Archive stale skills | Curator auto-archives; manual: just stop using, curator picks it up |

## Interaction with Other Agent Skills

| Skill | Relationship |
|-------|-------------|
| **anti-fabrication-guardrails** | Complementary. Anti-fabrication prevents bad output; this skill grows good knowledge. Both needed. |
| **doubt-driven-development** | DDD is adversarial review before decisions; this is post-hoc learning capture. Different phases. |
| **verification-before-completion** | Verification prevents false claims; this skill captures true corrections. Pipeline: verify → correct → capture. |
| **debugging-and-error-recovery** | Debugging finds root cause; once found, capture the fix via this skill so it doesn't resurface. |
| **auto-skill-suggester** | Suggests relevant skills at task start — reduces need to remember which skills exist. |
| **writing-skills** | Governs HOW to write skills; this skill governs WHY and WHEN to write them. |

## User-Provided Self-Improvement Instruction Protocol

When the user explicitly tells you HOW to improve (not just WHAT was wrong):

### Critical Rule: Apply Verbatim, Do Not Narrow

**Don't:**
- Take their instruction and make a "better" / narrower version of it
- Scope it down to the immediate domain (health → not just health, code → not just code)
- Save a memory entry that only covers the surface-level symptom

**Do:**
1. Repeat back exactly what they said to confirm understanding
2. If it feels too narrow, ASK before expanding — don't assume
3. Execute the instruction EXACTLY as stated
4. Only after execution, ask: "Does this capture what you meant?"

### Confirmation Requirement

After making any self-improvement change at the user's request:
- **Explicitly confirm the action was taken** (e.g., "Memory updated. Here's what was saved:")
- Show the actual content that was stored — not just a summary
- Let them verify and correct if needed

**Why:** The user has experienced agents that claim action but don't deliver. Confirming with evidence builds trust.

### Enforcement-Action Rule (System-Level Change Required)

When the user challenges a claimed improvement with language like "Hanya cakap je? Apa action kau?" / "Just talk?" / "What did you actually do?":

**Memory + verbal confirmation is INSUFFICIENT.** The user is demanding evidence of a permanent system-level change.

**Response must include at least one of:**
1. **Create/modify a script** — a stably-runnable tool (e.g. `format_doc.py`) that future sessions can invoke. This is stronger than instructions because it enforces correct behavior mechanically.
2. **Patch the relevant SKILL.md** — update the canonical procedure so the corrected approach is the default, not an override. Remove or flag any old contradictory instructions.
3. **Patch the relevant behavior-contract or reference file** — embed the user's explicit words and the corrected rule so it cannot be ignored as "one session's lesson."
4. **Verify the change works** — run the script/test and show output confirming it functions.

**After execution:**
- Show the actual diff, script path, or verification output — not a summary
- State explicitly: "X was created, Y was patched, Z was verified"
- Do NOT respond with just "noted" or "done" — those are the exact words that triggered this rule

### Pattern-Keys for User Self-Improvement Corrections

| Pattern-Key | Signal | Action |
|-------------|--------|--------|
| `narrow-scope-correction` | User says "make it broader/general, not just X" | Original instruction was general — apply as-is without domain restriction |
| `unapproved-rephrasing` | User says "I said X, you wrote Y" | Apply instruction verbatim next time; ask before rewording |
| `unconfirmed-improvement` | User asks "Dah update?" after you claimed done | Always confirm execution with stored content shown |
| `enforcement-action-needed` | User challenges "hanya cakap je / just talk?" | System-level permanent guard required (script + skill patch), not just memory |

## Historical Task-Identity Corrections

**Pattern-Key:** `historical-task-label-anchoring`

A user correction can expose a context-resolution failure rather than a missing technical detail. This happens when an agent sees a reused label such as `A5` in a recent document and silently maps it to that document's meaning, even though the user means the original roadmap/task entry from an earlier merge or audit session.

Before proposing a new plan or asking a clarifying question after a label correction:

1. Treat the label as an opaque pointer, not a semantic name.
2. Search the exact label and nearby domain terms in session history and the relevant task list/plan.
3. Read the matching task entry plus predecessor/successor gates; keyword snippets alone are insufficient.
4. Check for same-label collisions across later documents and preserve each meaning separately.
5. Restate the owner-defined task with its source boundary before discussing implementation approaches.
6. Keep these fields separate:
   - `TASK_IDENTITY`: what the owner asked for;
   - `CURRENT_FINDINGS`: what the system currently proves;
   - `APPROACH_CANDIDATES`: ways to execute the task;
   - `ACCEPTANCE_GATES`: evidence required for completion.
7. Only ask branch questions about approaches after the task identity is anchored. Do not use a design sub-question to make the owner redefine an already-defined task.

**Concrete failure pattern:** The owner’s roadmap `A5` meant “change Hermes’s WhatsApp bot number after the Hermes update, then smoke-test Telegram/WhatsApp.” A later operations document reused `A5` for LID/JID identity correction. Mapping the owner’s request to the later document caused an irrelevant clarification question. The correction is to retrieve the original roadmap entry first; this is a context error, not evidence that the migration scope is ambiguous.

**Reference:** `references/historical-task-label-anchoring.md` contains the retrieval recipe, collision table, evidence fields, and stop conditions.

## Pitfall: approval leakage across a read-only boundary

A prior `Proceed` or implementation approval is not durable permission for later turns. If the owner subsequently says `read-only`, `HOLD`, or `do not execute`, freeze the earlier plan immediately. Do not edit, stage, commit, delete, run write-capable tests, deploy, restart, or consume runtime markers. Classify each tool action as read-only, candidate write, runtime write, or external write before executing it. If a platform-mandated housekeeping write is unavoidable, disclose it as an exception; if an unauthorized write already happened, stop and report the exact path/action instead of continuing.

**Pattern-Key:** `read-only-scope-overrides-stale-approval`

## Pattern: evidence-first correction of contradictory plans

When an external reviewer identifies an internal contradiction in a plan, treat the reviewer text as a claim inventory—not as authority and not as execution approval.

1. Read the exact current artifact and locate every occurrence of the disputed terms, states, and task IDs.
2. Verify each reviewer claim against the artifact itself and, where relevant, the live system. Classify it `CORRECT`, `PARTIAL`, `FALSE`, or `UNKNOWN` before changing anything.
3. Patch only the affected plan sections; do not redesign unrelated goals or execute the underlying corrective work.
4. Re-scan the whole artifact for the same state terms after the patch. A local wording fix is insufficient if another task, checkpoint, receipt field, or test still encodes the old contract.
5. For automation, check activation order separately from configuration validity: keep an existing job paused/disabled while its script is being fixed and tested, and name the first task allowed to enable it.
6. For status labels, define one deterministic contract and repeat it everywhere. If a state is successful but not yet published, encode the publication boundary as metadata (for example `release_pending=true`, `push_allowed=false`) rather than mixing `PASS` and `HOLD` for the same inputs.
7. Report two separate outcomes: `PLAN PATCHED / READY FOR PLAN APPROVAL` and `CORRECTIVE EXECUTION NOT STARTED`.

This pattern prevents reviewer corrections from becoming either blind acceptance or unnecessary redesign, and prevents individually reasonable plan tasks from forming an unsafe sequence when combined.

## Pitfall: confusing plan approval with release approval

A multi-phase plan may authorize execution of safe diagnostics and candidate construction without authorizing publication, remote policy changes, branch merges, deployment, restart, or live config mutation. Preserve the distinction explicitly:

1. Capture a baseline before edits.
2. Build and test an isolated candidate.
3. Verify the exact diff and exact SHA.
4. Ask for or require the separate release/promotion gate defined by the repository policy.
5. Never infer live deployment from a green CI run or a `main` ref.

Related pattern keys: `approval-leakage-across-release-boundary`, `candidate-not-live`, `source-vs-deployed-reference`.

## Pitfall: verify mechanisms before automating around them

When an automation event is suspected, check the platform's authoritative event list first. Do not create a plausible-sounding hook or attribute non-execution to the environment until the mechanism itself is proven to exist. For Git, distinguish client `pre-push` from server-side `post-receive`/`post-update`; if the desired client event does not exist, use a tested scheduler/poller and document that as the supported path.

Related pattern key: `mechanism-before-workaround`.

## Pitfall: classify drift instead of suppressing it

A monitoring baseline must not turn an unverified deployment mismatch into a green status. Keep source publication and deployed runtime references separate, then classify:

- `NOOP`: service healthy, references equal, no runtime drift;
- `WARN`: service healthy but expected/documented runtime drift exists;
- `FAIL`: service failure, new unexpected drift, unreadable references, or threshold breach.

A baseline is evidence for classification, not permission to hide a mismatch.

Related pattern keys: `known-drift-warn`, `remote-vs-live-sha-separation`.

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Saving every correction as a skill (skill bloat) | Wait for pattern (2+ occurrences) before promoting. First time → memory only. |
| Creating duplicate skills for same lesson | Always Pattern-Key dedup first. `session_search` + `skills_list` before create. |
| Memory grows unbounded | Use heartbeat to review and prune. Stale entries in memory can be consolidated. |
| Session-specific narrow skill names (e.g. `fix-calcitriol-wednesday-bug`) | Name by class of work (e.g. `medication-schedule-validation`). If it only makes sense for today, it's too narrow. |
| Only capturing, never reviewing | Heartbeat prevents this. Set review triggers. |
| Mixing project-specific and global knowledge | Global → memory/skills. Per-project → `.learnings/` in project root. |
| Letting skills rot with outdated info | `skill_manage(action='patch')` immediately on discovering outdated content. Don't wait. |
| Creating new skill when existing one just needs a section | Prefer `skill_manage(action='patch')` over creating siblings. Check existing umbrellas first. |

## References

This skill synthesises patterns from:
- **ivangdavila/self-improving** (ClawHub) — heartbeat system, tiered memory, proactive agent patterns
- **pskoett/self-improving-agent** (ClawHub) — Pattern-Key dedup, categorized learnings, promote-to-AGENTS.md pipeline
- **Hermes Agent** — memory tool, skills lifecycle, session_search FTS5, curator auto-archive, anti-fabrication guardrails
