# 405/503 Reconnect Storm Case Study — 2026-07-29

## Scope
Read-only investigation of Hermes WhatsApp bridge and independent health monitor. No restart, session deletion, or source modification was performed.

## Proven local evidence

- `/health` repeatedly returned `{"status":"disconnected"}` while the gateway service and Node bridge process were alive.
- Bridge source used a global `sock` and, on every `connection === 'close'`, set `connectionState = 'disconnected'` then called `setTimeout(startSocket, 3000)`. No single-flight reconnect guard or socket-generation ownership was present.
- Installed Baileys: `@whiskeysockets/baileys` `7.0.0-rc.9`, package-lock pinned to commit `01047de...`.
- Baileys local source mapped WebSocket text `Unexpected server response: N` to status `N`; its named `DisconnectReason` enum did not include 405.

## Timeline

```text
05:40:34  stream 503 -> close 503 -> connected
05:50:38  stream 503 -> close 503 + close 405 -> connected
05:53:12  stream 503 -> close 503 -> connected
05:55:39  stream 503 -> close 503 + close 405 -> connected
05:59:44  stream 503 -> close 503 + two close 405 -> connected
06:05:32  stream 503 + five close 405; no later successful open in the captured window
```

The log reached roughly 43–51 close-405 events per five-minute bucket, proving a reconnect storm rather than a single normal retry.

## Separate monitor false-positive

The monitored cron job was `*/15 5-22 * * *`. Previous output was `22:45:37`; the health monitor ran at `05:00:01`; the first new job output was written at `05:00:41`. The monitor therefore reported the old output as 374 minutes old before the expected run had completed. The earlier 344-minute alert had the same boundary shape. The correct algorithm needs previous/next occurrence plus a post-run grace period.

## Unknowns that must remain explicit

The local evidence does not prove whether the upstream 405 trigger was stale WA version, session/device registration rejection, upstream policy/rate limiting, or an interaction with the reconnect storm. No 401/440/403/515 evidence was present in the relevant sequence; do not infer logout or delete credentials solely from 405.

## Durable resolution pattern

1. Controlled restart to clear overlapping sockets.
2. Verify `/health`, real delivery, and a quiet reconnect log window.
3. If persistent, backed-up session/linked-device investigation and explicit re-pair.
4. Permanent single-flight reconnect + generation token + bounded exponential backoff + structured error/version logging.
5. Health monitor must distinguish cron execution, transport delivery, and destination receipt.
