# Production update-routing matrix

Use this as a pre-implementation and pre-commit inventory for any update-policy
change spanning multiple processes or UI surfaces. It is a seam checklist, not
proof that a route is currently correct.

| Boundary | Concrete surface to inspect | Required contract |
|---|---|---|
| CLI apply | `cmd_update`, `_cmd_update_impl` | One resolver; clean-tree gate before all mutation; ff-only; no reset fallback |
| CLI check | `--check` path/banner probe | Same channel and remote; no upstream/fork intake |
| Gateway | `/update` subprocess | Explicit unattended argv: `update --yes --gateway --branch <production-channel>` |
| Dashboard | `POST /api/hermes/update` | Explicit argv: `update --yes --branch <production-channel>` |
| Desktop | check/apply/manual fallback/config setter | No `main` fallback; reject arbitrary persisted branch; exact handoff argv |
| Desktop scripts | POSIX + PowerShell handoff | Same canonical channel; no legacy default |
| Installers | shell + PowerShell repository update | Same channel; divergence stops; no automatic hard reset for production path |
| Native bootstrap | Rust/Tauri update argv/default | No build-stamp or old-install fallback that widens production routing |
| Notifications | banner/update availability | Probe same release channel or clearly label unsupported/unavailable |

## Search checklist

Search the candidate source and tests for all of these before closure:

```text
main
origin/main
upstream
remote add upstream
reset --hard
autostash
stash push
bare ["update"]
resolveHealedBranch
BUILD_PIN_BRANCH
```

Each hit needs a disposition: production path changed, developer-only path
explicitly isolated, test/documentation contract intentionally updated, or
unrelated historical text. Do not delete a hit merely to make the search zero.

## Gate order

1. Pin current target with direct remote query; record whether the production ref
   exists.
2. Write one seam RED test for the shared policy and one argv assertion per
   unattended boundary that constructs a command.
3. Implement the smallest vertical slice.
4. Run that slice, static checks, and call-site search.
5. Update tests that assert the intentionally superseded contract; classify old
   failures rather than weakening the new policy.
6. Rerun affected suites after every source/test change.
7. Stage exact paths and run cached whitespace/privacy checks before commit.
8. After commit, rerun validators against the final SHA. Keep pushed, deployed,
   process-loaded, and channel-smoke states separate.

## Failure classifications

- `POLICY-TESTED`: shared resolver/preflight contract passes.
- `ROUTE-WIRED`: source and argv inspection show every production caller uses the
  policy/channel.
- `CANDIDATE-INTEGRATED`: affected seam suites pass on the exact candidate.
- `CHANNEL-BLOCKED`: the configured production ref is absent or unavailable on
  the queried remote; never silently fall back to `main`.
- `PARTIAL`: any boundary remains un-audited, stale, untested, or uncommitted.
