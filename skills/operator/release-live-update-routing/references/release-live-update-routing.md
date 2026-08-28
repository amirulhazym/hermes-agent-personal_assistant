# Release/live update-routing audit matrix

## Entrypoint matrix

Audit all rows before changing the resolver:

| Surface | Expected production argv/route | Primary seam | Required assertions |
|---|---|---|---|
| CLI parser/resolver | `update` ⇒ `release/live` | `build_update_parser`, `_resolve_update_branch` | default route; explicit developer branch remains possible |
| CLI implementation | `fetch origin <branch>` + `merge --ff-only origin/<branch>` | `cmd_update`, `_cmd_update_impl`, `_cmd_update_check` | clean preflight first; no upstream/push/reset fallback |
| Gateway slash | `update --yes --gateway --branch release/live` | `_handle_update_command` | POSIX and Windows command construction |
| Dashboard action | `update --yes --branch release/live` | `/api/hermes/update` action builder | no bare `['update']` |
| Desktop/bootstrap | explicit release/live handoff | updater argv builders | no hidden `main` default in production flow |
| Installer scripts | release/live default | `scripts/install.sh`, `scripts/install.ps1` | no ff-only → reset fallback |

If a requested route literal is absent, record that fact and map the real
unattended equivalent. Do not create a new route as part of a routing-only fix
unless the product contract explicitly requires it.

## Dirty-tree preflight

Use a complete porcelain query:

```text
git status --porcelain=v1 --untracked-files=all
```

Fail closed for any output, including:

- ` M tracked.py` — unstaged tracked change;
- `M  tracked.py` — staged change;
- `?? new.py` — untracked file;
- `UU conflict.py` — unmerged entry.

The guard must execute before backup, lock/marker, process pause, git config or
cleanup, fetch, stash, checkout, merge, reset, dependency install, or restart.
A test should record all subprocess calls and verify that no forbidden call
occurred after the dirty status was observed.

## Divergence test template

Simulate:

```text
fetch origin release/live       => success
rev-list HEAD..origin/release/live => one or more commits
merge --ff-only origin/release/live => nonzero
```

Expected result:

- update exits nonzero;
- output identifies fast-forward/divergence failure;
- no `reset --hard` is issued;
- no stash restore/discard runs;
- no dependency installation or restart runs.

## Remote-policy test template

Use a fork-looking origin URL and fake subprocess responses. Assert that no
captured command contains any of:

```text
upstream
remote add
push
```

Run this against both the mutating path and `--check`, including explicit
`--branch main`; a branch-name conditional must not re-enable upstream intake.

## Evidence vocabulary

- `LOCAL-VERIFIED`: candidate files, local refs, or local subprocess capture.
- `REMOTE-VERIFIED`: direct `git ls-remote` result for the target ref.
- `LIVE-VERIFIED`: running process loaded the candidate and a user-visible path
  was exercised.
- `UNVERIFIED`: a required branch or runtime boundary was not accessible.
- `HARNESS-INVALID`: the test command did not exercise the intended candidate
  (wrong CWD, missing fixture, argument error, timeout, or setup failure).

Never call a unit-test route assertion “live” and never call a local branch
“released” without separately proving the remote ref and runtime activation.
