# Model-B Ordered Overlay Closure — Reusable Evidence Recipe

This reference captures the command/evidence pattern for a partial source index whose runtime behavior is represented by an upstream base plus ordered overlays. Replace angle-bracket placeholders; do not reuse a prior candidate SHA after any byte change.

## Identity record

Capture these fields before work and again at closure:

```text
DESTINATION_REMOTE_REF = <git ls-remote result>
APPROVED_BASE_SHA      = <donor/upstream base>
CANDIDATE_SHA          = <final local commit>
PATCH_SERIES           = <ordered IDs + SHA-256 values>
CANDIDATE_PATH         = <reconstructed output>
TREE_SHA256            = <manifest/tree hash>
LIVE_HEAD              = <live checkout HEAD, independently>
PUSHED_REF             = <explicitly absent or remote SHA>
DEPLOYED_HEAD          = <explicitly absent or observed SHA>
ACTIVE_RUNTIME         = <explicitly absent or observed process state>
```

Never collapse `CANDIDATE_SHA`, `PUSHED_REF`, `DEPLOYED_HEAD`, and `ACTIVE_RUNTIME` into one “release” value.

## Fresh overlay applicability

Use a disposable copy of the exact donor baseline, not a dirty candidate tree:

```bash
cp -a <clean-donor-tree> <fresh-apply-tree>
git -C <fresh-apply-tree> apply --check <ordered-patch>
git -C <fresh-apply-tree> apply <ordered-patch>
```

Then compare every intentional path against the development candidate. `git apply --check` proves that a patch can apply; it does not prove that the resulting bytes equal the candidate.

## Reconstruction gate

Use the repository’s reconstruction script and record raw output. The general shape is:

```bash
python3 scripts/reconstruct_hermes_runtime.py \
  --lock docs/reconciliation/<source-lock>.json \
  --tree-manifest docs/reconciliation/<tree-manifest>.json \
  --output <candidate-output> \
  --base-repo <donor-repo> \
  --validate
```

If the workflow supports it, use `--write-tree-manifest` only while intentionally regenerating the manifest, then rerun validation after the manifest is committed. The evidence must include base SHA, patch count/order, file count, tree hash, and exit code.

## Exact-SHA freshness loop

After every amend or byte-changing manifest/fixture edit:

1. stop using previous candidate test evidence as final evidence;
2. record the new `HEAD`;
3. run manifest validation against the new SHA;
4. rerun secret scan and reconstruction tests;
5. rebuild the exact-SHA candidate;
6. rerun affected tests and copied-state probes;
7. only then begin or resume the authoritative full suite.

A previous SHA is historical context, not the current candidate.

## Hermes full-suite boundary

Read `scripts/run_tests.sh` and its conftest before invoking the full suite. For the runner family where conftest creates the test sandbox, the proven invocation is:

```bash
env -u HERMES_HOME scripts/run_tests.sh -j <workers>
```

Do not substitute `HERMES_HOME=$(mktemp -d) python -m pytest ...` for the canonical suite and then report equivalent evidence. Direct pytest with an explicit temporary home remains useful for targeted isolation, but it is a separate scope.

Record:

- process/session ID;
- exact command;
- candidate output path and SHA;
- interpreter and worker count;
- runner startup diagnostics;
- final aggregate and exit code.

Progress counters such as `N passed / M failed` are **INTERIM** while the process is running. They are not a final full-suite verdict. A killed or timed-out process is `INCOMPLETE`.

A reconstructed tree may not contain `.git`; if precompile prints a Git warning, preserve it as a runner diagnostic and separate it from pytest result classification. It is not silently a PASS, and it is not automatically a test failure.

## Baseline attribution

For every final failure:

```text
candidate node → fresh isolated candidate rerun
clean donor node → fresh isolated baseline rerun
compare raw assertion/output
```

Classify only after both sides are exercised:

- `BASELINE`: same deterministic failure on clean donor;
- `CANDIDATE-DEFECT`: candidate-only deterministic failure;
- `CONTRACT-CHANGE/STALE-TEST`: intentional contract changed and test asserts old behavior;
- `HARNESS`: runner, fixture, import, path, or materialization problem;
- `ORDER-SENSITIVE/FLAKY`: full-run failure but isolated repeats do not reproduce;
- `UNRESOLVED`: insufficient evidence.

A baseline failure remains part of the unconditional full-suite failure count. An exclusion rerun is useful evidence but cannot be reported as an unconditional full-suite PASS.

## Session identity probes

When repairing listing/resume/search identity, print separate fields for:

```text
physical matched message/session
compression deduplication identity
current-session visibility fence
user-visible title/listing/resume projection
```

Synthetic tests should include reset children and unrelated branch/delegate/tool edges. When a copied incident DB is available, run at least one physical message-ID/title probe and one continuation resolver probe. A copied-DB pass proves candidate behavior against that copy; it does not prove deployment or live behavior.

## Disk pressure during long runs

At 90%+ usage, inventory before deletion:

```bash
df -B1 -P /
du -x -B1 -d1 /tmp
du -x -B1 -d1 /home/ubuntu
```

Check active process CWD/open-FD references for candidate/evidence paths. Classify cache, test-temp, source-overlay, baseline, and incident-evidence groups. Ask for explicit approval per deletion batch. An unanswered cleanup prompt is no approval; keep source-like and evidence directories.
