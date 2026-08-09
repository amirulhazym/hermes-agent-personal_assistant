# Canonical Decision Record Template

Use this reference when a document will be handed to a future coding agent or multiple reviewers.

## Required order

1. Metadata table: status, version, date/time, owner, executor, reviewer, environment, changed decisions.
2. Read-first orientation: purpose, current verdict, approval boundary.
3. Evidence tiers: EVIDENCE, INFERENCE, UNKNOWN, FORECAST.
4. Final verdict table: decision ID, decision, status, evidence/rationale.
5. Explicitly-not-doing list.
6. Invariants and proof obligations.
7. Consolidated baseline: runtime, repositories, refs, dirty/untracked state, external files, writers, databases, encryption, hashes.
8. Contradiction resolution: prior claim, competing claim, direct evidence, corrected conclusion.
9. Sequential gates: scope, exact commands, deliverables, exit evidence, rollback, approval string.
10. Final workflow policy: source-of-truth, branch/worktree policy, runtime/source separation.
11. Acceptance commands and post-change verification.
12. Risks/open items with status and resolution evidence.
13. Versioned change log.
14. Glossary and exact copy-paste prompts.
15. Primary technical references.

## Status discipline

Use `DECIDED` only for explicit final decisions backed by evidence or an explicit owner choice. Use `HOLD` for blocked execution. Use `UNKNOWN` when the operator cannot access or prove the fact. Use `INFERENCE` for reasoning derived from evidence. Use `FORECAST` for simulations or expected future results. The document itself can be complete while the project remains incomplete.

## Contradiction row

| Claim A | Claim B | Direct evidence used | Corrected conclusion | Decision impact |
|---|---|---|---|---|
| <claim> | <claim> | <command/output/source> | <conclusion> | <gate or scope impact> |

Do not resolve contradictions by averaging reviewer opinions.

## Gate row

| Gate | Status | In scope | Out of scope | Required evidence | Exact approval |
|---|---|---|---|---|---|
| Gate N | HOLD/READY/PASS | <actions> | <actions> | <artifacts/tests> | <literal approval string> |

A plan-only document must state that no execution is authorised until the exact checkpoint is approved.

## Handoff checklist

- [ ] A fresh session can execute from the document without chat history.
- [ ] Earlier competing recommendations and superseded decisions are retained.
- [ ] Every numeric fact has provenance and capture time.
- [ ] Current source, runtime, upstream, archive, and external-machine lanes are distinct.
- [ ] Dirty, untracked, ignored, secret, PII, generated, and uncertain states have preservation destinations.
- [ ] Every exit gate has a runnable verification command.
- [ ] Approval text names an exact checkpoint and forbids scope expansion.
- [ ] Rendered Google Doc passes `verify_doc.py` with zero defects.
- [ ] Drive parent folder is verified from file metadata.
- [ ] Markdown source is retained and delivered alongside the Google Doc.
