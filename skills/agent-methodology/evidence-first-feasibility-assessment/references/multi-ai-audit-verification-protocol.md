# Multi-AI Security Audit Verification Protocol

**Source session:** 2026-07-17 — Security audit of hermes-agent-personal_assistant repo + VPS
**Established:** 2026-07-18

## Problem

Multiple AI auditors (DeepSeek, Claude, Gemini, OpenCode, etc.) independently review the same system. Each produces plausible-sounding findings — some correct, some wrong, some overclaimed. Individually, any single AI can miss things or fabricate evidence. Using them sequentially without verification repeats the same failure pattern: confident wrong claims propagate unchecked.

## Solution: Live-VPS Cross-Verification Chain

```
External AI auditor A report
  → MJ/Hermes VERIFIES claims against live VPS
  → Finds errors (wrong log unit, wrong root state, wrong gitleaks install)
  → External AI auditor B also reviews same evidence
  → Auditor B INDEPENDENTLY catches different errors
  → MJ consolidates: accepted corrections + remaining gaps
  → Final verdict with confidence levels per claim
```

## Protocol Steps

### Step 0: Receive external audit report

When the user shares an audit from another AI (DeepSeek, Claude, Gemini, etc.):

1. **Do NOT accept any claim at face value.** The auditor is confident but may be wrong.
2. **Classify each claim** into:
   - (A) Verifiable from VPS now
   - (B) Requires user's local environment
   - (C) Speculative / overclaimed / not empirically testable

### Step 1: Live-VPS verification (for A claims)

For each (A) claim, independently verify using correct tools:

```bash
# SSH config — use sshd -T (not just reading /etc/ssh/sshd_config)
sudo sshd -T | grep -E "passwordauthentication|permitrootlogin|allowusers"

# Auth logs — use CORRECT journald unit (ssh, not sshd on Ubuntu)
sudo journalctl -u ssh --no-pager | grep -c "Failed password"

# Root account state
sudo passwd -S root   # 'L' means locked, 'P' means usable password

# Listening ports
sudo ss -tlnp

# Firewall
sudo ufw status
sudo iptables -L -n
```

### Step 2: Git branch topology analysis

When the audit involves a git repo, map which branches have sensitive content:

```bash
# List all branches (local + remote)
git branch -a

# Check each branch for sensitive content
git grep -l "PATTERN" branch-name

# Compare which branches are on GitHub vs local-only
curl -s "https://api.github.com/repos/OWNER/REPO/branches"

# Find divergence point
git merge-base branch-a branch-b

# Check if a branch was ever pushed
git branch -r --contains local-branch  # empty = never pushed
```

### Step 3: Secret scanning (not just manual grep)

**Limitations of manual git log grep:**
- Only tests specific regex patterns
- Misses: high-entropy strings, generic bearer tokens, webhook URLs, DB URLs, SMTP creds, JWT secrets
- Gitleaks/TruffleHog catch many patterns manual grep misses

**Command (disposable environment only — not VPS):**
```bash
# Docker (recommended)
docker run --rm -v ${PWD}:/repo ghcr.io/gitleaks/gitleaks:latest detect \
  --source=/repo --verbose

# All history + deleted blobs
gitleaks detect --source=/repo --log-opts="--all --full-history" --verbose
```

**Official wording until Gitleaks is run:**
> "No confirmed secrets within the patterns tested manually. Comprehensive secret scanning pending Gitleaks run in disposable environment."

### Step 4: Risk classification rubric

| Category | Criteria | Example |
|---|---|---|
| **Credential exposure** 🔴 | Actual API keys, tokens, private key blobs | `sk-...` in commit history |
| **Infrastructure recon** 🟠 | IP, SSH user+host, provider, ASN, SSH key paths | `119.28.119.151`, `ubuntu@` |
| **Personal privacy** 🟡 | Real name, email, OS username, file paths with PII | `amiru`, `C:\Users\username\` |
| **Operational detail** 🟢 | Cron schedules, architecture docs, tool names | Service names, ~/.hermes paths |
| **Generic docs** ✅ | PRD, architecture, README with no identifiers | Standard project documentation |
| **Best-practice gap** ℹ️ | Gitignore gaps, hardcoded paths, missing rate limiting | `.gitignore` missing PII files |

### Step 5: Multi-AI cross-correction

When multiple AIs review the same evidence:

1. **Each AI independently spots different issues** — DeepSeek caught wrong SSH log unit, root account state, gitleaks install method. Claude confirmed ordering and added compromise review step.
2. **Convergence on core findings** — all three AIs (MJ, DeepSeek, Claude) agreed SSH hardening was P0. This convergence increases confidence.
3. **Corrections are not failures** — they are the VALUE of the multi-AI approach. Each AI's blind spot is another AI's catch.
4. **Document every correction** — the final report should state "Claim X from Auditor Y was corrected by Auditor Z" so the user sees the full picture.

### Step 6: Remediation ordering

Following the principle of "fix the breachable gap first, then the visible leak, then the history":

```
P0 — SSH hardening (stops active attack)
  └── PasswordAuth no, PermitRootLogin no, key-only, fail2ban, security group

P1 — Content sanitisation (normal commits)
  └── Replace IP/SSH user/provider with placeholders in current files

P2 — Secret scan (disposable env)
  └── Gitleaks/TruffleHog against full history

P3 — History rewrite (optional, irreversible)
  └── git filter-repo to purge IP from git history
  └── Only after P0-P2 verified + backup created
```

### Step 7: File timestamp preservation

When rewriting history or sanitising:

- `git filter-repo` **preserves author dates** by default — file creation/commit dates match original work dates, not the rewrite date
- Normal `git commit` uses current time for committer date — this is correct for sanitisation commits (they represent when sanitisation happened)
- The user's concern about "tarikh sebenar file dikerjakan" is addressed by filter-repo's default behavior

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| `journalctl -u sshd` returns empty | Use `journalctl -u ssh` on Ubuntu/Debian |
| Assume `PermitRootLogin yes` = root exploitable | Check `passwd -S root` — `L` means locked, unusable |
| `pip install gitleaks` | Use official Go binary or Docker container — pip version may be different package |
| Only check current branch content | Scan ALL branches, including remote-only refs like `origin/overhaul/exec` |
| Only scan current content | Use `git log --all --full-history` to scan deleted blobs too |
| Trust "zero secrets" without Gitleaks | Manual grep misses high-entropy patterns. Official wording: "No confirmed secrets within tested patterns." |
| Assume env var names = secrets | Variable names are documentation, not credentials. Don't rename functional env vars. |
| **Assume main branch has all content** | Check branch topology. `main` may be clean while `hermes-live` or `overhaul/exec` have leaks. |

## Reference Session

Full worked example of this protocol: 2026-07-17 conversation between amirulhazym and MJ Hermes Agent covering:
- DeepSeek security audit of hermes-agent-personal_assistant repo
- Live VPS verification of 9 claims → found 4 real, 2 partial, 3 wrong
- Claude independent reviews and corrections
- 58,447 active SSH brute-force attempts discovered
- Branch topology: main clean, hermes-live local-only, overhaul/exec leaking on GitHub
- P0-P3 remediation plan with file-timestamp preservation
