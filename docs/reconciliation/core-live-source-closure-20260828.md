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

## Lock and manifest update

The candidate source lock now has 4 ordered entries. The new entry is
`custom-live-core-usage-and-billing-route` at order `4`.

- New patch-series digest:
  `6f6741592510f3394f0a11defbe98aa417603ad6ff9ed972a72395721705a37c`
- Updated tree manifest digest:
  `6c594aae2f0175f34ac631c1933a7ade1bc488315c0ad16d6db289a9815847ff`
- Updated manifest target hashes:
  - `agent/account_usage.py`:
    `646a5bdfa9a83bac22dce9132bf4e4b269025410d482bffda5e1f470d3463797`
  - `gateway/slash_commands.py`:
    `038f2dd352331dda278252751cef60b081e3783262c511310c418d78d8e05b32`
  - `tests/agent/test_account_usage.py`:
    `f8745145f0e63d330020f3af2692e349a3df77693ca21487658648dafcf87f63`

## Out-of-tree provider boundary

`agent/account_usage.py` intentionally imports the Antigravity provider from the
separate runtime path `~/.hermes/plugins/antigravity-provider/src`; the plugin is
not vendored into this personal application repository. The candidate test
monkeypatches the catalog function and therefore proves parsing/fallback logic
only. Plugin registration, source integrity, credential availability, live
catalog availability, inference, gateway reload, and channel E2E remain
separate integration gates and are not claimed here.

## Tests and current gate status

- `tests/reconciliation/test_hermes_runtime_reconstruction.py`:
  **6 passed in 7.36s**.
- Disposable affected-suite comparison:
  - clean donor base: **312 passed, 1 failed**;
  - C2/C3/C4 + generated overlay: **339 passed, 1 failed**;
  - same failure in both runs:
    `tests/test_hermes_state.py::TestFTS5Search::test_search_projection_skips_context_enrichment_queries`;
    expected one context-enrichment query, observed zero.
  - Classification: **BASELINE-REPRODUCED**, not fixed or silently ignored.
- The pre-commit evidence in this record is not a release authorization; the
  current candidate SHA, cleanliness, remote ref, deployment state, and process
  reload must be checked separately at each later gate.
