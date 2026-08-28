# Candidate Closure and Retry-Ownership Verification

Session-specific reference: 2026-08-12. Use this when a WhatsApp reconnect change crosses the Node bridge, Python adapter, and gateway supervisor.

## What was actually proven in the session

- A pure JavaScript reconnect-controller slice passed with injected timers/randomness. The tested behaviours included one retry timer per controller, one socket generation, stable-open retry reset, stale-generation rejection, budget exhaustion, and retry-ownership handoff signalling.
- The affected Python gateway/WhatsApp tests completed with `47 passed, 2 skipped in 11.07s`.
- Baileys-independent JavaScript suites passed, plus JavaScript syntax checks, Python `compileall`, and `git diff --check`.
- The candidate did **not** contain `node_modules/@whiskeysockets/baileys`. Any native Baileys bridge suite that was not run is `NOT-RUN`, not PASS. Do not borrow the live installation's dependency tree and call that candidate execution.
- The candidate edits were uncommitted at the interruption boundary. Those test results were candidate-working-tree evidence, not final exact-SHA or live-runtime evidence.

## Required closure sequence

1. **Resume audit first.** After compaction, delegation completion, or tool-budget interruption, re-check the candidate worktree, branch, HEAD, status, Git operation sentinels, and direct remote target. Treat summaries and subagent reports as leads only.
2. **Test the pure seam first.** Inject timers, randomness, and socket start/retire functions. Prove one generation and one pending timer before integrating real Baileys objects.
3. **Prove production wiring separately.** Search the actual `bridge.js` for the controller import, construction, startup call, close handler, and every socket-bound listener. A helper and green helper test are not production wiring.
4. **Prove ownership at each boundary.**
   - Bridge: owns transport retry timing, generation tokens, socket retirement, transient close classification, stable-open reset, and health counters.
   - Adapter: owns child-process observation, HTTP polling, cleanup, and machine-readable terminal/crash mapping.
   - Gateway: owns only adapter/process-level retry after the old bridge/adapter has stopped and its retry timer has been cleared.
   - `loggedOut`: terminal/non-retryable; preserve auth files and do not enter the generic retry queue.
5. **Check all listener paths.** `creds.update`, `connection.update`, `messages.update`, and `messages.upsert` must reject stale generations before mutating state or forwarding work. Retire the old socket/listeners before a new generation is active.
6. **Run the boundary matrix.** Cover transient 408/428/503 with bounded jittered backoff, 515 as its separate restart-required class, logged-out terminal handling, unknown-code safety, duplicate close events, startup failure, stable-open reset, retry-budget exhaustion, and no simultaneous bridge/supervisor retries.
7. **Keep evidence layers separate.** `helper-tested` ≠ `bridge-wired` ≠ `adapter-handoff-tested` ≠ `native-dependency-tested` ≠ `process-loaded` ≠ `channel-smoke-proven`.
8. **Invalidate stale evidence.** Any byte edit, fixture edit, target-SHA change, or dependency-boundary change invalidates prior test evidence for the final candidate. Commit first, then rerun the final gates against the exact commit.

## Safe status vocabulary

Use the lowest proven state:

- `DESIGNED`: control flow exists only on paper or in a plan.
- `HELPER-TESTED`: pure controller tests pass.
- `BRIDGE-WIRED`: real bridge call sites and listeners are verified.
- `HANDOFF-TESTED`: adapter/gateway retry ownership is tested.
- `NATIVE-TESTED`: the candidate's own Baileys dependency boundary was exercised.
- `PROCESS-LOADED`: a live process is proven to use the candidate bytes.
- `CHANNEL-SMOKE-PROVEN`: fresh user-visible delivery is observed.
- `RELEASE-COMPLETE`: all required gates are proven.

Never round `HELPER-TESTED` or `TARGETED-PASS` up to `RELEASE-COMPLETE`.
