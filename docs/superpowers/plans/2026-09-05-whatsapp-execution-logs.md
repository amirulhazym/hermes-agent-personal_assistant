# WhatsApp Execution Logs & Tool Progress Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable transparent live developer execution logs (tool progress) and reasoning display in WhatsApp chat sessions to achieve parity with Telegram, without code blocks, and preserving progress history in chat.

**Architecture:** 
1. Update `config.yaml` to enable `tool_progress: all` and `show_reasoning: true` for platform WhatsApp under `display.platforms.whatsapp`.
2. WhatsApp adapter leaves `supports_code_blocks = False` as requested in Q2 (Option B: inline text format `💻 terminal: "..."`), allowing compact command previews without multi-line code block fencing.
3. Synchronize template changes to SSOT repo (`/home/ubuntu/hermes-agent-personal_assistant-work/config/config.yaml.template`).
4. Validate live configuration loading via Python test harness without disrupting running session.

**Tech Stack:** Python 3.11, YAML, Hermes Gateway Display Config Resolver, Git SSOT.

## Global Constraints
- Sole development repo: `/home/ubuntu/hermes-agent-personal_assistant-work` on `main`.
- Live config lives in `/home/ubuntu/.hermes/config.yaml`.
- Do not perform disruptive gateway service restarts mid-session without verification.
- Evidence-first verification for all config changes.

---

### Task 1: Update SSOT Config Template
**Files:**
- Modify: `/home/ubuntu/hermes-agent-personal_assistant-work/config/config.yaml.template:364-368`

**Interfaces:**
- Consumes: User decisions (Q1: all, Q2: inline/no code block, Q3: show_reasoning true, Q4: history preserved).
- Produces: Updated SSOT template matching intentional configuration.

- [ ] **Step 1: Check diff before modifying template**
Run: `git -C /home/ubuntu/hermes-agent-personal_assistant-work diff config/config.yaml.template`

- [ ] **Step 2: Update template in personal assistant repository**
Modify `display.platforms.whatsapp` in `/home/ubuntu/hermes-agent-personal_assistant-work/config/config.yaml.template`:
```yaml
    whatsapp:
      show_reasoning: true
      busy_ack_detail: false
      tool_progress: all
```

- [ ] **Step 3: Verify git diff in personal assistant repository**
Run: `git -C /home/ubuntu/hermes-agent-personal_assistant-work diff config/config.yaml.template`

- [ ] **Step 4: Commit changes to SSOT repo**
Run:
```bash
git -C /home/ubuntu/hermes-agent-personal_assistant-work add config/config.yaml.template
git -C /home/ubuntu/hermes-agent-personal_assistant-work commit -m "fix(display): enable tool_progress and show_reasoning on whatsapp"
```

---

### Task 2: Update Live Runtime Configuration
**Files:**
- Backup: `/home/ubuntu/.hermes/config.yaml.bak.toolprogress.<timestamp>`
- Modify: `/home/ubuntu/.hermes/config.yaml:412-415`

**Interfaces:**
- Consumes: Task 1 verified schema.
- Produces: Active live config with WhatsApp tool progress enabled.

- [ ] **Step 1: Create backup of live config.yaml**
Run: `cp /home/ubuntu/.hermes/config.yaml /home/ubuntu/.hermes/config.yaml.bak.toolprogress.$(date +%s)`

- [ ] **Step 2: Apply patch to live config.yaml**
Update lines in `/home/ubuntu/.hermes/config.yaml`:
```yaml
    whatsapp:
      busy_ack_detail: false
      show_reasoning: true
      tool_progress: all
```

- [ ] **Step 3: Verify live configuration syntax and resolution**
Run:
```bash
python3 -c '
import yaml
from gateway.display_config import resolve_display_setting

with open("/home/ubuntu/.hermes/config.yaml") as f:
    cfg = yaml.safe_load(f)

tp = resolve_display_setting(cfg, "whatsapp", "tool_progress")
sr = resolve_display_setting(cfg, "whatsapp", "show_reasoning")
print(f"WhatsApp tool_progress: {tp}")
print(f"WhatsApp show_reasoning: {sr}")
assert tp == "all", f"Expected all, got {tp}"
assert sr is True, f"Expected True, got {sr}"
print("VERIFICATION PASS: WhatsApp display settings resolved correctly.")
'
```

---

### Task 3: End-to-End Resolution Verification
**Files:**
- Verification: Test resolution across Telegram vs WhatsApp to verify parity.

- [ ] **Step 1: Run cross-platform display parity check**
Run:
```bash
python3 -c '
import yaml
from gateway.display_config import resolve_display_setting

with open("/home/ubuntu/.hermes/config.yaml") as f:
    cfg = yaml.safe_load(f)

for plat in ["telegram", "whatsapp"]:
    tp = resolve_display_setting(cfg, plat, "tool_progress")
    sr = resolve_display_setting(cfg, plat, "show_reasoning")
    print(f"[{plat}] tool_progress={tp}, show_reasoning={sr}")
'
```
Expected output:
Both platforms report `tool_progress=all` and `show_reasoning=True`.
