# Single-Repo VPS Consolidation and Nightly Git Hygiene

## Context & Problem
Running two separate Git clones on the same VPS (e.g. `/home/ubuntu/.hermes/hermes-agent` for the engine and `/home/ubuntu/hermes-agent-personal_assistant-work` for user customizations) causes severe operational friction:
1. **Context confusion**: AI agents and operators get confused about which repo to edit, test, or commit in.
2. **Stranded hot-fixes**: Emergency fixes applied to the runtime clone are frequently forgotten and never ported to the personal repository.
3. **Stale branch sprawl**: Multiple temporary branches accumulate across both repositories without being merged, pushed, or pruned.

## Best-Practice Single Source of Truth (SSOT) Topology
1. **Single Application Repository**:
   - Maintain only ONE personal Git repository (`hermes-agent-personal_assistant`) representing the entire system state (custom scripts, med-tracker logic, overlay patches, skills, and configuration schemas).
   - Core framework updates from upstream (`NousResearch/hermes-agent`) are integrated via clean patch overlays or versioned dependency locks rather than maintaining a second active development clone.
2. **Runtime Directory Alignment**:
   - Runtime assets (`~/.hermes/skills/`, `~/.hermes/scripts/`, `~/.hermes/plugins/`, `~/.hermes/config.yaml`) map directly from the single personal repository.

## Nightly EOD Git Reconciliation Workflow
Every night, run an automated / operator-driven end-of-day Git hygiene routine:
1. **Inventory & Diff Check**:
   - Inspect all active workspaces for uncommitted modifications or untracked custom files.
   - Cross-check file modification times (`mtime`) against git status.
2. **Consolidation**:
   - Capture verified live changes into the personal repo with clean, atomic commit messages.
   - Run guard checks (secret scan, PII review, contract tests).
3. **Branch Cleanup**:
   - Identify merged or abandoned temporary branches (`feat/*`, `candidate/*`, `a4-*`).
   - Prune stale local and remote tracking refs.
4. **Receipt Generation**:
   - Output a clean, compact verification receipt summarizing committed SHAs, remaining pending work, and clean status.
