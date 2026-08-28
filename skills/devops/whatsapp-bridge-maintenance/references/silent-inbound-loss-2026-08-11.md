# Silent inbound loss: 2026-08-11/12 bridge reconnect storm

Incident: med confirmation messages never reached the gateway for ~16.5h
(11 Aug 16:27 → 12 Aug 08:58 MYT) while no_agent cron reminders kept
delivering. User saw "reminders keep nagging after I confirmed" and concluded
the agent was ignoring him / behaviour had changed.

## Evidence chain used to localize the failure layer

1. **gateway.log inbound gap** (transport check — do FIRST):
   `grep "inbound message: platform=whatsapp" gateway.log | tail`
   Last inbound 11/08 16:27 ("go"), next 12/08 08:58 ("Bro u ok?"). Every
   user message in between (6+ med confirmations) never arrived.
2. **med-status.json**: no entries for 12/08; D/E slots 11/08 absent — the med
   state was never written because the confirmations never arrived.
3. **med-auto-confirm-audit.log**: last event 11/08 19:16 — the auto-confirm
   hook never saw the messages either (consistent with transport loss).
4. **bridge.log reconnect storm**:
   - 11/08 ~01:25–05:26: repeated 428 + "AwaitingInitialSync" timeouts
   - 11/08 14:18 gateway restart → bridge respawned 15:34 → immediately into
     "Connection closed (reason: 428). Reconnecting in 3s..." bursts
   - 12/08 04:43: 503 stream error
   A fresh bridge process inherited the storm — restart alone is not recovery.

## Log fingerprints

- bridge.log timestamps are **ms epochs**; convert before aligning to wall
  clock: `python3 -c "import datetime; print(datetime.datetime.fromtimestamp(1786480998))"`
- "Job 'xxx' (no_agent): delivered to whatsapp:..." during the gap proves only
  the send queue works, NOT bridge health.
- Repeated "Timeout in AwaitingInitialSync, forcing state to Online and
  flushing buffer" = initial sync never completes; inbound can be silently
  dropped while the process stays "connected".

## Rule

When a user says "I confirmed / I replied but you ignored me": grep the
inbound log FIRST. If the message is absent from gateway.log, nothing
downstream (parser, hook, state, scheduler) could have acted on it — the
failure is at the transport layer. Debugging regex/state logic in that
situation wastes time and misattributes the cause.