# Live Runtime Preservation Baseline

Use this reference when repository reconciliation also includes a running service, mutable databases, credentials, messaging sessions, cron jobs, or nested source clones.

## Objective

Produce one canonical, timestamped, read-only baseline that lets a separate executor draft a preservation checkpoint without repeating the full audit or guessing what the live runtime reads.

The baseline is evidence, not execution approval.

## Mandatory Sections

### A. Runtime provenance

Record:

- PID, PPID, command, executable, working directory;
- service manager/unit, restart policy, stop timeout, kill mode/control group;
- interpreter, venv and safe environment paths;
- imported module origins using bytecode-disabled discovery where possible;
- actual config/scripts/hooks/skills/cron/runtime paths;
- health endpoints found from source or official service metadata, not guessed URLs;
- child processes and whether they are independent services or part of the parent service cgroup.

### B. Repository checkpoint

For each repo:

- purpose: runtime, application source, upstream/fork, donor, archive;
- toplevel, git-dir/common-dir, branch, full HEAD;
- staged, tracked-modified, untracked-all counts;
- remote names and current refs;
- worktree status.

Important parser rule: never call `.strip()` on raw `git status --porcelain` output before parsing. A leading space means “unstaged”; stripping it can falsely turn the first path into a staged change. Use `splitlines()` directly on raw stdout and preserve the two-character XY status field.

### C. Uncommitted/external state

Classify by top-level path and category:

- source/code;
- config/definitions/docs;
- runtime database/state;
- secrets/PII;
- generated/cache/logs;
- backup/archive;
- uncertain.

Path-based classification is heuristic. Preserve the uncertain bucket until semantic review; never auto-exclude it.

List relevant files outside repos by path/metadata only. Do not display contents of secret-bearing files.

### D. Database and writer map

Inventory:

- every valid SQLite DB;
- zero-byte placeholders separately;
- WAL/SHM/lock companions;
- current open FDs and access mode;
- persistent writers;
- transient scheduler/hook/tool writers;
- messaging-session writers and other non-DB mutable state.

Point-in-time absence of an open FD does not prove a path can never receive writes. Recheck immediately before capture.

Proposed pause sequence only:

1. external executor records health/PIDs/journal cursor;
2. external executor stops the owning service(s);
3. confirms persistent and transient writers are absent;
4. captures final delta/coherent state;
5. validates restored copies;
6. restarts externally;
7. verifies new PID, health, scheduler, hooks and logs.

Never let an in-process agent stop its own gateway during preservation.

### E. Encryption/recovery facts

Report only counts/capabilities—never identities, key IDs, passphrases or secret material.

Separate:

- local encryption capability;
- presence of a local secret key;
- off-device matching-key/passphrase/recovery availability;
- actual off-device decrypt/list/restore test.

A secret key stored only inside the machine being backed up is not proven disaster recovery.

### F. Reproducible version hashes

State exact inputs, source state and algorithm. Prefer both:

- SHA-256 for each file;
- a combined digest over a canonical stream such as sorted `path + NUL + byte-length + NUL + bytes`.

Hash inequality proves byte differences only—not recency, quality, completeness or correctness.

### G. Runtime acceptance baseline

Define pre/post checks for:

- service readiness and imported source paths;
- messaging bridge health;
- inbound, adapter acceptance and destination receipt as separate boundaries;
- restored database integrity/access;
- scheduler job definition and fresh run status;
- hooks loaded and exercised safely;
- targeted application flows using isolated state;
- new errors after a recorded journal/log cursor.

### H. Preservation requirements

Require coverage for:

- every Git ref/unique commit;
- dangling objects pinned before bundle creation;
- dirty/untracked/ignored worktree state;
- runtime state and messaging sessions;
- secrets/PII through encrypted non-Git storage;
- nested upstream/fork lane separately;
- root-level extras;
- independent off-device destination.

Acceptance requires:

- source/destination SHA-256 match;
- `git bundle verify`;
- `git bundle list-heads`;
- temporary clone/restore test for every bundle;
- encrypted archive decrypt/list test from the recovery location;
- restored-copy DB validation;
- exact before/after refs and process health.

### I. Remaining unknowns

List only genuine gaps, commonly:

- another machine's linked worktree status;
- actual external destination/capacity;
- off-device decryption capability;
- provider snapshot availability;
- exact writer set at future capture time;
- user approval for controlled downtime.

## End-State Boundary

A single canonical default branch can be the final application-source truth, but do not confuse that with storing everything in Git.

- Applicable tested application source may end at the default branch.
- Use a temporary integration branch during reconciliation, then fast-forward/promote after tests.
- Runtime state, secrets, PII, logs and machine-specific config remain outside Git.
- Unrelated upstream/fork source remains a separate lane or an explicitly maintained patch series.

No workflow can guarantee “no future conflicts.” It can preserve all inputs, forecast textual conflicts, and catch semantic conflicts with tests and runtime acceptance checks.

## Reporting Footer

End with:

- `LIVE BASELINE COMPLETE` or `LIVE BASELINE INCOMPLETE`;
- execution readiness separately (`READY` or `HOLD`);
- exact blockers;
- whether the executor has enough evidence to draft a plan;
- explicit confirmation of mutations performed—or none;
- natural background runtime activity distinguished from agent-triggered actions.
