# Session Structure Analysis (2026-07-14 Production System)

## Environment
- VPS: Tencent Lighthouse (Singapore), 1.9GB RAM, 2-core
- Bridge: @whiskeysockets/baileys v7.0.0-rc.9
- Session path: ~/.hermes/whatsapp/session/
- Bridge PID: 414126 (at time of analysis)
- Node.js: installed system-wide (no --max-old-space-size flag)

## Disk vs Memory: The Real Story

### Disk (all files)
- Total files: 2,134 JSON + 1 PID
- Total size: 9.4MB
- Average file: ~4.5KB

### Memory (bridge process)
- RSS: 1.04 GB
- Swap: 747 MB
- VSZ: 24 GB (virtual address space — normal for Node.js, not real)
- Node.js heap limit: default ~1.8GB

**Gap:** 9.4MB on disk → 1.04GB in RAM = ~113x multiplication factor.

### Why so much memory?
1. V8 engine baseline: ~30-50MB overhead
2. Baileys internal data structures: each sender-key JSON (100KB on disk) becomes a full JavaScript Map/object with references
3. App-state sync: WhatsApp syncs group metadata, participant lists, messages into in-memory caches
4. Contact list: loaded and kept in memory
5. Message queue: bridges accumulate pending messages in memory
6. Protobuf buffers: encoding/decoding creates temporary objects that V8 may not GC promptly

## Restart Code Flow (from gateway/platforms/whatsapp.py)

### Gateway restart (systemd-driven)
```
systemctl --user restart hermes-gateway
  → WhatsAppAdapter.disconnect() [line 649]
    → self._shutting_down = True
    → _terminate_bridge_process(SIGTERM) [line 658]
    → wait 1s
    → if still alive: _terminate_bridge_process(SIGKILL) [line 664]
    → cancel poll_task
    → close http_session
    → release platform lock
  → systemd re-spawns
  → WhatsAppAdapter.connect() [line 332]
    → check node, check creds.json
    → acquire lock
    → kill stale bridge by PID file
    → kill port 3000 process
    → spawn new bridge process
    → wait for health check (connected or 30s timeout)
    → start poll loop
```

### Bridge crash detection
```
_check_managed_bridge_exit() [line 617]
  → if _bridge_process is None: skip
  → poll() returncode
  → if returncode exists:
    → if _shutting_down AND returncode in {0, -2, -15}: skip (expected)
    → else: set fatal_error "whatsapp_bridge_exited" retryable=True
    → notify user via trigger_notification
```

## Session File Hierarchical Breakdown

```
session/
├── creds.json (2.7KB) — MASTER AUTH, DO NOT DELETE
├── bridge.pid (6B) — PID tracking
├── app-state-sync-*.json (~10 files, mostly small)
│   ├── app-state-sync-key-AAAAAGWq.json (160B)
│   ├── app-state-sync-version-critical_block.json (634B)
│   ├── app-state-sync-version-regular_high.json (766B)
│   └── app-state-sync-version-regular_low.json (1.1KB)
├── sender-key-<group>--<user>_<version>--<index>.json (MANY — bulk of total size)
│   ├── Largest: 357KB (active group)
│   ├── Typical: 20-100KB
│   └── Count: ~2000 files
├── session-<device>_<version>.json (~2 files)
│   ├── Largest: 39KB
│   └── Auth session state per device
├── identity-key-<device>_<version>.json (~3 files, 71B each)
├── lid-mapping-<lid>_reverse.json (MANY — 13-14B each)
├── device-list-<id>.json (~5 files, 5-9B each)
└── pre-key-*.json (may not be present — generated on demand)
```

## Memory Optimization History

At time of writing, no --max-old-space-size was set. The bridge starts without any V8 flags:

```
argv[0]: node
argv[1]: /path/to/bridge.js
argv[2]: --port
argv[3]: 3000
argv[4]: --session
argv[5]: /path/to/session
argv[6]: --mode
argv[7]: bot
```

## Alternative Solutions Quick Reference

### Evolution API Go
- GitHub: github.com/evolution-foundation/evolution-go
- Go + whatsmeow library
- Memory: ~30-50MB (Go's native WhatsApp implementation)
- License required (part of Evolution Foundation ecosystem)
- REST API + webhooks
- Source of this info: GitHub repository (verified 2026-07-14)

### WAHA (WhatsApp HTTP API)
- GitHub: github.com/devlikeapro/waha
- 3 engines: WEBJS (Chromium), NOWEB (Node.js websocket), GOWS (Go)
- GOWS engine memory: ~50-150MB
- Free core, Plus features via Patreon
- REST API + Swagger + Dashboard UI
- MCP server available for AI agent integration
- Source: docs at waha.devlike.pro, verified 2026-07-14

### whatsmeow
- Source: go.mau.fi/whatsmeow
- Pure Go WhatsApp implementation (same protocol as WA internal)
- Memory: ~20-40MB
- Library, not out-of-the-box API — needs wrapper
- MPL 2.0 license

### Wappfly
- Cloud-hosted WhatsApp API
- Free tier available (rate-limited)
- No self-hosting needed
- Verified 2026-07-14 via web search
