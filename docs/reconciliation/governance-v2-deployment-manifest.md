# Governance v2 Deployment Manifest (data only — NOT executed)

> For the operator-governance-v2 release. Deployment requires separate
> explicit owner approval: `APPROVE RELEASE <sha>`.
> No wildcards, no directories, no deletes. Destinations inside
> /home/ubuntu/.hermes. Rollback via just-in-time snapshot (per
> hermes-release-deploy) + Gate 1 artifacts.
>
> Release SHA: 1d00a622750a0248cc511155cedb63eed0ca7de0

| Source (release 1d00a62) | Source SHA-256 | Live destination | Action |
|---|---|---|---|
| AGENTS.md | 2ca6a80010ac887d029e6f7c0285a754cd2650f1633e1903a562a555812d3ed0 | /home/ubuntu/.hermes/AGENTS.md | add/replace |
| skills/operator/hermes-source-change/SKILL.md | 04ffe97abf9c985adbc3ed7b9f4ed5cf8c281bbc4171086e3714f584671b5bdf | /home/ubuntu/.hermes/skills/operator/hermes-source-change/SKILL.md | add |
| skills/operator/hermes-release-deploy/SKILL.md | be7e0c20812899a9d5607e1425fb17e42d53a7f38ace5fbfc63e91daab9c4c2f | /home/ubuntu/.hermes/skills/operator/hermes-release-deploy/SKILL.md | add |
| skills/operator/hermes-live-audit/SKILL.md | 4cfef17f726036515f2339b439c8c09bb2b41ce2b70b1e841460b99caa1f36b1 | /home/ubuntu/.hermes/skills/operator/hermes-live-audit/SKILL.md | add |
| skills/operator/hermes-recovery/SKILL.md | e2007bc5f47940da132bd69263680431c9c033d7204ac924f422ce6059d13846 | /home/ubuntu/.hermes/skills/operator/hermes-recovery/SKILL.md | add |
| scripts/guard/secret-scan.sh | c478ae2d06c5c53159ed2a2adf171960ff7a2eb612f542934963a6ef5a6623a5 | /home/ubuntu/.hermes/scripts/guard/secret-scan.sh | add |
| scripts/guard/docs-allowlist-check.sh | c3c6f92a618ab891a8a566021a1d9f4100a3bf4caea61697334ebbdd916c2072 | /home/ubuntu/.hermes/scripts/guard/docs-allowlist-check.sh | add |
| scripts/guard/manifest-validate.sh | 68e3fb358b0036c3419e91e79b4837825f099f2d9421447eed73c82b2b14b622 | /home/ubuntu/.hermes/scripts/guard/manifest-validate.sh | add |
| operations/ledger.json | f9401dc8f7802c1829d27476a050bf6ebdf0f48d64f5ef5b2c26f05bd234dddc | /home/ubuntu/.hermes/operations/ledger.json | add/replace |
| operations/README.md | ad87520e71bf4cfb2d3e45f5ed12ac5400f30cc41e9276c715ac346427733916 | /home/ubuntu/.hermes/operations/README.md | add |

## Notes
- No `.hermes.md` or `HERMES.md` exists on the live runtime (verified
  2026-08-06) — `AGENTS.md` will be the active project-context file.
- Runtime state, config.yaml real values, DBs, sessions, logs, memories,
  med state are NOT in this manifest.
- Post-deploy: gateway does NOT need a restart for skill/context files;
  verify hashes + owner E2E per hermes-release-deploy.
