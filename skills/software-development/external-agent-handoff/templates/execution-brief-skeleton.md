# Execution Brief — Fresh-Context Agent (SKELETON)

> Copy this, fill every section with VERIFIED facts (terminal/git, not assumptions).
> Purpose: self-contained prompt for an external executor agent (e.g. OpenCode) in a fresh context window.

---

## ⚠️ YOUR MODE
Strategic advisor + executor. Freedom to expand/improve the plan with own research. MUST ask before any system change.

## 🔧 SKILLS & METHODOLOGY REQUIREMENT (MANDATORY)
Use at max capability: `using-superpowers`, `mattpocock` (systematic-debugging + planning), `evidence-first`, `incremental-implementation`. `gsd` = required mindset (decisive execution) if not a literal skill. Apply when creating the master plan (`writing-plans` 11-section format).

## 1. Current State (verify live)
| Item | Detail |
|------|--------|
| HEAD | `<git hash>` |
| Branch | `<branch>` |
| Untracked | `<folders>` |
| Remote | `<url>` |
| Push | NONE / done |

## 2. File Inventory (byte-verify PC↔VPS with `wc -c`)
| Path | Bytes | Notes |
|------|-------|-------|
| | | flag PC↔VPS mismatch; untracked git = "file-synced NOT in git" |

## 3. Execution Mandate
- Role: you = EXECUTOR; MJ = VERIFIER ONLY (can't be DM'd directly — use `ssh` read-only or user-relay).
- Approval: per-phase/per-step explicit user "go". Freeze applies to MJ only, NOT you.

## 🔒 WORKING METHOD — HARD RULES
- R1 Context: report % every checkpoint; >70% → STOP.
- R2 Checkpoint: after each task, STOP, report, ASK OWNER confirm; if >70% → fresh context or subagent.
- R3 File-reading: NEVER load all files at once; subagent-per-folder → summary, else batched reads.
- R4 Per-phase fresh context.
- R5 Q&A gate before exec (correction ≠ approval).
- R6 VPS read-only via `ssh ubuntu@<ip>`; never modify without "go".
- R7 Freedom preserved (rules = HOW, not WHAT).

## 8. Verification Strategy
Sandbox/`--dry-run` only until "go". Labels: ✅ VALIDATED / 🔶 UNTESTED / ❌ REJECTED.

## Hard Constraints
Skills mandatory · evidence-first · single-source-flagged · partial≠done · secrets .env-only · MJ=verifier · sequential · stop-for-destructive · Manglish OK.
