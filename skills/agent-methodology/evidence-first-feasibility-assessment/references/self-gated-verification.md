# Self-Gated Verification: The Architectural Pattern

## The Failure Pattern

When an LLM agent is both the **answer producer** and the **answer verifier**,
verification becomes self-gated — the agent decides whether to verify itself.
When the agent is confidently wrong, it skips verification. The guards exist
only as advisory text in the system prompt.

**Every guard is self-administered:**
- "Refuse over guess" → the agent decides whether it's guessing
- "Load relevant skills" → the agent decides what's relevant
- "Check memory" → the agent decides to check

**Root cause:** The system has no separation of concerns between "doing" and
"checking." The same component produces errors and reviews itself. Blind
spots correlate perfectly.

## Recognising It

When analysing a failure involving LLM agent behavior, check:

1. List every verification guard that SHOULD have caught the error
2. For each guard, ask: "Who decides whether to activate this guard?"
3. If the answer is "the same agent that produced the wrong output" for ALL
   guards → the architecture is the root cause, not the agent's carelessness

## The Fix: External Enforcement

Move verification to a **separate layer** that the agent cannot bypass.

### Enforcement Hierarchy (strongest first)

| Solution | Strength | Works across LLMs? | Effort |
|----------|----------|-------------------|--------|
| **Tool-level rejection** | HIGH | ✅ Yes — hard API gate | Low |
| **Gateway-level pattern detection** | MEDIUM-HIGH | ✅ Yes — fires before agent | Medium |
| **Hook-authenticated skill injection** | MEDIUM | ✅ Yes — separate process | Low |
| **Adversarial subagent review** | MEDIUM | ⚠️ Same LLM class bias | High (2x cost) |
| **Prompt-level instruction** | LOW | ❌ Self-gated, same as having no guard | Lowest |

### Concrete Hermes Agent Implementation (verified 2026-07-04)

**Layer 1: Tool-level rejection (hardest gate)**
The tool itself validates inputs against known data and rejects unknowns.
Example: `med_confirm.py` calls `med_resolve.py` internally — if the agent
passes a fabricated drug name, the tool returns:
```
ERROR: 'letrozole' not found. Valid options: [akurit_4, pyridoxine, ...]
```
The agent CANNOT bypass this — it must pass a valid name or the operation
fails. See `med_resolve.py` for the implementation.

**Layer 2: Gateway hook + trigger file (process-level separation)**
A Python hook (separate from the LLM agent) runs on `agent:start`, detects
message patterns, and writes a trigger file. The agent's SOUL.md instructs
it to read this file at the start of each turn.

Flow:
```
User message → Hook (regex match) → writes triggered_skills.txt
                                          ↓
Agent starts → SOUL.md says "check trigger file"
                                    ↓
Agent reads file → loads skill → verifies before responding
```

Even though Step 3 is still LLM-gated, the hook mechanism adds:
- A concrete file artifact on disk (easier to monitor than abstract rules)
- Process-level separation (hook runs in gateway, agent processes later)
- Audit trail (file writes are timestamped)

**Layer 3: SOUL.md instruction (advisory, but strengthened)**
The instruction becomes specific: "At the START of EVERY turn, ALWAYS check
if ~/.hermes/triggered_skills.txt exists. If it exists: read it, load EACH
skill listed with skill_view(name), then DELETE the file."

## Testing the Fix

1. Send a message containing a known trigger pattern (e.g., "dah makan letram")
2. Check that `triggered_skills.txt` was written by the hook
3. Verify the agent loaded the skill (check response — it should resolve correctly)
4. Send an invalid/fabricated drug name to the tool directly
5. Verify the tool rejects with clear error listing valid options

## Limitation

No solution is 100% for LLM fabrication. The goal is to **raise the cost of
fabrication** to the point where the agent cannot accidentally produce
confidently-wrong output without external feedback. Tool-level rejection
is the strongest guard because it operates at the API boundary, not the
prompt boundary.
