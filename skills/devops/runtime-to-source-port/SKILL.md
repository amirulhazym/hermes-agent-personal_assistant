---
name: runtime-to-source-port
description: Port runtime artifacts into source clone safely.
version: 1
author: hermes-operator
license: MIT
metadata:
  hermes:
    tags: [git, source-preservation, manifest, release-gate, reconciliation]
    related_skills: [devops/git-repository-reconciliation, agent-methodology/verification-before-completion]
---

# Runtime → Source Port (manifest-gated capture)

## When to use
- The user wants installed/working artifacts (skills, hooks, plugins, agents,
  configs) made durable in the source clone.
- The durable repo has: a `docs/.../v3-source-coverage-manifest.json` (or similar)
  whose validator recomputes `sha256(git show {release_sha}:{source})` per entry,
  and an AGENTS.md/operator constitution requiring `APPROVE RELEASE <full-sha>`
  before `main` promotion.
- Live runtime (`~/.hermes/...`) is NOT the source clone. Do not commit from runtime.

## Core principle
A file existing only in the live runtime is **present but not durable**. The source
clone starts clean; `git add` there stages nothing until you copy the payload in.
And even after copying + committing, the repo constitution blocks push until the
exact-SHA release approval is issued. Treat these as separate, labeled states:
`staged → committed-local → validated-at-SHA → pushed → released-live`. Never call a
local commit "released" or "ready to push" without the approval gate.

## Procedure
1. **Inventory** the live-runtime packages; record exact file lists + counts.
   Confirm the source clone does NOT already contain them (use `search_files`
   with `target='files'`, or a `terminal` absent check — never trust a stale list).
2. **Copy** each package into the matching path under the source clone
   (`skills/productivity/...`, `skills/software-development/...`, etc.).
   - Check for nested `.git` in copied dirs → must be 0.
   - Check for `.gitattributes` in the repo (eol normalization can silently break
     sha256 manifest validation). No `.gitattributes` = no normalization surprise.
3. **Hash + append manifest entries.** Entries are **per-file**, not per-directory.
   For each file: `sha256`, append
   `{"destination": null, "kind": "source-only", "source": "<repo-relative-path>", "source_sha256": "<hash>"}`.
   Verify runtime vs source byte-identical before hashing. Reject duplicate sources.
   Leave `candidate_sha` as its placeholder (`PENDING_OWNER_RELEASE`) — the validator
   permits a placeholder that differs from the release SHA; do NOT set it to the
   commit you are about to make.
4. **Pre-commit privacy gates:** run the repo's `secret-scan.sh --staged` and a PII
   heuristic (email/phone) over the new files. Do not skip because the source is
   "trusted." Expect `SECRET-SCAN PASS` + no PII hits.
5. **Commit locally only**, scoped to the payload. Tree must be clean after
   (`porcelain_count=0`).
6. **Post-commit validator gate:** run the manifest validator against the NEW
   commit SHA: `bash scripts/guard/manifest-validate.sh <manifest.json> <new_sha>`.
   Expect `MANIFEST-VALIDATE PASS: parsed=N validated=N`. A pre-commit run would
   legitimately fail (files not yet committed) — post-commit is the real gate.
7. **STOP — release approval required.** Report the final SHA and ask for
   `APPROVE RELEASE <full-sha>`. Do not auto-promote, do not push, no force-push.

## Pitfalls
- Editing/committing from the live runtime tree instead of the source clone.
- Assuming `git add` in a clean source clone stages something — it stages nothing
  until the payload is copied in.
- Per-directory manifest entries — the validator requires per-file rows.
- Setting `candidate_sha` to the new commit before validation (leave as placeholder).
- Calling a local commit "released/ready to push" without the explicit
  `APPROVE RELEASE <sha>` (constitution §5).
- Skipping the post-commit manifest validation because a pre-commit run "failed"
  — that failure is a validator-boundary artifact, not a blocker.

## Reusable script + exact commands
See `references/manifest-gated-port.md` for the copy/hash/append Python, the
staged secret/PII gate, and the post-commit validator command.
