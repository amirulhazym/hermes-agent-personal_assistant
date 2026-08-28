# Process-Lifetime Cache and Refresh Evidence Pattern

## Reusable diagnostic

When a newly installed command is reported as unknown:

1. Compare the running daemon start time with the installed artifact mtime.
2. Confirm the daemon uses the expected profile/home.
3. Read the registry/dispatch code and answer:
   - where is the command map built?
   - is it process-global or per-session?
   - what causes a rescan?
   - does installation call that invalidation path?
4. Check whether the proposed reset operation only rotates session state.
5. Use the explicit reload operation, then test the exact command and capture the gateway log.
6. Keep these statuses separate:
   - installed on disk
   - found by a fresh process
   - loaded by the live process
   - executed and delivered to the user

## Incident pattern: Hermes skill slash command (2026-07-31)

Observed symptom: `/i-have-adhd` returned `Unknown command` after the installer reported success.

Evidence chain:

- Gateway PID 2415626 started at 12:33:26 MYT with `HERMES_HOME=/home/ubuntu/.hermes`.
- The Telegram command-menu path called `get_skill_commands()` at 12:33:36, populating the process-global skill-command map.
- The skill file mtime was 15:54:18 MYT, after the gateway had already populated its map.
- `get_skill_commands()` only rescans when its map is empty or the platform scope changes.
- `/reset` called the session-reset path and did not call `reload_skills()`.
- Repeated WhatsApp attempts at 15:56:57, 15:58:43, and 15:59:29 logged `Unrecognized slash command /i-have-adhd`.
- A fresh process scan later found `/i-have-adhd` and successfully built its invocation message; this proved disk discoverability, not live-gateway loading.
- The focused regression suite passed: `41 passed in 2.60s`.

Correct remediation sequence:

1. Run `/reload-skills` in the affected chat.
2. Wait for the reload result, then run `/i-have-adhd`.
3. If the reload command is unavailable, use the approved gateway restart path and verify the new PID before retesting.

Important interpretation: `disable-model-invocation: true` was present in the skill frontmatter, but the scanner's eligibility checks did not reject that field. It was not evidence that explicit slash dispatch was disabled. Likewise, the plain-text message `Enable /i-have-adhd` only proved that the model answered normal text; it did not prove command execution.
