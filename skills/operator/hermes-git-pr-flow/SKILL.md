---
name: hermes-git-pr-flow
description: Hermes Git autonomous publication flow for protected main branches.
---

# Hermes Git Protected-Main Publication Flow

Use when branch protection on `main` is active. This flow is **autonomous and end-to-end**: do NOT ask the owner to open GitHub, manually create PRs, click merge, or reply "done".

## Flow (Autonomous Protected-Main Publication)

1. **Commit on Main**: Develop and commit on clean local `main` with conventional commits (`type(scope): msg`).
2. **Quality & Security Gates**:
   - `bash scripts/guard/secret-scan.sh --tree` → PASS
   - `python3 scripts/guard/pii-review.py --diff origin/main..HEAD` → PASS
   - `bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json $(git rev-parse HEAD)` → PASS (if manifest modified, run `python3 scripts/guard/manifest_recompute.py docs/reconciliation/v3-source-coverage-manifest.json HEAD` first)
   - `bash scripts/run_contract_tests.sh` → PASS
3. **Autonomous Publication Execution**:
   - Resolve `GITHUB_TOKEN` from `~/.hermes/.env`.
   - Push commit to a deterministic remote publication branch (`feat/<slug>` or `nightly/publication-<id>`).
   - Create or reuse PR via GitHub REST API (`POST /repos/{owner}/{repo}/pulls`).
   - Observe CI status checks via REST API (`GET /commits/{head_sha}/check-runs`) until all checks pass (`status=completed, conclusion=success`).
   - Merge PR automatically via REST API (`PUT /pulls/{pr}/merge` with `merge_method: squash`).
   - Delete the remote publication branch via Git/REST (`git push origin --delete <branch>`).
   - Sync local `main` to `origin/main` (`git fetch origin main && git reset --hard origin/main`).
4. **Verification**:
   - `HEAD == origin/main`
   - `git status` shows 0 ahead / 0 behind, clean working tree
   - No stale publication branches remain on local or remote.

