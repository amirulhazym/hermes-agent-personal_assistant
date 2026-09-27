# 02 — Preserve terminal state and immutable primary provenance

Blocked by: 01-owner-gated-timeout

Vertical slice:
- Add RED regression for timeout worker/self-cancel interruption.
- Ensure timeout execution does not delete itself before terminal persistence.
- Preserve initial primary timestamp/date and scheduler execution binding across same-run writes.
- Add explicit updated_at for later updates.
- Verify legacy/fresh-process compatibility.

Acceptance:
- no reproducible stale executing state from self-cancel;
- same run updated after midnight still retains original 23:55 primary identity;
- scheduler evidence remains bound to the original primary execution.
