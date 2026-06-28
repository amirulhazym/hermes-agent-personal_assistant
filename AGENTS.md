# Agent Safety Rules

Before any destructive, irreversible, costly, credential-touching, deploy, external-message, public-posting, or out-of-scope action, STOP and ask the human in plain language. Wait for an explicit "yes".

These rules apply regardless of Plan mode, Build mode, sandbox mode, or approval presets.

Never print, commit, upload, or transmit secrets. Treat `.env`, Telegram bot tokens, DeepSeek keys, and WhatsApp session folders as sensitive.

No paid service may be enabled unless the human explicitly approves it.

## Git Commit Policy

The agent MUST ask the human before any `git add`, `git commit`, `git push`, `git amend`, or `git rebase`. After completing a unit of work (phase, file group, or logical change), the agent summarizes what changed and asks "Commit these changes?" — only on an explicit "yes" does the agent stage and commit.

- The agent never commits without asking, even if the human said "proceed", "go", or "continue" earlier in the session.
- "Proceed with the next phase" is NOT approval to commit the current phase. Ask separately for each commit.
- This rule overrides any inferred permission and complements the existing "STOP and ask before destructive actions" rule above.
- Commits must follow the repo's existing message style (concise, imperative, no emojis unless the human asks).
- Never stage `.env`, session folders, `auth.json`, `*.key`, `*.pem`, or any file matching `.gitignore`.

## `.env` and Secrets Access Policy

The agent has filesystem read access to `~/.hermes/.env` and similar secret files. This is necessary for discovering env var names and verifying config wiring.

- The agent MUST NEVER print, log, echo, transmit, or commit any secret VALUE from `.env` or any other secret file.
- When a script needs an API key, the agent references it by ENV VAR NAME (e.g. `OPENCODE_GO_API_KEY`) only — never inlines the value.
- When grepping `.env` to discover a variable name, the agent uses targeted patterns (e.g. `grep -E '^(OPENCODE|DEEPSEEK|NVIDIA|TELEGRAM).*_KEY=' .env | cut -d= -f1`) that return names only, not values.
- If a tool result accidentally exposes a secret value, the agent does not repeat it in subsequent messages or write it to any file.
- Treat Telegram bot tokens, DeepSeek keys, NVIDIA keys, OpenCode Zen/Go keys, and WhatsApp session folders as sensitive per the rule above.

## OpenCode-Specific Instructions

- Read `PRD.md` fully before any implementation work.
- Read Section 7 (Human-in-the-Loop & Safety Protocol) twice. It overrides speed and convenience.
- Fetch current official docs from PRD Section 6 before running setup commands, writing config, or assuming model names, CLI flags, provider schemas, or pricing.
- Work phase-by-phase. At the end of every phase, stop, report what changed, and wait for explicit approval before continuing.
- Maintain `PROGRESS.md`, `DECISIONS.md`, and `RUNBOOK.md` per PRD Section 0.
- Phase 0 is complete. Do not re-run Phase 0 verification unless explicitly asked.
