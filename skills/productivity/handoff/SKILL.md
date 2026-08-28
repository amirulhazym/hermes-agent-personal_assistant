---
name: handoff
description: |
  Use when the conversation has reached a natural breaking point, the context window is getting long, or work needs to continue in a fresh session. Compact the conversation into a handoff document so another agent can pick up seamlessly without losing progress.
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS — not the current workspace.

## Structure

Include the following sections in the handoff document:

- **Summary** — What was accomplished so far
- **Current State** — Where things stand now (files modified, decisions made, blockers)
- **Next Steps** — What needs to happen next
- **Open Questions** — Any unresolved decisions or unknowns
- **Suggested Skills** — Skills the next agent should load/invoke

## Rules

- Do **not** duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.
- Redact any sensitive information — API keys, passwords, personally identifiable information.
- If the user passed arguments, treat them as a description of what the next session will focus on and tailor the document accordingly.
