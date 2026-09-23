# Task 1 baseline / RED receipt — 2026-09-23

Scope: repair the provider-refresh test harness and prove a clean baseline before implementation.

## Clean reconstruction evidence

- SSOT base HEAD: f15dca09d7c22c5b60726f282b4c65059ea1161c
- Official Hermes base: a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8
- Active baseline patch count: 5
- Reconstructed files: 10494
- Tree SHA-256: cc229851a54a7f380d3c9a92509fa230e3553e851cc652ab4ba85df85056b5ea
- Validator verdict: RECONSTRUCTION PASS

The reconstruction used a full local cache of the exact official base to avoid the earlier inefficient per-blob network fetch path.

## Harness evidence

task1-red-harness.py was copied into the clean reconstructed runtime test tree and checked first with python -m py_compile.

- Harness compile: PASS
- Tests collected: 4
- Behavioral result: 4 failed
- Pytest return code: 1
- Classification: GENUINE RED, not a harness/collection error.

Expected baseline failures:

1. Codex offline fallback does not yet contain gpt-6-astra, gpt-6-sol, gpt-6-luna.
2. DeepSeek legacy Flash IDs still normalize to deepseek-v4-flash, not deepseek-flash.
3. DeepSeek provider profile still defaults to deepseek-v4-flash.
4. OpenCode Zen still exposes its old curated catalog instead of the owner-locked free-only fail-closed result.

No live Hermes runtime, gateway process, config, cache, or service was modified during Task 1.

## Working-tree reconciliation

Partial downstream implementation artifacts discovered before Task 1 were deliberately excluded from this checkpoint. They were preserved outside the repository before the Task 1 publication flow so later provider tasks can be reintroduced one vertical slice at a time.

Persistent preservation root:
- /home/ubuntu/hermes-task-preserve/model-refresh-20260923-pre-task1

The preservation bundle includes the original tracked diff, the original untracked archive, and individually parked downstream provider-refresh patches.
