# WhatsApp Bridge — Troubleshooting Guide

## Architecture

The WhatsApp bridge runs as a child process of the Hermes gateway:
```
hermes-gateway.service (systemd user service)
  └─ python -m hermes_cli.main gateway run
       └─ node bridge.js --port 3000 --session ... --mode bot
            └─ @whiskeysockets/baileys (WhatsApp Web library)
```

Bridge location: `~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js`
Logs: `~/.hermes/whatsapp/bridge.log`

## Common Issues

### 1. `ERR_MODULE_NOT_FOUND: Cannot find package 'link-preview-js'`

**Symptom:** Every message with a URL triggers logged errors and the bridge may reconnect repeatedly (reason 428).

**Log entry:**
```
{"level":40, "msg":"url generation failed", "trace":"Error [ERR_MODULE_NOT_FOUND]:
 Cannot find package 'link-preview-js' imported from .../baileys/lib/Utils/link-preview.js"}
```

**Root cause:** `link-preview-js` is an optional dependency of `@whiskeysockets/baileys`. When `npm install` runs, npm may skip optional deps if the download fails or if npm is configured with `--no-optional`. The package ends up in `package-lock.json` (declared) but not in `node_modules/` (missing binary).

**Fix:**
```bash
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
npm install link-preview-js
```

This forces npm to download the package even though it's already listed in the lockfile.

**Verification:**
```bash
node -e "require('link-preview-js')"  # Should resolve without error
ls node_modules/link-preview-js/       # Should show build/ package.json LICENSE
```

After fixing, restart the bridge process:
```bash
kill $(ps aux | grep "bridge.js" | grep -v grep | awk '{print $2}')
```
Gateway will auto-restart the bridge.

### 2. Reconnect Loop (reason 428)

**Symptom:** Log shows repeated "Connection closed (reason: 428). Reconnecting in 3s...", potentially multiple times per hour.

**Causes:**
1. **Missing `link-preview-js`** — URL processing fails, message handling crashes, Baileys drops connection → loop
2. **Session state corruption** — After multiple reconnections, local session state gets corrupted, each reconnect fails
3. **WhatsApp rate limiting** — Too many reconnects triggers server-side throttling

**Diagnostic:**
```bash
grep -c "Reconnecting\|Connection closed" ~/.hermes/whatsapp/bridge.log
```

**Fix pattern:**
1. Fix `link-preview-js` first (Issue #1 above)
2. Restart the bridge to get a clean session:
   ```bash
   kill $(ps aux | grep "bridge.js" | grep -v grep | awk '{print $2}')
   ```
3. If still looping after 15+ minutes, clear session state:
   ```bash
   rm -rf ~/.hermes/whatsapp/session
   systemctl --user restart hermes-gateway
   ```
   (This will require re-scanning the WhatsApp QR code)

### 3. Bridge Not Starting

**Symptom:** No bridge.js process, or bridge exits immediately after start.

**Check:**
```bash
# Is the process running?
ps aux | grep "bridge.js" | grep -v grep

# Any startup errors in log?
tail -20 ~/.hermes/whatsapp/bridge.log

# Check if gateway is healthy
systemctl --user status hermes-gateway | head -10
```

**Common causes:**
- Port 3000 already in use: `lsof -i :3000`
- Missing credentials/config
- Invalid session state

### 4. `AwaitingInitialSync timeout`

**Symptom:** Log entry `"Timeout in AwaitingInitialSync, forcing state to Online and flushing buffer"`

**Normal behaviour** on fresh start or after reconnect. Baileys attempts to sync message history, times out, and falls back to Online mode. Not an error — the bridge functions normally afterward.

## Bridge Health Check

```bash
echo "=== Bridge process ==="
ps aux | grep "bridge.js" | grep -v grep
echo ""
echo "=== Recent log ==="
tail -10 ~/.hermes/whatsapp/bridge.log
echo ""
echo "=== Reconnect count (24h) ==="
grep -c "Reconnecting" ~/.hermes/whatsapp/bridge.log
echo ""
echo "=== link-preview errors (24h) ==="
grep -c "link-preview" ~/.hermes/whatsapp/bridge.log
```

## Key Files

| Path | Purpose |
|---|---|
| `~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js` | Bridge entry point |
| `~/.hermes/hermes-agent/scripts/whatsapp-bridge/node_modules/` | Installed dependencies |
| `~/.hermes/whatsapp/bridge.log` | Runtime log (append-only) |
| `~/.hermes/whatsapp/session/` | WhatsApp session state (QR auth) |
| `~/.hermes/hermes-agent/scripts/whatsapp-bridge/package.json` | Dependency declarations |
