# Issue 02 — Add the 00:25 Autonomous Remediation Agent

**Blocked by:** Issue 01

## Vertical slice

Add a read-only context collector and a normal Hermes cron-job contract that
runs at 00:25 MYT, analyzes findings beyond Git, attempts only safe repairs,
and reports evidence plus blocked items. Keep the existing 01:55 watchdog
unchanged.

## Acceptance criteria

- The job is normal agent mode, not `no_agent`.
- Context includes the preceding primary receipt and current observations.
- Prompt requires independent checks, safe/reversible repair, read-back, and an
  honest conclusion; no interactive approval is assumed.
- Live cron read-back and one real fire provide scheduler/execution evidence.

## Verification

```bash
pytest -q tests/reconciliation/test_nightly_autofix_context.py
```
