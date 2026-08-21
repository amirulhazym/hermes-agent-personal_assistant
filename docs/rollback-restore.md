# Rollback Restore — LIVE (dry-run tested)

> **Status: LIVE 2026-08-21** — Script deployed. Previously proposal-only (`20260820-rollback-restore.md`).
> Canonical: `scripts/monitor/rollback_restore.sh` (repo) -> live `~/.hermes/scripts/rollback_restore.sh` (5693 bytes, hash 0232195a).

## Live state

- Repo canonical `scripts/monitor/rollback_restore.sh` mirrored to `~/.hermes/scripts/rollback_restore.sh` (hash match).
- Dry-run tested 2026-08-21: `testsha123 --dry-run --rollback-dir /tmp/throwaway-rollback --runtime /tmp/throwaway-runtime` -> `DRY-RUN plan for testsha123 (2 files) ... DRY-RUN OK` exit 0, no `pre-restore` created, no `throwaway-runtime` created, no live capture/copy/restart.

## Production use

**Requires `APPROVE RELEASE`** (or explicit owner approval for live restore). Do NOT run live restore (`--rollback-dir ~/.hermes/hermes-runtime-rollbacks --runtime ~/.hermes/hermes-agent` + gateway restart) without approval. This doc does not authorize production restores; it records that the tool is available and tested.

## Invocation

```bash
# Dry-run (safe, no live mutation):
bash ~/.hermes/scripts/rollback_restore.sh <sha> --dry-run --rollback-dir /tmp/throwaway-rollback --runtime /tmp/throwaway-runtime

# Production (requires approval — not run autonomously):
# bash ~/.hermes/scripts/rollback_restore.sh <sha> --rollback-dir ~/.hermes/hermes-runtime-rollbacks --runtime ~/.hermes/hermes-agent
```
