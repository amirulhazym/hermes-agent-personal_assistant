# Task 2 — OpenAI Codex GPT-6 fallback receipt

Date: 2026-09-23

Scope: refresh only the OpenAI Codex OAuth picker fallback. No live runtime deployment.

## Implemented

- Added gpt-6-astra, gpt-6-sol, and gpt-6-luna to DEFAULT_CODEX_MODELS.
- Preserved live Codex OAuth discovery as authoritative.
- Did not add GPT-6 entries to the synthetic forward-compat template list.
- Did not synthesize any GPT-6 -900k variants.
- Added a focused regression test in tests/hermes_cli/test_codex_models.py.
- Added the Codex-only upstream overlay as source-lock patch order 6.

## Verification before commit

- Patch git apply --check: PASS.
- Fresh deterministic reconstruction: PASS.
- Reconstructed files: 10494.
- Runtime tree SHA-256: ec89880da3c3ff6b798140ce6416154698c528c4d4b85db1a68de4468c929441.
- Codex targeted suite: 10 passed, 0 failed.
- Explicit-HERMES_HOME smoke: PASS.
- Offline fallback contains all three GPT-6 slugs.
- Synthetic GPT-6 -900k entries: none.

The earlier first draft of the unified patch had an invalid hunk line count. It was classified as an authoring/harness error, corrected, and git apply --check was rerun successfully before source-lock integration.

## Phase 5 correction

The first post-commit source-coverage manifest validation correctly failed because the changed source-lock/tree/README hashes had not yet been recomputed. The manifest was refreshed, the new Codex patch received its own source-only coverage row, and payload metadata was recomputed before amending the unpushed Task 2 commit. All gates must be rerun against the amended exact SHA before publication.
