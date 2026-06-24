# Agent Safety Rules

Before any destructive, irreversible, costly, credential-touching, deploy, external-message, public-posting, or out-of-scope action, STOP and ask the human in plain language. Wait for an explicit "yes".

These rules apply regardless of Plan mode, Build mode, sandbox mode, or approval presets.

Never print, commit, upload, or transmit secrets. Treat `.env`, Telegram bot tokens, DeepSeek keys, and WhatsApp session folders as sensitive.

No paid service may be enabled unless the human explicitly approves it.

## OpenCode-Specific Instructions

- Read `PRD.md` fully before any implementation work.
- Read Section 7 (Human-in-the-Loop & Safety Protocol) twice. It overrides speed and convenience.
- Fetch current official docs from PRD Section 6 before running setup commands, writing config, or assuming model names, CLI flags, provider schemas, or pricing.
- Work phase-by-phase. At the end of every phase, stop, report what changed, and wait for explicit approval before continuing.
- Maintain `PROGRESS.md`, `DECISIONS.md`, and `RUNBOOK.md` per PRD Section 0.
- Phase 0 is complete. Do not re-run Phase 0 verification unless explicitly asked.
