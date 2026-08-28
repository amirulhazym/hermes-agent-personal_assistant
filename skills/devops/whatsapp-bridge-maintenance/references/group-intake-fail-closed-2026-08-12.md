# Group silent after gateway restart — fail-closed intake policy (2026-08-12)

## Incident

Bot stopped responding in group `<GROUP_JID>` ("Health & Med") after the
2026-08-11 update (gateway restart 14:16:56). User's group confirmations got zero
response; DMs still worked. Earlier investigation had blamed the 428/503 bridge storm
— that was WRONG for the group case. The storm explained the 11/08 DM inbound loss
(16:27 → 12/08 08:58), but the group silence had a separate, deterministic cause.

## Root cause (live-tree verified)

`gateway/platforms/whatsapp_common.py` `_is_group_allowed()` is FAIL-CLOSED since
commit `bb304b4914` ("fix(gateway): fail-closed external-surface defaults",
authored/committed 2026-07-01):

- `group_policy == "pairing"` → `return False` (drop ALL groups)
- `group_policy == "allowlist"` → check `_matches_whatsapp_allowlist(chat_id, _group_allow_from)`
- `group_policy == "open"` → `return True`
- anything else → `False`

`group_policy` default = `"pairing"` (adapter.py L451:
`config.extra.get("group_policy") or _wenv("WHATSAPP_GROUP_POLICY", "pairing")`).

Production config: top-level `whatsapp: {}` (empty, config.yaml L571) + no
`WHATSAPP_GROUP_POLICY` env → default `"pairing"` → ALL group messages dropped at
`_should_process_message()` (whatsapp_common.py L390-422) BEFORE the agent sees them.

DM asymmetry: `_is_dm_intake_allowed()` with `"pairing"` returns `True` (pairing
forwards unknown DMs), so DMs kept flowing while groups were dead.

## Timeline evidence

| Time (MYT) | Event | Evidence |
|---|---|---|
| 11/08 13:57-14:01 | Last group inbound + response | gateway.log |
| 11/08 14:16:56 | Gateway restart (update) | `ps -o lstart`, gateway-starts.log `1786429023.63` |
| 11/08 14:01 → 12/08 09:46 | ZERO group inbound | `grep "inbound message" gateway.log \| grep <jid>` → 0 after 14:01 |
| 12/08 12:19:27 | User DM arrives fine | gateway.log `chat=<GROUP_JID>` |
| 12/08 12:19 | User group test message | never reached gateway — 0 matches |

Why group worked 11/08 13:57 but died at 14:17: the OLD gateway process was still
running pre-fail-closed code; the 14:16 restart loaded the fail-closed default.
The commit was authored 07-01 but the running process had not been restarted since
before it took effect — restart-time loading is what activates policy changes.

## Diagnostic recipe (reuse)

1. `search_files pattern='2026-08-1[12] .*<group-jid>' path=logs/gateway.log` — expect
   only pre-restart lines.
2. `grep "inbound message" logs/gateway.log | tail` — DMs still arriving = asymmetry.
3. Read `gateway/platforms/whatsapp_common.py` `_is_group_allowed()` + `_should_process_message()`.
4. Config check: `whatsapp:` top-level block in config.yaml + `WHATSAPP_GROUP_POLICY` in .env.
5. `git log -L 279,290:gateway/platforms/whatsapp_common.py` — date the fail-closed change.
6. Cross-check restart time: `gateway-starts.log` (epoch seconds) + `ps -o lstart` of gateway PID.

## Fix (CORRECTED same-day evening — the original `extra:`-only shape was WRONG)

The first attempt used `whatsapp.extra.group_policy` only → restart 22:33 → group
STILL dropped; `/proc/<gw-pid>/environ` showed ZERO `WHATSAPP_*` vars (env bridge
never fired). Verified-working shape (restart 22:45 → group inbound appears;
matches upstream test `tests/gateway/test_whatsapp_group_gating.py` L158-183):

```yaml
whatsapp:
  enabled: true
  group_policy: allowlist
  group_allow_from: ["<GROUP_JID>"]
  extra:
    group_policy: allowlist
    group_allow_from: ["<GROUP_JID>"]
platforms:
  whatsapp:
    extra:
      group_policy: allowlist
      group_allow_from: ["<GROUP_JID>"]
```

Mechanism: `_apply_yaml_config` (adapter.py ~L1860) bridges TOP-LEVEL keys only to
env; `_merge_platform_map` (config.py ~L1445) copies the `platforms:` section into
`config.extra`; shared-key loop (config.py ~L1634) skips a block without `enabled`.
`WHATSAPP_GROUP_ALLOWED_USERS` env is echoed to the bridge subprocess only (adapter
L699) — it is NOT read by `_is_group_allowed` (uses `config.extra`, adapter L452).

Requires gateway restart (config read at adapter construction). `allowlist` > `open`.
Verify: real group message → gateway.log shows `inbound message ... chat=<jid>@g.us`.

## Pitfalls

- Do NOT assume "group silent" = transport/bridge problem. Check the intake policy
  gate BEFORE blaming 428/503 storms. Both can coexist (they did here).
- The bridge.log has 0 group-send matches for the storm window — that's consistent
  with BOTH explanations; log absence alone proves neither. Policy gate is proven by
  reading the code path, not by log greps.
- `bridge.log` stopping writes at 09:47 does NOT mean bridge dead — `emitDebugEvent`
  only logs when `WHATSAPP_DEBUG` is set; a live bridge with debug off logs nothing
  per-message. Confirm liveness via `/proc/<pid>/fd` or a DM that still arrives.
- Old `rate-overlimit` entries in bridge.log for the group (July, pid 1178352) are
  outbound send failures, not current inbound evidence — date-anchor every grep.
