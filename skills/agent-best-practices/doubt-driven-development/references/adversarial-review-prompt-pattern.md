# Adversarial Review Prompt Pattern

> **Source:** 2026-07-05 med system v3 review (15 files, 18 live tests, 7 real issues found)
> **Pattern:** Build a standalone review prompt → run by separate LLM (fresh context) → cross-check findings with live tests before accepting

## Why This Pattern Exists

You cannot effectively review your own work. Context window accumulates assumptions that become "facts." The adversarial review pattern materializes a genuinely fresh reviewer with zero context — biased to **disprove**, not to approve.

## Prompt Structure

A review prompt needs 5 sections to be effective:

### 1. Role Framing
```markdown
## YOUR ROLE
You are an adversarial code reviewer. FIND PROBLEMS. Assume the author was overconfident.
Every claim is guilty until proven. Do NOT validate. Do NOT summarize. Find issues.
```

### 2. Context (minimal — enough to understand, not enough to bias)
```markdown
## CONTEXT
- Domain, tech stack, constraints
- What was built and why
- Who the system is for
- Any limitations (no external deps, runs on VPS, delivers via WhatsApp)
```

### 3. File-by-File Review with CHECK FOR Items

For each file, provide:
```markdown
**File:** `path/to/file`
**Purpose:** what it does
**CHECK FOR:**
- [Specific question 1]
- [Specific question 2]
- [Edge case to consider]
```
**Key:** Each CHECK FOR must be concrete enough that the reviewer can run a mental test. Not "find bugs" but "does this time zone handling handle DST?" Without specific check-for items, reviewers generate noise (style nits, hypotheticals).

### 4. Specific Claims to Verify
```markdown
## SPECIFIC CLAIMS TO VERIFY
| Claim | Source |
|-------|--------|
| "ALL 21 phases arithmetic correct" | self-test output |
| "ALL drug pairs SAFE 0 unsafe" | med_interact.py validate |
```

Each claim must include the evidence the author believes supports it. The reviewer then judges whether the evidence actually supports the claim.

### 5. Red Flags (explicitly point the reviewer at suspicious areas)
```markdown
## RED FLAGS TO CHECK
1. [Potential issue the author is worried about]
2. [Known edge case not explicitly tested]
3. [Overclaim risk: X was "verified" but only under ideal conditions]
```

Without red flags, reviewers miss subtle issues because they don't know where to look. Red flags direct attention to the highest-risk areas.

## Output Format

Request a structured output:
```markdown
## YOUR OUTPUT FORMAT

For each issue found:
```
ISSUE [severity]: [title]
FILE: [affected file]
LINE: [if applicable]
PROBLEM: [what's wrong]
EVIDENCE: [how you know]
FIX: [suggested fix]
```

Severity: CRITICAL | HIGH | MEDIUM | LOW
```

## Pitfall: False Positives

**The reviewer can be wrong.** In the 2026-07-05 review, 1 of 3 CRITICAL findings was a false positive (claimed `med_substitute.py` fuzzy match crashes — the code already handled the case). Of the remaining 18 findings, only 7 were real issues after cross-checking.

**Always cross-check review findings with live tests before accepting.** Code review is hypothesis generation. Live test is proof.

**Cross-check protocol:**
```python
# For each CRITICAL/HIGH finding, run a live test BEFORE deciding to fix
# If the reviewer claims X is broken:
result = do_the_thing()  # Run the actual code path
assert result == "broken"  # Confirm the reviewer is right
# Only then: fix it
```

Common false positive signals:
- "This function will crash if X" — but X never occurs in practice
- "This field is missing" — but the field exists, reviewer just searched wrong key
- "This code path is wrong" — but the reviewer missed the intermediate helper that handles the case

## Pitfall: The Reviewer's Severity Is Their Opinion, Not Yours

The reviewer labeled 3 findings CRITICAL. After cross-check:
- CRITICAL #1 (taper phases 1-3 arithmetic) → REAL, fixed
- CRITICAL #2 (BD 2pm dose missing) → REAL, fixed
- CRITICAL #3 (slot-level confirm no decrement) → REAL, fixed
- 1 claimed CRITICAL that was actually a FALSE POSITIVE

Re-evaluate severity yourself. A "CRITICAL" finding about a feature that won't activate for 2 months may be less urgent than a "HIGH" finding about something the user does daily.

## When to Use This Pattern

Use when:
- You've just completed a non-trivial implementation (5+ files, complex logic)
- The work involves medical/financial/security-critical data
- You suspect you may have overclaimed "done" on some items
- The user explicitly asks for a review (as in 2026-07-05)
- You want to preempt user frustration by finding your own bugs first

Do NOT use when:
- The task was trivial (single file, well-understood domain)
- The user is waiting for a quick answer
- You can verify correctness through the test suite alone
