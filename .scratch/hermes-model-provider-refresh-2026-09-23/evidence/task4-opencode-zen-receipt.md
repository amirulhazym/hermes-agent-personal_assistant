# Task 4 — OpenCode Zen free-only / fail-closed receipt

Date: 2026-09-23

Scope: enforce the owner-locked free-only policy for the built-in `opencode-zen` chat model picker. No live runtime deployment.

## Current official state re-checked

OpenCode's current Zen documentation lists limited-time free generative/chat SKUs including Big Pickle, Space Bunny Free, MiMo-V2.6-Flash Free, MiMo-V2.5 Free, Ling 3.0 Flash Fin Free, Nemotron 3 Ultra Free, Nemotron 3.5 Lightning Free, and Muse Spark 1.3 Contributor Free. Jev 1.13 Free is also free, but it uses the separate `/systemone` endpoint rather than chat/completions or responses as a normal chat model.

Official source: https://opencode.ai/docs/en/zen/

## Actual VPS probes

Using the existing OpenCode Zen credential and an honest `Hermes-Agent/0.21.0` User-Agent:

- All eight current official free generative/chat SKUs returned HTTP 403 with the provider message that the free tier can only be used from within the OpenCode client.
- `jev-1.13-free` returned HTTP 200 through `/systemone`.
- Therefore Jev is legitimately externally callable as System One, but it is intentionally excluded from Hermes `/model` because it is not a chat model.
- No client-identity spoofing or header impersonation is used.

## Implemented contract

- `_PROVIDER_MODELS["opencode-zen"]` is empty.
- `provider_model_ids("opencode-zen")` fails closed before live/models.dev merge.
- `cached_provider_model_ids("opencode-zen")` returns empty before stale-cache lookup.
- background provider-cache updates skip OpenCode Zen.
- typed `/model` validation rejects both paid and free Zen chat model IDs and explains the free-only policy.
- shared interactive picker filtering always hides the `opencode-zen` row, including when stale/current-provider state tries to reinsert a model.
- `opencode-free`, `opencode-go`, and Jev/System One behavior are outside this task and were not changed.

## Verification before commit

- Genuine RED harness: compile PASS; 4 expected behavioral failures on the Task 3 baseline.
- Current official free-chat external probes: 8/8 HTTP 403.
- Jev 1.13 Free `/systemone` probe: HTTP 200.
- Zen-only overlay `git apply --check`: PASS against a freshly reconstructed Task 3 baseline.
- Scratch GREEN tests: 8 passed.
- Fresh 8-patch runtime reconstruction: PASS.
- Runtime tree: 10,495 files.
- Runtime tree SHA-256: `21002f76312a177861d28719a662cb1d457321de61064b9346a273e752fa01df`.
- Fresh reconstructed targeted suite: 53 passed.
- Candidate against actual config/cache: live Zen picker `[]`; cached Zen picker `[]`; typed selection fail-closed; shared picker contains no `opencode-zen` row.

No live Hermes runtime file, config, cache, gateway process, or service was modified during Task 4.
