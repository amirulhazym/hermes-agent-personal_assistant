# Hermes Monitor & Runtime Reconciliation Specification

## Problem Statement

Hermes is operational, but several monitoring and reconciliation signals no longer reflect the live system accurately. The post-push smoke monitor fails from system cron because its `systemctl --user` probes do not receive the user-bus environment. Runtime drift still compares against the frozen deployed reference from 2026-08-20, while direct verification shows 14 reported mismatches already match current source and 15 intentional live-source paths still differ.

Nightly Git hygiene also reports owner HOLD for two different cases: the intentionally retained Gemini V2 candidate, and `xcute/pre-closure-614ab`, whose patch is already represented in current `main`.

The owner wants only these specific problems resolved. Unrelated cleanup, upgrades, provider work, medical state, dashboard work, and broad architecture changes are excluded.

## Solution

1. Establish durable `/xcute` planning artifacts and an isolated per-T execution boundary.
2. Repair the post-push smoke monitor at the cron-to-user-systemd environment boundary.
3. Capture the 15 intentional live-source differences into the SSOT after privacy/security review, without overwriting live copies.
4. Recompute the deployment manifest and remove obsolete hardcoded drift exceptions only after source capture proves parity.
5. Preserve the owner-approved Gemini V2 branch/worktree while preventing it from causing false HOLD; remove the local patch-equivalent pre-closure branch after fresh proof.
6. Publish each T through protected Git flow, then perform only the controlled live deployment required by the approved slice and prove final monitoring state.

## User Stories

1. As the Hermes owner, I want the post-push smoke monitor to run successfully from its real cron environment, so that a green receipt means the monitor actually executed.
2. As the Hermes owner, I want smoke receipts to have fresh timestamps, so stale August receipts cannot be mistaken for current health.
3. As the Hermes owner, I want intentional live custom source represented in the SSOT, so recovery and future changes do not lose live behavior.
4. As the Hermes owner, I want live-source reconciliation to preserve private and medical boundaries, so source capture never publishes raw mutable/private state.
5. As the Hermes owner, I want the drift monitor to compare against the approved deployed manifest without historical hardcoded exceptions, so PASS and FAIL have one meaning.
6. As the Hermes owner, I want the 14 already-aligned paths left untouched, so reconciliation does not create unnecessary churn.
7. As the Hermes owner, I want the Gemini V2 candidate to remain isolated and unmerged, so its existing evaluation state is preserved.
8. As the Hermes owner, I want nightly Git hygiene to recognize the exact owner-approved retained Gemini branch, so intentional retention does not create a false HOLD.
9. As the Hermes owner, I want unknown stale unique branches to continue producing HOLD, so the safety boundary is not weakened.
10. As the Hermes owner, I want `xcute/pre-closure-614ab` removed only after equivalence is re-proven, so no unique work is discarded.
11. As the Hermes owner, I want every T completed through tests, guards, commit, push, protected PR flow, and read-back evidence before the next T starts.
12. As the Hermes owner, I want no changes outside the approved monitor/reconciliation scope.

## Implementation Decisions

- The personal application repository remains the sole development SSOT.
- Each T-slice is executed independently and must complete verification and protected publication before the next T begins.
- Live runtime files are never used as an ad-hoc development repository.
- Post-push smoke repair changes the environment boundary, not cron cadence or unrelated service lifecycle.
- The 15 current live/source differences are source-preservation work: live bytes are reviewed and captured into source; they are not overwritten by older repository copies.
- The frozen deployment reference is not advanced until source capture, manifest recompute, protected publication, controlled deployment, and read-back establish the new deployed state.
- Drift classification is simplified only after reconciliation: deployed-manifest match is PASS; mismatch is FAIL. Historical hardcoded exceptions are removed rather than expanded.
- The exact Gemini V2 branch is an owner-approved retained exception. The exception must be narrow and must not make arbitrary stale unique branches pass.
- The local pre-closure branch is eligible for deletion only if fresh patch-equivalence proves it contributes no unique patch.
- Protected publication is per T. No later T change may be included in an earlier T commit or PR.

## Testing Decisions

- Prefer existing reconciliation tests as the highest stable seam.
- Post-push smoke must be tested under a sanitized cron-like environment and prove user-systemd lookup without relying on an interactive shell.
- Source capture must compare exact hashes and path sets before and after capture; secret and PII guards are separate gates.
- Drift changes must prove zero-drift PASS and unexpected managed mismatch FAIL.
- Nightly branch retention must prove the exact approved Gemini branch is retained without HOLD while another stale unique branch still HOLDs.
- Every T runs the smallest relevant tests first, then the repository quality/security gates required by release flow.

## Out of Scope

- Model/provider picker changes.
- Gemini V2 implementation, evaluation changes, merge, deletion, or live activation.
- Medication status/data mutation.
- WhatsApp account migration.
- Dashboard changes.
- General Hermes upstream upgrades.
- General disk cleanup.
- Unrelated cron jobs.
- Remote Gemini branch deletion.
- Historical incident-ledger closure.
- Deletion or regeneration of `cron-health.last.json`.

## Further Notes

Fresh evidence before T01 showed: clean synchronized `main`; broken post-push smoke with stale receipts; drift report at 29 total / 20 new while direct current-main comparison showed 14 already aligned and 15 genuinely different; Gemini V2 retained with unique commits and linked worktree; `xcute/pre-closure-614ab` patch-equivalent to current `main`; current health with zero consecutive failures.
