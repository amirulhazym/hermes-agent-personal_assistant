# Governance v2 Deployment Manifest (data only — NOT executed)

> For the operator-governance-v2 release. Deployment requires separate
> explicit owner approval: `APPROVE RELEASE <sha>`.
> No wildcards, no directories, no deletes. Destinations inside
> /home/ubuntu/.hermes. Rollback via just-in-time snapshot (per
> hermes-release-deploy) + Gate 1 artifacts.

| Source (release SHA) | Source SHA-256 | Live destination | Action |
|---|---|---|---|
| AGENTS.md | computed-at-release | /home/ubuntu/.hermes/AGENTS.md | add/replace |
| skills/operator/hermes-source-change/SKILL.md | computed-at-release | /home/ubuntu/.hermes/skills/operator/hermes-source-change/SKILL.md | add |
| skills/operator/hermes-release-deploy/SKILL.md | computed-at-release | /home/ubuntu/.hermes/skills/operator/hermes-release-deploy/SKILL.md | add |
| skills/operator/hermes-live-audit/SKILL.md | computed-at-release | /home/ubuntu/.hermes/skills/operator/hermes-live-audit/SKILL.md | add |
| skills/operator/hermes-recovery/SKILL.md | computed-at-release | /home/ubuntu/.hermes/skills/operator/hermes-recovery/SKILL.md | add |
| scripts/guard/secret-scan.sh | computed-at-release | /home/ubuntu/.hermes/scripts/guard/secret-scan.sh | add |
| scripts/guard/docs-allowlist-check.sh | computed-at-release | /home/ubuntu/.hermes/scripts/guard/docs-allowlist-check.sh | add |
| scripts/guard/manifest-validate.sh | computed-at-release | /home/ubuntu/.hermes/scripts/guard/manifest-validate.sh | add |
| operations/ledger.json | computed-at-release | /home/ubuntu/.hermes/operations/ledger.json | add/replace |
| operations/README.md | computed-at-release | /home/ubuntu/.hermes/operations/README.md | add |

## Notes
- No `.hermes.md` or `HERMES.md` exists on the live runtime (verified
  2026-08-06) — `AGENTS.md` will be the active project-context file.
- Runtime state, config.yaml real values, DBs, sessions, logs, memories,
  med state are NOT in this manifest.
- Post-deploy: gateway does NOT need a restart for skill/context files;
  verify hashes + owner E2E per hermes-release-deploy.
