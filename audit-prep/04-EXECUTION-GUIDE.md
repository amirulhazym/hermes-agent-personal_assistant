# Execution Guide — Step-by-Step for the System Overhaul

> **For:** Amirulhazym  
> **Goal:** Cross-platform sync, deep audit, and system overhaul  
> **Difficulty:** Beginner-friendly — follow steps in order  

---

## What These Files Are

You now have 4 preparation files on the VPS:

| # | File | What It Is | Who Uses It |
|---|---|---|---|
| 1 | `01-VPS-BASELINE.md` | Complete inventory of everything on the VPS | You + AI agents |
| 2 | `02-SYNC-GAP-ANALYSIS.md` | Framework for comparing platforms | AI agents |
| 3 | `03-AI-AUDIT-PROMPT-TEMPLATE.md` | Ready-to-paste prompt for any AI agent | You → AI agents |
| 4 | `04-EXECUTION-GUIDE.md` | This file — step-by-step instructions | You |

**File locations on VPS:** `/home/ubuntu/mjay/audit-prep/`

---

## Phase 1: Upload to AI Coding Agents (20 min)

### Step 1.1 — Choose Your AI Agents

You mentioned OpenCode, ZCode (Z.AI), and Gemini Antigravity. Here's how to use them:

| AI Agent | Best For | How to Upload |
|---|---|---|
| **OpenCode** | Deep code analysis, file reading, live testing | Use Claude Code or opencode CLI |
| **ZCode (Z.AI)** | Free-form exploration, finding hidden issues | Copy-paste prompt + files |
| **Gemini Antigravity** | Architecture review, security audit | Attach files, paste prompt |
| **Claude** | Thorough systematic audit | Attach files via conversation |
| **Qwen** | Cross-reference, find contradictions | Paste prompt |

**Recommendation:** Use 2-3 different AI agents — each will find different things.

### Step 1.2 — Send Files to AI Agents

**Option A: Copy from VPS (if agent can access VPS directly)**
```bash
# The files are at:
/home/ubuntu/mjay/audit-prep/01-VPS-BASELINE.md
/home/ubuntu/mjay/audit-prep/02-SYNC-GAP-ANALYSIS.md
/home/ubuntu/mjay/audit-prep/03-AI-AUDIT-PROMPT-TEMPLATE.md
```

**Option B: Download from chat (what you're reading now)**
- These files are being sent to you via WhatsApp
- Save them, then upload to your AI agent

**Option C: Use the prompt template**
- Open file `03-AI-AUDIT-PROMPT-TEMPLATE.md`
- Copy the "Quick Start" section
- Paste into your AI agent
- Attach files 01 and 02

### Step 1.3 — What to Tell Each AI Agent

**Agent 1 (OpenCode / primary):** "Do a DEEP AUDIT of this system. Read ALL attached files. Check every claim with evidence. Find what's broken, fragile, inconsistent."

**Agent 2 (secondary):** "Review this system. Additionally, find what Agent 1 might have MISSED. Be adversarial — assume the first audit was overconfident."

**Agent 3 (optional, for cross-reference):** "Compare the findings of Agents 1 and 2. Where do they agree? Where do they disagree? What did both miss?"

---

## Phase 2: Read and Compare Audit Results (1-2 hours)

### Step 2.1 — Collect All Findings
- Save each AI agent's response
- Create a simple list of ALL findings from ALL agents

### Step 2.2 — Cross-Reference
For each finding:
1. Which AI found it? (1 agent, 2 agents, all 3?)
2. Is there EVIDENCE or just opinion?
3. Can YOU verify it by checking the VPS?

### Step 2.3 — Prioritize
Sort findings into:
- **P0 (Fix today):** Breaks medication reminders, security risk, data loss
- **P1 (Fix this week):** Fragile, unreliable, sync issues
- **P2 (Fix this month):** Inefficient, cleanup, nice improvements
- **P3 (Backlog):** "Would be nice," low impact

---

## Phase 3: Sync All 3 Platforms (2-4 hours)

### Step 3.1 — Access Windows/WSL2
- Turn on your PC
- Open WSL2 terminal
- Navigate to the project directory

### Step 3.2 — Compare Files
Using the findings from AI agents:
1. Check SOUL.md on WSL2 vs VPS
2. Check scripts on WSL2 vs VPS
3. Check config.yaml on WSL2 vs VPS
4. Check cron jobs on WSL2 vs VPS

### Step 3.3 — Merge
For files where VPS is ahead:
- Copy from VPS to WSL2

For files where WSL2 is ahead:
- Copy from WSL2 to VPS (upload via git or SCP)

### Step 3.4 — Push to GitHub
```bash
cd ~/mjay  # or your WSL2 path
git add -A
git commit -m "cross-platform sync: unify VPS + WSL2 states"
git push origin hermes-live
```

### Step 3.5 — Create PR to Main
On GitHub:
1. Create Pull Request from `hermes-live` → `main`
2. Review the changes
3. Merge

---

## Phase 4: Fix Critical Issues (ongoing)

After sync is complete, work through the P0 findings:
1. Fix one issue at a time
2. Verify it works
3. Commit
4. Move to next

---

## Phase 5: Git History Rewrite (Optional)

You mentioned wanting to create "dummy" git commits matching actual work timeline.

### Step 5.1 — Create Timeline
List every significant event with actual date/time:
- Phase completions
- Bug fixes
- Feature additions
- Migrations

### Step 5.2 — Create Commits
For each event:
```bash
GIT_AUTHOR_DATE="2026-06-24T14:30:00+08:00" \
GIT_COMMITTER_DATE="2026-06-24T14:30:00+08:00" \
git commit --allow-empty -m "Phase X: description"
```

### Step 5.3 — Push New History
```bash
git push --force-with-lease origin your-branch
```

**⚠️ WARNING:** Force-pushing rewrites history. Do this on a separate branch. Only merge when verified.

---

## Phase 6: Ongoing Maintenance

After overhaul is complete:

### Daily
- Check `hermes cron list` for errors
- Verify medication reminders fired correctly

### Weekly
- Review `hermes insights` for unusual patterns
- Check disk, RAM, load average
- Run `hermes doctor`

### Monthly
- Rotate API keys (NVIDIA, OpenCode, DeepSeek, Telegram)
- Check Baileys for updates/patches
- Review memory usage (MEMORY.md + USER.md)

### On `hermes update`
1. Run `fix_models.py` to restore curated model lists
2. Run `hermes doctor --fix`
3. Restart gateway
4. Verify both platforms connected

---

## Quick Reference: Key Commands

```bash
# Check system health
hermes doctor
hermes cron list
hermes gateway status
df -h /
free -h
uptime

# Medication system
python3 ~/.hermes/scripts/med_confirm.py --status
python3 ~/.hermes/scripts/chain_calc.py --display
cat ~/.hermes/chain-state.json

# Git sync
cd ~/mjay
git status
git log --oneline -5
git diff origin/main

# Skills
hermes skills list
hermes skills list --category agent-methodology

# Fix after update
python3 ~/.hermes/scripts/fix_models.py
hermes doctor --fix
```

---

## Questions? Stuck?

- Ask MJ (me!) — "MJ, what's the status of [thing]?"
- Check the VPS Baseline file for reference
- The AI audit reports will have detailed findings

---

*End of Execution Guide. Follow phases in order. Don't skip steps.*
