# /status vs /model Divergence After Gateway Restart

Found 2026-07-15 during google-workspace plugin activation session.

## The Scenario

1. User types `/model` → shows `deepseek-v4-flash-free (opencode-zen)` — FREE model
2. User types `/status` → shows `deepseek-v4-pro (opencode-go)` — PAID model (DIFFERENT)
3. Config.yaml model.default = `deepseek-v4-flash-free` with provider `opencode-zen`

## Root Cause

After gateway restart, the NEW session inherits model state from `chain-state.json` rather than re-reading config.yaml cleanly. The chain-state is NEVER invalidated on gateway restart — it persists the post-fallback model from the previous session.

This means:
- **/status** reads session DB model column → populated by COALESCE(model, ?) in update_token_counts() after first successful API call → shows the FALLBACK model from the PREVIOUS session, NOT the configured default
- **/model** reads config.yaml model.default → shows the configured intended model
- **Actual API calls** use whatever the session-scoped model resolves to — may differ from BOTH

## Why This Is Dangerous

The user has THREE potentially different model sources and NO single authoritative source:

| Source | What it shows | When it's right |
|--------|--------------|-----------------|
| config.yaml model.default | Intended model | Always the configured default |
| /status (session DB) | Model from PREVIOUS session's first API call | Misleading after restart |
| /model CLI | Resolved model chain | Correct default, but not necessarily the runtime model |

A PAID model (deepseek-v4-pro) can show in /status while the user believes they're on a FREE model (deepseek-v4-flash-free). This can silently burn API credits if the session-scoped model routes to the paid endpoint.

## How to Diagnose

```python
# 1. Check configured default
grep -A3 'model:' ~/.hermes/config.yaml | head -6

# 2. Check session DB (what /status shows)
sqlite3 ~/.hermes/state.db "SELECT id, model, source, started_at FROM sessions ORDER BY started_at DESC LIMIT 3;"

# 3. Check actual API calls
grep 'API call' ~/.hermes/logs/agent.log | tail -5

# 4. Check chain-state (persist post-fallback model)
python3 -c "import json; cs=json.load(open('/home/ubuntu/.hermes/chain-state.json')); print(cs.get('model'), cs.get('provider'))"

# 5. Check fallback history
grep 'Fallback activated' ~/.hermes/logs/gateway.log | tail -3
```

## Fix Considerations

- Clearing chain-state.json on graceful gateway shutdown would fix the stale-model inheritance
- Or: making /status validate its model against config.yaml before displaying
- Or: adding a visible warning to /status output when model != config default

Not yet fixed as of 2026-07-15 — this document tracks the gap for future work.
