# Task 3 — DeepSeek V4.1 refresh receipt

Date: 2026-09-23

Scope: refresh only the native DeepSeek provider path. No live deployment.

## Current contract implemented

- Canonical Flash model: `deepseek-flash`.
- Retained native model: `deepseek-v4-pro`.
- Retired `deepseek-v4-flash` / `deepseek-v4-flash-vision-exp` are compatibility inputs only and normalize to `deepseek-flash`.
- Native picker filters retired Flash aliases while preserving future live-only models.
- Native reasoning efforts are `low`, `high`, `max`; compatibility maps `minimal→low`, `medium/xhigh→high`, `ultra→max`.
- `deepseek-flash` context metadata is 1,000,000 tokens.

## Pricing snapshot

Static cost estimation uses current documented peak rates to avoid under-reporting:

- `deepseek-flash`: input 0.30 USD / 1M, output 1.20 USD / 1M, cache hit 0.006 USD / 1M.
- `deepseek-v4-pro`: input 1.32 USD / 1M, output 3.96 USD / 1M, cache hit 0.044 USD / 1M.
- Legacy native Flash aliases inherit the current Flash rate.

Official source references used during verification:
- https://api-docs.deepseek.com/quick_start/pricing
- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/updates/

## Verification before commit

- Genuine RED harness: compile PASS; 4 expected behavioral failures on Task 2 baseline.
- DeepSeek-only overlay `git apply --check`: PASS.
- Scratch GREEN suite: 49 passed, 168 deselected.
- Fresh 7-patch runtime reconstruction: PASS.
- Runtime tree SHA-256: `24ac5a41e0377e64e97285614b78910870fd99dddb060fbfadd2d6567fdf3c87`.
- Fresh reconstructed targeted suite: 49 passed, 168 deselected.
- Read-only actual native DeepSeek catalog through candidate code: `deepseek-flash`, `deepseek-v4-pro`; retired Flash aliases absent.

No live Hermes runtime file, config, cache, gateway process, or service was modified during Task 3.
