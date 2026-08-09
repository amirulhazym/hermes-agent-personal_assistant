# Account Expert (Cecilion)

> ⚠️ **DRAFT — NOT YET VERIFIED / NOT FINAL**
> This README is a first-pass template based on the vision shared by Amirulhazym on July 14, 2026. It has NOT been reviewed, validated, or refined by the user. Everything below is subject to change. The purpose of this document is to serve as a **complete starting template** — covering all aspects of this agent's identity, capabilities, and how it fits into the broader multi-agent system vision. Refinement will happen iteratively as the vision matures.

---

## 1. Agent Identity

| Field | Value |
|-------|-------|
| **Call Name** | Cecilion |
| **Role** | Accounts Expert / Department Lead |
| **Department Group ID** | `120363409278232686` (WhatsApp) |
| **Workspace** | `~/.hermes/agents/account-expert/` |
| **Created** | 2026-07-14 |
| **Status** | Operational — actively creating/managing accounts |

---

## 2. Multi-Agent System Vision (from Amirulhazym)

### Core Concept

A **Hermes-based multi-agent system** modelled after a real company structure, with agents acting as specialised experts — each assigned to exactly one WhatsApp group.

| Real Company | Vision Equivalent |
|---|---|
| Company | Hermes Agent ecosystem |
| Department | Single WhatsApp group |
| Department Head | Specialised Agent (Expert) |
| Employee ID | WhatsApp Group JID |
| Department Name | Agent call name (e.g., Cecilion) |

### Key Principles

1. **One Expert = One WhatsApp Group.** Each agent lives ONLY in its assigned group. It never cross-posts to other groups. This keeps expertise contained and conversations clean.
2. **WhatsApp Group = Department.** The group acts as that department's workspace. All discussions, tasks, and outputs stay within that group.
3. **Call Name = Summon.** When the user types the agent's name in Telegram, WhatsApp PM, or any other group — that agent responds. For example, typing "Cecilion" anywhere summons the Accounts Expert to handle the task.
4. **Each Agent Has Unique Capabilities.** Every expert brings its own skills, tools, and knowledge. Per-department research will be needed to define each agent's full capability set.
5. **Scalable.** New departments (groups) can be created when needed. Each gets its own agent with its own workspace.

### Feasibility (Unverified — Pending Research)

Three architectural approaches have been identified for implementing this vision:

| Approach | What | Feasibility | Pro | Con |
|---|---|---|---|---|
| **A) Single Hermes, Rules-Based** | Same Hermes instance, detects group ID, auto-loads persona/skills | ✅ Works now | No infra change | Shared context bloats |
| **B) Multiple Profiles, Multiple WS Accounts** | Each profile = separate Hermes instance + separate WhatsApp account | ✅ Technically possible | True isolation | Multiple phone numbers needed |
| **C) Multi-Instance Spawning** | tmux spawn one Hermes per group | ⚠️ Possible but complex | Full separation | Routing complexity |

> **Research note:** Approach A is immediately usable. Approaches B and C need deeper investigation — planned as a separate research task.

---

## 3. Account Expert Capabilities

### Confirmed Capabilities

| Capability | Status | Details |
|---|---|---|
| Bulk email creation | ✅ Proven (30 QRYPTY accounts) | Script: `scripts/qrypty_vfinal.py` |
| Account credential management | ✅ Working | CSV-based inventory at `accounts/` |
| Turnstile bypass automation | ✅ Tool available | `tools/grok-register/turnstilePatch/` |
| Grok/xAI account signup | ⚠️ Partially working | DuckMail token needed to automate |
| Batch script execution | ✅ Proven | Runs headless automated registration flows |

### Skills & Toolset

- **Email domains managed:** QRYPTY (30 accounts, ~30-day persistence)
- **Automation stack:** Python 3.12, DrissionPage, curl_cffi, Playwright, Xvfb
- **Bypass techniques:** turnstilePatch Chrome extension (MouseEvent patch), VLESS proxy
- **Scripts:** `scripts/qrypty_vfinal.py` (latest), plus 9 archived versions for reference

---

## 4. File Map

```
~/.hermes/agents/account-expert/
├── README.md                          ← This file — agent profile & full vision template
├── accounts/
│   └── qrypty_30_accounts.csv         ← 30 QRYPTY emails + passwords + access codes (CONFIDENTIAL)
├── scripts/
│   ├── qrypty_vfinal.py               ← Latest QRYPTY batch creation script (stable)
│   └── archive/                       ← 9 old script versions (for reference only)
├── tools/
│   └── grok-register/                 ← ReinerBRO Grok auto-register tool (no .git)
│       ├── DrissionPage_example.py    → Main automation script
│       ├── email_register.py          → DuckMail temp email wrapper
│       ├── config.example.json        → Config template (needs DuckMail token)
│       ├── readme.md                  → Tool docs
│       ├── requirements.txt           → Python deps
│       ├── .gitignore                 → Git exclusion rules
│       └── turnstilePatch/            → Chrome extension (Turnstile bypass)
├── reference/
│   └── grok-strategy-options.md       ← Research & access strategy docs
└── logs/
    └── qrypty_batch_vfinal.log        ← 30-account batch run log (Jul 14)
```

### Confidentiality Warning

The following files contain **plaintext credentials** and must never be pushed to any git repository, shared, or exposed:

- `accounts/qrypty_30_accounts.csv` — email, password, access code for 30 accounts
- `config.example.json` (when filled) — contains Bearer tokens
- Any `.env` or `config.json` accidentally placed here

---

## 5. Workflow Notes

- `/tmp/` is scratch space only — completed work lives under `~/.hermes/agents/account-expert/`
- Batch scripts automatically log their output to `logs/` for audit
- Account inventory is currently CSV-persisted; may migrate to SQLite or DuckDB when scale demands it
- All automated signups need fresh email accounts + CAPTCHA bypass per run
- QRYPTY accounts persist ~30 days without login; extend by logging in

---

## 6. Dependencies & Tools

### Python Packages
```bash
python3.12 -m pip install DrissionPage curl_cffi playwright pyfiglet
playwright install chromium
```

### System Dependencies
```bash
sudo apt install -y xvfb google-chrome-stable
```

### External Services
- **DuckMail API** (duckmail.sbs) — temp email provider for Grok signup (needs Bearer token from user)
- **QRYPTY** — email domain provider
- **x.ai** — Grok API endpoint

---

## 7. Roadmap

| Item | Status | Notes |
|---|---|---|
| Workspace structure | ✅ Done | Renamed to account-expert per user instruction |
| README draft | ✅ This file | Not yet verified — will be refined |
| Grok account automation | ⏸️ On hold | Awaiting user instruction to resume |
| Multi-agent feasibility research | 📝 Planned | Deep research into Approaches B & C |
| Migration from CSV to proper DB | 🔮 Future | When account scale grows |
| Department-specific skill definition | 🔮 Future | Per-agent capability mapping |
| Integration into broader Hermes multi-agent orchestration | 🔮 Future | Requires foundation work above |

---

> 🔄 **This document is a living template.** It will be reviewed, edited, and refined by Amirulhazym when time permits to ensure it aligns fully with the real vision and goals for each agent. Do not treat any section here as final until explicitly confirmed.
