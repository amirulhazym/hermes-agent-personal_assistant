# Feedback Loop Construction Techniques

## Core Principle

A feedback loop is a **tight pass/fail signal** for the bug — one that goes red on *this specific bug*. Without one, staring at code won't save you. With one, bisection and hypothesis-testing consume it.

## Construction Techniques (in rough priority order)

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **cURL / HTTP script** against a running dev server.
3. **CLI invocation** with fixture input, diff stdout against known-good snapshot.
4. **Headless browser script** (Playwright) driving UI, asserting DOM/console/network.
5. **Replay captured trace** — save real request/payload/log to disk, replay through code path in isolation.
6. **Throwaway harness** — minimal subset of system (one service, mocked deps) exercising the bug code path.
7. **Property / fuzz loop** — if "sometimes wrong output", run 1000 random inputs looking for failure.
8. **Bisection harness** — automate "boot at state X, check, repeat" for `git bisect run`.
9. **Differential loop** — same input through old vs new versions, diff outputs.
10. **HITL script** — drive a human through structured steps.

## Tightening the Loop

Treat the loop as a product. Once you have *a* loop, tighten it:
- **Faster?** Cache setup, skip unrelated init, narrow test scope.
- **Sharper signal?** Assert on specific symptom, not "didn't crash".
- **More deterministic?** Pin time, seed RNG, isolate filesystem, freeze network.

A 30-second flaky loop is barely better than no loop. A 2-second deterministic one is a debugging superpower.

## Completion Criterion

Phase 1 is done when the loop is:
- [ ] **Red-capable** — asserts the user's exact symptom
- [ ] **Deterministic** — same verdict every run
- [ ] **Fast** — seconds, not minutes
- [ ] **Agent-runnable** — unattended
