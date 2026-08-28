# Session Resume Lineage and Title Verification

## Trigger

Use when a user asks which chat session is active, asks to resume a specific session, or reports that `/resume` says `Already on session ...` while `/status` shows a different title or ID.

## Verified failure pattern

A requested session ID may be an ancestor. Hermes can resolve it to the latest descendant continuation before checking whether the current route is already there. The confirmation may still echo the user's original ID, while `/status` reads the effective descendant session. A search/UI title may be generated from content and need not equal the stored `sessions.title`.

## Read-only verification sequence

1. Inspect the requested row in `sessions`:
   - `id`, `parent_session_id`, `title`, `title_source`
   - `end_reason`, `started_at`, `ended_at`
   - `source`, `session_key`, `chat_id`, `thread_id`
2. Inspect `gateway_routing` for the active `(scope, session_key)` and parse `entry_json.session_id`. This is the live route used by `/status`.
3. Walk the parent/child chain to the effective tip. Mark separately:
   - requested ID;
   - resolved/effective ID;
   - live routing ID;
   - stored title;
   - search/UI display label.
4. Locate the exact target content by session ID and message ID. If it lives in a descendant, report that descendant explicitly.
5. Do not rename, repair routing, edit `state.db`, or force a session switch merely to make titles match without explicit approval.

## Evidence format

```text
Requested: <ancestor ID>
Resolved/effective: <tip ID>
Live routing: <gateway_routing entry_json.session_id>
Stored title: <sessions.title or NULL>
Display label: <search/UI label, if any>
Content located at: <session ID>, message <ID>
```

## Hermes-specific source check

Current gateway `/resume` behavior calls `resolve_resume_session_id()` before comparing against the current session. The “already on” response can interpolate the original argument rather than the resolved tip. Verify the live source before calling this a bug, because implementations may change.

## Incident record (2026-08-12)

Read-only DB evidence showed:

```text
20260811_190404_b8f21a  title=NULL, end_reason=compression
  -> 20260811_191501_990b01  title="Hermes Integration Reconciliation Review #204", contains the final A4/A5 audit block (message 90892)
  -> 20260812_004652_1e77848c  title="Resume session and run regression tests", current gateway routing session
```

The reply `Already on session 20260811_190404_b8f21a` referred to the requested ancestor, not the effective current child. The earlier label `Hermes Integration Reconciliation Review` came from session-search display and was incorrectly treated as the canonical stored title. No state/config/source write was required to diagnose the mismatch.
