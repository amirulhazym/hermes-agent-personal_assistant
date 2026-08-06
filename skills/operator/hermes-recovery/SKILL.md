---
name: hermes-recovery
description: Procedure for recovering the Hermes Agent system after failure or data loss — restore source from Git/tags, restore runtime from Gate 1 encrypted artifacts or the latest predeploy rollback snapshot, validate gateway/crontab/channels, and verify database integrity. Use when the gateway is down, files are missing/corrupt, or a deployment failed.
---

# Hermes Recovery

Always-on policy lives in `AGENTS.md`. This skill is the operational procedure
for **recovery**. If this skill conflicts with `AGENTS.md`, `AGENTS.md` wins.

## 1. Assess first (read-only)

- Gateway state: `systemctl --user is-active hermes-gateway.service`.
- Crontab: `crontab -l | sha256sum` vs recorded hashes.
- Channels: WhatsApp `/health`, `gateway_state.json` telegram state.
- Journals: `journalctl --user -u hermes-gateway.service -n 50`.
- Which layer failed: source clone, live runtime files, DB, config, sessions,
  or process.

## 2. Restore source (from Git, not live copies)

- Clean source clone on VPS: fetch origin, `git checkout main`,
  `git merge --ff-only origin/main`, verify SHA.
- PC clone: same procedure.
- Do NOT restore source from `~/.hermes` or `~/.hermes/hermes-agent`.

## 3. Restore runtime (two tiers)

### Tier 1 — recent predeploy rollback snapshot (fastest)
`/home/ubuntu/backups/gate<N>-predeploy-<timestamp>/` contains:
`rollback.sh` (restore/remove commands), `snapshot.txt` (hashes/modes/owners),
crontab copy. Run `rollback.sh`, then verify each restored hash.

### Tier 2 — Gate 1 encrypted preservation (deep)
`/home/ubuntu/backups/gate1/` (VPS) and `D:\hermes-gate1\vps` (PC):

- Runtime tree: `runtime/*_runtime.tar.gpg`
- Databases: `databases/*_databases.tar.gpg`
- Git dirs: `gitdirs/*.tar.gpg`
- Bundles: `bundles/*.bundle`

Decrypt with the Gate 1 passphrase (owner-held in their password manager).
Restore only the paths that failed; never blanket-overwrite newer live state.

## 4. Validate after restore

- All restored file hashes match the snapshot/manifest.
- Gateway `active`; crontab hash matches; WhatsApp `/health` connected;
  Telegram connected.
- Med-chain safe smoke: `chain_calc.py --next` exits 0.
- Database integrity: `PRAGMA integrity_check` + `foreign_key_check` on
  restored copies (never the production original as a test target).
- Journal: no new tracebacks.
- Owner E2E on WhatsApp + Telegram (benign messages, reply within 5 min).

## 5. Post-recovery

- Update the operation ledger with the incident + recovery evidence.
- If recovery used Gate 1 artifacts, note that a fresh Gate 1 capture may be
  needed to re-anchor preservation at the new state.

## 6. Never

- Delete or overwrite preservation/rollback artifacts without explicit approval.
- Test against production DBs; always use restored copies.
- Print or transmit the Gate 1 passphrase.
- Restore without verifying hashes afterwards.
