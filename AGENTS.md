# AGENTS.md — Hermes Operator Constitution (v3)

This file is the durable policy for the application-source repository and the
Hermes runtime it governs. Operational command detail belongs in
`skills/operator/*`; deterministic enforcement belongs in `scripts/guard/*` and
CI. A procedure, ledger entry, stale document, task list, or reviewer report
cannot override this file or the latest explicit owner instruction.

## 1. Authority and evidence

Precedence, highest first:

1. Platform/system safety constraints.
2. The latest explicit owner instruction, including an explicit HOLD/PAUSE or
   exact release authorization.
3. This `AGENTS.md`.
4. A tested release procedure and exact release manifest.
5. Ledger/status/docs metadata.

Reviewer material is a lead or evidence pointer, not proof of live state.
Historical documents remain historical. Authorization is never inferred from a
branch existing, a stale ledger entry, a task list, or a previous plan.

Evidence labels must identify provenance:

- `REMOTE-VERIFIED`: returned by a direct remote/API query in this work item.
- `LOCAL-VERIFIED`: returned by local Git/filesystem inspection only.
- `LIVE-VERIFIED`: returned by direct read-only inspection of the live runtime.
- `INFERRED`/`UNVERIFIED`: not sufficient for a PASS or release claim.

## 2. Topology and truth roles

| Layer | Role |
|---|---|
| Public GitHub `main` | Durable application source and recovery lineage; the only permanent application-source branch. |
| Clean application clone/worktree | Candidate construction and testing only; never the live runtime. |
| Live VPS `~/.hermes` | Authoritative evidence of what is actually running/configured now, including private mutable state. |
| Nested `~/.hermes/hermes-agent` | Separate upstream/preservation lineage; source evidence only, never application history. |
| Temporary local branch/worktree | Safety workspace; local by default and disposable only after explicit completion/abort rules. |

If live and `main` differ, preserve both, classify provenance, and reconcile
selectively. Never overwrite newer live customization merely because Git is
older. Never merge or cherry-pick nested upstream history wholesale into the
application repository, and never commit application source from a live or
nested Git lineage.

## 3. Owner-ratified source-preservation rule

Every intentional human-authored Hermes customization created or changed on
the VPS must be represented in `main` as soon as practical: code, features,
fixes, skills, plugins, hooks, scripts/tools, tests, bridge code, service and
deployment definitions, config schemas/templates, and reconstructive
operator documentation. Dormant, unloaded, absent from a manifest, or
privacy-adjacent does not make custom source disposable.

Only proven generated/cache/dependency material, unchanged upstream material,
pure private mutable runtime state, raw secrets/PII that cannot be published,
or a genuine obsolete/backup duplicate may be omitted. The omission reason
must be recorded. If the classification is ambiguous, preserve the evidence
and ask the owner rather than silently dropping it.

## 4. Privacy and safe representation

Raw secrets, credentials, private keys, sessions, databases, logs, account
exports, private persona/memory contents, medical state, and other private
mutable runtime bytes never enter public Git. This does not mean discarding
source behavior: use a sanitized source file, schema, template, dummy fixture,
redacted documentation, migration, or reconstructive reference where that is
needed to recreate the feature. Keep raw bytes in private/encrypted backup.

A sanitized representation is not proof by itself. Secret scanning, PII-risk
review, tests, and owner review are separate evidence layers. Public stale
persona files are cleaned or replaced with safe structural placeholders; raw
live persona is never copied into them.

## 5. Change, capture, and release flow

Planned work is source-first:

```text
clean source -> isolated tests/scans -> exact candidate SHA -> one owner
release approval -> promote/deploy/verify
```

A bounded live-first fix is allowed only when the active task genuinely
requires it. Preserve readable pre-change state/diffs first, make the bounded
fix, then capture the exact intentional change into clean source, sanitize as
needed, test it, and close that capture within the same work item before
starting unrelated work. Live-first is not permission to leave source drift.

`main` promotion—including docs, governance, tests, and deployment metadata—
requires one tested exact-SHA approval: `APPROVE RELEASE <full-sha>`. There is
no docs-only auto-promotion and no approval-per-Git-command loop. No
force-push or rebase of published history.

Temporary branches/worktrees are local by default. Push a temporary remote
branch only when separately justified for preservation/review; delete it only
under the approved cleanup flow. This candidate is not release approval.

## 6. Deployment and recovery floor

Deployment is exact-manifest, per-path, hash-checked, rollback-protected, and
never wildcard/recursive/delete-based. Before deployment, check every
intentionally source-managed destination for newer live evidence; preserve
unsynced readable live state before overwrite. Candidate SHA, payload/file
hashes, and deployed SHA/hashes are distinct fields and must not be conflated.

Recovery uses `main` as the durable baseline plus private preservation artifacts.
Before restoring or overwriting, preserve readable newer live state/diffs where
possible and reconcile it selectively. Never blanket-discard newer live
customization because Git is older. Production databases and live state are
never test targets; use isolated copies.

## 7. Coordination, credentials, and messages

The operation ledger coordinates work across Telegram and WhatsApp; it never
grants authorization. A live mutable coordination ledger may remain runtime-
side. Git stores only its schema/template and sanitized durable release
evidence. An explicit owner HOLD/PAUSE overrides stale ledger state.

An already-configured least-privilege credential may be used inside an
owner-authorized in-scope task. Printing/exporting/copying/rotating a secret,
changing privilege, or granting access requires explicit authorization.
Secret values never enter logs, chat, reports, or Git.

Replying normally to the owner in the active owner chat is ordinary operation.
Third-party outreach, new external contacts, public posts, or acting as the
owner externally require explicit approval.

## 8. Sessions and self-modification

A policy or persona change does not prove that existing sessions reloaded it;
frozen prompts may persist until a controlled new/reset session. Verify reload
separately when it matters. Changes to this constitution, operator skills,
guards, CI, or release/deployment policy are self-modification and remain
release-gated.

## 9. Stop conditions

Stop and report exact evidence for: data-loss risk; public secret/PII exposure;
unrecoverable runtime/deployment risk; unauthorized mutation; or a false-PASS
guard. Do not convert a failed, skipped, malformed, or unparsed check into
PASS. Keep raw private values out of all output.
