# Monitor Stack

Live monitoring scripts are installed under `~/.hermes/scripts/` on the VPS.

Canonical source representation lives under [`scripts/monitor/`](../../scripts/monitor/)
in this repo. Do not run those repo copies on the live host — the host runs
its `~/.hermes/scripts/` copies; the repo copies exist for audit, review, and
reconstruction.

| Live path | Repo path | Purpose |
|---|---|---|
| `~/.hermes/scripts/post_push_smoke.sh` | `scripts/monitor/post_push_smoke.sh` | Read-only smoke check |
| `~/.hermes/scripts/rollback_list.sh` | `scripts/monitor/rollback_list.sh` | List rollback artifacts |
| `~/.hermes/scripts/rollback_cleanup.sh` | `scripts/monitor/rollback_cleanup.sh` | Cron cleanup |
| `~/.hermes/scripts/auto_after_midnight.sh` | `scripts/monitor/auto_after_midnight.sh` | Post-midnight diagnostics |
| `~/.hermes/scripts/cron_health_report.py` | `scripts/monitor/cron_health_report.py` | Cron health |

Crons (user crontab, not Hermes cron):
```text
*/5 * * * * /home/ubuntu/.hermes/scripts/post_push_smoke.sh >> ~/.hermes/logs/post-push-smoke.cron.log 2>&1
0 1 * * *  /home/ubuntu/.hermes/scripts/auto_after_midnight.sh
0 3 * * *  /home/ubuntu/.hermes/scripts/rollback_cleanup.sh
```

Receipts (live, NOT in repo):
- `~/.hermes/logs/post-push-smoke.last.json`
- `~/.hermes/logs/cron-health.last.json`
- `~/.hermes/logs/deployed-runtime-reference.json` (frozen reference per approval: `8f4620e461d811fbf272baa7ae4ecc69aa4f39e9`)
- `~/.hermes/logs/drift-baseline.txt`

Config placeholder: `docs/monitor-config.example.md`.

Recovery note: after `APPROVE RELEASE <sha>` that touches `scripts/monitor/`,
the new repo copies become the reference; live `~/.hermes/scripts/` remains the
authoritative running copy until explicitly refreshed under owner approval.
