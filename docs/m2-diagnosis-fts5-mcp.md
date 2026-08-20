# M2 Diagnosis — FTS5 + MCP (corrected scope)

**Date:** 2026-08-20  
**Status:** Diagnosis/documentation only. No M2 code fix applied.

## Important distinction

The work-repository GitHub CI track is green. This is directly verified by
GitHub runs:

- Main `43b1089c757f94babfc97dc65d5dde1bb3245181`: run `32354925776`,
  `guards=success`, `test=success`.
- Med-hook `0defbdc91b10919f1e75f65220644bb2e08af5f5`: run `32346419995`,
  `guards=success`, `test=success`.

The `full suite exits 1` claim does **not** refer to GitHub CI. It refers to
the manual Gate 2 full-suite run against a reconstructed runtime tree. That
run recorded `TestFTS5Search` as a **proven C0 baseline failure**. It is a
known baseline result for the reconstructed-tree test run, not a current
work-repo CI failure.

## Production FTS5 evidence

Read-only probes against the live database showed:

```text
messages_count=111104
messages_fts_count=111104
medication hits=5889
dexamethasone hits=4490
gateway hits=20199
cron hits=9232
```

The production FTS5 search path therefore returns indexed results. This does
not, by itself, prove that every C0 baseline assertion is correct; it only
proves the live search index is populated and queryable for these probes.

## Correct owner decision point

The unresolved decision is:

1. **Accept the C0 baseline failure** for the manual reconstructed-tree full
   suite and record it as an acknowledged test baseline; or
2. **Relax/fix the test expectation** after reviewing the exact failing
   assertion and deciding what behavior the test should require.

No implementation should be selected from the earlier CJK-tokenizer
hypothesis alone. The previous CJK/live-only diagnosis covered tests present
under the nested live source tree, but it did not settle the manual Gate 2
`TestFTS5Search` C0 baseline result.

## Decision (2026-08-20 23:45 MYT)

**ACCEPTED UPSTREAM BASELINE.** Production FTS5 verified working (probes above).
The manual Gate 2 `TestFTS5Search` failure is a proven C0 baseline for the
reconstructed-tree run, not a current work-repo CI failure. Do not relax or
modify the upstream test tonight. Candidate for a future upstream issue/PR;
no code change applied.

## MCP scope

No MCP fix is proposed here. Any future MCP test-isolation work must identify
the exact test, command, SHA, fixture, and raw failure before code changes.

## State

- Work-repo CI: **GREEN**
- Manual Gate 2 reconstructed-tree `TestFTS5Search` C0 baseline: **PROVEN
  BASELINE FAILURE, OPEN DECISION**
- Production FTS5 sample queries: **WORKING for tested probes**
- M2 code fix: **NOT IMPLEMENTED**
