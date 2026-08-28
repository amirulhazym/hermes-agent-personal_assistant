# Iteration-Budget Exhaustion and Live-Runtime Verification

## Evidence chain

In the Hermes agent loop:

- `agent/conversation_loop.py` stops consuming iterations when `agent.iteration_budget.consume()` returns false.
- `agent/turn_finalizer.py` emits `Iteration budget exhausted (N/N) — asking model to summarise` when no final response exists and the budget is exhausted.
- `agent/chat_completion_helpers.py::handle_max_iterations()` appends a user message requesting a final summary **without more tools**, then performs the final API call.

Therefore the resulting summary is a transport/control-limit fallback, not proof that the task completed.

## Recovery procedure

1. Search the preceding session for the exact exhaustion message and the last unfinished acceptance criterion.
2. Read the live configuration:

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import yaml
   c = yaml.safe_load((Path.home()/'.hermes/config.yaml').read_text()) or {}
   print('agent.max_turns =', (c.get('agent') or {}).get('max_turns'))
   PY
   ```

3. Inspect the source/test diff and run the unfinished targeted test first.
4. Run the smallest relevant complete test file or command.
5. For live gateways, compare process start time with changed-file mtime:

   ```bash
   ps -o pid,lstart,cmd -p <gateway_pid>
   stat -c '%y %n' <changed_file>
   ```

   If the process started before the patch, source-level success does not prove live behavior.
6. Report separately: source/config, tests, commit/push, loaded process, and user-visible behavior.
7. Never report "done" merely because the forced summary was generated.

## Correct status language

- **Source-level proven:** the current files contain the change and tests pass.
- **Runtime unproven/stale:** the running process predates the file change or has not been restarted.
- **Live proven:** a new process loaded the change and the actual user-facing path was exercised.
- **Interrupted:** the previous turn hit its iteration ceiling before acceptance criteria were complete.

## Restart safety

Do not restart the active gateway from inside its own conversation. The restart can interrupt the tool turn and trigger replay or an unintended restart loop. Use an explicitly approved external/supervisor mechanism, then verify the new PID, service readiness, and the actual user-facing path.
