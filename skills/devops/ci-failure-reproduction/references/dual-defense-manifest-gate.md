# Dual-Defense Manifest Gate (Hermes pattern)

Captured from the 2026-08-20 Gate 2 + CI fix session. Reproducible recipe
for the two-gate pattern that survived: pre-push local hook (refresh
existing rows) + CI-side recompute (enforcement gate + receipt).

## When this applies

A repository has:

- A source-coverage manifest at `docs/reconciliation/v3-source-coverage-manifest.json`
  with one row per tracked file (`source`, `source_sha256`, `kind`, `destination`).
- A `ci.yml` with two guard jobs in order: `PII review screen` then `Validate
  source coverage manifest`.
- The manifest validator is **not diff-scoped**: it validates the full
  manifest against the release SHA.

This is the pattern that triggers this dual-defense need. If your
validator is diff-scoped or you don't have a separate PII step, a single
CI job is enough.

## Why both pieces are needed

- **Local hook alone**: owner-skippable, no enforcement at CI, easy to
  forget to install.
- **CI recompute alone**: forces a noisy re-run cycle every push; doesn't
  help owners avoid pushing stale rows in the first place.
- **Both together**: local hook catches 99% of cases silently with a
  receipt file; CI recompute is the safety net that makes "CI green"
  verifiable to the exact SHA.

## Component 1: local pre-push hook

Install in the work repository, not the live runtime:

```bash
git config core.hooksPath .githooks
```

Hook at `.githooks/pre-push-manifest-refresh` (Python 3). Behavior:

- Walk every existing manifest row.
- For each `source`, compute `actual = sha256(git show HEAD:source)`.
- If `actual != entry["source_sha256"]`, update `source_sha256` to `actual`.
- NEVER add new rows (absent row = policy decision; warn).
- Write a receipt under `docs/reconciliation/manifest-receipts/<short-sha>.json`
  with `status` (REFRESHED/NOOP), `refreshed_count`, `refreshed[]`,
  `head_sha`, `upstream_ref`, `timestamp_utc`, `manifest_sha256`.
- Auto-stage the manifest and the receipt on success.

Failure modes the hook MUST handle:

- Branch never pushed yet (`origin/<branch>` doesn't exist): fall back to
  `HEAD~1` for the diff range, but walk ALL rows against HEAD (do NOT
  filter by `changed_paths`; that misses manual manifest edits on
  throwaway branches). This was the actual bug caught during the 2026-08-20
  acceptance test.
- Manifest dirty in working tree: refuse and exit 2. Do NOT auto-overwrite.

## Component 2: CI-side recompute job

Add a step in `.github/workflows/ci.yml` BEFORE the strict validator:

```yaml
- name: Recompute source coverage manifest (enforcement gate)
  run: |
    set -eu
    python3 scripts/guard/manifest_recompute.py docs/reconciliation/v3-source-coverage-manifest.json "$GITHUB_SHA"
- name: Validate source coverage manifest
  run: bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json "$GITHUB_SHA"
```

`scripts/guard/manifest_recompute.py` behavior:

- Recompute `source_sha256` for every existing row against `$GITHUB_SHA`.
- Write receipt under `docs/reconciliation/manifest-receipts/<short-sha>.json`.
- **FAIL** if any tracked source is missing in HEAD tree (absent row =
  policy decision pending, do not silently skip).
- Otherwise exit 0 with `MANIFEST-RECOMPUTE: status=REFRESHED refreshed=N`
  or `MANIFEST-RECOMPUTE: status=NOOP refreshed=0`.

The receipt contract is:

```json
{
  "status": "REFRESHED" | "NOOP",
  "refreshed_count": 0,
  "refreshed": [{"source": "path", "old": "sha", "new": "sha"}],
  "head_sha": "40char",
  "timestamp_utc": "ISO-8601",
  "manifest_sha256": "sha"
}
```

Any "DONE/GREEN/CLOSED" claim for a CI fix must cite this receipt file
path and the `status` / `refreshed_count` keys.

## Field-scoped PII exception (companion fix)

If your `pii-review.py` matches email-shaped tokens and the manifest's
`source` / `destination` paths contain strings like
`contributors/emails/foo@example.com`, the guard will flag every row.

Fix: **field-scoped exception, NOT file exclusion**.

In `pii-review.py`:

```python
MANIFEST_PATH = "docs/reconciliation/v3-source-coverage-manifest.json"

def findings(path, data, *, field_scope=None):
    if path == MANIFEST_PATH and field_scope == {"source", "destination"}:
        # Mask ONLY the source/destination values; leave other fields
        # and other files fully scanned.
        data = MASK_PATH_FIELDS.sub(rb'\1""', data)
    # ... existing scan unchanged
```

In `scan_diff(spec)`:

```python
scope = {"source", "destination"} if current == MANIFEST_PATH else None
out.extend(findings(current, line[1:], field_scope=scope))
```

Required regression tests:

1. Manifest path with email-like substring → PASS (field-scoped exception)
2. Same manifest with an email in a different field (e.g. `metadata`,
   `comment`) → FAIL (real content, still scanned)
3. Other unrelated files containing an email address → FAIL (no blanket
   exclusion)
4. Plus a real `scan_diff(...)` round-trip test that walks a fake
   git repo with the manifest file present, so the path/field plumbing
   is exercised end-to-end.

## Why local CI-mode validator is required

A clean-clone validator run against `HEAD~1` or against a prior SHA is not
predictive of CI. The CI invocation MUST use the exact release SHA the
push will see. The same trap caught the 2026-08-20 session once: local
battery reported green against `cad8c97b` (a prior HEAD), CI then failed
on the actual merge commit's manifest mismatch.

Hardcoded in the local battery script (and in any post-push smoke script):

```bash
bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json "$(git rev-parse HEAD)"
```