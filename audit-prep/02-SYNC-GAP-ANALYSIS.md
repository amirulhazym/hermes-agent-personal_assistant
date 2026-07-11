# SYNC-GAP-ANALYSIS.md — Cross-Platform Comparison Framework

> **Purpose:** Framework for external AI agents to compare VPS ↔ WSL2/Windows ↔ GitHub  
> **Generated:** July 7, 2026 — 12:15 MYT  
> **Context:** All 3 platforms contain the same project but are NOT synchronized

---

## 1. Platform Overview

### Platform A: VPS (Singapore)
- **This document's baseline** — see `01-VPS-BASELINE.md`
- **Role:** 24/7 live production system
- **How to access:** Through Hermes agent on WhatsApp/Telegram, or SSH
- **Git branch:** `hermes-live`
- **Last synced:** No commits since July 1

### Platform B: Windows PC / WSL2
- **Role:** Original development environment, first platform built
- **Location:** `F:\AI Prep\OVIS\Hermes Agent\MJay\` (Windows)  
  WSL2 distro at `F:\wsl\hermes-agent\`
- **Git branch:** Presumably `main`
- **Last known state:** Rebuilt from scratch after original WSL2 broke (Phase 14 recovery). Was primary platform before VPS migration.
- **Contains:** All original development files, scripts, Obsidian vault

### Platform C: GitHub
- **Role:** Version control, collaboration, backup
- **Repo:** `amirulhazym/hermes-agent-personal_assistant`
- **Branches:** `main` (primary), `hermes-live` (VPS pushes here)
- **Last commit:** Phase 23 era (July 1)

---

## 2. Known Differences

### Persona / System Prompt

| Aspect | VPS (live) | VPS (git) | Likely WSL2 |
|---|---|---|---|
| SOUL.md size | 132 lines, 10.8KB | 61 lines, 3.6KB | Unknown — likely somewhere in between |
| Content | Full epistemic standards, geo-protocol, skill trigger system, tool enforcement | Original MJ persona (Jun 28) | May have intermediate versions |

**Action for auditor:** Compare all 3 SOUL.md versions line-by-line.

### Config / Provider Setup

| Aspect | VPS Live | VPS Git | Notes |
|---|---|---|---|
| Default model | deepseek-v4-pro | Unknown | Pro is expensive — likely different on WSL2 |
| Provider | opencode-go | Unknown | Paid subscription — WSL2 may use different provider |
| Fallback providers | [] (none) | Unknown | Gap visible in live config |
| Vision model | opencode-zen / mimo-v2.5-free | Unknown | |
| Reasoning effort | xhigh | Unknown | |

### Cron Jobs

| Aspect | VPS | Likely WSL2 |
|---|---|---|
| Total jobs | 14 (was 15, Morning Briefing removed) | May have different count |
| Medication jobs | via chain_monitor.sh + scripts | May have hardcoded 20 jobs |
| Script-based jobs | 7 no_agent jobs | May differ |

### Scripts

| Aspect | VPS | Notes |
|---|---|---|
| fix_models.py | Jul 5 version (16KB) | Post-update model restoration |
| chain_llm.py | Jul 7 version (15KB) | Latest — uses LLM for reminders |
| med_confirm.py | Jul 7 version (21KB) | Drug-level tracking with --dry-run |

The Windows/WSL2 likely has different versions of these scripts — possibly older, possibly newer.

### PROGRESS.md / Documentation

| Aspect | VPS Git | Notes |
|---|---|---|
| Latest phase | Phase 23 (June 29) | Design methodology skill |
| Phase 17b+ | "Option C build start" | What is this? |

Windows/WSL2 may have PROGRESS.md with additional phases or modifications post-Phase 23.

### Git Branches

| Branch | Location | Purpose |
|---|---|---|
| `main` | GitHub | Human-reviewed stable branch |
| `hermes-live` | VPS + GitHub | Agent-pushed working branch |

The `hermes-live` branch has commits not yet merged to `main` (git workflow setup, scripts update, Option C).

---

## 3. Gap Detection Methodology

### For External AI Agent:

**Phase 1: Catalog Each Platform**
1. Read all files on each platform
2. Record file name, size, last-modified timestamps
3. Note any file that exists on one but not others

**Phase 2: Compare Content Line-by-Line**
Priority files to diff:
- `SOUL.md` / system prompt
- `config.yaml` structure (model, provider, features)
- `PROGRESS.md` (phase tracking)
- `DECISIONS.md` (decision log)
- All `scripts/*.py` and `scripts/*.sh`
- Cron job definitions (`jobs.json` vs `hermes cron list`)
- State files (med-status.json, med-schedule.json, etc.)

**Phase 3: Identify Sync Drift**
For each difference found:
- Which platform has the LATEST version?
- Is the change intentional (work in progress) or accidental (forgotten sync)?
- Does the change depend on platform-specific context (e.g., WSL2 paths vs VPS paths)?

**Phase 4: Classify Gaps**
| Classification | Meaning |
|---|---|
| **DRIFT — VPS AHEAD** | VPS has changes not on WSL2 or GitHub |
| **DRIFT — WSL2 AHEAD** | WSL2 has changes not on VPS or GitHub |
| **DRIFT — BOTH AHEAD** | Both have different changes, neither on GitHub |
| **ORPHAN** | File exists on only one platform |
| **CONFLICT** | Same file, different content, both valid |
| **STALE** | File is outdated on all platforms |

---

## 4. Sync Protocol

### Step 1: Establish Source of Truth
For each file category, determine which platform is authoritative:
- **Live behavior:** VPS (it's what's running)
- **Development history:** WSL2/Windows (it's where work was done)
- **Version control:** GitHub (it's the single source for collaboration)

### Step 2: Reconcile SOUL.md
1. Diff all 3 versions
2. VPS live version is the LATEST (updated today, 132 lines)
3. Merge any good changes from WSL2 version into VPS
4. Commit final version to GitHub

### Step 3: Reconcile Scripts
1. Diff `~/.hermes/scripts/` on VPS vs WSL2
2. Latests should be on VPS (med_confirm.py Jul 7, chain_llm.py Jul 7)
3. Check if WSL2 has scripts VPS doesn't
4. Unify — commit to GitHub

### Step 4: Reconcile Config
1. Diff config.yaml on VPS vs WSL2
2. Identify which provider/model setup is correct for current state
3. Align fallback provider configuration
4. Commit to GitHub

### Step 5: Reconcile Cron
1. Export cron list from both platforms
2. Identify jobs that exist on one but not other
3. Review which should be kept vs removed
4. Align

### Step 6: Reconcile Documentation
1. Update PROGRESS.md with all phases since Phase 23
2. Add decisions made in recent sessions to DECISIONS.md
3. Update AUDIT.md with current state
4. Commit ALL to GitHub

### Step 7: Git History Rewrite (Optional — User Plan)
1. Create timeline of actual work based on file timestamps + session contexts
2. Create "dummy" commits with appropriate dates and realistic intervals
3. Rebase current commits into proper chronological order
4. Push to new branch

---

## 5. Verification Checklist

After sync, verify:

- [ ] SOUL.md is identical on all 3 platforms (VPS live, VPS git, WSL2, GitHub)
- [ ] config.yaml provider/model config is aligned
- [ ] All scripts exist on all platforms with same versions
- [ ] cron jobs list is identical (within platform-specific constraints)
- [ ] PROGRESS.md is up to date
- [ ] DECISIONS.md reflects ALL decisions
- [ ] No orphan files (files on one platform only, unless intentionally local)
- [ ] Gateway restarts cleanly with synced config
- [ ] Medication reminders fire correctly with synced scripts
- [ ] Med state files (med-status.json, med-schedule.json) are correct on VPS

---

*End of Sync Gap Analysis. This framework assumes the external AI agent has access to all 3 platforms' filesystems.*
