---
name: hermes-live-audit
description: Procedure for auditing the live VPS state against GitHub main and recorded overlays — verify source identity, process architecture, managed/unmanaged file classification, channel/cron/med/DB health, and GitHub write capability. Zero-mutation audit; produce a classification ledger as evidence. Use for periodic health audits or before/after releases.
---

# Hermes Live Audit

Always-on policy lives in `AGENTS.md`. This skill is the operational procedure
for **auditing** the live runtime vs source. Read-only: no ref mutation, no
process restart, no live file writes, no messages sent.

## 1. Source identity (Requirement A)

From the clean VPS source clone:

- `git ls-remote --heads origin` — exactly one head: `main`.
- `git ls-remote --tags origin` — release + archive tags resolve correctly.
- `git status --short --branch` on the clone — clean, on `main`.
- Record: main SHA, tag objects + peeled commits.

## 2. Process architecture (Requirement B)

- `systemctl --user status hermes-gateway.service` — active, start time.
- `readlink /proc/<pid>/{exe,cwd}` + `gateway_state.json` argv — prove the
  gateway runs from `~/.hermes` runtime + nested `hermes-agent` code.
- WhatsApp bridge child PID; Telegram = in-process transport.

## 3. Managed mapping comparison (Requirement C)

From the deployment manifest (per-file SHA-256):

- For every managed source path: `git show <main>:<path> | sha256sum` vs
  `sha256sum <live-destination>`.
- For overlay patches: `git apply --reverse --check` on the nested repo.
- Report MATCH / PARTIAL DRIFT / MISSING per mapping.
- Drift is expected for runtime-only paths (DBs, config, sessions, logs,
  memories, med state) — classify, do not flag as defect.

## 4. Unexpected drift / source candidates (Requirement E)

- Post-release scan: files newer than the deploy timestamp with source-like
  extensions, excluding runtime dirs → report (should be zero).
- Nested repo untracked/modified classification:
  - overlay-new files (in recorded patch),
  - upstream-tree-only (verify `git cat-file -e origin/HEAD:<path>`),
  - local-only (not in patch, not upstream),
  - runtime/install metadata, stale backups.
- `git check-ignore` each candidate; nothing should be silently hidden.

## 5. Health (Requirement G)

- Gateway, WhatsApp, Telegram states.
- Crontab SHA-256 (and note the MD5-vs-SHA256 pitfall — record SHA-256).
- Med-chain smoke (read-only `chain_calc.py --next`), med JSON validity.
- Journal: no tracebacks; classify transient items (503 retries, benign
  warnings) separately.
- DBs open read-only via sqlite3 `mode=ro`; quick_check.

## 6. GitHub capability (Requirement H)

- `git remote -v` (no embedded creds), credential helper, `~/.ssh`,
  `gh` CLI presence.
- `GIT_TERMINAL_PROMPT=0 git push --dry-run origin HEAD:<temp-ref>` — must
  fail with no remote ref created; proves auth status without mutation.

## 7. Report

Output a zero-mutation audit report with: verdict (PASS/HOLD), raw command
evidence, managed/unmanaged classification ledger, health table, and
recommended follow-ups. Redact all secret values — names/paths/hashes only.

## 8. Never

- Send automated messages, restart processes, write live files, create refs,
  or change configuration during the audit.
- Record secret values; expose only names, types, sizes, hashes, classifications.
