# Cross-Platform Audit Preparation — Session Template (2026-07-07)

> Full worked example of preparing a multi-platform Hermes Agent system for external AI audit.
> Reference for `system-verification-qa` skill.

## Context

User has 3 platforms (VPS / WSL2-Windows / GitHub) all out of sync. User wants external AI coding agents (OpenCode, ZCode, Gemini Antigravity) to do a full deep audit, cross-reference findings, and reconcile all platforms.

## Preparation Deliverables

### 1. PLATFORM-BASELINE.md
Complete inventory of the accessible platform. Sections:
1. System Overview (specs, IP, OS, Hermes version)
2. Model & Provider Configuration (config.yaml excerpt)
3. Cron Jobs — Complete Inventory (every job with ID, schedule, script, status, history)
4. Scripts Directory (every .sh/.py with purpose + first 50 lines)
5. Active Plugins (with purpose)
6. State Files — Complete Inventory (size, modified date, purpose)
7. Skills Library (count + categories)
8. Persona Files (SOUL.md, MEMORY.md, USER.md summary)
9. Gateway Status
10. Git Repository (branch, commits, key files)
11. Existing Audit Trail (previous audit files + consensus findings)
12. File Age Map (every tracked file with last-modified)
13. Session Database Summary
14. Known Issues & Gaps (live on this platform)

### 2. SYNC-GAP-ANALYSIS.md
Framework for comparing platforms:
1. Platform Overview (role, location, access method per platform)
2. Known Differences (SOUL.md, config, cron, scripts, docs)
3. Gap Detection Methodology (catalog → compare → classify → prioritize)
4. Sync Protocol (7 steps: truth → reconcile per category → commit)
5. Verification Checklist

### 3. AI-AUDIT-PROMPT-TEMPLATE.md
Provider-agnostic reusable prompt:
1. Quick Start — paste-ready prompt block
2. Methodology rules (evidence-first, 11 audit dimensions)
3. Anti-fabrication guardrails
4. Output format specification
5. Adaptation guide per AI agent (OpenCode, ZCode, Gemini)
6. Pro tips for getting better audits

### 4. EXECUTION-GUIDE.md
Beginner-friendly step-by-step:
1. Upload to AI agents (which agent, how to send files)
2. Read and compare audit results (cross-reference findings)
3. Sync all 3 platforms (access → compare → merge → push → PR)
4. Fix critical issues (one at a time)
5. Git history rewrite (optional)
6. Ongoing maintenance (daily/weekly/monthly)
7. Quick reference commands

## Key User Preferences Applied

- Multiple separate files > one giant file
- 100% completeness demanded
- Beginner-friendly step-by-step format
- Files saved on VPS for direct access + delivered via chat
- Role clarified BEFORE execution (preparation, not audit)
