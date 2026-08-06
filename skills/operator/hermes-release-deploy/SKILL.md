---
name: hermes-release-deploy
description: Procedure for deploying a tested release to the live VPS — validate the exact approved SHA, fast-forward main, build the deployment package from Git objects, create a just-in-time rollback snapshot, deploy atomically via an exact manifest, and verify gateway/WhatsApp/Telegram/E2E with rollback on any failure. Use only after the owner issues APPROVE RELEASE <sha>.
---

# Hermes Release & Deploy

Always-on policy lives in `AGENTS.md`. This skill is the operational procedure
for **promoting and deploying**. If this skill conflicts with `AGENTS.md`,
`AGENTS.md` wins.

## 1. Preconditions (all must hold)

- Owner approval verbatim: `APPROVE RELEASE <exact-sha>`.
- The release candidate SHA equals the temporary branch tip being deployed.
- Live gateway healthy; WhatsApp + Telegram connected; crontab known-hash.
- Gate 1 artifacts and prior rollback snapshots present.

## 2. Validate the deployment package

Deployment manifest: `docs/reconciliation/gate4-deployment-manifest.md`
(or the manifest for the release being deployed).

For every manifest entry, from **Git objects at the release SHA** (never from
an uncontrolled working tree):

- Source path exists at the release SHA.
- Source SHA-256 equals the manifest SHA.
- Destination is an explicit path inside `/home/ubuntu/.hermes`.
- No destination resolves through a symlink outside `/home/ubuntu/.hermes`.
- No wildcard, recursive sync, or delete action.
- No secret/DB/session/memory/log/credential destination.

Record: source hash, current live destination hash, intended post-deploy hash.

## 3. Fast-forward main (no force)

1. Re-read remote `main` immediately before push.
2. Verify the current remote main is an ancestor of the release SHA.
3. `git push origin <release-sha>:main` (ordinary push; no `--force`).
4. If GitHub rejects: HOLD, report the exact protection/error. Never bypass.

## 4. Just-in-time rollback snapshot

Before touching any live destination:

```
mkdir -p /home/ubuntu/backups/gate< N >-predeploy-<timestamp>   # mode 700
```

- Copy the exact current version of every destination file.
- Record absent destinations separately.
- Record SHA-256, permissions, ownership per file.
- Write `rollback.sh` (restore/remove commands) + crontab copy.
- Verify the backup before deployment.

## 5. Controlled atomic deployment

1. Stage all verified source files (temp files in destination dirs).
2. Arm a detached watchdog (restores gateway + crontab) and prove it
   (timer active, ExecStart correct). Keep a standby SSH session.
3. Stop the gateway only after staging + rollback verification pass.
4. Install each file atomically (temp file → rename); preserve modes.
5. Restart gateway + restore/verify crontab immediately.
6. Never overwrite files outside the manifest.

**Any failure** → restore all destinations from the rollback snapshot, remove
only files recorded as previously absent, restart gateway, verify rollback
health, return HOLD.

## 6. Post-deployment verification (all must pass)

- All live destination hashes equal release-source hashes.
- Gateway `active`; WhatsApp `/health` connected, queue 0.
- Telegram transport connected (gateway_state.json).
- Crontab equals predeploy hash.
- Journal: no new traceback/error.
- Med-chain safe smoke passes; P1/P2/effective-done behaviour pass using
  isolated temp-HOME tests.
- DB files present, unmodified by deployment.
- Owner E2E: benign message on WhatsApp AND Telegram, reply within 5 min.

## 7. Finalize

- Create annotated tag `release/<date>-<name>` at the release SHA; push.
- Keep rollback + Gate 1 artifacts.
- Cleanup temporary branches only after production PASS (Gate 7 procedure).

## 8. Never

- Deploy without the exact manifest + approval SHA.
- Deploy with wildcards, directory sync, or deletes.
- Modify `main` before the manifest is validated.
- Deploy secrets, runtime state, DBs, sessions, logs or generated files.
