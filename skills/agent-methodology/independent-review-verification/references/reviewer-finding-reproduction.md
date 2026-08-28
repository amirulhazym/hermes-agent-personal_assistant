# Reproducing Independent Review Findings

Use this when a fresh reviewer flags a wrapper, fallback, middleware, retry, or
source-closure candidate as unsafe. The report is a lead, not proof: reproduce
the exact finding against the candidate bytes before accepting or dismissing it.

## Freeze the boundary

Record the candidate worktree, branch, HEAD, staged path set, donor/base
identity, and exact reviewer claim. Do not let the reviewer mutate the
candidate. Re-check candidate status after review. Keep live runtime, production
state, and candidate verification separate.

## Materialize before probing

For a patch or overlay candidate, create a fresh temporary source tree from the
pinned base and apply the complete ordered series. Run the probe against that
materialized tree, not an unpatched working copy or live checkout. Use a
temporary `HOME`/`HERMES_HOME` whenever imports can read configuration, state,
plugins, caches, or credentials. Never use production databases or medication
state as test fixtures.

A clean patch application proves structure only. The probe must exercise the
behavior named in the finding.

## Wrapper and fallback failure matrix

For code shaped like:

```python
try:
    return middleware(request, provider_call)
except Exception:
    return provider_call(request)
```

run two independent failure cases:

1. **Provider failure:** middleware invokes the provider callback and the
   provider raises. Assert one physical provider invocation and propagation of
   the original error.
2. **Middleware failure:** middleware raises before invoking the provider.
   Assert zero provider invocations and propagation of the middleware error.

A happy-path test cannot detect duplicate execution or policy bypass.

## TDD correction cycle

Add the smallest regression tests at the real seam before changing production
logic. Run them RED against the materialized candidate and retain that output.
Assert invariants rather than only mock interactions:

- one physical attempt makes at most one provider invocation;
- middleware runtime exceptions are not silently converted into raw-provider
  fallback;
- error identity is preserved unless translation is contractual;
- any compatibility fallback is narrowed to a tested import/availability class.

Apply the minimal fix, rerun the same tests GREEN, then rerun the original
un-minimized reproduction. Do not mix unrelated retry/refactor work into the
fix.

## Preserve provenance without preserving a defect

When the bad code came from a live-only commit:

1. Keep the exact live change as its own ordered overlay when lineage matters.
2. Add a separate corrective overlay instead of silently rewriting history.
3. Record both source provenance and candidate-created hardening.
4. Recompute every patch SHA-256 value, patch-series digest, manifest entry, and
   tree digest after any byte change.
5. Rebuild from the pinned base and apply the complete series again.

A selective candidate is not a byte-for-byte clone of live when unrelated
upstream history is intentionally excluded. Behavioral parity at the affected
seam is the relevant acceptance check.

## Candidate gates after correction

Run fresh after the fix:

- materialization and patch-applicability checks;
- affected regression tests and the relevant contract suite;
- compile/import checks;
- staged secret scan and separate PII review;
- full staged whitespace check;
- exact lock/manifest/hash consistency checks;
- a fresh independent review of the corrected staged bytes.

If a unified patch artifact triggers a whitespace warning because it contains a
valid diff marker, do not normalize it blindly. Prove applicability against a
fresh base and preserve target source bytes; if needed, regenerate a normally
applicable hunk whose artifact representation also passes the repository gate.

A passing candidate remains candidate-only. Do not call it pushed, merged,
deployed, reloaded, or live until each separate boundary has direct evidence.
