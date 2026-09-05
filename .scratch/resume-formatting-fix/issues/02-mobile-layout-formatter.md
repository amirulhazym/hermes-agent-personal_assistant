# 02 — Mobile Layout & Platform Tag Formatter

**What to build:**
Implement the clean 3-line format for `/resume` session items:
Line 1: `{index}. {active_label}\`{session_id}\` {source_tag}`
Line 2: `   🏷️ {title}` (or `   🏷️ (no title set yet)` if title is empty)
Line 3: `   > _{preview}_`
With blank line separation between items.
Platform tag mapping: `telegram` -> `[TG]`, `whatsapp` -> `[WA]`, fallback `[{SOURCE[:2].upper()}]`.

**Blocked by:** 01 — Query & Ordering Pipeline

**Status:** ready-for-agent

- [ ] Line 1 renders index, active label if current, monospace session ID, and platform tag.
- [ ] Line 2 renders title with `🏷️` prefix or `(no title set yet)`.
- [ ] Line 3 renders quote block `> _{preview}_`.
- [ ] Each session block separated by a clean newline.
