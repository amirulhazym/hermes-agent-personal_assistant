---
name: live-system-usage-audit
description: Use for live host/runtime usage checks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [linux, runtime, observability, resource-usage, infrastructure]
    related_skills: [hermes-live-audit, system-verification-qa, systematic-debugging]
---

# Live System Usage Audit

## When to Use

- The user asks for current hardware, software, CPU/RAM/swap/disk/I/O usage, or
  “any insights” about a live host.
- The user asks whether a configured Hermes service, gateway, browser, provider,
  container runtime, or listener is actually working now.
- A status/configuration view looks green but the user needs capability proof,
  resource accounting, or a current-vs-historical distinction.
- A live diagnostic is blocked or permission-limited and the evidence gap must
  be reported without guessing.

Use this skill for a read-only snapshot of a live Linux host and the services it
runs: hardware, CPU/RAM/swap/disk/I/O, processes, cgroups, software versions,
service state, exposed listeners, and capability health. It is for answering
“what is the system using now?” and “what is the operational risk?” It is not a
replacement for source-drift reconciliation, a release audit, or a destructive
cleanup plan.

## Safety and evidence contract

- Read-only by default: no install, restart, stop, config edit, checkout,
  fetch, credential refresh, deletion, or state mutation.
- Anchor every snapshot to an exact timestamp and timezone. Separate current
  samples from historical logs and from static accumulated data.
- Use evidence labels:
  - `LIVE-VERIFIED` — direct process/service/capability output now;
  - `LOCAL-VERIFIED` — current local filesystem or configuration metadata;
  - `HISTORICAL` — bounded past log evidence, not current proof;
  - `DATA GAP` — blocked, permission-limited, unavailable, or incomplete probe;
  - `HYPOTHESIS` — interpretation not yet confirmed by a live test.
- Preserve raw exit status and the decisive output for every important probe.
  A successful wrapper, “enabled” flag, or status page is not proof of
  end-to-end capability.
- Redact secrets, tokens, private payloads, account IDs, medical data, and
  raw user/session content. Paths, modes, sizes, PIDs, hashes, versions, and
  sanitized error categories are normally sufficient.

## Phase 1 — Scope and timestamp

1. State the scope: host only, Hermes gateway, containers, network exposure,
   browser/provider capability, or all of them.
2. Capture the target timezone explicitly, then record host identity, kernel,
   uptime, and collection time.
3. Note the observation window for samples and logs. Do not mix a 1-second
   metric, a five-hour service lifetime, and a historical log entry as though
   they describe the same horizon.

## Phase 2 — Host resource baseline

Collect, without changing state:

- CPU topology/model/virtualization: `uname -a`, `lscpu`;
- memory and swap: `free -h`, `/proc/meminfo`, `swapon --show`;
- filesystem capacity and inodes: `df -hT`, `df -ih`;
- short utilization sample: `vmstat 1 3`;
- pressure signals: `/proc/pressure/cpu`, `memory`, and `io`;
- block-device activity: a short `iostat` sample when installed;
- GPU/local-inference evidence when relevant: `lspci`, `nvidia-smi` if present,
  and an exact process-name scan for Ollama/vLLM/llama/TGI/etc.

Interpret metrics together:

- load must be read against the number of CPUs;
- available memory is more useful than “free” alone;
- swap used is a risk signal, not by itself proof of active memory pressure;
- current I/O utilization and PSI are different horizons;
- one sample cannot prove a growth rate, leak, or sustained bottleneck.

## Phase 3 — Service and runtime accounting

For a Hermes gateway or other service, collect both application and service-
manager evidence:

- application status and version;
- gateway/service status and child-process tree;
- active session/job counts and database size where the application exposes
  them;
- service PID, active timestamp, restart count, task count, CPU time, memory
  current/peak, swap current/peak, and resource limits;
- failed-unit list and relevant listener sockets.

Do not report the main Python/Node PID RSS as the whole service when the service
owns bridges, browser drivers, workers, or nested cgroups. For cgroups, read
`memory.current`, `memory.peak`, `memory.swap.current`, `memory.swap.peak`,
`memory.max`, `memory.swap.max`, `memory.events`, and `pids.current`. A simple
`cgroup.procs` traversal may omit nested child cgroups; label a per-process sum
as partial unless the hierarchy was walked completely.

## Phase 4 — Capability versus configuration

For every capability that matters, keep these states separate:

1. configured/enabled in settings;
2. installed/discoverable on disk;
3. loaded by the running process;
4. exercised successfully through the real runtime path;
5. user-visible end-to-end success.

Use the smallest safe live probe that tests the actual boundary. Examples:

- launch the runtime's browser through its installed Playwright environment;
- run a read-only provider/catalog probe using the configured transport;
- inspect a gateway status path and then verify a fresh log/event, not merely an
  accepted request.

Capture exit code, stdout/stderr, and the exact missing/failed dependency when a
probe fails. Do not repair the environment during an audit unless the user
explicitly changes the scope to maintenance.

## Phase 5 — Storage and permission boundaries

Use filesystem authority from `df` and allocated-byte accounting for consumers:
`du -x -B1` or metadata-only `st_blocks * 512`. Report exact paths, sizes,
classification, and unreadable paths.

- A large database or evidence directory is not automatically a leak.
  Historical size samples are required to establish growth.
- A partial `du` over root-owned directories is a partial ledger, not a full
  root-disk attribution.
- If `docker ps`, `docker stats`, or `docker system df` is denied by the
  socket, retry once via `sudo -n docker system df` (non-interactive) before
  reporting `DATA GAP — container inventory unavailable`; never report zero
  containers. Do not add the user to a privileged group as an audit
  shortcut.
- Do not delete caches, sessions, databases, backups, incident evidence, or
  virtual environments from an observation task. Cleanup needs a separate
  retention manifest, owner approval, and post-delete `df` proof.

## Phase 6 — Logs and currentness

Use a bounded journal/service-log window. Aggregate repeated signatures and
redact payloads rather than dumping prompts, tokens, or full message bodies.
Classify each observation as:

- current and reproduced now;
- historical but relevant;
- configuration-only;
- one-off watch item;
- unresolved/data gap.

A log entry showing that a feature failed earlier does not prove it fails now;
conversely, absence of log entries does not prove the feature works if nobody
attempted it during the window. A stale-session recovery, non-zero restart
counter, or prior provider rotation should be reported as a watch item unless
reproduced or corroborated.

If an in-process safety guard blocks a read-only diagnostic, preserve the exact
failure and switch to direct `/proc`, `/sys/fs/cgroup`, service-manager,
journal, socket, or filesystem-metadata probes. A blocked diagnostic is not a
passing diagnostic, and an unavailable doctor command is not a clean bill of
health.

## From audit findings to action (handoff, not execution)

A deep audit ("yang boleh deleted, redundancies, stale files, any improvements") often surfaces reclaim candidates and improvement items. The audit turn stays read-only: do NOT delete or reconfigure during it. When candidates are found, classify them into an approval ledger and continue under the `vps-disk-reclaim` skill's flow (per-batch owner gate, `df` before/after proof). Recurring probe targets worth checking in any deep audit on a small VPS: `journalctl --disk-usage` + journald.conf cap check, `~/.agent-browser/browsers/chrome-*` version accumulation, HuggingFace hub caches vs configured model path, `/var/cache/apt/archives`, `git worktree list` in every repo that ever registered worktrees under /tmp, failed-auth rate from the ssh journal slice, and idle docker/containerd RAM cost.

## Reporting format

Lead with the verdict, then give evidence-backed sections:

1. snapshot time and scope;
2. host/hardware/resource usage;
3. software/runtime/service state;
4. capability tests;
5. ranked risks and insights;
6. data gaps and failed probes;
7. recommended next gate, with no action implied unless explicitly approved.

For every major finding use:

```text
Verdict: TRUE / FALSE / PARTIAL / WATCH / DATA GAP
Actual evidence: exact value or sanitized output
Source: command, path, service, or bounded log window
Interpretation: what the evidence supports and what it does not prove
```

Do not call the system “healthy” from one green status command. Use the lowest
proven state and distinguish operationally running, resource-safe, capability-
working, and end-to-end proven.

## Reusable probe details

Use `references/host-runtime-probe-pattern.md` for the command matrix, cgroup
fields, safe capability-test pattern, log aggregation rules, and the compact
WhatsApp-friendly evidence ledger.

## Completion checklist

- [ ] Timestamp/timezone and observation window recorded
- [ ] Host, resource, service, and capability evidence separated
- [ ] Main-PID versus cgroup accounting distinguished
- [ ] Current samples separated from historical logs
- [ ] Permission/blocked probes recorded as `DATA GAP`
- [ ] No secrets or private payloads exposed
- [ ] No restart, install, write, deletion, or credential refresh performed
- [ ] Every recommendation is clearly separate from observed fact
