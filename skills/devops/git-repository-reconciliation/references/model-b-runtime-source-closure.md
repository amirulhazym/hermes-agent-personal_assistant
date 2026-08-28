# Model B runtime source-closure recipe

Use this reference when an application repository must reproduce an upstream runtime without vendoring the entire upstream tree.

## Required artifacts

```text
docs/reconciliation/<runtime>-source-lock.json
 docs/reconciliation/<runtime>-tree-manifest.json
 patches/upstream-hermes/<ordered-patch>.patch
 scripts/reconstruct_<runtime>.py
 scripts/deploy_<runtime>.py or sync/deploy-<runtime>.sh
 docs/reconciliation/<runtime>-source-authority.md
```

The lock should contain:

- official repository URL;
- full official base commit SHA;
- ordered patch entries with stable IDs, paths, descriptions, and SHA-256 values;
- tree-manifest path and runtime destination root;
- forbidden runtime paths/patterns;
- explicit non-authoritative legacy paths.

## Safe reconstruction sequence

1. Create a disposable **plain directory**, not a Git worktree or development branch.
2. Clone/fetch the official repository at the exact base SHA. Verify `rev-parse <sha>^{commit}` equals the lock.
3. Materialize the tree with `git archive` or an equivalent exact checkout.
4. Restore Git file modes from `git ls-tree -r` (`100644 → 0644`, `100755 → 0755`). Do not trust archive extraction mode: host umask may produce `0664` for a Git `100644` file.
5. For each lock entry, verify the patch file SHA-256, run `git apply --check`, then apply it.
6. Compare the resulting file set against the explicit tree manifest. Verify every content hash, destination, and mode; reject extra forbidden files.
7. Run tests with an isolated `HOME`/`HERMES_HOME` and `PYTHONPATH` pointing at the materialized output.
8. Before calling source closure complete, repeat from a fresh official clone. A local nested/live clone is useful for debugging but is not independent disaster-recovery proof.

## Patch generation pitfalls

Generate patches with valid framing and line endings. A safe programmatic pattern is:

```python
lines = list(difflib.unified_diff(
    old_text.splitlines(), new_text.splitlines(),
    fromfile="a/path.py", tofile="b/path.py", lineterm=""
))
patch = "".join(line + "\n" for line in lines)
```

Add a `diff --git a/path b/path` header when the patch will be consumed by `git apply`. Always test applicability on a clean base. A malformed join can concatenate `---`, `+++`, or hunk headers and yields `patch fragment without header`—regenerate; do not hand-edit the target source around it.

Valid unified-diff context blank lines may look like `+ ` when the patch file itself is shown through an outer Git diff. Do not strip the context marker just to satisfy the outer whitespace check; that can invalidate the patch. Use `git apply --check` for the patch and run whitespace checks against the reconstructed source separately.

## Evidence ladder

Report these independently:

| Layer | Evidence | Status label |
|---|---|---|
| Lock | JSON parses; base/patch IDs and hashes match | `LOCK-PROVEN` |
| Materialization | Fresh base resolves; patches apply; file set/hash/mode checks pass | `RECONSTRUCTED` |
| Behavior | RED→GREEN regression tests on materialized output | `BEHAVIOR-PROVEN` |
| Baseline | Same failing node tested against clean base | `BASELINE` / `CANDIDATE` |
| Commit | Exact local Git SHA contains the artifacts | `COMMITTED-LOCAL-ONLY` |
| Remote | Direct `git ls-remote` sees the SHA | `PUSHED` |
| Runtime | Deployment manifest and live hashes match | `DEPLOYED` / `LIVE-VERIFIED` |

A targeted regression pass does not make the full suite green. If a full-suite failure occurs, run the same node against a clean baseline in a fresh process and isolated home. If it fails on both, classify it as baseline/harness debt, retain the raw failure, and do not silently fix or suppress it inside the candidate. The candidate may still be locally usable, but the release gate remains whatever the full-suite evidence proves.

## Source-authority acceptance test

Before release, answer all of these with artifacts:

- Can a fresh clone of the canonical application repo locate the source lock and every patch?
- Can a fresh official upstream clone resolve the locked base without using the VPS source tree?
- Does reconstruction produce the exact manifest file set, bytes, and modes?
- Are every old tracked upstream copy explicitly non-authoritative or converted into a patch/source artifact?
- Does deployment consume only the manifest, with no wildcard or fallback to root legacy copies?
- Are DB/schema actions explicitly absent from the reconstruction/deploy path?

Any “no” is a source-closure data gap, not a reason to round the result up to exact reproducibility.
