# Exact vs effective `/resume` target — 2026-08-17 incident

## Trigger
Telegram DM `/resume <ancestor-id>` returned `Already on <ancestor-id>`, but the next user turn still used the current-day child. The user meant **enter the exact stored chat/session**, not merely continue the effective lineage.

## Verified incident shape

- Requested ancestor: `20260816_165131_62990a`
- Auto-reset child: `20260817_091858_68a7f428`
- Gateway key: `agent:main:telegram:dm:679729206`
- Durable `gateway_routing` and legacy `sessions.json` both pointed to the child after recovery.
- The follow-up test message and response were persisted under the child.
- The acknowledgement echoed the original argument, so it did not prove that the requested ancestor was the effective route.

Raw evidence at the time:

- Gateway log: `/home/ubuntu/.hermes/logs/gateway.log` lines `20592–20602`.
- Resolver/source: `gateway/slash_commands.py` lines `4591–4620`; `hermes_state.py` lines `8566–8653`.
- Existing resolver tests: `tests/hermes_state/test_resolve_resume_session_id.py` lines `53–99`.

The live DB changed while the investigation continued; message counts and end-state are therefore timestamped moving snapshots, not immutable incident facts.

## Root cause

`_handle_resume_command()` first calls `resolve_resume_session_id(target_id)`. The resolver has two relevant phases:

1. `get_compression_tip()` — compression-aware lineage handling.
2. A later generic child walk using `parent_session_id`, excluding branch/delegate/tool children but not necessarily requiring `end_reason='compression'`.

If the requested ancestor has a message-bearing `session_reset`/`session_switch` child, phase 2 can select that child. The handler then compares the current route to the **resolved child**, returns `Already on ...`, and formats the message with the original user argument. This produces a false-looking exact-resume acknowledgement even when the parent was not reopened.

## Read-only reproduction

1. Capture `requested_id`, `gateway_routing.entry_json.session_id`, and all `sessions` rows where `id = requested_id OR parent_session_id = requested_id`.
2. Record `parent_session_id`, `end_reason`, `started_at`, and active message counts.
3. Read the full `resolve_resume_session_id()` implementation; do not stop after `get_compression_tip()`.
4. Reproduce the later child selection from a read-only DB snapshot and record:

```text
requested_id → resolver_result → current_routing_id → test_message.session_id
```

5. Classify separately:

- `EXACT PARENT ENTERED` — all stages remain the requested ID;
- `ALREADY ON EFFECTIVE CHILD` — resolver and route agree on a descendant;
- `ACK MISLEADING` — displayed ID is original input but effective ID differs;
- `NOT SWITCHED` — no route mutation or supported exact mode occurred.

## Fix boundary

Do not remove descendant resolution blindly: existing compression-resume behavior and tests depend on it. A durable exact-session feature needs an explicit semantic boundary (for example an exact/no-follow mode) or a carefully specified change to which child types the default resolver follows. The acknowledgement must expose both requested and effective IDs when they differ.

Do not claim an exact switch from session discovery, `session_search`, a CLI listing, or a direct DB read. Do not mutate live `state.db` or restart an active gateway as an unapproved workaround; verify the source-level behavior and the supported gateway switch path first.
