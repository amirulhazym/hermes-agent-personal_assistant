# Isolated live-base rebuild and verification

Use when a prepared update/candidate cannot apply cleanly to the running Hermes source because its Git lineage or working-tree overlay differs from the patch base.

## Invariants

- Do not force-apply, use `--3way`, or overwrite live to make an old patch fit.
- Treat the running worktree as operational truth. First prove a checkpoint matches its exact HEAD, tracked changes, untracked source records, modes, and symlinks.
- Materialize the candidate from that verified checkpoint in an isolated workspace. Never test against the live directory.
- Port the old update as a **semantic delta**, path by path. A clean patch application is not evidence of compatible behavior.
- Preserve an existing live customization when the old update would weaken or replace it. Record the behavior conflict explicitly; do not silently broaden routing, bypass a fail-closed gate, or rewrite custom state merely to make legacy tests pass.
- Define the deployment delta as `verified live pre-update state -> rebuilt candidate`; it must contain only justified update changes, not a wholesale re-copy of the live overlay.

## Verification order

1. Run focused tests for the ported behavior and explicit regression tests for preserved custom behavior.
2. Parse/check data files changed by the port (for example YAML locale files) and run `git diff --check`.
3. Run the authoritative suite in a disposable `HOME`/`HERMES_HOME`.
4. Ensure that disposable HOME contains every runtime extension required by source tests (e.g. hooks, skills, plugins, agents, scripts) plus an available venv. If a failure is a missing fixture/extension in that disposable environment, label it **test-environment failure**, repair the isolated harness, and rerun; do not call it an update regression.
5. Keep test-environment failures separate from candidate code failures in the result.

## Completion boundary

Only after a tested exact SHA and an exact deployment-path manifest exist may the owner be asked for a separate live-swap/restart approval. Candidate construction, push, disk writes, live deployment, restart, and user-visible runtime smoke tests are distinct states.
