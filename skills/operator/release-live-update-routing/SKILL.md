---
name: release-live-update-routing
description: Use when changing production self-update routing.
---

# Release/Live Update Routing

Use this skill when a CLI, gateway, dashboard, desktop updater, bootstrap
installer, or shell script can mutate a Hermes checkout or select the branch
used for production updates.

## Objective

Keep production self-updates deterministic and fail-closed:

- the production default route is `origin/release/live`;
- unattended callers pass `--yes --branch release/live` explicitly;
- a dirty or unmerged checkout is rejected before any updater side effect;
- update intake is origin-only, with no upstream remote intake or fork push;
- fast-forward failure/divergence stops without `reset --hard`;
- explicit developer branch selection remains possible only when isolated from
  production entrypoints.

## Procedure

1. **Freeze scope and identity.** Record the candidate path, branch, exact HEAD,
   merge-base, configured remotes, and direct remote refs with `git ls-remote`.
   Keep local candidate, remote target, deployed files, and loaded runtime as
   separate evidence layers.
2. **Enumerate every entrypoint before editing.** Inspect the CLI parser and
   resolver, update implementation, gateway slash handler, dashboard action,
   desktop/bootstrap handoff, and installer scripts. Search for the requested
   route literally; if `/update/unattended` does not exist, identify the actual
   unattended equivalent instead of inventing a route.
3. **Define the route contract once.** Production code should resolve the
   default to `release/live`. Every unattended production caller should pass the
   branch explicitly, rather than relying on an ambient parser default. Keep
   `--branch` as a developer override only if production callers cannot inherit
   or forward it accidentally.
4. **Put the dirty-tree gate first.** Run
   `git status --porcelain=v1 --untracked-files=all` and fail closed for any
   tracked, staged, untracked, or unmerged entry. This check must precede
   backups, locks/markers, process pausing, git config or cleanup, fetch,
   stash, checkout, merge, reset, dependency installation, and restart. Do not
   use autostash to make a production update appear safe.
5. **Constrain remote intake.** Fetch and compare only `origin/<branch>`.
   Remove or bypass fork/upstream synchronization, `remote add upstream`,
   `fetch/pull upstream`, and any update-time push. Apply this rule to
   `--check` as well as the mutating update path, including explicit developer
   `--branch main` calls.
6. **Handle divergence conservatively.** Use `merge --ff-only
   origin/<branch>`. If it fails, report the failure and stop nonzero. Do not
   fall back to `git reset --hard` to repair divergence. Do not restore a stash
   or continue dependency/restart work after the failed code update.
7. **Wire unattended callers explicitly.** Test the exact generated argv or
   shell command from gateway, dashboard, desktop, bootstrap, and installer
   paths. The production form is `update --yes --branch release/live` plus
   each caller's required gateway/force flags.
8. **Test negative space.** Capture subprocess calls and assert forbidden
   commands never occur. Cover dirty tracked, staged, untracked, and unmerged
   states; ff-only divergence; upstream/fork-shaped origins; default routing;
   explicit developer routing; and each unattended entrypoint.
9. **Verify without overstating.** Run targeted route and guard tests, then the
   canonical broader suite as a separate evidence layer. Report missing remote
   branches, stale moving targets, unresolved worktree state, harness-invalid
   runs, and untested runtime activation explicitly.

## Design guidance

Prefer one small resolver and one small preflight seam reused by all production
callers. Do not duplicate branch literals across unrelated business logic when
an explicit production adapter can own the contract. Conversely, do not hide
production policy in a generic developer-facing `--branch` parser default.

Treat all update-side mutations as part of the safety boundary. A backup,
update lock, marker write, line-ending normalization, lockfile cleanup, or
process pause is still a side effect that must not happen before the dirty-tree
failure decision when the contract requires no mutation.

## Required test matrix

- Default CLI update fetches, compares, and merges `origin/release/live`.
- `--check` also uses only `origin/release/live` by default.
- Explicit developer `--branch X` targets only `origin/X` and does not activate
  upstream/fork synchronization.
- Dirty tracked, staged, untracked, and unmerged trees fail before any mutating
  or side-effect subprocess.
- Failed `merge --ff-only` exits nonzero and issues no `reset --hard`, stash
  restore, dependency install, or restart.
- Gateway and dashboard unattended commands contain `--yes --branch
  release/live`.
- Desktop/bootstrap/installer command builders default to `release/live` and
  do not carry a hidden `main` fallback.
- No update path adds/fetches/pulls an `upstream` remote or pushes to origin.

## Pitfalls

- Changing only `_resolve_update_branch()` is insufficient: unattended callers
  may pass bare `update`, and `--check` may have a separate upstream probe.
- Removing upstream logic only from the normal update path is insufficient if
  fork synchronization is still called when the checkout is already current.
- A dirty check after backup, lock acquisition, or cleanup violates the
  fail-before-mutation requirement even if Git itself was not changed yet.
- A test that asserts only the final branch is weak; assert the complete command
  sequence and the absence of forbidden commands.
- Do not claim `/update/unattended` coverage until a literal search proves that
  route exists; map the real dashboard/gateway unattended surface instead.
- A successful unit test against a fixture does not prove that the remote
  `release/live` ref exists or that a running gateway loaded the change.

## Reference

See `references/release-live-update-routing.md` for the entrypoint audit matrix,
negative-space test template, and evidence/status vocabulary.
