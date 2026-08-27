# Implementation Plan: Single Source of Truth (1 Repo) Migration & Nightly Git Flow

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the dual-repository structure on the VPS into a single source-of-truth Git repository (`hermes-agent-personal_assistant`), update runtime and service paths safely, update `AGENTS.md` for nightly Git self-improvement, and establish an automated, auditable nightly Git hygiene workflow.

**Architecture:** 
- The single repository `~/hermes-agent-personal_assistant-work` acts as the definitive source of truth (SSOT) containing personal skills, scripts, config templates, and upstream framework patch overlays.
- The secondary Git clone `~/.hermes/hermes-agent` is deprecated from dual-origin workflows and designated strictly as a read-only live runtime install location (or cleanly linked to SSOT).
- A nightly Git reconciliation runner inspects daily deltas, runs test/pii/secret gates, reconciles branches, and prepares PR/push actions with an auditable receipt.

**Tech Stack:** Git, Python 3.11, Pytest, Bash, Systemd user service.

---

## Global Constraints

- Never commit raw secrets, passwords, OAuth tokens, or private medical database entries to Git.
- Keep `SOUL.md` untracked and excluded from public commits.
- Ensure zero disruption to the active Telegram gateway session during runtime file operations.
- Require explicit user approval before executing any remote Git push to `main` or service restart.

---

## Current State & Inventory

| Item | Current State | Target State |
|---|---|---|
| **Personal Repo** | `/home/ubuntu/hermes-agent-personal_assistant-work` (Branch: `main`, Worktree: `candidate/core-source-closure-20260828`) | Single authoritative workspace (SSOT) for all custom logic & upstream overlays. |
| **Live Core Clone** | `/home/ubuntu/.hermes/hermes-agent` (Dual remotes, 11 local branches, tracked as active editable venv) | Deprecated as a separate development origin; aligned cleanly with SSOT. |
| **Systemd Service** | Points to `/home/ubuntu/.hermes/hermes-agent/venv` | Unchanged runtime stability, pointing directly to validated runtime dependencies. |
| **AGENTS.md** | Focuses on multi-folder reconciliation and source locks | Updated with clear Single Repo rules & Nightly Git Self-Improvement protocols. |

---

## Task Breakdown

### Phase 1: Establish Single Source of Truth (SSOT) Repository

#### Task 1.1: Verify & Finalize Candidate Overlay in Personal Repo
- [ ] **Step 1:** Verify candidate branch commit `1b666a6d4e` in `.worktrees/core-source-closure-20260828`.
- [ ] **Step 2:** Merge/Rebase candidate changes into personal repo `main` locally.
- [ ] **Step 3:** Run contract tests: `bash scripts/run_contract_tests.sh` and pytest reconciliation suites (18 tests).
- [ ] **Step 4:** Verify `SOUL.md` remains untracked.

#### Task 1.2: Reconcile Live Custom Scripts & Skills into SSOT
- [ ] **Step 1:** Audit all modified scripts in `~/.hermes/scripts/` (e.g. `chain_calc.py`, `med_confirm.py`, `med_report.py`, `dexa_taper_lookup.py`).
- [ ] **Step 2:** Ensure identical, verified copies are committed into `hermes-agent-personal_assistant-work/scripts/`.
- [ ] **Step 3:** Run medical dataflow tests in personal repo: `pytest scripts/test_chain_adapter.py scripts/test_dexa_dose_dataflow.py`.

#### Task 1.3: Clean Up Secondary Repository Remotes & Stale Branches
- [ ] **Step 1:** In `~/.hermes/hermes-agent`, delete obsolete local experiment branches (`a4-*`, `candidate/*`, `fix/*`).
- [ ] **Step 2:** Remove confusing multi-push remote configurations in `~/.hermes/hermes-agent`.
- [ ] **Step 3:** Mark `~/.hermes/hermes-agent` clearly as `LIVE_RUNTIME_ONLY - DO NOT EDIT MANUALLY`.

---

### Phase 2: Update AGENTS.md & Governance for Single Repo

#### Task 2.1: Update AGENTS.md Policy
- [ ] **Step 1:** Update `AGENTS.md` to establish `hermes-agent-personal_assistant` as the sole Git development repo.
- [ ] **Step 2:** Define clear boundaries: all feature work, fixes, and PRs must originate from `hermes-agent-personal_assistant-work`.
- [ ] **Step 3:** Add Nightly Git Self-Improvement & Hygiene operational section.

---

### Phase 3: Implement Automated Nightly Git Self-Improvement Flow

#### Task 3.1: Build Nightly Git Audit & Cleanup Script
- [ ] **Step 1:** Write `scripts/nightly_git_hygiene.py` in the personal repo.
- [ ] **Step 2:** Script logic:
  - Check `git status` across working repo.
  - Detect stale branches (>7 days or merged).
  - Run `secret-scan.sh` and `pii-review.py`.
  - Check sync status against `origin/main` and `upstream/main`.
  - Output structured JSON and Markdown audit receipt to `/home/ubuntu/.hermes/logs/git-nightly-receipt.md`.
- [ ] **Step 3:** Write unit tests for `nightly_git_hygiene.py`.
- [ ] **Step 4:** Verify script runs cleanly with zero side-effects in dry-run mode.

#### Task 3.2: Schedule Nightly Cron Job
- [ ] **Step 1:** Configure a scheduled cronjob in `~/.hermes/cron/jobs.json` to execute every night at 23:55 MYT.
- [ ] **Step 2:** Deliver daily audit summary to Telegram/chat channel.

---

## Expected Outcomes & Acceptance Criteria

1. **Single Repo SSOT:** All development and agent instructions strictly operate out of `/home/ubuntu/hermes-agent-personal_assistant-work`. No more confusion about which repo to edit.
2. **Zero Runtime Disruption:** Gateway service remains online and stable without broken imports or missing files.
3. **Up-to-date AGENTS.md:** Durable rules enforcing 1 repo and self-improving nightly audits.
4. **Nightly Git Self-Improvement:** Automated audit runs every night, detecting uncommitted drift, running security scans, and providing a clean receipt.
