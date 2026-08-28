# Case Study: Shell-Row + Self-Listing Quirk (2026-08-24/25, runtime drift)

## Symptom (user-visible, Telegram DM)
1. `/sessions` and `/resume` numbered lists included the conversation the user was currently typing in (titled `session-resume-git`), looking stale/duplicated.
2. Empty "shell" session rows accumulated in the DM lane (32 rows with 0 messages).
3. A "quote your last reply verbatim" request returned a paraphrase-from-memory that didn't match the actual stored message — user caught it ("Wtf... belum settle2 lagi?").

## Root cause chain (verified from live runtime git state)
- Live runtime clone (`~/.hermes/hermes-agent`, branch `main` @ upstream `a31be48030`) had **14 uncommitted modified files** (+789/−211) — an earlier "resume work" experiment edited the gateway in place instead of going through the source-clone → feat branch → PR flow.
- Key drift: `_list_titled_sessions()` in `gateway/slash_commands.py` was rewritten to call
  `current_entry = await self.async_session_store.get_or_create_session(source)` and pass `current_entry.session_id` as `current_session_id` into `query_session_listing`.
- Effect A: `get_or_create_session()` CREATES a row when none is bound for the key at call time → listing path itself minted empty sibling rows.
- Effect B: exclusion then targeted the freshly-minted empty row (newest by started_at), not the live row holding messages → the real titled conversation stayed listed.
- Upstream comparison: clean HEAD's `_list_titled_sessions()` calls `self._session_db.list_sessions_rich(...)` directly — no current-session exclusion, no creation. So this quirk class is LOCAL DRIFT, not upstream behavior.

## Evidence commands (all read-only)
```
git -C ~/.hermes/hermes-agent status --short          # M gateway/slash_commands.py etc.
git -C ~/.hermes/hermes-agent diff gateway/slash_commands.py | head -60
git -C ~/.hermes/hermes-agent log --oneline -3        # identify base vs upstream
```
```sql
-- shell rows per lane
SELECT s.session_key, COUNT(*) total,
       SUM(CASE WHEN s.message_count=0 THEN 1 ELSE 0 END) empty_rows
FROM sessions s WHERE s.source='telegram'
GROUP BY s.session_key HAVING empty_rows>0;
-- resolve CURRENT session from latest inbound user msg (session-scoped)
SELECT m.session_id FROM messages m WHERE m.role='user' AND m.content LIKE '%<recent phrase>%'
ORDER BY m.timestamp DESC LIMIT 1;
```

## Verbatim-quote discipline (lesson from the fabrication catch)
When asked to quote/resend a previous reply: query `messages` filtered to the CURRENT session id (resolved as above), `role='assistant'`, ordered by timestamp/id DESC — never answer from conversational memory, and never scope by platform-wide lane (sibling fresh sessions share the lane key). Present provenance (session id, ordering predicate) with the quote.

## Disposition (as of 2026-08-25)
- Owner accepted cosmetic quirks; upstream issue draft written to `~/.hermes/logs/proposals/20260825-upstream-issue-sessions-lists-own-conversation.md` — NOTE: after drift discovery, its "upstream bug" framing is wrong; it documents local-drift symptoms. Rewrite before ever filing upstream.
- Options presented: (A) revert working tree (destroys un-promoted resume-work incl. +163 test lines), (B) promote via source clone feat branch + PR per hermes-git-pr-flow, (C) document now, decide later. Recommended C→B. No mutation executed without owner approval (constitution: live runtime never directly edited; high-level ops need human gate).
