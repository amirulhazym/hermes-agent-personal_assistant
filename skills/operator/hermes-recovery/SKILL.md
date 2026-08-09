---
name: hermes-recovery
description: Evidence-first recovery of Hermes source and runtime after failure, preserving newer live customization before restore.
---

# Hermes Recovery

`AGENTS.md` is normative. Assess read-only first and identify which layer
failed: application source, nested upstream, runtime files, config, database,
session, process or channel.

## 1. Preserve before overwrite

Before restoring or overwriting anything, preserve readable live state, diffs,
metadata and hashes where possible. A newer live customization that has not
yet been captured into `main` is evidence to reconcile, not disposable drift.
Do not blanket-copy or blanket-delete.

## 2. Restore the durable baseline

Use the exact approved `main` SHA as the application-source baseline and use
private/encrypted preservation artifacts for secrets and mutable runtime state.
The nested upstream clone and live runtime are evidence/donor layers, not the
application Git lineage. Never merge their history wholesale.

Restore only explicitly affected paths. Keep raw secrets, sessions, databases,
medical state, memories and logs private. Use sanitized templates/schema/dummy
fixtures for reconstructable behavior.

## 3. Validate in isolation

Verify restored hashes, modes and ownership; gateway/channel/cron health; and
DB integrity on restored copies, never on production originals. Run targeted
and integration tests with an isolated temporary HOME. Any mismatch is HOLD,
not a rounded-up PASS.

## 4. Post-recovery

Record what was restored, what newer live evidence was preserved, and what must
be captured/backported into clean source. The ledger coordinates this work but
cannot authorize it. Preserve Gate-1 and rollback artifacts unless the owner
separately authorizes deletion.
