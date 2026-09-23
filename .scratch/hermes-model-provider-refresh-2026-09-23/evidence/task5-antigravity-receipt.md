# Task 5 — Antigravity / Gemini 3.8 default receipt

Date: 2026-09-23

Scope: refresh the source-controlled Antigravity dependency representation so its next approved deployment defaults to `gemini-3.8-flash`. No live plugin deployment in this task.

## Current external contract re-checked

- Google documents `gemini-3.8-flash` as a stable Gemini model and the default model for the current Antigravity managed agent/SDK.
- `antigravity-preview-09-2026` is the managed-agent identifier, not the underlying Hermes model-picker ID.
- Therefore Hermes keeps `gemini-3.8-flash` as the model ID and does not add the managed-agent ID to `/model`.

Official references used during verification:
- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- https://ai.google.dev/gemini-api/docs/antigravity-agent
- https://ai.google.dev/gemini-api/docs/changelog

## Deterministic dependency chain

Pinned upstream base: `097db5303a610d7e5d75a2fef58d4aefb18436d6`

1. `2026-09-23_local_dependency_commits_base.patch`
   - SHA-256 `50ed309a7a9a9a542aec6b361c0280f9317ac839e8d1c8e44ba9b766d1e102c3`
   - Rebuilds local dependency commits `e7e1833` and `8cccbb6`.
2. `2026-09-04_custom_antigravity_features.patch`
   - SHA-256 `f5f726808dd1935f9551dea258432c2450be2a013798dd393273042002844520`
   - Rebuilds the existing intentional live personal overlay.
3. `2026-09-23_gemini_3_8_default.patch`
   - SHA-256 `35fa5040e7886cf233614ee2248fcf5cb86d152d905efb8f77f251b7d8c6d016`
   - Changes `DEFAULT_MODEL` from `gemini-3.7-flash` to `gemini-3.8-flash` and adds its regression test.

## Verification before commit

- All three patches apply cleanly, in order, from the pinned upstream base.
- Genuine RED against the reconstructed pre-change plugin: 1 expected failure because default was still `gemini-3.7-flash`.
- After the Gemini 3.8 patch: targeted model/picker tests 11 passed.
- Full reconstructed plugin suite: 57 passed.
- Actual bound-account catalog through reconstructed candidate includes `gemini-3.8-flash` and excludes `antigravity-preview-09-2026`.
- Candidate reconstruction reconciliation test: PASS.
- Current live pre-release parity reconciliation test: PASS.
- Patch 1 rebuilt tree matches exact live local commit tree `8cccbb6b891164f7aeceb09695e43b4a12d6a83e`.

The live plugin remains intentionally unchanged during Task 5 and still defaults to `gemini-3.7-flash`; promotion to live is reserved for the final approved release/deploy flow.
