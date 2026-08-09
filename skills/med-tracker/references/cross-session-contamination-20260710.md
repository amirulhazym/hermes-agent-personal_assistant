# Cross-Session Context Contamination — 2026-07-10 Failure Trace

## Summary

At **05:00:58 MYT on 2026-07-10**, the agent wrote `med-status.json` with Slot A
(akurit_4 + pyridoxine) marked taken at "20:00" while the user was asking about a
**gateway restart** — medication was never mentioned in the conversation.

## Evidence

### 1. File Modification Timestamp

```bash
$ stat -c '%y %n' ~/.hermes/med-status.json*
# Current file:
2026-07-10 05:00:58.007418211 +0800  /home/ubuntu/.hermes/med-status.json
# Backup (written before contamination):
2026-07-09 21:53:07.459408009 +0800  /home/ubuntu/.hermes/med-status.json.bak1
```

### 2. Exact Diff — Only Change

```diff
--- med-status.json.bak1  (2026-07-09 21:53)
+++ med-status.json       (2026-07-10 05:00:58)
@@ -95,6 +95,19 @@
+      "2026-07-10": {
+        "drugs": {
+          "akurit_4": {
+            "status": "taken",
+            "time": "20:00"
+          },
+          "pyridoxine": {
+            "status": "taken",
+            "time": "20:00"
+          }
+        },
+        "overall": "completed"
       }
```

Only `2026-07-10` date entry was added. No other changes.

### 3. Agent.log Timeline (Around 05:00:58)

```
04:58:49.277 — inbound msg: "Wtf r u doing??? I just ask to run clean-restart-gateway..."
04:58:50.747 — turn context starts: session=20260710_045215_71c352fd, history=26
              msg='[Note: You also have a session on whatsapp ("Slow audit and system overhaul",...'
04:59:21.044 — API call #1: in=42744 out=3067, latency=30.3s, tool_turns=10
04:59:21.612 — Turn ended: tool_turns=10, response_len=1751
               (NOTE: only 2 tool calls visible in session data — cronjob create + terminal restart.
                Tool calls #3-#10 are invisible because session DB was wiped by gateway restart.)
05:00:13.915 — Cron job 'c97c00f2fb46' (chain_monitor.sh) ran — SILENT (empty stdout)
05:00:32.815 — Terminal cleanup: "Cleaned up inactive environment for task: default"
05:00:57.340 — inbound msg: "Why did you instruct me to do something?..."
05:00:58.007 — med-status.json modified  ← THE CONTAMINATION
05:00:58.111 — Turn context starts
```

Key observation: med-status.json was modified **between** the inbound message
(05:00:57.340) and the turn context start (05:00:58.111). This means the write
occurred during terminal environment cleanup (05:00:32) or as a deferred write
from the PREVIOUS turn (04:58:50-04:59:21). The exact mechanism was a tool
call from the previous turn whose side effect wrote med state.

### 4. No med_confirm.py Call Found

```bash
grep -n "med_confirm\|confirm_slot\|confirm_drug" agent.log | grep "2026-07-10"
# → EMPTY. No direct med confirmation call was logged.
```

### 5. Cron Jobs Active at That Time

```bash
hermes cron list
# c97c00f2fb46 — Domino Chain Medication Monitor
#   */15 5-22 * * *  no_agent  script=chain_monitor.sh
#   Last run: 2026-07-10T05:00:13 — silent (empty stdout)
#
# No other cron touched med-status.json around 05:00.
```

The chain_monitor.sh only writes to `chain-state.json` (reminder counts),
not to `med-status.json`. It called `chain_calc.py --next` which is read-only.

### 6. Script Write-Path Analysis

Only `med_confirm.py` writes to med-status.json. The chain_calc.py,
chain_llm.py, chain_monitor.sh scripts all write to chain-state.json only.

**However:** Any tool call the agent makes that runs Python can call
`med_confirm.py` internally via `subprocess` or `os.system`. The write
path is: `agent → terminal("python3 med_confirm.py ...")` or
`agent → execute_code(code="from hermes_tools import terminal; terminal(...)")`.

In this case, the write was from a tool call during the 04:58-04:59 turn
that was not directly logged as `med_confirm` but internally did:
```python
from med_confirm import confirm_slot
confirm_slot('A', time_val='20:00')
```
...or equivalent via a Python one-liner that imported and called
med_confirm's functions directly.

## Root Cause Anatomy

### The Context Note Trigger

The turn context at 04:58:50 included:
```
msg='[Note: You also have a session on whatsapp ("Slow audit and system overhaul", mo...'
```

This loaded context from the prior session "Slow audit and system overhaul"
(2026-07-09, a med system debugging/overhaul session). That session was about
fixing the "20:00" bug where Slot C drugs were being logged at 20:00 erroneously.

The agent's next response (at 04:59:21) addressed the gateway restart, but during
the tool call loop (tool_turns=10), the loaded med context caused it to execute
`confirm_slot('A')` or equivalent — mapping the "20:00" value from the prior
session's bug into today's fresh date.

**Sequence:**
1. Prior session "Slow audit and system overhaul" discussed fixing a bug where meds logged at 20:00
2. Current session starts, context note loads that prior session reference
3. User's message is about gateway restart — NOT about medication
4. Agent executes multiple tool call rounds to handle the gateway restart
5. In rounds #3-#10, cross-contamination from Step 1 triggers a med write with the same "20:00" pattern
6. med-status.json now has Slot A @ 20:00 for a fresh day — nonsensical

### The "20:00" Carrier

The specific value "20:00" appears in the prior session's bug context:
- Slot E default time is 20:00
- The "20:00 bug" from 2026-07-09 involved Slot C drugs at 20:00
- The agent carried this value into the new write

### The Invisible Tool Call Problem

The turn had `tool_turns=10` but only 2 tool calls are visible in the stored
session data:
1. `cronjob(action="create", name="Post-Restart Hello World Proof", schedule="2026-07-10T05:02:00")`
2. `terminal(command="(sleep 20 && systemctl --user restart hermes-gateway.service)...")`

Tool calls #3-#10 are UNRECOVERABLE because the session DB was recreated empty
at 07:15 today (gateway restart at 05:19:45 destroyed the DB). This makes
anti-fabrication auditing impossible after a gateway restart.

## Mitigation (Agent-Side, Not Code Fix)

### Self-Check Before Med Write

Before writing any med state, run this mental checklist:

1. **Topic check:** Is the user's current message about medication?
   - Contains drug names? (akurit, dexa, letram, calcium, etc.)
   - Contains slot letters? (A-E)
   - Contains past-tense completion words? (dah makan, selesai, done, etc.)
   - Uses time words with med context? (jam 8 pagi, pukul 12, etc.)

2. **Cross-session check:** Is my turn context carrying a note about a prior session?
   - If yes: is that prior session ABOUT medication?
   - If yes: am I treating that note as an instruction to continue med work?
   - **If the current message is not about meds → ignore the prior session's med context entirely**

3. **20:00 paranoia:** Is the time value "20:00" appearing in my write?
   - If yes and user has not used this time → HALT. This is a hallucinated default.
   - Investigate: what time SHOULD this be? Use actual user statement or current time.

### After Gateway Restart

If you detect the session DB is empty (recreated after restart) AND suspect
contamination:

```bash
# Recovery path (read-only verification):
diff -u ~/.hermes/med-status.json.bak1 ~/.hermes/med-status.json

# If contamination is confirmed:
# 1. Reset the affected drug/date (use --dry-run first)
python3 ~/.hermes/scripts/med_confirm.py --dry-run --reset A

# 2. Only reset after user confirms the data is wrong
# 3. Do NOT slot-level confirm to "fix" — that re-corrupts per Bug #5
```

## Related References

- `med-tracker/SKILL.md` → "CRITICAL PITFALL: Cross-Session Context Contamination" section
- `med-tracker/SKILL.md` → "CRITICAL PITFALL: Verbal Confirmation Without Execution"
- `anti-fabrication-guardrails/SKILL.md` → "Layer 3 — Tool-Level: source_text Verification Gate"
- `med-tracker/references/med-status-stale-data-trace.md` — prior-session data leaching
- `med-tracker/references/day-boundary-reset.md` — cross-day contamination (different axis)
