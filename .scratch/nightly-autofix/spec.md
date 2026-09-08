# Nightly Autonomous Remediation

## Problem Statement

The 23:55 personal-repository audit currently treats the external `upstream`
remote as part of the personal health gate. A GitHub rate limit on that
unmanaged remote can therefore produce a false `FAIL` for a clean personal
repository. The existing 30-minute continuation is created only for a
pre-built Git action or a narrow provenance hold, so a failed audit has no
follow-up agent that can investigate and repair other safe operational issues.

## Solution

Keep the 23:55 job as a deterministic, read-only-first audit of the personal
repository and its managed `origin` remote only. Add a separate normal Hermes
agent job at 00:25 MYT (30 minutes after 23:55) that receives fresh audit
context, independently checks the live state, analyzes findings beyond Git,
and attempts only safe, bounded, reversible, directly verifiable repairs.
The existing 01:55 MYT closure watchdog remains in place as the final
verification boundary.

## User Stories

1. *As the owner of the personal repository, I want nightly health to depend
   only on the repository and its managed origin, so that an external upstream
   outage cannot create a false failure.*
2. *As the owner, I want Hermes to investigate and repair safe problems 30
   minutes after the nightly audit, so that non-Git failures do not wait for
   manual rediscovery.*
3. *As the owner, I want every autonomous repair to report its evidence and
   unresolved boundaries, so that automation does not hide partial or failed
   work.*
4. *As the owner, I want the 01:55 job to remain a separate final verification,
   so that remediation and verification are independently observable.*

## Implementation Decisions

- `scripts/nightly_git_hygiene.py` checks `origin` only; the external
  `upstream` remote is not a nightly gate or source of failure status.
- `scripts/nightly_autofix_context.py` performs read-only collection of the
  preceding primary receipt, current repository observations, scheduler state,
  and the autonomous-repair policy.
- Cron job contract: name `nightly-autofix-30m`, schedule `25 0 * * *`, normal
  agent mode (`no_agent: false`), context script
  `nightly_autofix_context.py`, delivery to the originating owner channel,
  workdir `/home/ubuntu/hermes-agent-personal_assistant-work`, and terminal/file
  tools only.
- The agent may repair only local, bounded, reversible, directly verifiable
  issues. Medical/private state, credentials, destructive or ambiguous deletion,
  protected/public publication, deployment/service lifecycle, and unclear
  provenance remain owner-required or blocked.
- The 01:55 watchdog schedule and role are unchanged.

## Testing Decisions

- Regression test that an advanced external upstream does not appear in
  personal sync state or fail the audit.
- Context collector tests for primary receipt selection, policy boundaries,
  rendered evidence, and exact 00:25 agent-mode job shape.
- Live cron read-back must show the job's schedule, normal agent mode, context
  script, workdir, delivery target, and unchanged 01:55 watchdog.
- Manual live fire must observe scheduler execution, agent output artifact, and
  delivery status separately; a run request alone is insufficient.
- Run affected reconciliation tests and the canonical contract suite after
  every source-byte change.

## Out of Scope

- Removing or changing the 01:55 final-verification watchdog.
- Giving unattended automation authority over medical records, secrets,
  private data, protected publication, deployment, restart, or ambiguous
  deletion.
- Treating a successful agent response as proof of user receipt without
  destination evidence.
- Using upstream repository state to classify the personal repository.
