# Reconnect-storm controller and runtime-boundary pattern

**Observed class:** Baileys/WhatsApp WebSocket close storms where one upstream disconnect becomes many overlapping `startSocket()` calls.

## Reproduction signature

- `connection.update` handles `close`.
- Every close calls `setTimeout(startSocket, ...)` directly.
- There is no single-flight lock, pending-timer deduplication, socket-generation token, or backoff.
- The result is repeated 405/503 closures and misleading availability: the Node HTTP process can be alive while WhatsApp transport is disconnected.

## Minimal implementation pattern

Use a small controller independent of Baileys:

1. `request(reason)` returns false when a retry is already scheduled or startup is in flight.
2. Schedule retries with exponential backoff plus bounded jitter.
3. Keep an incrementing generation for each startup; event handlers must ignore generations that are no longer current.
4. On startup rejection, schedule the next retry after the current attempt completes.
5. On `connection === "open"`, reset the attempt counter.
6. Keep the controller testable with injected timer/random functions; tests must not load Baileys or touch session credentials.

## Required regression checks

The isolated test should prove all of these:

- Three rapid close requests produce one pending timer.
- A completed retry permits a later retry.
- A failed startup schedules the next retry with the next backoff interval.
- A successful connection resets the attempt counter.
- Existing send-queue tests still pass.

A fake-timer test harness must exclude timers that already ran (`!cancelled && !ran`) when counting pending retries. Otherwise the test can falsely report duplicate timers.

## Candidate versus live evidence

Track these separately:

| Layer | Evidence | What it proves |
|---|---|---|
| Candidate | `node --check`, isolated regression output | Candidate syntax/logic only |
| Filesystem | source SHA-256 | Candidate file identity |
| Runtime | `/health` `scriptHash` | Which source the running bridge loaded |
| Delivery | HTTP send result + destination receipt/reply | User-visible transport behavior |
| Stability | repeated health probes + quiet bridge log window | Short-window stability only |

Do not call the fix live when the candidate SHA/hash differs from `/health.scriptHash`. Do not call delivery recovered from health alone. A controlled reload is a separate side-effect step and must be followed by fresh runtime and destination-side verification.

## Session evidence (29 Jul 2026)

- Existing process remained connected while candidate code was edited.
- Candidate tests passed: reconnect-controller regression tests and existing send-queue tests.
- Candidate `bridge.js` hash: `cac5bff6ed6e7c14cc3b62558287aefffd8c09f4e7b1dd8144b1fb48b002e057`.
- Running `/health` still reported `scriptHash: c292ba0c6549a809`, proving the candidate had not yet been loaded.
- Therefore the correct status was **candidate implementation tested; live behavior unverified**, not “fixed.”
