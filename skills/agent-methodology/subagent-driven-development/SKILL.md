---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Core principle:** Fresh subagent per task + task review (spec + quality) + broad final review = high quality, fast iteration

**Narration:** between tool calls, narrate at most one short line — the ledger and the tool results carry the record.

**Continuous execution:** Do not pause to check in with your human partner between tasks. Execute all tasks from the plan without stopping. The only reasons to stop are: BLOCKED status you cannot resolve, ambiguity that genuinely prevents progress, or all tasks complete. "Should I continue?" prompts and progress summaries waste their time — they asked you to execute the plan, so execute it.

## When to Use

**vs. Executing Plans (parallel session):**
- Same session (no context switch)
- Fresh subagent per task (no context pollution)
- Review after each task (spec compliance + code quality), broad review at the end
- Faster iteration (no human-in-loop between tasks)

## The Process

Per task:
1. Dispatch implementer subagent
2. Answer questions if needed
3. Implementer implements, tests, commits, self-reviews
4. Write diff file, dispatch task reviewer subagent
5. Task reviewer reports spec compliance + quality
6. Dispatch fix subagent for issues
7. Mark task complete
8. Dispatch final code reviewer when all tasks done

## Model Selection

Use the least powerful model that can handle each role to conserve cost and increase speed.

- **Mechanical implementation tasks** (isolated functions, clear specs, 1-2 files): use a fast, cheap model.
- **Integration and judgment tasks** (multi-file coordination, pattern matching, debugging): use a standard model.
- **Architecture and design tasks**: use the most capable available model.
- **Review tasks**: choose model commensurate with diff's size, complexity, and risk.

## Handling Implementer Status

| Status | Action |
|--------|--------|
| DONE | Generate review package, dispatch reviewer |
| DONE_WITH_CONCERNS | Read concerns, address if needed, proceed to review |
| NEEDS_CONTEXT | Provide missing context, re-dispatch |
| BLOCKED | Assess blocker, escalate if plan is wrong |

## Advantages

**vs. Manual execution:**
- Subagents follow TDD naturally
- Fresh context per task (no confusion)
- Parallel-safe (subagents don't interfere)

**vs. Executing Plans:**
- Same session (no handoff)
- Continuous progress (no waiting)
- Review checkpoints automatic

**Quality gates:**
- Self-review catches issues before handoff
- Task review carries two verdicts: spec compliance and code quality
- Review loops ensure fixes actually work

## Red Flags

**Never:**
- Start implementation on main/master branch without explicit user consent
- Skip task review
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Skip review loops
- Accept "close enough" on spec compliance
- Move to next task while the review has open Critical/Important issues
