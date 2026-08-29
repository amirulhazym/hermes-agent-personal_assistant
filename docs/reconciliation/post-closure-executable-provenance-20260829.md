# Post-Closure Executable Provenance Correction — 2026-08-29

## Scope

This is a bounded correction to the previously closed Goal 1/Goal 2 evidence,
not a redesign of the SSOT architecture and not a live deployment. It covers
only the nightly `no_agent` executable chain, its source-closure representation,
the verifier blind spot, and non-sensitive evidence provenance.

No live wrapper, live target, cron record, service, remote ref, or protected
`origin/main` ref is changed by this candidate correction.

## Reproduced pre-correction state

The natural 2026-08-28 23:55 MYT execution record was:

- Cron job: `9517378892e3` (`nightly-git-hygiene`)
- Job script field: `nightly_git_hygiene_wrapper.sh`
- Allowed runtime script root: `/home/ubuntu/.hermes/scripts/`
- Natural output: `/home/ubuntu/.hermes/cron/output/9517378892e3/2026-08-28_23-56-02.md`
- Receipt timestamp: `2026-08-28 23:55:38 MYT`
- Receipt audited repository: `/home/ubuntu/hermes-agent-personal_assistant-work`
- Receipt audited HEAD: `24a6bd19883b492dfcb7b286824df84b8e336140`

The live wrapper was not tracked by the `$HERMES_HOME` Git root and was not
present in the candidate or source-closure manifest. Its pre-correction bytes
were 106 bytes with SHA-256
`60b0824f85b7ab99764133edb220e3d5e2eb5e639c948f86fa59352cb6b25f99`, and its
`exec` target was the personal-main path:

```text
/home/ubuntu/hermes-agent-personal_assistant-work/scripts/nightly_git_hygiene.py
```

That target matched the personal-main `24a6bd19883b492dfcb7b286824df84b8e336140`
Git blob at SHA-256
`6c0a62f258d7c39fb5eabf3ac50fdb82d4203305d50c350bcdd570d0590d2adc`.
The corrected candidate implementation at `0ed8838fcbc3c6b0acdc2418bc87f74d73205407`
had a different target SHA-256
`0473742e0b661d393f7c3dd4247d3a3d5c84bee5389e09937cb580fb85a809a4`.

The receipt therefore correctly reported the repository HEAD that its target
actually audited, but it did not prove that the corrected candidate executed.
The old receipt also did not contain an execution-time script hash.

## Candidate correction

The candidate now represents the complete chain as two explicit SSOT source
files:

| Source | Runtime destination | Manifest kind |
|---|---|---|
| `scripts/nightly_git_hygiene_wrapper.sh` | `/home/ubuntu/.hermes/scripts/nightly_git_hygiene_wrapper.sh` | `runtime-deploy` |
| `scripts/nightly_git_hygiene.py` | `/home/ubuntu/.hermes/scripts/nightly_git_hygiene.py` | `runtime-deploy` |

The candidate wrapper is owner-executable and resolves only to the runtime
script-root target:

```text
/home/ubuntu/.hermes/scripts/nightly_git_hygiene.py
```

The nightly implementation now records, in every future JSON/Markdown receipt:

- the executable path;
- the executable SHA-256;
- executable byte size;
- the separately audited repository path;
- the separately audited repository HEAD.

This prevents repository HEAD from being mistaken for executable identity.

## Deployment write-set and rollback invariant

The custom deployment plan has one canonical write set:

```text
content mismatch ∪ new destination
```

`mode_only` and unchanged entries are metadata/no-action rows. Dry-run reports
`plan.write_sources`; apply iterates the same manifest-ordered set and returns
`written_sources` for direct parity checking. Existing destination modes remain
unchanged; no unrelated chmod normalization is performed.

Before `os.replace` can mutate a destination, the transaction records the
(destination, previous-snapshot) pair. This covers failures before replacement,
immediate post-replace failures, post-write hash failures, multi-file failures,
and failures after creation of a new destination. Rollback restores existing
bytes/modes from the per-path snapshot and removes only a newly-created declared
destination. Undeclared files are never part of the rollback/delete set.

## Verifier correction

`scripts/verify_post_closure.py` is a read-only deterministic verifier. It
checks:

1. job ID, enabled state, and `no_agent` mode;
2. scheduler script resolution under the allowed runtime script root;
3. wrapper syntax, executable mode, target path, and arguments;
4. candidate Git blob hashes for wrapper and target;
5. runtime hashes for wrapper and target;
6. `runtime-deploy` manifest rows and exact destinations;
7. receipt audited HEAD separately from receipt executable hash/path;
8. the distinction between `PROVEN`, `HOLD`, `FAIL`, and historical
   execution identity that is only `PARTIAL` when the old receipt lacks a hash.

A scheduler execution cannot receive an operational `PROVEN` result merely
because it has a delivery record or because the receipt reports the candidate
HEAD. The runtime chain and execution identity must match the same candidate.

Regression coverage is in:

- `tests/reconciliation/test_post_closure_executable_provenance.py`
- `tests/reconciliation/test_nightly_execution_identity.py`
- `tests/reconciliation/test_custom_runtime_deploy.py`

## Deployment boundary

The live wrapper and live runtime target remain unchanged in this correction.
The new source/manifest representation is candidate-only. Live application
still requires the existing exact-SHA release approval and deployment gate.
No merge to local `main`, protected remote push, live apply, cron edit, or
service restart is implied.

## Evidence durability boundary

The complete post-closure evidence package is generated after the final
candidate commit under the existing private local evidence/archive boundary.
Only non-sensitive closure metadata, hashes, paths, receipts, and test output
are retained there. Secrets, private runtime state, medical state, and excluded
credential-bearing artifacts are not copied into the candidate evidence set.
