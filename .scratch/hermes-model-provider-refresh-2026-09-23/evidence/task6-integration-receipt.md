# Task 6 — Four-provider integration receipt

Date: 2026-09-24

Scope: integrate and verify the complete pre-release model-provider candidate across Codex, DeepSeek, OpenCode Zen, Antigravity, and the shared gateway /model paths. No live deployment, cache invalidation, restart, or channel send was performed.

## Integration finding and fix

The initial combined candidate exposed one real channel-parity gap:

- Telegram's interactive path used list_picker_providers() and correctly hid OpenCode Zen.
- WhatsApp Cloud has no send_model_picker() method, so /model falls back to the shared text path using list_authenticated_providers().
- That base list still emitted an empty opencode-zen row, even though no Zen chat model was selectable.

A genuine RED regression test reproduced the gap. The Task 6 incremental overlay now removes opencode-zen from the base authenticated provider list before current-model injection/sorting. The existing interactive Zen filter remains as defense-in-depth.

## New runtime overlay

- Patch: patches/upstream-hermes/2026-09-24_shared_model_catalog_integration.patch
- SHA-256: 5755e7b77d4fcdbcdb3368f5aec55562c4f2bacb4a3e8d2329f937d6eb45311a
- Source-lock order: 9
- Changed runtime files:
  - hermes_cli/model_switch.py
  - tests/hermes_cli/test_opencode_zen_model_limit.py

Fresh reconstructed core candidate:
- official base: a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8
- ordered patches: 9
- files: 10495
- tree SHA-256: 38e6566e854bb419d289cfe6a2df5146cf1ac9272369647ec89a6bae38f248f1

Antigravity candidate was independently reconstructed from its pinned upstream base plus the three authoritative dependency/personal/default patches from Task 5.

## Verification before commit

- Genuine Task 6 RED: 1 expected failure proving WhatsApp/text fallback still surfaced the empty Zen row.
- Shared-model GREEN after fix: 12 passed.
- Combined provider matrix:
  - Codex: 10 passed.
  - DeepSeek: 49 passed, 168 deselected.
  - OpenCode Zen: 54 passed.
  - Shared gateway /model: 6 passed.
  - Antigravity plugin: 57 passed.
  - Combined targeted passes: 176.
- Channel-catalog parity smoke:
  - text fallback has Zen: false.
  - interactive picker has Zen: false.
- Architecture evidence:
  - Telegram adapter implements send_model_picker().
  - WhatsApp Cloud does not; it follows the gateway text fallback.
  - both paths enter the same GatewayRunner /model handler and derive from the authenticated provider catalog.

## Pre-release boundary

Task 6 proves the integrated source candidate only. The following remain intentionally pending until the final exact-SHA owner release gate:

- publication/promotion to protected origin/main;
- live Hermes runtime deployment;
- live Antigravity default switch from Gemini 3.7 to Gemini 3.8;
- provider-model cache invalidation;
- gateway restart/reload;
- controlled Telegram and WhatsApp post-deploy channel smoke;
- rollback snapshot/deployed-hash evidence.

No production runtime bytes were changed by Task 6.
