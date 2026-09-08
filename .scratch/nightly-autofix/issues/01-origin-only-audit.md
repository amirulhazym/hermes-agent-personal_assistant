# Issue 01 — Make the 23:55 Audit Origin-Only

**Blocked by:** None

## Vertical slice

Remove the unmanaged external `upstream` fetch/classification from both
nightly audit paths while retaining personal `origin` synchronization checks.
Add a regression case proving an upstream-only change is absent from the
personal audit result and cannot create a failure.

## Acceptance criteria

- `run_audit()` and `_inspect_git()` inspect `origin` only.
- Upstream-only movement is absent from `sync_state` and does not add errors.
- Existing origin ahead/behind/divergence behavior remains covered.

## Verification

```bash
pytest -q tests/reconciliation/test_nightly_git_hygiene.py
```
