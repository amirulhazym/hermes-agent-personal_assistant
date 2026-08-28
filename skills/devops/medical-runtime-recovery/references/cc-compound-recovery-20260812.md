# CC Compound Recovery — split-brain diagnosis + coherent 4-file set (2026-08-12)

Verified end-to-end: diagnosis (read-only) → deploy → hermetic probes → live
verify. 52 tests green; live med state untouched.

## Split-brain classification of live `~/.hermes/scripts` (before fix)

| Path | Live state | Verdict |
|---|---|---|
| med_resolve.py | old tracked-clean runtime blob (Jul-11 init commit), no COMPOUND_ALIASES; `CC` → `UNKNOWN` | stale-live |
| med_confirm.py | equivalent to governance-v3 source-closure candidate; no `--compound`/`confirm_compound` | stale-live |
| med_supply.py | no shared-lock/HERMES_HOME support | stale-live |
| med_state_lock.py | ABSENT | missing-live |
| med_safety_gate.py, hooks/med-auto-confirm/handler.py, chain_calc.py, chain_llm.py | byte-identical live vs clean source | current-compatible |

Key insight: live was a MIXED overlay (old resolver + V3-equivalent confirmer
+ newer handler/chain), not one uniform version. The Gate-1 staging backup
matched the STALE hashes — backups are NOT automatically recovery sources.

Historical proof of split-brain (WhatsApp session DB, read-only):
`state.db` `messages` table, `source='whatsapp' AND chat_id LIKE '%@g.us'`,
date-range filter: on 2026-08-08 and 2026-08-10 `--compound cc` commands
wrote both calcium+calcitriol into live med-status.json (9/9 atomic tests
passed) — but on 2026-08-09 the resident live resolver still returned
`UNKNOWN: 'cc'`. Candidate path proven working; resident path never deployed.

## The coherent recovery set (deploy TOGETHER, never mixed)

From clean source worktree to `~/.hermes/scripts/`:
`med_resolve.py` + `med_confirm.py` + `med_supply.py` + `med_state_lock.py`
(new file).

- Do NOT assemble from commit `44d679f` (governance-v3 source-closure
  candidate): it contains a PARTIAL hybrid (med_confirm matching the old live
  hash + distinct resolver/supply). Mixing breaks the atomic transaction set.
- Do NOT replace the already-compatible files (gate/hook/chain) — larger
  blast radius, zero benefit.

## Acceptance probes (hermetic; live state untouched)

1. Resolver: `med_resolve.resolve("CC", slot="C", time_24h="13:35")`
   → `ok:true, compound:true, compound_id:"cc"`,
   components exactly calcium + calcitriol.
2. Gate: `med_safety_gate.evaluate(msg, "13:35", reference_dt)` — note the
   3-arg signature (message, stated_time, reference datetime) →
   `decision:ALLOW`, 2 mentions, `compound_complete:true`, no findings.
3. Dry-run: `med_confirm.py --dry-run C --compound cc --at 13:35
   --source-text "dah makan CC jam 1.35pm tadi"` on a FRESH empty-state
   fixture → `ok:true, dry_run:true, would_set:{calcium:13:35, calcitriol:13:35}`,
   fixture hashes unchanged. HERMES_HOME env var points the scripts at the
   temp home (med_confirm/med_supply/med_resolve all honor it).
4. Suites: `test_cc_atomic` 9/9, `test_safety_gate` 18/18.

## Pitfall: partial-state dry-run REJECT (by design, not a failure)

Probing the REAL live state with `--dry-run C --compound cc` can return:
`REJECTED: partial/conflicting CC state for ['calcium','calcitriol']; create
HOLD, do not overwrite` — happens when both components are already `taken`
(e.g. 08:20) but the slot overall is still `partial` (Dexa #2 missing).
This is the no-overwrite safety invariant, NOT a deployment failure. Rules:
- both components already taken at the SAME time → `ok, idempotent` (no
  double supply decrement);
- partial/conflicting → HOLD path, agent asks the user;
- success-path acceptance must use a fresh empty-state fixture.

## Deployment discipline (AGENTS.md-compliant, proven this run)

1. Record live destination hashes + med state hashes FIRST.
2. Timestamped rollback dir: `~/.hermes/backup-pre-phase2/med-cc-recovery-<ts>/`,
   `cp -p` every replaced file (mode-700 dir).
3. `install -m <original-mode>` — med_confirm.py is 711, the rest 600.
   Modes are meaningful; preserve them.
4. Post-copy: deployed hashes == source hashes; med state hashes UNCHANGED
   (med-status/supply/holds/schedule/dexa_taper); `py_compile` each file.
5. No commit/push/restart without owner approval. Hook code loads at gateway
   startup — a running gateway keeps the OLD modules in memory until the
   owner-approved restart.
