# `hermes_ovis_2_bot` Candidate/TDD Receipt

**Timestamp:** 2026-09-11 09:36 MYT
**Approval boundary:** `APPROVE ARCHITECTURE - CANDIDATE/TDD ONLY`
**Overall status:** `PROVEN — candidate source/tests`; `PARTIAL — live activation`

## Candidate materialization

- Disposable candidate: `/tmp/hermes-ovis-2-candidate-20260911`
- Official base: `a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8`
- Four authoritative pre-existing overlays were hash-checked and applied with `git apply --check` before this change.
- Incremental overlay: `patches/upstream-hermes/2026-09-11_profile-routing-fail-closed.patch`
- Incremental patch size: `16,576` bytes
- Incremental patch SHA-256: `d9990d2e55bbb7553e6f6563e55a8afb65f805b8078208d9007997d67695234e`
- Patch changed paths: `gateway/run.py`, `tests/gateway/test_profile_resolution.py`
- Patch reapplication: `PASS`; rebuilt target hashes matched the tested candidate.

## TDD evidence

- Pre-change baseline: `13 passed` — `/tmp/hermes-ovis-2-baseline-profile-tests-20260911.txt`
- Initial RED: `3 failed` for missing-profile fallback and secondary dispatch — `/tmp/hermes-ovis-2-red-profile-tests-20260911.txt`
- Primary-handler RED: `UnboundLocalError` exposed an import-scope defect in the first implementation — `/tmp/hermes-ovis-2-primary-handler-red-20260911.txt`
- Unserved-profile RED: existing but unserved `ovis2` was accepted before the served-set guard — `/tmp/hermes-ovis-2-unserved-profile-red-20260911.txt`
- Final candidate profile module: `17 passed` — `/tmp/hermes-ovis-2-profile-module-after-served-guard-20260911.txt`
- Final candidate regression subset: `88 passed` — `/tmp/hermes-ovis-2-profile-provider-suite-after-served-guard-20260911.txt`
- Refreshed patch-applied tree regression subset: `88 passed` — `/tmp/hermes-ovis-2-patched-tree-suite-final-20260911.txt`
- Python compile check: `PASS` for modified source/test files.

## Implemented candidate behavior

- Explicit missing profile → `ProfileRouteRejected`; no global-home fallback.
- Explicit profile-directory resolution error → fail closed; no global-home fallback.
- Existing but unserved profile → `ProfileRouteRejected` when multiplexing is active.
- Secondary profile handler → marks `profile_route_rejected` and drops before `_handle_message`.
- Primary/default profile handler → same fail-closed behavior for already-stamped stale profiles.
- Genuinely unrouted source → existing active/default behavior retained.
- Served-profile contract test proves `default` + existing `bot_2`; absent `ovis2` is skipped and warned.

## Provider boundary evidence

Fresh-process resolver under `HERMES_HOME=bot_2`:

- Config provider count: `6`
- Resolver count: `6/6`
- All resolved as `openai_chat` with one configured key-env mapping each.
- Raw receipt: `/tmp/hermes-ovis-2-resolver-receipt-final-20260911.txt`

Actual picker functions in a temporary copy of the `bot_2` provider surfaces (`config.yaml`, `.env`, `auth.json`, `plugins/`):

- Authenticated inventory: `14` rows; `13` non-empty before custom live probing.
- Interactive picker: `14` rows; `14` non-empty after picker discovery.
- Raw receipt: `/tmp/hermes-ovis-2-picker-receipt-final-20260911.txt`

Existing zero-token provider receipts:

- `bot_2`: `/tmp/provider-probe-bot_2-20260911.txt`
- `default`: `/tmp/provider-probe-default-20260911.txt`
- `ovis2`: `/tmp/provider-probe-ovis2-20260911.txt`

Observed provider classifications from those receipts:

- `bot_2` model-list HTTP 200: A6API, A6API Gateway, APIMaster, Custom FTF/FTF, DeepSeek, GMI, Nous, OpenAI API, OpenCode Go, OpenCode Zen.
- Shared/external failures: Antigravity loopback connection refused; Fiq HTTP 503 maintenance.
- Unresolved contract/auth-path responses: Copilot HTTP 400; OpenAI Codex HTTP 400.
- `ovis2`: most profile-configured providers had `SKIP no_key`; shared Nous pool returned HTTP 200.
- No completion/inference request was sent.

## Explicitly not done

- No live `config.yaml` mutation.
- No credential or `.env` mutation.
- No gateway stop/start/reload.
- No stale `gateway_routing` cleanup.
- No deployment into `/home/ubuntu/.hermes/hermes-agent`.
- No commit, push, merge, or release approval.
- `docs/reconciliation/hermes-runtime-source-lock.json` and its tree manifest are unchanged; the new patch remains a candidate/source overlay until a later release decision.

## Hygiene

- Candidate patch introduced exactly two paths.
- Added-line trailing whitespace: `0`.
- Secret-pattern matches in patch: `0`.
- Inherited context trailing whitespace: `20` lines; not modified by this patch.
