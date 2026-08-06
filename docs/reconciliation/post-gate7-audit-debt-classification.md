# Post-Gate-7 Audit Debt — Classification (2026-08-06)

Canonical audit: `hermes-live-state-audit-20260806-2.md` (LIVE RELEASE PASS).
First audit superseded (crontab value `756bdde7…` was MD5; corrected SHA-256
is `b107c7397c7e13a9e0eefef707212d7378ec45c8dfa1a1fa9243eb028ff48176`).

## Overlay gap (1/26 files)

| File | Patch-recorded | Live | Verdict |
|---|---|---|---|
| tests/agent/test_nontech_contract.py | 75 lines, ends `assert content == "non-tech"` (SHA 41f39e88… section) | 76 lines, adds `assert "deep" not in content` (SHA 70df1f38…) | **LIVE IS NEWER** — the deep-check assertion completes the existing `test_confusion_trigger_never_requests_deep_mode` test; written same 2026-07-31 batch (mtime 12:32:58), pre-Gate-6. Test-only, runtime unaffected. Regenerate overlay patch with live content in a maintenance release. |

## 12 nested candidates

| # | Path | Class | Resolution |
|---|---|---|---|
| 1 | scripts/whatsapp-bridge/bridge.sendqueue.test.mjs | UPSTREAM-TREE-ONLY | verified in upstream origin/HEAD; do not port as custom; arrives via upstream sync |
| 2 | ui-tui/src/app/petFlashStore.ts | UPSTREAM-TREE-ONLY | same |
| 3 | ui-tui/src/app/usePet.ts | UPSTREAM-TREE-ONLY | same |
| 4 | ui-tui/src/components/petPicker.tsx | UPSTREAM-TREE-ONLY | same |
| 5 | ui-tui/src/components/petSprite.tsx | UPSTREAM-TREE-ONLY | same |
| 6 | ui-tui/src/__tests__/modelPicker.test.ts | UPSTREAM-TREE-ONLY | same |
| 7 | ui-tui/packages/hermes-ink/src/ink/app-stdin-recovery.test.ts | UPSTREAM-TREE-ONLY | same |
| 8 | ui-tui/packages/hermes-ink/src/ink/ink-backpressure.test.ts | UPSTREAM-TREE-ONLY | same |
| 9 | .install_method | RUNTIME/INSTALL-METADATA | never port; runtime-only |
| 10 | scripts/whatsapp-bridge.old/ | STALE-BACKUP | archive only; preserved in Gate 1; not ported |
| 11 | scripts/whatsapp-bridge/bridge.reconnect.test.mjs | PORT-CANDIDATE | source-worthy test for reconnect-controller overlay; port in maintenance release |
| 12 | skills/computer-use/ | PORT-CANDIDATE | genuinely custom/active (computer_use.enabled=true live); port in maintenance release |

All 12 verified `git check-ignore` = VISIBLE (not silently hidden). None
introduced post-Gate-6. Classification recorded in `operations/ledger.json`.
