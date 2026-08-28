# Implementation Execution — Worked Example (2026-07-16)

> **Context:** Executing the Runtime Resolver Architecture implementation after design freeze.
> 6 epics, 4 completed in-session (Tasks 1-4), 37+ tests passing.
> **Skill reference:** `planning-and-task-breakdown` → Implementation Execution Order.

---

## The Architecture Being Implemented

- **Design doc:** Runtime Resolver Architecture v2 (~550 lines, 12 sections)
- **Preceding work:** Architecture adversarial review → 13 findings → 5 blockers resolved → freeze
- **Migration strategy:** Phase 1a adapter (new wraps old), Phase 1b new consumers adopt, Phase 2 old consumers migrate, Phase 3 delete adapter

---

## Task 1: RuntimeContext + RuntimeResolver

**Goal:** Create the typed data model (RuntimeContext) and resolver wrapper (RuntimeResolver).

**Files created:**
- `hermes_cli/runtime_context.py` — 181 lines
- `hermes_cli/runtime_resolver.py` — 182 lines
- `tests/hermes_cli/test_runtime_context.py` — 197 lines, 26 tests

**Key decisions:**
- RuntimeContext is `@dataclass(frozen=True)` — immutable after construction
- Invariants enforced in `__post_init__`: R01 (provider non-empty), R02 (api_mode non-empty), R03 (source_tier is SourceTier enum), R06 (configured + requested tracked)
- SourceTier is a string Enum with `_missing_` fallback to DEFAULT for unknown values
- generation_id is auto-incremented module-level counter (not uuid)
- `replace()` uses `dataclasses.replace` — preserves generation_id (Phase 1 documented behaviour)

**Resolver implementation:**
```python
def resolve_runtime(*, requested_provider=None, target_model=None, ...) -> RuntimeContext:
    raw = resolve_runtime_provider(...)  # call old function (unchanged)
    # map raw dict to RuntimeContext, derive source_tier, build resolution_reason
    return RuntimeContext(...)
```

**Old resolver unchanged — zero regression risk.**

---

## Task 2: /status + /model Using Same Resolver

**Goal:** Both commands consume RuntimeResolver instead of ad-hoc config reads.

**Files modified:**
- `hermes_cli/status.py` — added `_runtime_status_section(agent=None)`, "Runtime Resolution" block in status
- `gateway/slash_commands.py` — `--status` flag on `/model` command
- `acp_adapter/server.py` — `--status` flag in ACP sessions
- `tests/hermes_cli/test_status_runtime.py` — 7 tests

**Key decisions:**
- `/model` (no args) still shows interactive picker where supported — `--status` shows the new text view
- ACP adapter shows simplified fallback info since agent is available
- Status section shows: Configured, Requested, Primary, Source, Resolution, Fallback (and Effective + Reason when fallback active)

---

## Task 3: Fallback Reporting

**Goal:** Always set resolution_reason and fallback_state when fallback activates (N01 fix).

**Files modified:**
- `agent/chat_completion_helpers.py` — added `_fallback_state` and `_resolution_reason` after line 1182
- `agent/agent_runtime_helpers.py` — reset `_fallback_state` and `_resolution_reason` in restore_primary_runtime
- `hermes_cli/status.py` — enhanced `_runtime_status_section()` for dual display
- `tests/hermes_cli/test_fallback_reporting.py` — 4 tests

**Key decisions:**
- Agent attributes (not RuntimeContext fields) track fallback state — resolver is stateless
- resolution_reason format: `"provider_{old}_failed_falling_to_{new}_with_model_{model}"`

---

## Task 4: ExecutionContext Inheritance

**Goal:** Create ExecutionContext as delivery wrapper for child execution boundaries.

**Files created/modified:**
- `hermes_cli/execution_context.py` — 177 lines (created)
- `tools/delegate_tool.py` — +parent_context param to _build_child_agent
- `tests/hermes_cli/test_execution_context.py` — 7 tests

**Key decisions:**
- ExecutionContext uses COMPOSITION (contains RuntimeContext), not class inheritance
- Properties (.model, .provider, .generation_id) delegate through self.runtime
- RuntimeContext stays as single source of truth
- Inheritance priority: explicit override > parent_context > parent_agent attribute

---

## Test Architecture

All tests use this pattern:
- **Standalone unit tests** (no external deps): `RuntimeContext("provider=p", "model=m", "api_mode=c")`
- **Adapter tests** (calls old function): `resolve_runtime(requested_provider="...")` with explicit provider
- **Env-dependent tests**: skipped with `pytest.skip("reason")` when the test environment lacks the required credentials, not failed
- **Agent mock tests**: `SimpleNamespace(model='x', provider='y', ...)` — lightweight, no circular imports

---

## Lessons Learned

1. **Adapter pattern (Phase 1a) works.** 0 regressions in old callers across 4 tasks. New code coexists with old.
2. **Start with the data model.** Creating RuntimeContext first, before any wiring, forced the design doc's terminology to be real. Every field had to have a concrete type and default.
3. **Skip, don't fail, env-dependent tests.** Makes CI green even when the test runner has no API keys.
4. **SimpleNamespace for agent mocks** avoids import issues with the actual AIAgent class (which imports half the codebase).
5. **Report after every task.** The user asked for: files changed, exact invariant updated, example output before/after, remaining edge cases. This structure is reusable.
