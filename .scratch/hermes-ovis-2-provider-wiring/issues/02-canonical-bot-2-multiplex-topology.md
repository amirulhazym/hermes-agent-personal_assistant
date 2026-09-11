# 02 — Serve `bot_2` as the canonical multiplexed bot profile

**What to build:** The default multiplex gateway serves `@hermes_ovis_2_bot` through `bot_2`, with one token owner and no competing standalone `bot_2` gateway.

**Blocked by:** 01 — Fail closed on stale or unserved profile routing

**Status:** ready-for-agent

- [ ] The served-profile contract proves `default` + `bot_2` and does not serve the absent `ovis2` profile.
- [ ] The approved runtime config read-back shows `gateway.multiplex_profile_allowlist: [bot_2]` with no secret changes.
- [ ] After the approved reload, root runtime state reports `bot_2:telegram` owned by the default multiplex PID and no standalone token-lock owner remains.
- [ ] The stale `agent:ovis2:telegram:dm:679729206` routing row is preserved as pre-change evidence and is not manually deleted or rewritten without a supported migration path.
- [ ] The runtime report keeps config-on-disk, process-reloaded, token-lock, and channel-E2E statuses separate.
