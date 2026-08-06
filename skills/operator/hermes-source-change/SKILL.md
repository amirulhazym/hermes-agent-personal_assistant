---
name: hermes-source-change
description: Procedure for making any source change to the Hermes Agent personal-assistant repository — classify the request, start from a clean clone, work on a temporary branch, test, and either auto-promote (docs-only) or stop for one APPROVE RELEASE <sha>. Use whenever the owner requests a change through Telegram/WhatsApp or the repo needs a modification.
---

# Hermes Source Change

Always-on policy lives in `AGENTS.md` (repo root). This skill is the
operational procedure for **making changes**. If this skill conflicts with
`AGENTS.md`, `AGENTS.md` wins.

## 1. Classify the request

| Class | Paths | Approval |
|---|---|---|
| Docs-only | `docs/**` (except `docs/reconciliation/`), `README.md`, `PROGRESS.md`, `DECISIONS.md`, `RUNBOOK.md`, `CHANGELOG*`, root `*.md` (except governance) | Auto-promote after verification |
| Protected | `AGENTS.md`, `skills/**`, `.github/**`, `config/**`, `scripts/**`, `hooks/**`, `patches/**`, deployment manifests, `sync/**`, `windows/**`, `tests/**`, persona, `operations/**` | `APPROVE RELEASE <sha>` |

If mixed (docs + protected in one request): the whole change is protected.

## 2. Start from a clean source clone

```
VPS:  /home/ubuntu/hermes-agent-personal_assistant-work   (branch main)
PC:   F:\AI Prep\OVIS\Hermes Agent\MJay                  (branch main)
```

- Verify `git status --porcelain` is empty and `git rev-parse main` equals
  `origin/main`.
- Never work from `/home/ubuntu/.hermes` or the nested upstream clone.
- Never edit live runtime files directly.

## 3. Create a temporary branch

```
git checkout -b <type>/<purpose>-<date>   # feat/*, docs/*, release/*-candidate
```

Branch is deleted automatically after promotion or explicit abort.

## 4. Edit + test

- Make the smallest semantic change.
- Docs-only: run link validation + secret scan (`scripts/guard/secret-scan.sh`).
- Code: run the targeted tests, then the full med suite
  (`scripts/med_chain/tests/`, `test_cc_atomic`, `test_chain_adapter`,
  `test_chain_llm`, `test_effective_done`) with isolated temp-HOME — never
  against live medical state.
- Secret scan every staged byte (`scripts/guard/secret-scan.sh`).

## 5. Promote

### Docs-only (no repeated approval)
1. Commit (conventional style, no emojis).
2. `git merge --ff-only` into `main` on the clean clone.
3. Push to `origin main` (no force).
4. Delete the temporary branch.
5. Record final SHA in the operation ledger.

### Protected (single approval gate)
1. Commit and push the temporary branch (e.g. `feat/...`).
2. Publish the release candidate SHA = tip of the temporary branch.
3. **STOP.** Ask the owner:
   `APPROVE RELEASE <exact-sha>`
4. Only after exact approval: fast-forward `main`, deploy per
   `hermes-release-deploy`, verify, cleanup.

## 6. Never

- Force-push, rebase published history, delete `release/*`/`archive/*`/`rescue/*` tags.
- Commit secrets, runtime state, DBs, sessions, logs, caches, `.pyc`, `__pycache__`.
- Commit from `~/.hermes` or the nested upstream clone.
- Modify `AGENTS.md`/skills/guard scripts without release approval.
