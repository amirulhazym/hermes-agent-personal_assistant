# Ordered-Patch Evidence Closure

Use this reference when a release candidate is represented as an official base plus ordered patch artifacts, especially when a patch, test contract, lock file, or manifest was regenerated after tests already ran.

## Evidence layers

Keep these identities separate:

- `BASE`: official repository and full pinned base commit;
- `PATCH SERIES`: ordered patch IDs, paths, and SHA-256 values;
- `MATERIALIZED SOURCE`: the tree produced by applying that series;
- `TREE MANIFEST`: exact source path, destination, content SHA-256, and mode;
- `CANDIDATE SHA`: local Git commit containing the release artifacts;
- `TEST EVIDENCE`: command, interpreter, isolated HOME, source tree, log, final exit state;
- `ROLLBACK`: exact production touched set and pre-release C0 bytes/modes.

A historical test log is evidence for the source representation used by that run, not automatically for a later candidate SHA.

## Patch applicability versus patch-file whitespace

Run both gates because they answer different questions:

```text
git diff --check                         # candidate/repository whitespace quality
git apply --check --directory=<root> <patch>  # unified-diff applicability
```

A valid unified diff can contain a blank context marker represented as a line containing one space. That can make an outer repository `git diff --check` report trailing whitespace even though the patch applies correctly. If the owner requires the artifact gate to be clean, remove only asserted whitespace-only marker lines with a byte-level operation, then rerun `git apply --check` and affected tests. Never alter production additions or removals merely to silence the diagnostic.

Record the transformation defensively:

```python
marker = bytes((32, 10))
count = data.count(marker)
assert count == EXPECTED_COUNT
new_data = data.replace(marker, bytes((10,)))
```

After any patch-byte change, regenerate the patch SHA, source lock, tree-manifest patch-series digest, and exact candidate SHA.

## Proving runtime bytes did or did not change

Do not compare patch files and call that a runtime comparison. Patch regeneration may change context layout, hunk boundaries, or test-only sections without changing the materialized source.

Use two equivalent isolated copies of the same pinned base/C3 source files:

1. apply the previous patch representation;
2. apply the final patch representation;
3. compare every production touched file's bytes and modes;
4. compare exact path sets;
5. record per-file SHA-256 and equality results.

Classify separately:

```text
RUNTIME SOURCE CONTENT CHANGED = YES/NO
RECONSTRUCTION/PROVENANCE BEHAVIOR CHANGED = YES/NO
```

A reconstruction script that restores Git modes can change provenance behavior while leaving runtime Python bytes unchanged. A patch-text diff alone cannot decide either label.

## Git-mode authority

A host umask can extract an official Git `100644` file as filesystem `0664`. The manifest must represent official Git modes, not the host default.

After applying the ordered series:

1. restore modes from the pinned Git tree;
2. enumerate the complete output path set;
3. hash every file;
4. record `mode` for every file;
5. compare path set, content hash, and mode against the manifest.

`tree_sha256` is valid only when the manifest input set and mode model are explicit.

## Reusing prior behavioral evidence

Historical evidence can be reused only when the materialized runtime path set and bytes/modes are proven identical to the tested representation. If only metadata, test contract, patch formatting, or provenance changed, rerun the affected static/applicability/provenance gates and create a new exact candidate SHA. If any runtime byte or mode changed, invalidate the relevant behavioral evidence and rerun it.

Keep these labels distinct:

- `REUSED — SOURCE BYTE/MODE PARITY PROVEN`;
- `RERUN — FINAL SOURCE DIFFERED`;
- `NOT REUSABLE — PARITY UNPROVEN`;
- `HISTORICAL — LOG PRESERVED, SOURCE CLONE NO LONGER PRESENT`.

A valid targeted suite does not prove the full repository suite. `READY FOR FINAL FULL SUITE` means the remediation gate is complete and the full-suite gate is intentionally next; it does not mean the full suite passed.

## Production rollback proof

Derive the deployment set from all ordered patch/deployment manifest headers. Do not hard-code a remembered list.

In a temporary destination:

```text
C0 touched files → pre-release reference
final touched files → candidate-deployed reference
candidate-deployed → apply rollback artifact
```

Require all of:

- exact deployment file set;
- exact rollback file set;
- no missing files;
- no extra files;
- every touched-file byte equal to C0 after rollback;
- every touched-file mode equal to C0 after rollback.

Report production rollback separately from development history rollback. The former is candidate content back to exact pre-release C0; the latter is usually candidate patch history back to the prior development boundary.

## Boundary evidence

For session/resume behavior, separate:

1. real copied-database rows and their physical identities;
2. synthetic contract fixtures;
3. no-data cases.

Use the actual stored production boundary literals. If a real copied DB has no row for a boundary, report `NO REAL COPIED-DATA ROW` and show synthetic evidence separately. Do not silently replace the stored literal with a legacy alias to make the matrix look complete.

For every row preserve: candidate SHA, DB identity/hash, immutable/read-only mode, before/after sidecar hashes, exact resolver input/output, and whether the result is real-data or synthetic.
