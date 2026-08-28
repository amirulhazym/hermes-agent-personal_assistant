# Test-fixture pattern remediation

Use this when a candidate privacy/secret scanner detects credential-shaped text inside a test fixture.

## Goal

Keep the scanner fail-closed for real credentials while retaining the test's intended runtime behavior. A path under `tests/` is not automatically safe.

## Procedure

1. **Locate, do not waive**
   - Identify the exact matched literal, test method, assertion, and validation/redaction branch it is meant to exercise.
   - Do not print the matched bytes in reports. Record file, rule/category, line, and a SHA-256 of the source line if evidence needs to be durable.

2. **Establish the required runtime property**
   - Examples: expected prefix/suffix after redaction, invalid-vs-valid token family, required minimum length, or expected rejection status.
   - Preserve that property—not necessarily the original literal bytes.

3. **Use a synthetic construction, not an allowlist**
   - Replace the static credential-shaped literal with clearly synthetic source fragments joined at runtime.
   - The static scanner sees no credential-shaped source token; the test receives the required shape at runtime.
   - Never encode/reconstruct a real credential. Do not make the guard ignore all tests or all fixtures.

4. **Check candidate closure**
   - Test failures caused by missing helper fixtures, `conftest.py`, or support source are source-closure findings. Add the exact required path to the candidate ledger/provenance/manifest and classify it before accepting a test result.
   - A test source port may be new relative to the application baseline; describe its prior state as the pinned donor/live source, not as a missing baseline diff.

5. **Test only with a valid isolated harness**
   - Run the affected test before and after where possible, using a temporary HOME/state root.
   - If candidate imports resolve to live/donor code, the harness is invalid for candidate behavior. Stop and report `NOT-RUN`; do not mix in live code to manufacture a pass.

6. **Re-run full hygiene gates**
   - Scan every intended candidate path, including newly discovered dependencies and changed ledger/manifest files.
   - Validate: per-file provenance hashes, manifest entry hashes, manifest payload hash, path-count/uniqueness, explicit private exclusions, and tracked/untracked sets.

## Required report split

| Claim | Required evidence | Does not prove |
|---|---|---|
| Static hygiene clear | full intended-path rule scan returns zero matches/read errors | endpoint behavior |
| Fixture semantics preserved | affected test passes in valid isolated harness | broader candidate behavior |
| Candidate closure correct | ledger/provenance/manifest hashes and counts validate | a committed/released SHA |
| No live contamination | live status/hash unchanged before vs after | candidate deployment safety |

## Pitfalls

- A direct scan of only the changed file is insufficient; manifests and support files can create new matches.
- A successful test that imported a live checkout is not candidate evidence.
- Updating the candidate source without updating its ledger/manifest/provenance turns exact evidence stale.
- A static scanner PASS is hygiene evidence only; do not call it a release or behavior PASS.
