---
name: cross-boundary-integration
description: Use for changes crossing process or module boundaries.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [integration, architecture, supervision, lifecycle, testing, handoff]
metadata:
  hermes:
    tags: [integration, architecture, supervision, lifecycle, testing, handoff]
    trigger: Use when a change crosses a module, process, adapter, queue, or supervisor boundary.
---

# Cross-Boundary Integration

## When to Use

Use this skill for changes crossing modules, processes, adapters, queues, or
supervisors. Prove the real seam before calling the change implemented.

## Purpose

Use this skill when a change crosses a real runtime boundary: helper → production
entry point, bridge → adapter, adapter → gateway supervisor, CLI → updater,
worker → queue, or service → external process. The central rule is:

> A passing detached helper test is not proof that the production path uses the helper.

This skill complements incremental implementation, TDD, systematic debugging,
and source-change workflows. It exists because cross-boundary failures often
look solved after a pure unit test passes while the actual call site, lifecycle,
ownership, or handoff remains unchanged.

## Status vocabulary

Keep these statuses separate in every report:

| Status | Evidence required |
|---|---|
| `HELPER-TESTED` | Pure helper/isolated unit tests pass. |
| `WIRED-CANDIDATE` | Production source imports and invokes the helper; source inspection proves the call path. |
| `INTEGRATED-CANDIDATE` | Tests exercise the real seam, including ownership, handoff, and cleanup. |
| `PROCESS-LOADED` | Runtime process identity/hash/start evidence proves the new source is loaded. |
| `LIVE-PROVEN` | Fresh end-to-end evidence proves the user-visible or external-service path. |

Never upgrade one status into another. In particular, `HELPER-TESTED` is not
`WIRED-CANDIDATE`, and `WIRED-CANDIDATE` is not `PROCESS-LOADED`.

## Workflow

### 1. Establish the boundary and baseline

Before editing:

1. Identify every component and the exact production entry point.
2. Capture the clean baseline branch/SHA and relevant runtime identity.
3. Trace the event from source to sink: who creates it, who owns it, and who observes it.
4. Inspect both the candidate/source artifact and the installed/running artifact when they differ.
5. Write the acceptance contract in observable terms, not implementation nouns.

For a bridge change, the source tree, installed bridge directory, candidate helper,
and running process are four distinct artifacts. Do not collapse them into
“the bridge code.”

### 2. Write the ownership matrix before implementation

For each failure or state, record:

- **scheduler owner** — who may create the next retry/timer;
- **resource owner** — who closes, retires, or replaces the socket/process;
- **state owner** — who declares connected, degraded, terminal, or stopped;
- **handoff owner** — when and how responsibility moves to the next layer;
- **forbidden action** — which adjacent layer must not duplicate the work.

A valid matrix has one owner per retry class. If bridge and gateway can both
schedule the same failure, the design is incomplete until one side is removed
or explicitly gated.

### 3. Start with a seam-level RED test

Pure tests are useful for deterministic policy, but the first acceptance test
for a cross-boundary change must reach the production seam. It should fail
because the current source does not yet:

- call the new helper/controller/router;
- propagate the expected state or reason;
- retire the old resource;
- hand off exactly once; or
- prevent the forbidden duplicate action.

Then implement the smallest wiring needed for that one behavior. Do not build a
large generic controller while the production entry point remains untouched.

### 4. Use thin vertical slices

Recommended slice order:

1. **Single happy-path ownership:** one event reaches the real entry point and one owner handles it.
2. **Duplicate suppression:** repeated events create one timer/attempt/handoff.
3. **Stale-generation or stale-owner rejection:** an old resource cannot mutate current state.
4. **Failure classification:** terminal, transient, restart-required, and unknown states have explicit policies.
5. **Cleanup:** old resources, listeners, timers, locks, and child processes are retired before replacement.
6. **Handoff:** bounded local retries stop before process/supervisor retries begin.
7. **Observability:** health/status exposes state, reason, generation, counters, and next action without leaking secrets.

Run the narrow seam test after every slice, then the pure helper tests and the
existing boundary regression tests. Keep each increment independently revertable.

### 5. Treat lifecycle and async boundaries as first-class

For socket/process controllers:

- use a generation/token or equivalent ownership check;
- re-check ownership after every awaited startup step;
- retire the old resource before installing the replacement;
- allow at most one active attempt and one pending timer per owner;
- clear timers and detach listeners on stop/shutdown;
- define what happens if a callback arrives twice or after handoff;
- preserve terminal/auth state rather than deleting credentials by guesswork.

For Python/Node or CLI/service boundaries, test both directions: the producer’s
output and the consumer’s interpretation. A callback registration alone is not
proof of delivery or handoff.

### 6. Verify in layers

Use this order:

1. static source reachability — import and call-site evidence;
2. pure unit tests — deterministic policy and edge cases;
3. seam tests — real production entry point with fakes/doubles at the external boundary;
4. component integration tests — adapter/supervisor/CLI behavior;
5. candidate identity — exact commit, changed paths, clean tree;
6. runtime identity — process PID/start/cwd/hash or equivalent;
7. fresh end-to-end test — actual channel/API/user-visible result.

Report failed, skipped, and unrun layers explicitly. A green lower layer does
not cancel an unrun higher layer.

## Common failure patterns

- **Detached-helper completion:** tests pass for a new controller, but the old
  scheduler remains the live call path. Fix: add a seam RED test that observes
  the production entry point.
- **Controller accretion:** add hundreds of lines and more unit cases while the
  real bridge/adapter is still unchanged. Fix: stop, shrink to one vertical
  slice, wire it, and test it.
- **Dual retry ownership:** bridge, adapter, and gateway each retry the same
  close. Fix: ownership matrix plus a test asserting exactly one active timer
  and one handoff.
- **Stale callback mutation:** an old socket/process emits after replacement.
  Fix: generation and identity checks around every listener and awaited step.
- **Health optimism:** HTTP server alive or a `connected` flag is treated as
  transport/channel recovery. Fix: require repeated health, destination-side
  or API evidence, and a quiet observation window.
- **Runtime/source conflation:** disk checkout is called “running” without a
  process reload/hash check. Fix: report `ON-DISK`, `PROCESS-LOADED`, and
  `LIVE-PROVEN` separately.

## Production update/router boundary addendum

For an updater or release-routing change that crosses CLI, gateway, dashboard,
desktop, installer, and native bootstrap boundaries, treat the route matrix as
the seam contract—not as a collection of independent callers:

1. Define one fail-closed production policy boundary and one canonical channel.
2. Make each production caller either invoke that boundary or pass the exact
   canonical argv; never let a caller derive a branch from current checkout,
   persisted UI state, build stamps, or a legacy `main` fallback.
3. Audit both apply and check paths, plus manual fallback, installer scripts,
   native bootstrap, and notification/banner probes. A remaining caller with a
   fallback is an independent policy implementation and leaves the integration
   partial.
4. Put dirty-tree preflight before marker, lock, backup, process pause, Git
   config, cleanup, fetch, checkout, stash, merge, and dependency mutation.
   Do not use autostash as a substitute for the preflight.
5. Test the actual generated subprocess argv for gateway/dashboard/desktop
   handoffs. A shared helper test does not prove that an unattended caller uses
   it.
6. If the target release ref is absent remotely, keep local policy tests
   separate from live-channel availability; do not substitute a default branch.

This session exposed the common false closure: Python policy tests passed while
old tests and non-Python callers still encoded `main`, upstream synchronization,
autostash, or `reset --hard`. Replace stale contract tests deliberately and rerun
affected callers after every byte-changing slice.

See `references/production-update-routing-matrix.md` for the reusable matrix
and gate checklist.

## Completion checklist

- [ ] Ownership matrix has one retry owner per failure class.
- [ ] Seam RED test failed before production wiring.
- [ ] Production call path imports and invokes the new behavior.
- [ ] Duplicate, stale, terminal, cleanup, and handoff cases are tested.
- [ ] Pure, seam, and component tests have fresh outputs.
- [ ] Candidate SHA and changed paths are exact and clean.
- [ ] Runtime loading and external behavior are separately verified.
- [ ] Any unrun or blocked gate remains visible in the final report.

## References

- `references/cross-boundary-slice-gates.md` — compact ownership matrix, RED/GREEN seam recipe, and evidence ledger for controller/router changes.
