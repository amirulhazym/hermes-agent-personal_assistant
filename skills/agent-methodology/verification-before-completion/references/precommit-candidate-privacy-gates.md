# Pre-commit candidate privacy gates

## Problem

A candidate worktree may be intentionally uncommitted and mostly untracked. In that state, common Git-scoped guard commands can falsely report a clean result:

- `git diff BASE..HEAD` compares commits, so it omits unstaged candidate changes.
- `git ls-files` lists tracked files, so it omits candidate files that are untracked.

A green result from either command is not evidence that the actual pre-commit candidate was scanned.

## Required pre-commit scan scope

1. Build a deduplicated candidate-path manifest before testing. Include every intended public path, including an explicit entry for any manifest/control file that is excluded from its own hash listing to avoid self-reference.
2. Scan every path in that manifest using the same secret and PII rule functions as the normal guard. Diagnostics must print only `path` and `rule/category`, never a matched value.
3. Independently record:
   - tracked working-tree delta against the approved base;
   - sorted untracked path list;
   - their counts and SHA-256 list hashes;
   - intended paths that are byte-identical to the base (they legitimately produce no Git delta).
4. Treat any secret-pattern hit as `HOLD`, including hits in tests, until its semantics are proven and an explicit remediation/allow policy is reviewed. Do not weaken or bypass the guard to get a pass.
5. Verify private-path exclusions directly by exact path presence/absence, not by filename heuristics alone.

## Completion evidence

Record separately:

```text
base SHA
candidate worktree + branch
candidate commit SHA (NONE before commit)
manifest path + SHA-256
candidate path count
copy-integrity result
private exclusions result
secret result
PII result
tracked/untracked counts + list hashes
```

A candidate may be constructed successfully while its privacy gate remains `HOLD`; do not call the release candidate ready or advance to commit/testing as if the gate passed.
