# Fast Contract-Subset Runner — Session/Lineage/Resume Pre-Gate

Captures the reproducible pattern used 2026-08-20 to build `scripts/run_contract_tests.sh` — a ~10-15s contract subset that gates the session-identity / lineage-traversal / resume logic before the ~100 min full suite. Use as the cheap pre-gate; full suite remains the authority.

## When to use

- You need a fast feedback loop before `scripts/run_tests.sh -j N` (≈100 min budget / 5-6 min single-core).
- The change touches `hermes_state.py` session/listing/resume paths, `gateway/slash_commands.py` numeric resume, or C2/C3/C4 overlay patches.
- Work repo is a partial index; live agent has the full tree — imports may diverge between the two checkouts.

## How to identify the contract set

1. **Grep the runtime contract surface** (not test names):
   ```
   hermes_state.py: get_compression_tip, _session_lineage_root_to_tip,
                    list_sessions_rich (recursive CTE), resolve_resume_session_id,
                    parent_session_id, SessionDB, session_key
   gateway:         SessionSource, build_session_key, numeric resume parity
   patches:         C2 pr85505 reset-boundary, C3 unbounded cycle-safe, C4 shared identity
   ```
2. **Collect, don't assume counts** — template specs often say "200-300 tests / 5 min" but the work repo may have far fewer pinned contract tests. Run:
   ```bash
   python3 -m pytest tests/ --collect-only -q | tail
   python3 -m pytest <candidate_files> --collect-only -q
   python3 -m pytest tests/hermes_cli/test_web_server.py -k "<lineage keywords>" --collect-only -q
   ```
3. **Classify into two tiers:**
   - **CORE (must-pass, no live deps):** reconstruction/lock (C2/C3/C4 pin) + canonical/billing identity + lightweight session store. In this repo: 14 tests.
   - **LINEAGE best-effort (needs live checkout):** web_server compression/search/resume projection (4 tests). Runs on VPS after deploy; must be best-effort in the work repo.

## Script essentials (what made the 2026-08-20 runner work)

- **PYTHONPATH live fallback** — work `hermes_cli/` has no `__init__.__version__`; live `~/.hermes/hermes-agent` does. Do:
  ```bash
  LIVE_AGENT="$HOME/.hermes/hermes-agent"
  [[ -d "$LIVE_AGENT" ]] && export PYTHONPATH="$REPO:$LIVE_AGENT:$PYTHONPATH" || export PYTHONPATH="$REPO:$PYTHONPATH"
  ```
- **Timeout + help/collect flags** — `timeout 300` wrapper (pytest-timeout may be absent), `--collect`, `--verbose`, `--help` that prints the header rationale.
- **Best-effort lineage handling** — capture output then classify by string, not just exit code:
  - `ImportError.*__version__|_default_db_path` → NOTE (expected work/live `hermes_state_common` split), don't fail the gate.
  - `rc==5` (pytest "no tests collected") → NOTE skip.
  - `FAILED` substring → warn but non-blocking in work repo; blocking on live VPS.
  Core failures remain blocking (`exit 1`).
- **Header docs in the script** — Purpose, selection rationale, usage, and "no pyproject/pytest.ini" note so the next agent doesn't re-derive.
- **Timing budget line** — print `contract ~Xs` vs `full suite ~100 min → Nx faster` so the speed claim is evidenced, not asserted.

## Pitfalls discovered

- `hermes_state.py` is single-file in work repo but split (`hermes_state_common`) on live — web_server imports break with `_default_db_path` in work repo. Treat as harness-invisible, not candidate defect.
- `python -m pytest tests/` collection fails with 8 ImportErrors when live deps absent; filter with `--ignore` or target the 14-file core set instead of assuming the full tree collects.
- `timeout` binary may not exist; probe with `command -v timeout` and fall back to unguarded `pytest`.

## Verification

```bash
chmod +x scripts/run_contract_tests.sh
bash scripts/run_contract_tests.sh --collect   # expect 14 core + 4 lineage
bash scripts/run_contract_tests.sh            # expect Contract PASS in ~11-14s; lineage NOTE is OK in work repo
python3 -m pytest tests/reconciliation/test_hermes_runtime_reconstruction.py \
  tests/hermes_state/test_billing_canonical_attribution.py \
  scripts/web_operator/tests/test_sessions.py -q  # 14 passed sanity
```

See `scripts/run_contract_tests.sh` for the canonical instance.
