# Gate 4 Classification Ledger — 2026-08-06

Donor: live /home/ubuntu/.hermes (HEAD 08cf26ba) + nested hermes-agent (HEAD f94dff11) + VPS root extras.
Base: integration/reconcile-20260806 @ 05d7016. Counts: 67 tracked-modified + 592 untracked (~/.hermes).

## A. Med-tracker skill documentation (PORT-DOC)
| Path | Decision |
|---|---|
| skills/med-tracker/references/20260729-cli-confirmation-and-future-intent.md | PORT (new factual ref) |
| skills/med-tracker/references/compound-runtime-drift-20260804.md | PORT (new factual ref) |
| skills/med-tracker/references/dexa-resolver-and-timing.md | PORT (new factual ref) |
| skills/med-tracker/SKILL.md (live) | NOT ported wholesale: live REMOVED safety-gate/regimen sections that integration handler implements; integration SKILL.md retained; only the 3 new refs + CLI/compound/Dexa sections added |
| skills/med-tracker/references/* (other 34 live refs) | ALREADY-PRESENT in integration SKILL.md citations or runtime knowledge; not ported (preserved in Gate 1) |

## B. Med-chain source logic (PORT-SOURCE)
| Path | Decision |
|---|---|
| scripts/chain_calc.py — is_effectively_done/resolved/skip-accounting WIP (9 hunks, live 21191688) | PORT (source-worthy: skipped doses resolve reminders without being marked taken; clinically relevant) |
| scripts/chain_monitor.sh — is_effectively_done housekeeping | PORT (paired dependency) |
| scripts/med_confirm.py | NOT ported: integration version NEWER (HERMES_HOME + state-lock + txn) |
| scripts/chain_llm.py, med_chain/*, med_safety_gate.py, hooks handler | line-ending-only or identical; ALREADY-PRESENT |

## C. Hooks (PORT-HOOK)
| Path | Decision |
|---|---|
| hooks/med-auto-confirm/test_hook_chain.py | NOT ported: integration version NEWER (portable Path, no hardcoded /home/ubuntu) |
| hooks/med-auto-confirm/test_med_auto_confirm.py | NOT ported: integration has MORE tests (safety-HOLD) |
| hooks/skill-trigger/handler.py | RUNTIME (live .bak variants); integration has no skill-trigger; not source-worthy for personal repo |

## D. Nested upstream overlays (PORT-AS-PATCH/OVERLAY)
| Path | Decision |
|---|---|
| hermes_cli/models.py + model_switch.py + gateway/slash_commands.py + tests (P1-C 6 commits) | PORT as patches/upstream-hermes/2026-08-06_p1c-selected-model-contract.patch (base 2bd1977d8) |
| 11 modified + 30 untracked nested files (runtime_resolver, observability, goals, turn_finalizer, bridge.js, etc.) | PORT as patches/upstream-hermes/2026-08-06_vps-runtime-overlays.patch (base f94dff11) |
| optional-skills/*, web/public, website/, venv, node_modules | EXCLUDED (upstream noise/vendored) |

## E. Sanitized templates (SANITIZE-AS-TEMPLATE)
| Path | Decision |
|---|---|
| config/config.yaml.template | add `personality:` key (live-only new key) |
| web-operator templates | ALREADY-PRESENT in integration |

## F. Root docs (PORT-DOC)
| Path | Decision |
|---|---|
| ~/.hermes/MED_CHAIN_ENGINE_SPEC_v3.md, VPS_AUDIT_STATE.md, docs/px1b-*.md, design/*.md, notes/skills-to-add.md | ARCHIVE/not ported: preserved in Gate 1 root-sensitive/root-extras; design docs describe live architecture not personal-repo source |
| /home/ubuntu root extras (0001-backup.md etc.) | ALREADY in Gate 1 root-extras; not ported |

## G. Runtime / never port
config.yaml (real values), cron/jobs.json, memories/, state.db, chain-state.json, med-status.json, logs/, sessions/, agents/, backups/, secure-env-gpg/, web-operator bridge state, accounts CSVs, .pyc, __pycache__, *.log — RUNTIME-STATE/SECRET/PII/GENERATED.

## H. .gitignore audit
cache/, jobs.json, gateway_state.json, pairing/, med-*.json — verified NOT hiding any tracked/expected source; narrow enough; retained.
