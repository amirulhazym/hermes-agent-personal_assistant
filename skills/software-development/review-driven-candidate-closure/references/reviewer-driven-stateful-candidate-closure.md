# Reviewer-Driven Stateful Candidate Closure — Field Recipe

This reference condenses a recurring review pattern from a medication-intake safety gate. The domain details are examples; the workflow applies to any stateful parser, policy gate, schedule engine, quota system, or write-protection layer.

## 1. Finding-to-test matrix

| Finding shape | Isolated fixture | Required assertion |
|---|---|---|
| Canonical entity omitted from a hand-maintained whitelist | Active schedule/registry includes an entity absent from the old regex | Genuine change language produces `HOLD`; timing-anchor language without a change request remains allowed |
| Active anchor missing or malformed | Replace one slot’s `time`/anchor with `null`, empty, or invalid text | Valid-looking intake cannot fall through to `ALLOW`; output contains a configuration finding |
| Phase/taper changes timing | Use a phase where the active non-zero positions and ordered times differ from static config | Event at the new active time is allowed; event immediately before it is held; output records the selected anchor |
| Exact ID overlaps a generic alias | Message contains a canonical ID that contains a shorter generic alias | Only the exact canonical record is resolved; no duplicate/conflicting slot appears |
| Parser branch changed without exact coverage | Use the real separator/leader/context form | Parsed value matches the exact expected 24-hour time |

## 2. Isolated reproduction recipe

1. Create a temporary application root.
2. Copy only the schedule/registry, phase/taper data, resolver dependencies, candidate source, and minimal fixture state.
3. Set `HOME`/`HERMES_HOME` or the equivalent application-root variable to the temporary root.
4. Run the reviewer’s input directly against the pure decision function when possible.
5. Capture structured output: decision, findings, resolved entities, selected authority, and side-effect files.
6. Assert the temporary state changed only where the test explicitly expects it.
7. Hash/read live state separately if the reviewer process had any chance of using production paths.

Do not use a production confirmation command as a “read-only” probe. If the code has no dry-run mode, use a copied state root rather than a backup-and-restore dance.

## 3. Authority-derived recognition

A robust change detector should assemble terms from the active canonical source:

```text
active scheduled entries
+ active extras/PRN entries
+ canonical IDs and display names
+ resolver aliases
+ explicit slot/entity tokens
```

Do not fix an omitted entity by appending one more literal to a static regex. That only moves the omission to the next entity. The regression test should use an entity that was absent from the old list to prove the detector is no longer partial.

Keep “timing anchor assertion” separate from “regimen/configuration modification.” A phrase such as `START 8AM AS PER DOCTOR` contains a clinician reference and `START`, but it is not a modification by itself. A phrase such as `Doctor told me start calcium` or `Hospital suruh tukar dose` is modification language and must be held.

## 4. Active temporal authority

For phase-driven schedules, do not map times to slots with a fixed literal dictionary unless the schema guarantees that mapping for every frequency. Prefer:

```text
active positions = non-zero dose/active keys in canonical order
anchors = zip(active positions, phase.times)
```

Then carry the resulting `slot/entity -> anchor` mapping in the immutable snapshot used by evaluation. This makes the decision auditable and prevents a stale static schedule value from winning after a phase transition.

Test both sides of the boundary:

```text
at active anchor       -> allowed, assuming all other checks pass
one minute before      -> held with expected active anchor
late actual intake     -> preserved if the contract says reminder window is not a hard boundary
```

## 5. Fail-closed authority checks

Treat these as separate outcomes:

```text
valid anchor + actual before anchor   -> BEFORE_ANCHOR / HOLD
valid anchor + actual at/after        -> continue evaluation
missing/malformed anchor              -> CONFIGURATION / HOLD
missing/malformed actual time         -> INPUT / HOLD
inactive phase/entity                 -> INACTIVE / HOLD
```

A helper returning `None` is not an allow result. The evaluator must turn it into an explicit finding before the final `ALLOW` assignment.

## 6. Exact-before-generic resolution

Reserve exact canonical-ID spans before scanning aliases. Use overlap detection, not only “alias fully contained in canonical span,” because a broad alias can partially overlap a canonical token.

The invariant is:

```text
one source span -> at most one canonical resolution
specific canonical form -> generic alias cannot override it
```

Add a regression case where the canonical identifier contains the generic alias, otherwise this class of duplicate-resolution bug can return after a refactor.

## 7. Candidate evidence ledger

Use one row per reviewer finding:

```text
id: F1
claim: <short reviewer claim>
repro: PROVEN | NOT_REPRODUCED | UNVERIFIED
fixture_root: <temporary path>
red_test: RED | COVERAGE_ONLY | HARNESS_INVALID | WRONG_RED
fix: <source boundary changed>
negative_probe: <input and observed result>
affected_suite: <raw final output>
baseline: BASELINE | CANDIDATE_DEFECT | HARNESS | FLAKY | UNRESOLVED
final_sha: <full SHA>
worktree_vs_commit_bytes: EQUAL | DIFFERENT
live_hashes: EQUAL | DIFFERENT | NOT_CHECKED
runtime_reload: NOT_DONE | DONE
user_visible_smoke: UNVERIFIED | PROVEN
```

Do not collapse `final_sha`, `live_hashes`, `runtime_reload`, and `user_visible_smoke` into one “done” field.

## 8. Final gate sequence

After the last source/test byte changes:

1. run the finding-specific tests;
2. run the complete affected suite;
3. run the broader relevant suite and retain every failure;
4. compare unchanged failures against the clean baseline;
5. run compile/whitespace/static checks;
6. stage only intended files and run staged checks;
7. commit and capture the full SHA;
8. rerun affected checks against the committed tree;
9. compare `git show <sha>:<path>` bytes with the tested worktree;
10. inspect live files/processes independently;
11. stop at `CANDIDATE-CLOSED` until explicit release approval exists.

A bounded pass proves only the bounded scope. A local commit proves only candidate source. Neither proves live behavior.
