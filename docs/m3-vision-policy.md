# M3 Vision Policy — LIVE

> **Status: LIVE 2026-08-21** — Implementation complete. Previously proposal-only (`20260820-m3-vision-policy.md`).
> See live files: `~/.hermes/config-templates/auxiliary-vision.yaml`, `~/.hermes/policies/vision-semantic-only.md`, `~/.hermes/docs/m3-vision-policy.md`, `~/.hermes/skills/vision-semantic-only/SKILL.md`.

## What was done (2026-08-21)

1. **Config-as-code** `~/.hermes/config-templates/auxiliary-vision.yaml` — `auxiliary.vision: provider=apimaster model=gpt-5.6-terra` (api_mode intentionally absent — deepseek fabricated fallback with success=true).
2. **Policy file** `~/.hermes/policies/vision-semantic-only.md` + live docs mirror `~/.hermes/docs/m3-vision-policy.md`.
3. **Prompt-injection wire** `~/.hermes/skills/vision-semantic-only/SKILL.md` (injects `<vision_policy>SEMANTIC-ONLY</vision_policy>`) + `hooks/skill-trigger/handler.py` patterns `vision_analyze` / `\bvision\b` -> `vision-semantic-only`.

## Rule

Vision output is **semantic-only** — never authoritative for numbers, hashes, CI/deploy state, file contents, or security findings. Re-verify via direct tool/API/filesystem.

## Test

Trigger `vision_analyze` -> `triggered_skills.txt` contains `vision-semantic-only` -> skill loads `<vision_policy>SEMANTIC-ONLY</vision_policy>` block. Verified 2026-08-21: `Wrote ... triggered_skills.txt: vision-semantic-only`.

## Config template usage

```bash
# On a new host after hermes setup:
yq -i '.auxiliary.vision = {"provider":"apimaster","model":"gpt-5.6-terra"}' ~/.hermes/config.yaml
# Or apply template:
cp ~/.hermes/config-templates/auxiliary-vision.yaml /tmp/ && yq eval-all 'select(fileIndex==0) * select(fileIndex==1)' ~/.hermes/config.yaml /tmp/auxiliary-vision.yaml
```
