# Gate 4/5 Deployment Manifest (data only — NOT executed)

> Integration SHA at manifest time: f0f91329e6e945af93a08c58e89e0552dfdbecd3
> Deployment requires separate explicit owner approval. This document maps exact
> source files to exact live destinations. No wildcards, no directories, no deletes.

| Source (integration f0f91329e6e945af93a08c58e89e0552dfdbecd3) | Source SHA-256 | Live destination | Action |
|---|---|---|---|
| scripts/chain_calc.py | 2119168801631280663b77e014eaf7c3740793e5c6dfaace39dfe3fdac425826 | /home/ubuntu/.hermes/scripts/chain_calc.py | replace |
| scripts/chain_monitor.sh | b5d005d38a6133f631bdfd395d1c490ba914a7d6f94688cccc607df8c12a7c77 | /home/ubuntu/.hermes/scripts/chain_monitor.sh | replace |
| scripts/test_effective_done.py | 7689f060684a008042440983aa47e9a55c25afe3a365487011c7a9479ccb0eb3 | /home/ubuntu/.hermes/scripts/test_effective_done.py | add (test-only) |
| skills/med-tracker/references/20260729-cli-confirmation-and-future-intent.md | d75ebbd47e8760e7cc092432437562e2a83eb7192b2b787d2fad9866c80ac2f8 | /home/ubuntu/.hermes/skills/med-tracker/references/ | add |
| skills/med-tracker/references/compound-runtime-drift-20260804.md | 7d698048e91d2db031ad9c9397503afa5ae86c838066ac273faf2f38884147fa | /home/ubuntu/.hermes/skills/med-tracker/references/ | add |
| skills/med-tracker/references/dexa-resolver-and-timing.md | 18a44fe9e662844022650317e257c271148e79ca7aec4a7627e28c0dc00f98c1 | /home/ubuntu/.hermes/skills/med-tracker/references/ | add |
| patches/upstream-hermes/2026-08-06_p1c-selected-model-contract.patch | 0e8b3e255bb786ceb3caa7587130c51afcb505b5e9173d74db95e0edf58204f2 | /home/ubuntu/.hermes/hermes-agent (apply vs 2bd1977d8) | git apply |
| patches/upstream-hermes/2026-08-06_vps-runtime-overlays.patch | 43ace7847b1076c9fc595cb5feea4a1e1c91ae6822f2291d6b6aced88e4a6f5d | /home/ubuntu/.hermes/hermes-agent (apply vs f94dff11e) | git apply |
| patches/upstream-hermes/README.md | eb2334590e233aec9676a58776af5ff96572cf6f3247cfdfeadc289a9162b58d | /home/ubuntu/.hermes/hermes-agent/ (reference) | add |

## Rollback
Every destination is covered by Gate 1 encrypted artifacts (VPS /home/ubuntu/backups/gate1:
runtime archive + databases + gitdirs; D:\hermes-gate1\vps). Pre-deploy, record live SHA-256
of each destination; on failure restore from Gate 1 artifacts and restart gateway.

## Explicitly NOT deployed
config.yaml real values, cron/jobs.json, memories/*, state.db (+wal/shm), sessions/, logs/,
med-*.json, chain-state.json, .env*, web-operator bridge state, agents/ accounts.

## Deploy preconditions
1. Owner explicit approval of this manifest.
2. P1 heads-up (HEADS_UP_WINDOW_MIN=30) before any gateway restart.
3. Post-deploy E2E on WhatsApp + Telegram; rollback via Gate 1 artifacts if either fails.
