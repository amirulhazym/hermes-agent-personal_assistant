# Budget Exhaustion + Restart-Latch Audit Reference

## Trigger

Use when Hermes emits `Iteration budget exhausted (N/N) — asking model to summarise` and the same task may have been interrupted by context compaction, a gateway restart, or a candidate source patch.

## Root-cause proof chain

Read the live config first, then trace:

```text
~/.hermes/config.yaml: agent.max_turns
→ agent/agent_init.py: max_iterations + IterationBudget
→ agent/conversation_loop.py: loop condition and budget consume
→ agent/turn_finalizer.py: exhausted-turn finalisation
→ agent/chat_completion_helpers.py: summary request with tools stripped
```

The final summary request is not evidence of completion. Classify the turn as incomplete unless the requested acceptance criteria were independently proven.

## Separate budgets

Do not conflate these values:

| Setting | Scope | Meaning |
|---|---|---|
| `agent.max_turns` | Normal foreground agent | Maximum API/tool-loop iterations for the turn |
| `delegation.max_iterations` | Child `delegate_task` agents | Child-agent iteration cap |
| `goals.max_turns` | `/goal` Ralph loop | Number of continuation turns across goal-loop iterations |
| `checkpoints.enabled` | Filesystem safety | Enables file snapshots before mutations; not progress continuation |

Raising `agent.max_turns` only postpones forced summarisation. It does not implement continuation.

## Read-only restart inspection

Run before deciding whether another restart is needed:

```bash
systemctl --user is-active hermes-gateway.service
systemctl --user show hermes-gateway.service -p MainPID -p ActiveState -p SubState -p ActiveEnterTimestamp -p ExecMainStartTimestamp -p TimeoutStopUSec
cat ~/.hermes/gateway.pid
cat ~/.hermes/restart-state.json
journalctl --user -u hermes-gateway.service --since '<request minus 1 minute>' --until '<request plus 3 minutes>' --no-pager -o short-iso
```

Interpretation rules:

- `requested` + missing `new_pid` is an incomplete ledger record, not proof that restart failed.
- Prove an existing restart by matching old-PID termination, systemd start, new PID, and readiness/bridge evidence in the journal.
- If the journal reports drain timeout with active agents, report `systemd-restarted, drain incomplete`; do not call it graceful.
- Do not clear or overwrite stale restart state without explicit approval.

## Candidate vs live deployment

Collect:

```bash
git status --short --branch
git diff --stat
git diff --check
git branch --show-current
git rev-parse HEAD
git remote -v
git log -5 --oneline --decorate
stat <candidate-file>
```

Then classify separately:

- candidate source present;
- targeted tests passing;
- committed/pushed;
- process started after the change;
- live path exercised.

A passing unit test proves candidate source behaviour only. A process start time after file mtime is useful evidence but does not prove a lazy-loaded module was imported; use a fresh live probe or controlled reload to prove runtime behaviour.

## Mixed worktree rule

If unrelated tracked or untracked files exist, do not blanket-stage or commit before restart. Selective staging may be possible, but commit safety is not established until the exact file scope and ownership are reviewed. Report the branch divergence and worktree scope before asking for commit/restart approval.

## Status wording

Use explicit labels:

- `PROVEN`: direct source/output/log evidence shown.
- `CANDIDATE`: source/test evidence, not live-loaded.
- `LIVE`: runtime probe or post-restart evidence exercised the path.
- `INCOMPLETE`: budget/restart/transport ended before acceptance criteria were proven.
- `UNVERIFIED`: evidence gap remains; do not round up.
