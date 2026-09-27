# 03 — Codify Anti-Fabrication Rules in Skills

**What to build:** Formulate explicit guardrails in `anti-fabrication-guardrails` and `med-tracker` skills forbidding automated or inferred medication inventory values without explicit user count disclosure.

**Blocked by:** 02 — Sanitize Runtime Supply Data in med-supply.json

**Status:** ready-for-agent

- [ ] Add rule to `skills/software-development/anti-fabrication-guardrails/SKILL.md` prohibiting hallucinated or inferred medical stock counts
- [ ] Add rule to `skills/med-tracker/SKILL.md` specifying that medication inventory is strictly untracked (`current: null`) unless user explicitly provides count
- [ ] Verify skills reflect SSOT standards and pass manifest verification
