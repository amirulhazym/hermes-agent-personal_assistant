# /resume lineage-tip redirect bug (2026-08-12)

## Symptom (as seen by user)

- `/resume Hermes Integration Reconciliation Review #204` → gateway replied "↻ Resumed session [Wed 2026-08-12 05:48:00 +08] Latest fourth… (1 message). Conversation restored." — the OLD #204 transcript never loaded; the resume landed on the current live session.
- `/resume Hermes Integration Reconciliation Review #203` → "📌 Already on session Hermes Integration Reconciliation Review #203." — same root cause, different message.
- Earlier the same night (00:46–01:11) `/resume 20260811_190404_b8f21a` (direct session ID of #204's parent) failed the same way.
- User's question "Aren't we in #204??" was a **resume-failure complaint**, not a literal session-ID question. Answering it as a DB question (which session ID do messages land in) answered the symptom, not the cause → "Habistu kenapa kau response macam ni barua???"

## Root cause

`resolve_resume_session_id()` — `hermes_state.py:8566` — redirects a resume target to the descendant in the parent chain holding the most recent messages. Its forward walk follows ALL children; it only excludes children tagged `_branched_from`, `_delegate_from`, and `source='tool'` (the SQL at hermes_state.py:8634-8641). **`session_reset` children are NOT excluded.**

So any lineage that contains a reset-created child has its live tip at the current session, and `/resume <ANY ancestor title or ID>` resolves to the current session:

```
#1 → #2 → … → #203 → #204 → "Resume session and run regression tests" (session_reset child of #204) → current session
```

The review series was one long compression chain (Hermes Integration Reconciliation Review #1…#204, each `end_reason='compression'`, parent = previous), then a `session_reset` child ("Resume session and run regression tests", 20260812_004652), then the current session (20260812_054800) as its continuation.

## Gateway resolution path

```
gateway/slash_commands.py:4515  _handle_resume_command
  → resolve_session_by_title()  hermes_state.py:6940  (exact title → " #N" variants → latest numbered)
  → resolve_resume_session_id() hermes_state.py:8566  (lineage-tip redirect — THE BUG)
  → "Already on" check          slash_commands.py:4617-4620 (current_entry.session_id == target_id)
```

Note: `resolve_session_by_title` itself works correctly (returns the exact #204 row). The redirect happens in `resolve_resume_session_id`.

## Verification (read-only, runs the exact production code)

```python
from hermes_state import SessionDB
from pathlib import Path
db = SessionDB(Path(os.path.expanduser('~/.hermes/state.db')))

db.resolve_session_by_title("Hermes Integration Reconciliation Review #204")
# -> 20260811_191501_990b01   (correct row found)

db.resolve_resume_session_id("20260811_191501_990b01")
# -> 20260812_054800_956102d1  (redirected to CURRENT session, title "Latest fourth…")

# Same redirect for #203 and for the direct parent ID:
db.resolve_resume_session_id(db.resolve_session_by_title("Hermes Integration Reconciliation Review #203"))
# -> 20260812_054800_956102d1
```

## "Which session are we in?" diagnostic workflow

1. `~/.hermes/sessions/sessions.json` — gateway routing index. Per-platform key (`agent:main:<platform>:<chat>`) → `session_id` = the gateway's active session (what `/resume`'s "Already on" check reads via `async_session_store.get_or_create_session`).
2. `~/.hermes/state.db` → `sessions` table `ORDER BY started_at DESC` — canonical store. Follow `parent_session_id` up/down to map the lineage and see the `end_reason` chain.
3. `session_search` browse is NOT reliable for "latest session": on 2026-08-12 it returned only 3 sessions and omitted #203/#204 plus the current one. Always cross-check against state.db.

## Impact / workaround

- As long as a lineage has a `session_reset` child, users CANNOT return to an ancestor transcript via `/resume` (title or session ID) — it always bounces to the live tip.
- Practical path to continue old work without a fix: pull the ancestor transcript (`state.db` messages, or session_search by exact session_id) and continue the work in the current session.
- Fix (not yet applied): in `resolve_resume_session_id` / `get_compression_tip` walk, require the child's parent to have `end_reason='compression'` (mirroring `get_compression_tip`'s lineage-aware logic at hermes_state.py:7004) instead of following any child. Needs approval + gateway restart.
