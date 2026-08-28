---
name: diagnosing-bugs
description: "6-phase bug diagnosis methodology for hard bugs, test failures, and performance regressions. Use when facing a difficult-to-diagnose issue — before making changes."
version: 1.0.0
author: Hermes Agent (adapted from mattpocock)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation, diagnosis]
    related_skills: [systematic-debugging, test-driven-development, spike, plan]
---

# Diagnosing Bugs

A 6-phase discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, first build a mental model of the relevant modules before theorising.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug — one that goes red on _this_ bug — you will find the cause; bisection, hypothesis-testing, and instrumentation all just consume it. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL script.** Last resort. If a human must click, drive _them_ with a structured loop script so the loop is still captured and feedable back to you.

Build the right feedback loop, and the bug is 90% fixed.

### Tighten the loop

Treat the loop as a product. Once you have _a_ loop, **tighten** it:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is tight — a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. Do **not** proceed to hypothesise without a loop.

### Completion criterion — a tight loop that goes red

Phase 1 is done when the loop is **tight** and **red-capable**: you can name **one command** — a script path, a test invocation, a curl — that you have **already run at least once** (paste the invocation and its output), and that is:

- [ ] **Red-capable** — it drives the actual bug code path and asserts the **user's exact symptom**, so it can go red on this bug and green once fixed. Not "runs without erroring" — it must be able to _catch this specific bug_.
- [ ] **Deterministic** — same verdict every run (flaky bugs: a pinned, high reproduction rate, per above).
- [ ] **Fast** — seconds, not minutes.
- [ ] **Agent-runnable** — you can run it unattended.

If you catch yourself reading code to build a theory before this command exists, **stop — jumping straight to a hypothesis is the exact failure this skill prevents.** No red-capable command, no Phase 2.

## Phase 2 — Reproduce + minimise

Run the loop. Watch it go red — the bug appears.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

### Minimise

Once it's red, shrink the repro to the **smallest scenario that still goes red**. Cut inputs, callers, config, data, and steps **one at a time**, re-running the loop after each cut — keep only what's load-bearing for the failure.

Why bother: a minimal repro shrinks the hypothesis space in Phase 3 (fewer moving parts left to suspect) and becomes the clean regression test in Phase 5.

Done when **every remaining element is load-bearing** — removing any one of them makes the loop go green.

Do not proceed until you have reproduced **and** minimised.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is AFK.

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) make that a concrete recommendation for architectural improvement. Make the recommendation **after** the fix is in, not before — you have more information now than when you started.

## CRITICAL PITFALL — Trust the live system's resolution path, not external shell probes

When debugging a *running system* (agent gateway, model picker, provider resolution,
auth chain), **never conclude "it doesn't work" from a standalone shell `curl`/DNS test.**
The system often reaches the network through a different code path than your shell:

- The gateway resolves providers via `resolve_runtime_provider()` — built-in plugin
  overrides, env-var injection, credential pools — NOT via the raw `config.yaml`
  `model.base_url` you read by eye.
- A `curl` from the shell may fail DNS (NXDOMAIN) or return 401 while the gateway's
  actual call path (Anthropic-format payload to a plugin-resolved base_url, internal
  proxy, or pool credential) succeeds.
- **Your own running session is evidence.** If the agent is currently responding and
  the user says "I'm talking to model X," that IS proof model X is reachable — do not
  override it with a shell test that says otherwise. The shell test is the weaker signal.

**Correct approach (the feedback loop for system-resolution bugs):**
1. Reproduce by calling the system's OWN resolution function in a throwaway Python
   script: `sys.path.insert(0, "<hermes-agent>"); from hermes_cli.runtime_provider
   import resolve_runtime_provider; print(resolve_runtime_provider())`.
2. Read the gateway log (`~/.hermes/logs/agent.log`) for the actual `provider=`,
   `base_url=`, `model=` of recent API calls — this shows what REALLY happened.
3. Only AFTER the system-path repro matches the user's report, form hypotheses.
4. Shell `curl`/DNS is a *secondary* check, never the primary verdict.

**Documentation-completeness variant (2026-07-09, audit handoff):** When the "bug" is *incomplete handoff docs* (external agent would work on stale/missing info), the Phase1 feedback loop is: for each artifact the external agent needs, does it EXIST and is every claim VERIFIED against live state (not memory)? A claim stated without a tool-verified backing = red. This is the same discipline applied to docs instead of code — paste the verification command + output for each.

**Anti-pattern (2026-07-09, MiniMax investigation):** Agent ran `curl api.minimax.com`
→ NXDOMAIN, concluded the MiniMax provider was dead, then argued with the user who was
literally receiving minimax-m3 responses. Root cause: the gateway used the built-in
plugin's `api.minimax.io/anthropic` (Anthropic mode), not the shell's OpenAI-format curl
to `api.minimax.com/v1`. The agent's own session + gateway log were the real evidence;
the curl was noise. The user's rebuke ("baca internet je barua") was earned.

See `references/system-resolution-debugging.md` for the full MiniMax/Hermes model-picker
investigation recipe (dual code-path trap, picker vs gateway base_url divergence, fallback
chain hiding the real provider).

## CRITICAL PITFALL — Re-derive prior-session root causes from RAW evidence (2026-07-10)

When you re-investigate a bug a PRIOR session claimed to have found/fixed, DO NOT trust that session's narrative. Re-derive the root cause from raw code + logs yourself. A prior session can present a fabricated or unsupported root cause that you then inherit into your own fix.

VERIFIED case (2026-07-10): a prior (07:04) session concluded "the med-auto-confirm hook false-positive'd on the user's 05:00 message about the 20:00 bug." Re-investigation REFUTED it:
- The actual 05:00:57 gateway.log inbound was "Why did you instruct me to do something? I ask you to work on it for me. Who are" — NO med content, NO "20:00".
- The hook's `COMPLETE_RE` requires "dah makan/selesai/done/took/ate/confirm" — that message matches none → hook returns early, cannot fire.
- `config.yaml` has `hooks: {}` (hook not registered) and there are zero hook runtime traces for 07-10.

The real root cause (proven by repro + code read): `med_confirm.py --at 20:00` was called by some caller (writer ultimately UNATTRIBUTED — no per-write audit log existed), and the script writes any `--at` value blindly with no validation.

Discipline: for any "we found/fixed X yesterday" claim, before building on it, run the same evidence steps a fresh investigation would — read the exact source, grep the exact logs, reproduce. If the prior claim doesn't survive contact with raw evidence, say so explicitly; do not silently inherit a wrong root cause. This is Phase 1 (feedback loop) applied to the investigation itself: the "loop" is "does the prior claim reproduce against raw evidence?"

## Quick Reference

| Phase | Focus | Completion Criterion |
|-------|-------|---------------------|
| **1. Feedback Loop** | Build a tight, red-capable pass/fail signal | One command that goes red on the exact bug, green when fixed |
| **2. Reproduce + Minimise** | Confirm the bug, shrink repro to minimum | Every remaining element is load-bearing |
| **3. Hypothesise** | Generate 3–5 ranked falsifiable hypotheses | Ranked list with predictions, shown to user |
| **4. Instrument** | Test predictions one at a time with tagged probes | Hypothesis confirmed or ruled out |
| **5. Fix + Regression** | Write regression test first, then fix | Bug resolved, regression test passes |
| **6. Cleanup + Post-mortem** | Remove instrumentation, document root cause | Checklist complete, architectural recommendations made |

## Hermes Tool Integration

### Investigation Tools

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs
- **`process`** — Manage long-running repro loops and server processes

## Supporting References

- **`references/feedback-loop-techniques.md`** — condensed catalog of 10 feedback loop construction techniques, tightening strategies, and the completion criterion. Reference this when you get stuck building a repro loop in Phase 1.
- **`references/cron-trace-debugging.md`** — concrete cron-output fingerprinting technique: use output file sizes to identify firing patterns before reading code. Includes the 2026-07-17 boundary-bug case study.
- **`references/system-resolution-debugging.md`** — MiniMax/Hermes model-picker investigation: dual code-path trap, picker vs gateway base_url divergence, fallback chain hiding the real provider.

## Related Skills

**Overlap note:** `systematic-debugging` (Superpowers 4-phase) and `debugging-and-error-recovery` (addyosmani) both cover debugging territory. This skill (mattpocock 6-phase) shares the same class but foregrounds the feedback-loop construction as the primary discipline. Use whichever matches the team's methodology; the feedback-loop reference file here is useful alongside any of them.
- **`test-driven-development`** — RED-GREEN-REFACTOR discipline for regression tests
- **`spike`** — Throwaway experiments to validate hypotheses
- **`plan`** — Structured task breakdown for multi-phase investigations
