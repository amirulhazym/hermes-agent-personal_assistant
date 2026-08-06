# Gate 4 Deployment Manifest (dry run — NOT executed)

Future source → live mapping after integration promotion to main. Live = /home/ubuntu/.hermes.

| Source path (integration) | Live destination | Action |
|---|---|---|
| scripts/chain_calc.py | scripts/chain_calc.py | replace (after test+approval) |
| scripts/chain_monitor.sh | scripts/chain_monitor.sh | replace |
| scripts/test_effective_done.py | scripts/test_effective_done.py | add (test-only) |
| skills/med-tracker/references/20260729-cli-confirmation-and-future-intent.md | skills/med-tracker/references/ | add |
| skills/med-tracker/references/compound-runtime-drift-20260804.md | skills/med-tracker/references/ | add |
| skills/med-tracker/references/dexa-resolver-and-timing.md | skills/med-tracker/references/ | add |
| patches/upstream-hermes/* | ~/.hermes/hermes-agent (via git apply, base 2bd1977d8/f94dff11e) | apply per README |

NOT deployed (runtime-only): config.yaml real values, cron/jobs.json, memories/, state.db, sessions, med-*.json, chain-state.json.
Deploy requires: explicit approval, gateway restart coordination (P1 HEADS_UP_WINDOW_MIN=30 heads-up), post-deploy E2E on WhatsApp+Telegram, rollback = Gate 1 encrypted artifacts.
