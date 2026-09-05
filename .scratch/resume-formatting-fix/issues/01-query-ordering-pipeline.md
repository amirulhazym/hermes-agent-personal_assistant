# 01 — Query & Ordering Pipeline

**What to build:**
Update `_list_titled_sessions` in `gateway/slash_commands.py` to query `SessionDB.list_sessions_rich` with `order_by_last_active=True` and `limit=50`. Extract the active/current session (if present in caller context) and up to 10 past titled sessions ordered by `last_active DESC`.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Query passes `order_by_last_active=True` and `limit=50`.
- [ ] Active session is identified and prepended to the list if found.
- [ ] Up to 10 past titled sessions are collected, excluding the active session duplicate.
- [ ] Numeric resume indexing (`/resume 1`, `/resume 2`, etc.) points to the exact item in the assembled list.
