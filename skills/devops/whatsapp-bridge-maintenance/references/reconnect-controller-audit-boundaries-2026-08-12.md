# Reconnect-controller audit boundaries — 2026-08-12

## Current repository truth

Repository: `/home/ubuntu/.hermes/hermes-agent`.

Tracked bridge implementation:

- `scripts/whatsapp-bridge/bridge.js`
- `scripts/whatsapp-bridge/bridge_helpers.js`
- `scripts/whatsapp-bridge/bridge.reconnect.test.mjs`

The repository bridge imports and uses `createReconnectScheduler()` from `bridge_helpers.js`. It does **not** import `reconnect-controller.js`.

Current scheduler behavior:

- `createReconnectScheduler()` catches rejected/synchronous startup failures.
- Each call creates a raw timer with no timer handle, cancellation, or in-flight guard.
- Close handling uses 1 second for reason 515 and 3 seconds for every other reason.
- There is no generation token, stale-socket guard, jitter, cap, stable-open reset, flap state, reason counters, or controller cleanup.

The current pure JS test verifies only startup rejection containment and bounded/cached Baileys version resolution.

## Separate installed artifact warning

`/home/ubuntu/.hermes/scripts/whatsapp-bridge/reconnect-controller.js` and its test exist outside the repository and are not imported by the repository `bridge.js`. They are candidate/historical evidence, not active repository behavior. Never infer that a standalone controller file is deployed without checking import reachability, tracked status, source hash, and the running process's `/health.scriptHash`.

## Retry ownership matrix

| Failure/event | Bridge controller | Python adapter | Gateway watcher |
|---|---:|---:|---:|
| 408 / 428 / 503 transport close | Own retry | Observe health only | Must not queue a second retry |
| 515 restart required | Own distinct restart policy | Observe health only | Must not treat as process crash |
| 401 / loggedOut | Terminal state; preserve auth | Map to non-retryable terminal error | Remove from retry queue |
| bridge process exit | Process is gone; stop controller | Detect child exit and clean resources | Queue one process-level reconnect |
| explicit gateway shutdown | Stop controller and socket | Set shutdown flag before terminating child | Do not reconnect |

The handoff invariant is: no bridge transport retry and gateway/adapter process retry may be active for the same failure at the same time.

## Required controller interface/invariants

Use a pure controller seam with injected timer, clock, and random dependencies. It should provide a small interface such as:

- `request(reason)` — idempotently schedule one retry;
- `startNow(reason)` — begin one attempt if no attempt is active;
- `connected()` — record open and reset only after the stable-open rule;
- `invalidate()` / `isCurrent(generation)` — reject stale socket events;
- `stop()` — clear the one timer, invalidate generation, detach/retire socket, and prevent future retries;
- `state()` — expose generation, timer/in-flight status, attempt, last reason, health, and counters.

MUST ALWAYS:

- have at most one pending reconnect timer;
- have at most one socket creation attempt in flight;
- close/retire the old socket before a replacement becomes current;
- check generation after every awaited startup boundary before installing a socket/listener;
- preserve auth files for all transient/unknown reasons;
- emit machine-readable terminal information for loggedOut.

MUST NEVER:

- let stale socket events mutate current state;
- delete `creds.json` for 408/428/503/515/unknown reasons;
- let adapter health polling schedule a transport retry;
- let a generic `whatsapp_bridge_exited` retryable error represent loggedOut;
- start a replacement bridge before the old bridge/controller has been stopped and cleaned up.

## Health and verification contract

Existing bridge `/health` exposes only `status`, `queueLength`, `uptime`, `scriptHash`, and `sendReadReceipts`. The controller change should add bounded fields for:

- `state`: connecting/connected/degraded/flapping/logged_out;
- `generation`;
- `lastDisconnectReason`;
- `attempt` / `nextRetryAt` or delay;
- total reconnects and per-reason counters;
- flap count and stable-open information.

Verify each layer separately:

1. pure controller tests;
2. bridge syntax/tests;
3. adapter tests for terminal-vs-crash mapping and cleanup;
4. gateway tests for queue ownership and duplicate suppression;
5. candidate source hash vs running `/health.scriptHash`;
6. repeated health probes plus real inbound/outbound delivery and a quiet log window.

A green pure test or a connected HTTP health endpoint alone does not prove stable WhatsApp transport or live deployment.
