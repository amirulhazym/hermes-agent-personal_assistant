# Evidence-Based Security Audit — Condensed Reference

Source: 2026-07-17 session — user shared external AI security audit; verified every claim against live VPS.

## Key Epistemic Lesson

The external AI audit claimed 9 issues. After live verification:

| Category | Count |
|---|---|
| ✅ Verified as real | 4 (SSH open, WhatsApp creds, outdated Hermes, RUNBOOK exposure) |
| ⚠️ Partially true | 3 (.env path exposed, git var names, FlareSolverr port) |
| ❌ Falsified | 2 (REDACT_SECRETS said false but was true, git history said leaked secrets but none found) |
| 🔴 Extra issues found | 3 (GitHub repo public, Root SSH enabled, FlareSolverr public) |

**Rule of thumb:** AI security audits reliably identify ~50-60% of real issues. The remaining 40% are either wrong claims or missed findings. Always verify.

## The "Don't Rotate Unless Values Leaked" Decision

User's explicit reasoning (confirmed 2026-07-18):
1. No actual secret VALUE ever committed — only env var NAMES
2. Knowing `DEEPSEEK_API_KEY` exists != knowing the key value
3. Rotation = make-work without actual benefit
4. Named variable in .env can't be exploited without access to .env or SSH

**Exception:** If actual `sk-...` or bot token pattern found in git history → rotate immediately.

## Portfolio-VS-Private Decision

When user says "I want this repo public as portfolio":
- DO NOT recommend "make repo private" as a solution
- DO recommend content sanitization (replace IP/username/paths with placeholders)
- Optional: git filter-repo to purge from history
- Risk acceptance: repo structure/architecture is showcase-worthy; infrastructure details are not

## Git Scan Common Results Pattern

For a repo that's been used by AI agents writing audit files:

| What's typically found | What's typically NOT found |
|---|---|
| IP addresses in audit-prep docs | Actual API key values |
| Usernames in shell scripts | .env content |
| SSH commands in sync docs | SSH private keys |
| Provider details (ASN, colo) | auth.json / creds.json |
| API key NAMES in documentation | Password hashes |
| Personal paths (~/home/username) | Database connection strings |
| System architecture descriptions | OAuth tokens |

This pattern is predictable because:
- AI agents document everything (operational detail leak)
- But respect `.gitignore` and agent safety rules (no credential commit)

## Quick-Reference Commands

```bash
# Full repo secret scan
git log --all --full-history -p | grep -c "sk-[a-zA-Z0-9]\{20,\}"          # API keys
git log --all --full-history -p | grep -c "[0-9]\{8,\}:AA"                     # Telegram tokens
git log --all --full-history -p | grep -c "BEGIN.*PRIVATE KEY"                # Private keys
git log --all --full-history -p | grep -c "ghp_\|github_pat_"                 # GitHub PATs
git log --all --full-history -p | grep -c "AIza[0-9A-Za-z\-_]\{35\}"         # Google keys

# IP in current content
git grep -n "X\.X\.X\.X" -- '*.md' '*.py' '*.sh' '*.yaml' '*.json'

# IP in history
git log --all --oneline -S "X.X.X.X"

# Branches with sensitive content
for branch in $(git branch -a | sed 's/..//'); do
  matches=$(git grep -c "SENSITIVE_STRING" $branch -- '*.md' 2>/dev/null | wc -l)
  echo "$branch: $matches files"
done
```
