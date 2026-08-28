# Git-backed final-suite materialization parity

Use this reference when a repository-wide final suite requires a valid `.git` tree, but the authoritative candidate is represented by a manifest-backed reconstruction.

## Required sequence

1. Pin the exact candidate commit, official base commit, remote ref, current disk, live process state, and the authoritative reconstruction tree SHA.
2. Materialize one disposable Git-backed validation tree from the exact official base. Keep it detached; do not create a development branch or register a project worktree.
3. Read the candidate source lock. Hash every ordered patch artifact from disk and compare it with the lock before applying anything. Run `git apply --check` and then apply each patch in order; retain the raw output.
4. Before running pytest, compare the validation tree with the authoritative manifest-backed reconstruction:
   - authoritative manifest path set (excluding `.git` and proven generated validation artifacts);
   - source bytes and SHA-256 values;
   - file type;
   - executable/non-executable class, not arbitrary host Unix permission bits;
   - canonical manifest/tree SHA for the authoritative reconstruction;
   - missing and extra paths, with generated extras classified separately.
5. Treat the corrected parity fields as the hard gate. Required counts are zero for path mismatches, byte mismatches, file-type mismatches, and executable-class mismatches. A clean `git diff --check`, successful patch application, or zero byte mismatches alone is insufficient.

## Deployment modes versus disposable validation modes

Keep two mode authorities separate:

- **Authoritative deployment reconstruction:** exact runtime bytes and exact deployment modes from the manifest (for example `0644` and `0755`) remain mandatory.
- **Disposable Git-backed validation tree:** compare regular-file type, bytes, and executable class. Git's relevant regular-file distinction is `100644` versus `100755`; host-umask/group-write differences such as `0644` versus `0664` or `0755` versus `0775` are non-semantic validation artifacts when executable class is unchanged.

A validation-tree mode difference that changes executable status remains a blocker. Do not chmod the candidate, reconstruction, manifest, or validation tree merely to force arbitrary full-stat equality.

Generated files such as `__pycache__`, `.pytest-cache`, and `test_durations.json` are validation-environment outputs. Do not delete protected reconstruction/evidence paths merely to make a whole-directory walk match the manifest. Compare the authoritative manifest path set explicitly; classify proven generated extras as allowed validation artifacts and classify authoritative/source unexpected extras as blockers.

## Evidence record

Persist a compact parity record containing: candidate/base/tree SHAs, validation-tree path, patch hashes and apply results, manifest entry count, separate path/byte/file-type/executable-class mismatch counts, non-semantic umask/group-write differences, generated-extra exclusions, `git diff --check` result, Git index mode classes, whether the suite started, the exact command, and the stop/proceed reason. If a required parity count is non-zero, classify the run as `BLOCKED — INFRASTRUCTURE/HARNESS` and do not report final test totals; if all required counts are zero, proceed with the canonical suite without mutating candidate source.

## Live dirt scope and attribution

A tracked-only live pin proves only tracked dirt. Do not later summarize it as the complete live dirty set if an all-path pin exposes untracked files. Record tracked and untracked paths separately, label untracked writer provenance `UNKNOWN` unless directly proven, preserve them as pre-deploy protected material, and do not inspect/attribute/modify them when the suite scope explicitly excludes live-runtime investigation. The disposable validation tree and the live checkout are separate evidence boundaries.