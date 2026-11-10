# P2 — hybrid-web Playwright driver leak: root cause + source fix (2026-11-10)

Follow-up to `docs/reconciliation/health-monitor-p1-2026-11-07.md` (P0 reaped 17
leaked `run-driver` processes; P1 hardened the health monitor). This record
covers **P2 only** — the source-level leak fix. P3 (dashboard / RDC / VPS
upgrade) remains an owner decision and was not touched.

## Root cause (LIVE-VERIFIED + reproduced)

Two independent defects in `plugins/hybrid-web/provider.py`:

1. **No Playwright browser build on the host.** `~/.cache/ms-playwright` does
   not exist, so every `chromium.launch()` with the default channel raises
   `Executable doesn't exist at .../chromium_headless_shell-1228/...`.
   Consequence: *every* SPA extraction routed to crawl4ai has been failing
   since the Playwright 1.61.0 upgrade, silently returning "extraction failed".
   System Chrome is available at `/usr/bin/google-chrome`.

2. **crawl4ai leaks its Playwright node driver when the launch raises.**
   `AsyncWebCrawler.__aexit__` does not stop the Playwright client on that
   path, so the driver (`playwright/driver/package/cli.js run-driver`) survives
   as a **direct child of the gateway**, childless, sleeping, ~135 MB RSS and
   pinning swap. This is exactly the P0 signature (PPID=1210, 0 children,
   gateway holding both pipe ends).

Reproduction (isolated process, local HTTP page, no gateway involved):

| Path | Result | Leaked drivers |
|---|---|---|
| Old code, crawl4ai, no browser installed | launch fails | **1 × 135 MB RSS** |
| Old code, `_extract_with_playwright` | launch fails, `with sync_playwright()` | 0 |
| crawl4ai with `chrome_channel="chrome"` (system Chrome) | extraction OK | 0 |
| New code, crawl4ai success path | extraction OK | 0 |
| New code, forced launch failure | failure handled | 0 (reaped) |

Repro harness: `/tmp/p2/repro.py`, `/tmp/p2/verify_fix.py` (ephemeral, not
committed).

## Fix

`plugins/hybrid-web/provider.py`

- `CHROME_CHANNEL_CANDIDATES = ("chrome", None)` — use the system Chrome
  channel first (zero download, zero extra disk), fall back to a bundled build
  on hosts that have one. Applied to both the crawl4ai path
  (`BrowserConfig(chrome_channel=...)`) and the direct Playwright fallback
  (`chromium.launch(channel=...)`).
- `_child_playwright_drivers()` — enumerate `/proc` for `run-driver` children
  of the current process (no subprocess, ~ms).
- `_reap_new_drivers(before, grace_s)` — SIGTERM only drivers **created by the
  current attempt** and **childless** (a driver that still owns a browser
  process belongs to a live extraction). Polls briefly because the driver can
  register just after the exception surfaces; SIGKILL only stragglers after 2s.
- Reaping runs in three places: inside the running loop on exception, after the
  loop closes, and as a single non-blocking scan on the happy path
  (`grace_s=0.0`, no added latency).

## Tests

`tests/plugins/test_hybrid_web_provider.py` — 7 hermetic tests (fake `/proc`,
monkeypatched reaper, no browser, no network). `7 passed in 0.27s`.

Live E2E (isolated process, SPA page with `__NEXT_DATA__`): content extracted
via crawl4ai **and** `LEAKED_DRIVERS=0`; forced-failure run reaps 1 and ends
with `LEAKED_DRIVERS=0`.

## Not done (owner-gated)

- Deploy to `/home/ubuntu/.hermes/plugins/hybrid-web/provider.py` + manifest
  hash update — requires a gateway restart to load the new module. Not
  performed from inside an active session.
- P3 baseline reduction.
- Push of this commit and of P1 `a0ab892572` — requires `APPROVE RELEASE <sha>`.

## Deploy — 2026-11-10 15:37 MYT (owner-approved, file stage only)

Owner: "proceed with gate 1 dulu, approve".

| Item | Value |
|---|---|
| Backup | `~/.hermes/plugins/hybrid-web/provider.py.bak.p2-20261110-1537` (sha `1cb5e6f4c36c…`) |
| Live after copy | `~/.hermes/plugins/hybrid-web/provider.py` (sha `9a86f6b7978a…`) |
| Source | `plugins/hybrid-web/provider.py` (sha `9a86f6b7978a…`) |
| `cmp` | identical |
| `py_compile` | OK |
| Manifest | `v3-source-coverage-manifest.json` entry updated `1cb5e6f4→9a86f6b7` |

Rollback: `cp ~/.hermes/plugins/hybrid-web/provider.py.bak.p2-20261110-1537
~/.hermes/plugins/hybrid-web/provider.py` then restart the gateway.

**Still pending at time of writing:** gateway restart
(`systemctl --user restart hermes-gateway.service`, owner-run from SSH —
not executable from inside the gateway process). Until that restart the
running process (PID 1210) keeps the old module in memory.

