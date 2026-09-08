# Implementation Plan: Nightly Autonomous Remediation

## Overview

Repair the nightly flow so the personal-repository audit is not coupled to the
unmanaged upstream remote, and so an agent-mode autonomous remediation run
executes 30 minutes after the primary audit. Preserve the 01:55 final
verification boundary.

## Tasks

1. RED: change the upstream regression expectation and add the exact agent-job
   contract/context tests.
2. GREEN: remove upstream from both audit paths; add the read-only context
   collector and bounded remediation prompt.
3. Run affected reconciliation tests and the full contract suite.
4. Update the managed-runtime manifest and deploy the exact source bytes.
5. Create/read back the live 00:25 cron job; verify the existing 01:55 job is
   unchanged.
6. Fire the job through the real scheduler, read back execution/output/delivery
   evidence, and independently verify the final runtime state.
7. Commit the exact SSOT change through the protected repository workflow.

## Safety and boundaries

- No upstream fetch is a personal audit gate.
- No unattended medication/private-state/secret/destructive/deployment/restart
  action is authorized by this job.
- Failed tests, missing scheduler evidence, or uncertain delivery remain
  visible as PARTIAL/FAILED rather than being rounded up.
