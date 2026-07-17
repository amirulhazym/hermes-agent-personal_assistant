# PX-1b Findings Log

> Final for 2026-07-17 RC after L4 bridge + 20/20 acceptance.

## Closed

- Live L1–L3 wiring on VPS (browser + search/extract)
- Telegram `/browse` slash alias fix
- WhatsApp + Telegram live public browse
- Outbound PC bridge (SSH mailbox, signed grants, cua-driver named-app)
- Wrong-app fail-closed, offline postpone
- Acceptance suite **20/20 PASS**
- Unit tests **37 OK** on VPS (crypto present)

## Residual / ops notes (not blockers for 20/20)

1. Formal Research Expert chat package/trace path still intermittent (PX-1 residual).
2. Keep Hermes **v0.17.0** (no silent upgrade).
3. `computer_use.enabled` remains **false** in Hermes config — project bridge is separate; do not claim native Hermes MCP CUA.
4. PC worker must be running (or `Run` loop) for L4; offline correctly postpones.
5. Install free `cryptography` on PC Python for signed grants (done this session).
6. Production L3 concurrency stays **1** on ~1.9 GiB RAM.
7. Native browser has no download/upload tools — project quarantine adapters used.

## Status

**PX-1b formal acceptance: 20/20 PASS (2026-07-17).**  
Package + live phone paths + L4 bridge validated.
