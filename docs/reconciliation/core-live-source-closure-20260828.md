# Core live-source closure — 2026-08-28

## Scope

This record covers only the exact 16-path Hermes **core** inventory from the
2026-08-27 live backup. Medical state, dosage/taper logic, persona/memory
values, credentials, databases, logs, and platform session state are excluded.

The permanent candidate is the isolated local branch
`candidate/core-source-closure-20260828`, based on directly observed personal
`origin/main` `bc4ad6a8ed36bde76a280c6e53a5d18bf0420563`.

## Source provenance

- Official donor base: `a31be48030f60383bf4c1d96ba46bd4b48430218`.
- The 16 old Git blob IDs in `~/.hermes/backups/live_fixes_20260827.patch`
  matched that donor base **16/16**.
- The backup patch applied to the donor base with `git apply --check`.
- The backup snapshot was not byte-identical to the current live disk for the
  16 paths: **0/16** matched in the independent comparison probe. It remains
  historical source evidence, not proof of current live bytes.
- Evidence probes:
  - `/tmp/core_overlay_probe_20260827T163101Z.json`
  - `/tmp/core_three_way_forecast_20260827T163658Z.json`
  - `/tmp/core-source-closure-generation-20260827T164756Z.json`

## Exact 16-path reconciliation

The existing ordered C2 -> C3 -> C4 stack was applied first. The comparison
then used a three-way merge with `a31be...` as the common base:

- `ALREADY_REPRESENTED` (13):
  - `gateway/session.py`
  - `hermes_cli/cli_agent_setup_mixin.py`
  - `hermes_cli/session_listing.py`
  - `hermes_state.py`
  - `hermes_state_common.py`
  - `hermes_state_schema.py`
  - `tests/cli/test_resume_display.py`
  - `tests/gateway/test_resume_command.py`
  - `tests/hermes_cli/test_session_listing.py`
  - `tests/hermes_state/test_resolve_resume_session_id.py`
  - `tests/test_hermes_state.py`
  - `tests/tools/test_session_search.py`
  - `tools/session_search_tool.py`
- `AUTO_MERGE_NO_CONFLICT` (1):
  - `gateway/slash_commands.py`
- `BACKUP_UNIQUE_NO_CONFLICT` (2):
  - `agent/account_usage.py`
  - `tests/agent/test_account_usage.py`
- True three-way conflicts: **0**.

The 3 exceptional paths were converted into one incremental overlay after
C2/C3/C4:

`patches/upstream-hermes/2026-08-28_live-core-usage-and-billing-route.patch`

- Bytes: `8352`
- SHA-256:
  `a14b02c6109c9faf3a33f6eb979e5229d637661425764677273e0d55b252426c`
- The two trailing blank-line defects in the raw backup were normalized only in
  `agent/account_usage.py` and `tests/agent/test_account_usage.py`.
- Raw backup patch `git diff --check`: **2 whitespace errors**.
- Generated incremental patch `git diff --check`: **PASS**.
- Generated patch applies to a fresh reconstructed C2/C3/C4 tree: **PASS**.
- Applied target hashes match the generated patch output: **3/3**.

## Post-snapshot live-only core drift captured

The current live checkout is not the same source boundary as the 2026-08-27
16-path backup. Direct current-upstream graph evidence is:

- Official remote `main`: `0dfba37b11ff2ca908ae2df85b55f4f4c9b7fd8b`.
- Live core `HEAD`: `a1a38baea746f90d551a278e85bd885c3fa0f117`.
- Common base: `a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8`.
- Graph counts in a throwaway graph clone: official `main` is **76 commits
  ahead** and live has **2 local-only commits**.
- The two local-only commits are `c39995e94d78abd33e21ecb6e47051b644d26640`
  and `a1a38baea746f90d551a278e85bd885c3fa0f117`.

Those two intentional source changes were captured as ordered overlays 5 and 6:

- `2026-08-28_live-auxiliary-middleware-route.patch`
  - 1,181 bytes; SHA-256
    `e6f42cfc76ecf9b8c9c75a665ebe79b7ffc16f708056de3646cef6936b785f41`.
- `2026-08-28_live-goal-resume-counter-reset.patch`
  - 610 bytes; SHA-256
    `52b0827a7c04fa4e2a7e8247597465af6f2666bc61d437eab78c46bde8981e96`.

The independent review then found a real failure in the live middleware change:
when the middleware or provider raised, the catch-all fallback could bypass the
middleware or invoke the provider twice. A separate order-7 candidate overlay
preserves those exceptions and removes the duplicate/bypass path:

- `2026-08-28_harden-auxiliary-middleware-fail-closed.patch`
  - 1,022 bytes; SHA-256
    `afa7cfdfc0c73b179543336496097e3193d2e8b3203031dfd9a29aed9d075eb3`.

The three overlays apply cleanly after the existing four-entry series. The
candidate is a selective source index, not a byte-for-byte clone of the entire
live upstream history; the materialized whole-file SHA therefore may differ
where official upstream history between the pinned base and live checkout is
absent.

## Lock and manifest update

The candidate source lock now has 7 ordered entries; the new entries are
`custom-live-auxiliary-middleware-route` at order `5`,
`custom-live-goal-resume-counter-reset` at order `6`, and
`candidate-harden-auxiliary-middleware-fail-closed` at order `7`.

- New patch-series digest:
  `a4dcdf42db9274148ede372925492a23c59e3bf6f72240ba9cf1634a19ed825f`
- Updated tree manifest digest:
  `dca85c4a06dd1a5cb84efe39eeab537c8183e5e5d8b7f8288d970cd41660ab42`
- Updated manifest target hashes:
  - `agent/account_usage.py`:
    `646a5bdfa9a83bac22dce9132bf4e4b269025410d482bffda5e1f470d3463797`
  - `gateway/slash_commands.py`:
    `038f2dd352331dda278252751cef60b081e3783262c511310c418d78d8e05b32`
  - `tests/agent/test_account_usage.py`:
    `f8745145f0e63d330020f3af2692e349a3df77693ca21487658648dafcf87f63`
  - `agent/auxiliary_client.py` (materialized candidate):
    `f92926e0eb64424cee28afb80bbbb62da6b5b75744a134a4190d086b2656f179`
  - `hermes_cli/goals.py` (materialized candidate):
    `97973f093df92b022d23bb2def2d80f5ed7c38b2adfff02ba3699c9b68537a70`

## Out-of-tree provider boundary

`agent/account_usage.py` intentionally imports the Antigravity provider from the
separate runtime path `~/.hermes/plugins/antigravity-provider/src`; the plugin is
not vendored into this personal application repository. The candidate test
monkeypatches the catalog function and therefore proves parsing/fallback logic
only. Plugin registration, source integrity, credential availability, live
catalog availability, inference, gateway reload, and channel E2E remain
separate integration gates and are not claimed here.

## Tests and current gate status

- `tests/reconciliation/test_hermes_runtime_reconstruction.py` plus
  `tests/reconciliation/test_live_core_drift_regressions.py`:
  **10 passed in 13.91s** after the fail-closed correction.
- TDD evidence for the middleware correction:
  - before order 7: **2 failed, 2 passed**; the two failures were the expected
    duplicate-provider and middleware-bypass cases;
  - after order 7: **4 passed** in the affected regression file.
- `scripts/run_contract_tests.sh`: **18 collected, 18 passed**. Its final
  informational line still says “14 tests expected”; that text is stale, not a
  test failure.
- Staged secret scan: **PASS**.
- Staged added-line PII scan: **PASS**.
- Full staged whitespace check: **PASS**.
- The earlier four-overlay focused comparison remains historical evidence only:
  clean donor base **312 passed, 1 failed** and four-overlay candidate **339
  passed, 1 failed**, with the identical baseline-reproduced FTS5 failure.
  It was run before overlays 5–7 and is not being reused as current full-suite
  evidence.
- The current candidate has not been pushed, merged, deployed, or reloaded into
  the running process. `SOUL.md` remains untracked and excluded.
- The candidate SHA, cleanliness, remote ref, deployment state, and process
  reload must be checked separately at each later gate.
