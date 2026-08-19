# Hermes runtime source authority

## One authoritative path

The Hermes runtime source is **not** the collection of root-level Python files in
this application repository and it is not copied from the live VPS checkout.
The only authoritative reconstruction path is:

```text
approved application Git SHA
  -> docs/reconciliation/hermes-runtime-source-lock.json
  -> official NousResearch/Hermes-Agent commit a31be48030...
  -> ordered, hash-pinned patch series
  -> scripts/reconstruct_hermes_runtime.py
  -> docs/reconciliation/hermes-runtime-tree-manifest.json
  -> explicit manifest-driven deployment
  -> /home/ubuntu/.hermes/hermes-agent
```

The tree manifest contains one explicit source/destination/hash/mode row for each
reconstructed runtime file. It is not a wildcard, recursive copy instruction,
or permission to delete undeclared live files.

## Non-authoritative material

The following tracked application-repository files remain for historical or
application-test compatibility only:

- `hermes_state.py`
- `gateway/slash_commands.py`

They are marked `SOURCE ROLE: REFERENCE-ONLY` in-file and in the source lock.
They must never be used as Hermes runtime deployment inputs. Session-fix changes
belong in the ordered patch series and are tested against reconstructed output.

`docs/reconciliation/v3-source-coverage-manifest.json` is an application-source
coverage inventory. It is not the Hermes runtime source lock or deployment
authority. The live nested clone under `~/.hermes/hermes-agent` is a source
witness used to verify a pinned official commit, not a second application-source
lineage.

Historical overlays in `patches/upstream-hermes/` remain source evidence unless
and until an entry is explicitly added to `patch_series` with its exact SHA-256.
Their presence does not make them active runtime inputs.

## Runtime exclusions

The reconstruction/deployment path excludes mutable/private runtime state,
including credentials, databases, sessions, logs, caches, and platform pairing
state. No DB migration, DB repair, transcript rewrite, or state-file deployment
is part of this source model.

## Commands

Reconstruct from a local official clone for an offline test:

```bash
python3 scripts/reconstruct_hermes_runtime.py \
  --lock docs/reconciliation/hermes-runtime-source-lock.json \
  --tree-manifest docs/reconciliation/hermes-runtime-tree-manifest.json \
  --base-repo /home/ubuntu/.hermes/hermes-agent \
  --output /tmp/hermes-runtime-build \
  --validate
```

The normal no-local-clone path fetches the exact official commit from the pinned
repository. Deployment is a separate release-gated operation:

```bash
export HERMES_SOURCE_TREE=/tmp/hermes-runtime-build
sync/deploy-hermes-runtime.sh --dry-run
```

`--apply --release-sha <full-sha>` is reserved for the post-Gate-2 release
procedure. This source-closure commit does not deploy or restart anything.
