# Baseline-First Reconciliation Reference

## Evidence matrix template

| Layer | Evidence source | Exact result | Status | What it proves | What it does not prove |
|---|---|---|---|---|---|
| Original contract/design | URL/path + date/version | quoted invariant or acceptance rule | DOCUMENTED / PARTIAL / CONTRADICTED | intended behavior | current deployment |
| Historical candidate | branch/commit + test command/date | exact commit/test output | HISTORICAL / TESTED-THEN / UNVERIFIED-NOW | what existed then | current main/live |
| Current source/worktree | repo/path + ref/status | exact file/ref/diff result | PROVEN / DIRTY / MISSING / UNVERIFIED | current source state | runtime behavior |
| Current live runtime | direct probe + timestamp | raw output | PROVEN / CONTRADICTED / PARTIAL / UNVERIFIED | current running behavior | source ancestry |

## Scope wording template

```text
Verdict: This is [RECOVERY / RECONCILIATION / ROOT-CAUSE REPAIR / NEW DESIGN].

Checked: [canonical document], [pre-change path set], [current source paths],
[current live probes].

Proven now: [short list].
Historical only or contradicted: [short list].

Actual goal: [one sentence].
Will change: [exact components].
Will not change: [regimen/state/history/unrelated release lane].
Next gate: [test, approval, deployment, or further evidence].
```

## Medical/runtime reconciliation example

A design document can state that a Safety Gate was deployed and a compound alias was fixed. A fresh live resolver probe can still return `UNKNOWN`. The correct report is not “the document is wrong” or “the live runtime is wrong” without further lineage evidence:

```text
Historical document: Safety Gate / CC fix recorded as deployed.
Live probe: canonical resolver returns UNKNOWN for CC.
Current verdict: CONTRADICTION. The live capability is not proven.
Next action: reconcile source commit, current deployment manifest, live file hash,
and runtime import/entry point before changing medication state or re-deploying.
```

## Acceptance checklist

- Canonical artifact read completely, including tables.
- Pre-change search boundary stated.
- Candidate identity and current source ref are separate.
- Live probe is timestamped and raw output retained.
- Recovery is not claimed from a symptom fix.
- Medical regimen, dose, taper, timing, and history remain untouched during read-only reconciliation.
- Source/release work is not mixed with runtime symptom repair.
- Every proposed fix has a causal boundary and reproduction/acceptance test.
