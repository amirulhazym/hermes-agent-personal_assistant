---
name: hermes-live-audit
description: Read-only audit of live VPS, local application source, nested upstream lineage and remote Git refs. Use before release or when classifying source drift.
---

# Hermes Live Audit

`AGENTS.md` is normative. This skill is read-only evidence collection: no
checkout/fetch/ref mutation, source edit, runtime write, restart, deployment,
or outbound message.

## 1. Label every evidence source

Report remote/API results as `REMOTE-VERIFIED`, local Git/filesystem results as
`LOCAL-VERIFIED`, and direct runtime inspection as `LIVE-VERIFIED`. Do not
upgrade one into another. Record exact full SHAs and command output needed to
reproduce the claim.

Remote heads may include temporary review branches. `main` is the only
permanent application-source branch; do not require a temporary-branch-free
remote as an audit PASS. Use `git ls-remote` for remote state, not local refs.

## 2. Audit identity and topology

From a clean application clone, inspect `git ls-remote origin`, local status,
local `main`, the live runtime root, and the nested upstream clone separately.
Never call the nested branch application `main`, and never use a stale ledger
entry as authorization.

## 3. Classify, then close

For every source-like path, classify exactly one of:

- source match / already represented;
- live-newer source candidate;
- patch/template/sanitized representation;
- private mutable runtime;
- generated/cache/dependency;
- unchanged upstream;
- stale/backup with canonical-preservation reason;
- owner decision.

The closure condition is **zero unclassified source-like paths**, not zero
live/source differences. Drift means capture/reconcile promptly, not
automatically a defect. Preserve paths before excluding them.

## 4. GitHub capability probe

A dry-run push may succeed when valid write authentication exists. Capture
remote refs before and after the probe and prove that no remote ref changed;
do not require the probe to fail. Never perform a real push in an audit.

## 5. Output

Return exact path/count ledgers, source/live/remote provenance, sensitivity and
proposed disposition. Redact secret, medical, account, session and persona
values; metadata, path, size, mode and hashes are sufficient. Include a
no-change proof covering refs, working trees, runtime files, processes and
channels.
