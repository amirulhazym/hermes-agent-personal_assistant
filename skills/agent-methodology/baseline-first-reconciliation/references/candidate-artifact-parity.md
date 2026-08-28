# Candidate Artifact Parity and Rollback Evidence

Use this reference when a release candidate is represented by a pinned Git base plus ordered patch files, especially when the runtime tree itself is intentionally not a normal Git checkout.

## Evidence layers

Keep these separate:

- **Base:** exact official Git SHA and Git-recorded tree modes.
- **Candidate:** fresh non-Git materialization of the base plus the ordered series.
- **Git-backed test clone:** disposable detached clone with the same base and series, used only for tests that require `.git`.
- **Rollback artifact:** temporary pre-release base files for the actual runtime deployment paths.
- **Final candidate:** a clean rebuild after tests, with generated test artifacts absent.

## Reliable parity sequence

1. Materialize the non-Git candidate and validate the patch series.
2. Restore modes from the official tree after all patches are applied. Do not treat host umask as provenance.
3. Create a fresh detached clone from the exact base and apply the same ordered series.
4. Before running tests, compare every relevant path's raw bytes, SHA-256, file type, and mode between the two trees.
5. Run only the bounded test family in the Git-backed clone with isolated state. Preserve the inner pytest RC and raw log; an outer shell wrapper returning zero is not a test result.
6. Rebuild a clean non-Git candidate after tests and regenerate the tree manifest/hash.

A clone that is compared only after testing is not a valid parity witness: tests can create caches, duration files, bytecode, or state mutations.

## Mode normalization

For regular files, read the expected mode from Git rather than from the extracted filesystem:

```bash
git ls-tree -r <base-sha>
```

Apply the recorded `100644`/`100755` mode to the materialized file after the patch series. Compare byte changes separately from mode-only differences. An all-files mode delta is usually an extraction/umask artifact, not an all-files source change.

## Rollback proof

Derive the touched set from the deployment manifest's runtime entries, not from every file that differs in a raw tree comparison. In a disposable destination:

```text
pre-release base → copy candidate runtime files → restore rollback artifact
```

For every touched path, prove:

- post-rollback SHA-256 equals pre-release SHA-256;
- post-rollback mode equals pre-release Git mode;
- no live runtime/database/config path was used.

## Status labels

- `PROVEN`: raw command output and exact artifact support the claim.
- `PARTIAL`: some boundaries pass, but a required layer is missing.
- `UNVERIFIED`: output was truncated, masked, or not independently captured.
- `HARNESS-INVALID`: the test did not exercise the intended candidate (for example, missing `.git`).
- `BLOCKED`: a required gate is not proven or a real candidate defect remains.

Never upgrade `HARNESS-INVALID`, `UNVERIFIED`, or `PARTIAL` to `PASS` because a related baseline comparison is green.
