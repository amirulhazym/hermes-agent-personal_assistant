# Conversation + Repository Audit Reference

Use for audits that compare prior chat claims with current Hermes state.

## Evidence Matrix

| Evidence layer | Proves | Does not prove |
|---|---|---|
| Session message | What user/assistant said and observed then | Current state |
| Current file/config | Present content on this machine | Active process loaded it |
| Local git ref | Commit content on that ref | Ref is pushed/public |
| Remote ref | Commit reachable from remote | Runtime deployed it |
| Runtime discovery | Active process loaded provider/config | User-facing request succeeds |
| E2E request | Actual command/provider/model behavior | All channels/models behave identically |

## Recurring Audit Failure Patterns

- Historical “verified” claims can coexist with later user-visible failure. Preserve both; do not erase the contradiction.
- `git branch` and local commit evidence are insufficient for push claims. Check `git ls-remote --heads origin`.
- Deleting a plugin file is not complete removal if tests, docs, curated lists, caches, or channel-specific output still expose it.
- `/model` selection and `/status` output may represent configured/requested state, not effective model/provider for the completed request. Require request-level identity evidence.
- A successful direct API probe proves provider endpoint access, not Hermes registration or channel integration.
- A model being listed by `/v1/models` proves metadata exposure, not that the account/workspace can invoke it.
- Formatting verification and content verification are separate acceptance criteria.

## Session Lineage + Change Attribution (what did session X actually touch)

When the question is "which session did this happen in" or "what did that session change", reconstruct from the session DB, then attribute file changes with diffs — never from narrative.

1. **Lineage:** `session_search(query)` discovery → read `parent_session_id` from the result → `session_search(session_id=...)` for bookends (first 20 + last 10 messages) → scroll with `around_message_id` + `window` for the middle. Parent chains (`20260731_080352_8943f41f` → `20260731_173518_ad3344`) show continuity; `PARENT: NONE` = root session.
2. **Big dumps:** session reads >100KB get persisted to `/tmp/hermes-results/*.txt` — parse the JSON with python (extract `role=assistant` content + `tool_calls`), don't read the raw file into context.
3. **Attribution by diff, not memory:** for each candidate file, diff the pre-change backup (`.bak-*`, `.bak-v2.1`) against current. `stat %y` mtime chronology orders writes; `git log` in `~/.hermes` shows tracked files only — untracked scripts must be diffed against their `.bak`.
4. **Distinguish "touched by session X" from "pre-existing":** e.g. `google_api.py` mtime Jun 30 + zero diff = CLI limitations (drive search rejection, no move subcommand) are pre-existing, NOT caused by the audited session. A skill referencing a script that lives in a different repo (`wiki/lint_md.py` vs `$SK/lint_md.py`) = integration gap — label it explicitly, don't call it a regression.
5. **Display redaction:** terminal output redacts secret-like values — when verifying file content containing `TOKEN=`/`KEY=` values, use len()+chunked repr, not grep display (see verification-before-completion skill).

## Required Classification

- RESOLVED: current evidence proves the requested behavior end-to-end.
- PARTIAL: one or more layers prove progress, but a required boundary remains.
- UNRESOLVED: current evidence shows the problem remains or no fix is present.
- UNVERIFIED: plausible or historically claimed, but decisive current evidence is missing.

Always state the missing boundary explicitly.