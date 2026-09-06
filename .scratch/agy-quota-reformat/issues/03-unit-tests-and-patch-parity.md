# Issue 03: Unit Test Updates, Patch Generation & Parity Contract Gates

- **Status**: ready-for-agent
- **Blocked by**: Issue 02
- **Target File**: `tests/test_hermes_plugin.py`, `patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch`

## Description
1. Update existing unit test assertions in `~/.hermes/plugins/antigravity-provider/tests/test_hermes_plugin.py` to match the new sectioned and numbered structure.
2. Run pytest across `antigravity-provider` to verify 100% pass rate.
3. Export clean git diff into personal repo patch: `patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch`.
4. Run `bash scripts/run_contract_tests.sh` to confirm `test_runtime_dependency_drift.py` passes with zero unrepresented drift.

## Verification
- All 114 contract tests green.
- Live `/usage agy` smoke test returns the new structured layout.
