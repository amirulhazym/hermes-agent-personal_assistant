---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## The Rule

**Invoke relevant or requested skills BEFORE any response or action** — including clarifying questions, exploring the codebase, or checking files. If it turns out wrong for the situation, you don't have to use it.

**Before entering plan mode:** if you haven't already brainstormed, invoke the brainstorming skill first.

Then announce "Using [skill] to [purpose]" and follow the skill exactly. If it has a checklist, create a todo per item.

## Skill Priority

When multiple skills apply, process skills come first — they set the approach, then implementation skills (frontend-design, etc.) carry it out. Brainstorming and systematic-debugging are Superpowers' most common process skills, but the rule holds for any of them.

- "Let's build X" → superpowers:brainstorming first, then implementation skills.
- "Fix this bug" → superpowers:systematic-debugging first, then domain skills.

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
| "I already loaded the skill, that's good enough" | Loading a skill ≠ following its **process**. E.g. loading brainstorming, asking 1 question, then jumping to testing = skipping the flow. Complete the full cycle: explore → question → propose → approve → spec → review → THEN implement. See brainstorming "Anti-Pattern: Loading then Ignoring." |
| "I found something new while exploring, let me share it first" | You discovered new info (a code path, a system feature, an alternative) while exploring context. The user's current question hasn't changed. **Answer what they asked first** — mention the new finding only after, if still relevant. Getting excited about a discovery and answering a different question answers a question nobody asked. |
| "This can't be done / Not possible / Too hard" | Stop assuming. Try 3 distinct approaches first. The user has explicitly rejected "alasan" (excuse-making) — you DO NOT get to conclude impossibility without live evidence of failure from at least 2 different methods. A plain curl 403 from a datacenter IP does not prove "everything blocked." A hunch about CAPTCHA/phone requirements does not prove "can't automate." Defer: try, then show the actual failures, then propose alternatives. |
| "Let me explain why this won't work first" | No. Try first. Show the user you exhausted options, then explain the blocker — not the other way around. "Alasan, pemalas" was the user's verdict on this pattern (2026-07-13). |
| "I know they chose X, but let me suggest Y anyway" | User decided = execute mode. Once they say "proceed with approach X", stop offering alternatives — especially the one they already rejected. Persisting after decision gets "shibau" / "jangan palatao" / "pandai-pandailah aku decide". Trust they heard your options. If a real blocker appears, report it — do not re-litigate the decision. |
| "Let me flag these claims as UNVERIFIED / wrong" (about external response) | Did you SEARCH first? Counter-claiming without evidence is worse than the external claim you're criticizing. Apply the SAME evidence bar to your own counter-claims: web_search → verify → THEN label. Flagging 5 claims as UNVERIFIED when all 5 are proven correct with a 30-second web search is a pattern failure, not a mistake. Signal: "Kau tak search and verify??? Apa yang menghalang kau dari buat auto research?" (2026-07-28). See evidence-first-feasibility-assessment Pitfall #8. |

## Platform Adaptation

If your harness appears here, read its reference file for special instructions:

- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`

## User Instructions

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.

## Explicit user directive (2026-07-09)

When the user says to "use superpowers / mattpocock skills" or "check in depth, not
just read internet," they mean: for ANY system-investigation or debugging task, you
MUST load and follow `using-superpowers` + `diagnosing-bugs` (or `systematic-debugging`)
BEFORE touching the problem. Ad-hoc shell poking without the structured methodology is
explicitly rejected ("baca internet je barua"). The user values: (1) loading the
relevant skill first, (2) building a real reproduction via the system's own code path,
(3) reading gateway logs as ground truth, (4) NOT concluding "broken" from a shell
`curl`/DNS test that disagrees with the running session.
