# Monitor Stack Config Example

This file documents the runtime configuration consumed by the VPS monitor
scripts. Copy to your own `config.yaml` location and fill values. Do not paste
live secrets or host-specific paths.

```yaml
# ~/.hermes/config.yaml (excerpt — structure only, no live values)
auxiliary:
  vision:
    provider: ""   # e.g. apimaster, openai — placeholder only
    model: ""      # e.g. gpt-5.6-terra — placeholder only
    base_url: ""   # placeholder — do not commit live URL
    api_key: ""    # placeholder — leave empty; inject via env/secret manager
    timeout: 120   # seconds

# Monitor crons (installed via `crontab -l`, not via Hermes cron):
# */5 * * * * /home/ubuntu/.hermes/scripts/post_push_smoke.sh
# 0 1 * * *  /home/ubuntu/.hermes/scripts/auto_after_midnight.sh
# 0 3 * * *  /home/ubuntu/.hermes/scripts/rollback_cleanup.sh

# Receipts (live runtime state — NOT committed):
# ~/.hermes/logs/post-push-smoke.last.json
# ~/.hermes/logs/cron-health.last.json
# ~/.hermes/logs/deployed-runtime-reference.json  # frozen per approval
# ~/.hermes/logs/drift-baseline.txt               # curated, not auto-generated
```
