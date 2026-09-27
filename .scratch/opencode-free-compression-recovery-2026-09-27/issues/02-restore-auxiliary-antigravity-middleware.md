# 02 — Restore Auxiliary Antigravity Middleware Route

**What to build:** Restore the SSOT-authoritative auxiliary `llm_execution` middleware path so Antigravity compression is intercepted in-process instead of calling the dummy 127.0.0.1:8765 URL.

**Blocked by:** None — can start in parallel with 01

**Status:** ready-for-agent

- [ ] Add RED regression coverage around `_relay_sync_completion` for `provider=antigravity`.
- [ ] Prove the current live bytes lack the authoritative middleware relay while the reconstructed candidate contains it.
- [ ] Preserve the existing fail-closed middleware hardening; middleware exceptions must not silently bypass to direct HTTP creation.
- [ ] Keep `auxiliary.compression = antigravity / gemini-3.8-flash`.
- [ ] Re-run auxiliary relay, compression, Antigravity plugin, and reconstruction tests.
- [ ] Produce an exact reconstructed candidate; do not patch the live framework checkout by hand.
