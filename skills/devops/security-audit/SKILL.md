---
name: security-audit
description: "Evidence-based security audit methodology — verify external AI audit claims against live system, scan git repos for credential exposure across all branches/history/refs, classify risk (credential leak vs recon vs privacy), and recommend portfolio-safe hardening without unnecessary key rotation."
tags: [security, audit, git, secrets, hardening, repo-sanitization]
---

# Security Audit

## When to Load

- User shares a security audit from another AI (DeepSeek, Claude, Gemini, etc.) and asks you to verify it
- User says "check if my repo has leaked credentials" or "audit my repo for security issues"
- User asks about credential rotation, secret exposure, or repo sanitization
- User asks about portfolio-safe security (keep repo public, remove sensitive data)
- Any task involving scanning git history for secrets across multiple branches/refs

## Core Principle

**Fix the source of exposure, not the symptom.** SSH lockdown doesn't help if the repo still publishes your IP. Making the repo private destroys portfolio value when content sanitization is sufficient.

## Chat-Delivered Credential Boundary

Use the reusable procedure in `references/chat-edge-secret-handoff.md` whenever a credential must arrive through WhatsApp, Telegram, or another chat channel while remaining outside the LLM context.

The minimum distinction is:

- **Model-blind** is not the same as **runtime-blind**. Intercepting before message extraction prevents prompt exposure; writing the key to `.env` does not prevent same-user model tools from reading it.
- Prefer an edge-owned control lane, exact sender/chat authorization, one-time challenge/reference, bounded TTL, fail-closed consumption, and message-ID replay suppression.
- Prefer a memory-only broker over `.env` persistence. Keep the broker environment minimal, expose only a non-secret loopback token to Hermes, inject the upstream credential internally, and redact response headers/stream bodies before returning provider output.
- Do not request the real credential until the candidate process is actually live-loaded. Candidate tests and a provider config readback do not prove runtime activation.
- Obtain explicit approval before a bridge/gateway restart. Report candidate, live-loaded, provider-verified, and end-to-end states separately.

A same-OS-user memory broker is a hardening improvement, not proof against privileged inspection or a malicious same-user process. If that boundary matters, require a separate OS service identity and tool sandbox, or label the requirement unresolved.

See the reference for the verification ladder, synthetic-sentinel tests, response-redaction pitfalls, and status vocabulary.

## Evidence-Before-Action Protocol

When another AI produces a security audit, DO NOT accept claims at face value. Follow this protocol:

### Phase 0: Claim Extraction
Extract every specific, verifiable claim from the audit. Example claims:
- "HERMES_REDACT_SECRETS = false" → check config.yaml
- "SSH password auth enabled" → check sshd_config
- "Git history leaked secrets" → scan all branches, all refs
- "creds.json stored in plaintext" → check file existence + permissions

Label each claim's evidence level in the source audit as:
- ASSERTED WITH EVIDENCE (has specific file/line/code reference)
- ASSERTED WITHOUT EVIDENCE (just a statement)
- CONFIDENT ASSERTION (no evidence, strong language)

### Phase 1: Live Verification
For each verifiable claim, run the actual system check:

| Claim type | Verification command | What to look for |
|---|---|---|
| SSH config | `sudo cat /etc/ssh/sshd_config \| grep -iE "Password\|PermitRoot\|AllowUsers"` | PasswordAuthentication yes/no |
| Secret redaction | `grep redact_secrets ~/.hermes/config.yaml` + check /proc/PID/environ for env var override | Config + runtime match? |
| File existence/permissions | `stat --format='%A %U:%G' ~/.hermes/path` | 600 vs 644 vs 777 |
| Firewall | `sudo iptables -L -n`, `sudo ufw status`, `fail2ban-client status` | Open ports, active protections |
| Listening ports | `sudo ss -tlnp` | 0.0.0.0 vs 127.0.0.1 binding |
| Cron jobs | `crontab -l`, `ls /etc/cron.d/` | What runs as which user |
| Service version | `hermes --version`, `git log --oneline -3` | How outdated? |

### Phase 2: Classification per Claim
After verification, label each claim:

- **✅ VERIFIED — MATCHES** — Audit claim is correct, evidence supports it
- **✅ VERIFIED — ALREADY FIXED** — Audit identified a real issue, but it's already resolved
- **❌ FALSIFIED** — Audit claim is wrong; evidence contradicts it
- **⚠️ PARTIALLY TRUE** — Core concern valid, but specifics wrong or overclaimed
- **❓ UNVERIFIABLE FROM CURRENT CONTEXT** — Cannot confirm or deny with available tools

### Phase 3: Risk Chain Mapping
Map the actual attack path, not the theoretical worst case:

```
Step 1: [public repository / Shodan scan / other]
  → Step 2: [what attacker learns]
  → Step 3: [what attacker needs to exploit]
  → Step 4: [what attacker gains]
  → Step 5: [blast radius]
```

For each step, identify what BLOCKS the chain. Example:
```
Public repo → IP known
  → SSH brute-force → BLOCKED BY: no password auth (key-only)
  OR → BLOCKED BY: fail2ban after 3 attempts
  OR → BLOCKED BY: Security Group whitelist
```

## Git Secret Scanning Methodology

### Scan targets (in order):
1. **Current content** — `git grep` across current HEAD for all sensitive patterns
2. **All branches** — `git branch -a`, scan each branch
3. **All tags** — `git tag -l`, scan if any exist
4. **Full history** — `git log --all --full-history -p | grep` for each credential pattern
5. **Deleted files** — `git log --all --diff-filter=D` for files that existed but were removed
6. **Reflogs** — `git reflog show --all` if accessible (local repos only)
7. **Patch files** — committed patches may contain sensitive diff context

### Credential patterns to scan:

| Pattern | Type | Example |
|---|---|---|
| `sk-[a-zA-Z0-9]{20,}` | OpenAI/DeepSeek API keys | `sk-abc123...` |
| `[0-9]{8,}:AA[a-zA-Z0-9_-]{20,}` | Telegram bot tokens | `123456789:AAbbcc...` |
| `BEGIN (RSA\|EC\|DSA\|OPENSSH\|PRIVATE) KEY` | Private keys | SSH, TLS, signing keys |
| `ghp_\|gho_\|github_pat_` | GitHub tokens | Personal access tokens |
| `AIza[0-9A-Za-z_-]{35}` | Google API keys | AIzaSy... |
| `$2[abxy]\$[0-9]{2}\$` | bcrypt password hashes | Shadow file contents |
| `-----BEGIN CERTIFICATE-----` | TLS certificates | Exposed in git |
| `smtp://.*:.*@` | SMTP credentials | Email login |
| `mongodb://.*:.*@` | Database URLs | With embedded passwords |

### Pattern classes that are NOT secrets (don't flag):
- Environment variable NAMES (`DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`) — knowing the name is not knowing the value
- Redacted values (`***`, `YOUR_KEY_HERE`, `sk-...`) — intentionally obscured
- Config templates with placeholder values — `.template` files are documentation
- Documentation listing credential LOCATIONS — unless the exact path reveals sensitive system structure

### Confirmed-false signals:
- `GITHUB_TOKEN=***` in documentation with asterisks = intentional redaction, not a leak
- Partial key in commit message like `sk-cp-...1s5U` = already redacted by user/agent

## Risk Classification Framework

Every finding belongs to exactly ONE of these categories:

| Category | Severity | Example | Action |
|---|---|---|---|
| **Actual credential exposure** | 🔴 Critical | API key value, bot token, private key committed | Rotate key NOW, purge from history, force-push |
| **Infrastructure reconnaissance** | 🟠 High | Public IP, SSH username, provider, ASN, SSH commands in repo | Redact from content + optionally purge history |
| **Personal privacy exposure** | 🟡 Medium | Real name, email, Windows username, home paths | Redact from content |
| **Operational detail leak** | 🟡 Low-Med | Cron schedules, recovery procedures, architecture docs | Redact from public repo content |
| **Best-practice gap** | 🔵 Informational | .gitignore missing entries, hardcoded paths, missing security hardening | Document as improvement opportunity |

### Don't rotate keys unless:
1. Actual credential VALUE was found in git history (sk-..., bot token, private key)
2. OR the key was confirmed in a log/artifact that git history reference proves exists
3. OR the key grants access to a system directly reachable from the exposed info

**Environment variable NAMES are not secrets.** Rotating because `DEEPSEEK_API_KEY` appeared in a README is cargo-cult security. The attacker needs the VALUE, and if it was never committed, rotation is unnecessary.

## Portfolio-Safe Repo Hardening

When the user wants to keep the repo PUBLIC (portfolio/project showcase), DO NOT recommend making it private. Instead:

### Content sanitization (P0):
Replace these with placeholders:
- Public IPs → `[vps-ip]` or `[server-ip]`
- SSH usernames → `user@host`
- Provider names + locations → `[cloud-provider]`, `[region]`
- SSH key paths → `~/.ssh/[ssh-key]`
- ASN/IP details → `[asn-details]`
- Personal paths (`/home/username/`) → `$HOME` or `[home]`
- Email addresses → `[email]`
- Full real names → `[name]`

### History purge (P1, optional):
`git filter-repo` to remove IP from all historical commits.
Force-push affects all branches and remote refs.
Any existing clones retain the old data.

### What NOT to rename:
- Functional env var names used in runnable code (breaks scripts)
- Config keys or provider names (code will fail)
- Variable names in .env references (no security value, high maintenance cost)

## Common Pitfalls

| Pitfall | Correction |
|---|---|
| Assuming an audit claim is true because it's "from an AI" | Verify every claim against live system before accepting |
| Recommending key rotation for env var NAME exposure | Rotation is for VALUE leaks only — names are not secrets |
| Making repo private as first resort | Content sanitization + public portfolio > private repo |
| Patching SSH without addressing repo exposure first | Fix the public information source FIRST, then harden access |
| Renaming env vars in runnable code for "security" | Renaming breaks scripts without improving security |
| Presenting system-certificate rotation alongside credential rotation | Different class of action with different urgency |

## SSH Exposure Snapshot (quick probe for general system audits)

When doing any live host audit (not just repo scans), a 4-command read-only check
surfaces the highest-frequency real exposure on internet-facing VPS hosts:

```bash
sudo -n journalctl -u ssh --since "24 hours ago" | grep -ciE 'failed|invalid'   # brute-force volume
sudo -n sshd -T | grep -iE '^(passwordauthentication|permitrootlogin)'          # effective config
systemctl is-active fail2ban; which fail2ban-server                              # brute-force defense
ls -lh /var/log/btmp*                                                            # failure log growth
```

2026-08-23 baseline on this VPS: 6,057 failed attempts/24h with
`passwordauthentication yes` + `permitrootlogin yes` and fail2ban not installed —
the btmp rotation alone held ~102MB. Recommended fix ORDER matters: (1) verify the
owner's SSH key login works from their machine FIRST, (2) only then set
`PasswordAuthentication no` + `PermitRootLogin no`, (3) install/enable fail2ban.
Flipping password auth off before key-verification risks full lockout.

## Related Skills

- `evidence-first-feasibility-assessment` — General verification methodology; the External AI Agent Audit Workflow section covers runtime/medication auditing
- `system-verification-qa` — Hermes-specific runtime verification (model, provider, config)
- `anti-fabrication-guardrails` — Preventing agent fabrication in medical/health contexts
