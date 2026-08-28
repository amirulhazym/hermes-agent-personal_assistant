# Fork-Migration Partial-Index Harness — 2026-08-21

## Context
- Repo: `/home/ubuntu/hermes-agent-personal_assistant-work`, branch `feat/phase3-4-fork-migration`, SHA `cf1abe4a0` (docs-only `docs/fork-migration.md`, parent `7c3eae732` M2 baseline).
- This is a **partial source index** (personal-assistant slice). Tracked tree has `agent/conversation_loop.py`, `hermes_cli/models.py`, `gateway/slash_commands.py`, `hermes_state.py`, but **no** `providers/`, `run_agent.py`, `pyproject.toml`/`requirements*.txt`, `scripts/run_tests*`.
- Donor/upstream full checkout: `/home/ubuntu/.hermes/hermes-agent` — contains `providers/__init__.py` (`get_provider_profile`), `hermes_cli/__init__.py` (`__version__ = "0.20.0"`), `run_agent.py`, and the venv `venv/bin/pytest` (Python 3.11.15, pytest 9.1.1).

## Symptom
Bare collect in the workdir fails with harness errors, not candidate defects:

```
cd /home/ubuntu/hermes-agent-personal_assistant-work
python -m pytest --collect-only -q
# 1049 collected, 8 errors
# ERROR tests/providers/test_provider_profiles.py - ImportError: cannot import name 'get_provider_profile' from 'providers'
# ERROR tests/run_agent/test_provider_parity.py - ImportError: cannot import name '__version__' from 'hermes_cli'
# (6 more: test_auxiliary_client, test_status_canonical_display, test_models, test_e2e_wiring, test_profile_wiring, test_transport_parity)
# Interrupted: 8 errors during collection in 3.85s
```

## Fix — donor PYTHONPATH + donor venv (read-only, no repo mutation)

```bash
# clear stale bytecode (as the task requires isolation)
rm -rf .pytest_cache
find . -type d -name __pycache__ -exec rm -rf {} +  # needs approval; report full rm
find . -name "*.pyc" -delete

# prove harness boundary
PYTHONPATH=/home/ubuntu/.hermes/hermes-agent:$PYTHONPATH /home/ubuntu/.hermes/hermes-agent/venv/bin/python -m pytest --collect-only -q
# → 1387 collected in ~1.5s

# full timed run (foreground 900s exceeds 600s limit → use background)
# background=true + notify_on_complete=true, tee to /tmp/pytest-cf1abe4a0.log, /usr/bin/time -p
PYTHONPATH=/home/ubuntu/.hermes/hermes-agent:$PYTHONPATH /usr/bin/time -p \
  /home/ubuntu/.hermes/hermes-agent/venv/bin/python -m pytest tests/ -v --tb=short \
  2>&1 | tee /tmp/pytest-cf1abe4a0.log
```

## Observed result (cf1abe4a0)
- `1387 collected → 1287 passed, 88 failed, 12 errors, 2 warnings in 144.29s (real 146.44s, wall 147s)`
- 88 failures dominated by `tests/hermes_cli/test_web_server.py` (71), plus 9 in `test_auxiliary_client.py` and scattered singles in `test_insights`, `test_model_metadata`, `test_models_dev`, `test_moonshot_schema`, `test_turn_finalizer_budget`, `test_usage_pricing`, `test_fast_command`, `gateway/test_status_canonical_display`, `hermes_cli/test_model_switch`, `hermes_cli/test_models`, `run_agent/test_provider_parity` (3).
- 12 errors = `TestPluginAPIAuth` (7) + `TestDashboardPluginStaticAssetAllowlist` (5) — `active_session_file` kwarg mismatch.
- Without PYTHONPATH fix the gate is `HARNESS-INVALID`; do not label candidate broken/green from the 8 collection errors. Failures on the donor-backed run appear pre-existing drift (candidate is docs-only SHA).

## Rules for future sessions
1. Before calling a candidate broken on collection `ImportError` in this workdir, check `ls providers/ run_agent.py pyproject.toml` and retry with donor PYTHONPATH + donor venv.
2. No local venv exists (`.venv`/`venv` absent) — use `/home/ubuntu/.hermes/hermes-agent/venv/bin/python`. `pip --version` may point at system 3.12, but project deps are in the donor venv.
3. `find ... -delete` triggers a security approval gate — note it in the report.
4. Foreground `timeout 900s` is rejected (max 600s); use `background=true` with `notify_on_complete=true` for the full suite (actual run ~2.5 min, not the 10-15 min estimate).
5. Cache clear is part of the task: `.pytest_cache` + `__pycache__`/`*.pyc`. Re-collect after clearing.

## Tail (last 40 lines) on cf1abe4a0 — donor-backed run
```
FAILED tests/hermes_cli/test_web_server.py::TestDeleteSessionEndpoint::test_delete_existing_session
... (see /tmp/pytest-cf1abe4a0.log for full list)
FAILED tests/run_agent/test_provider_parity.py::TestBuildApiKwargsNousPortal::test_includes_nous_product_tags
FAILED tests/run_agent/test_provider_parity.py::TestAuxiliaryClientProviderPriority::test_openrouter_always_wins
FAILED tests/run_agent/test_provider_parity.py::TestAuxiliaryClientProviderPriority::test_nous_when_no_openrouter
ERROR tests/hermes_cli/test_web_server.py::TestPluginAPIAuth::test_plugin_route_requires_auth (×7)
ERROR tests/hermes_cli/test_web_server.py::TestDashboardPluginStaticAssetAllowlist::test_python_source_is_404 (×5)
====== 88 failed, 1287 passed, 2 warnings, 12 errors in 144.29s (0:02:24) ======
real 146.44 / user 100.19 / sys 11.42 / WALL 147s
```
