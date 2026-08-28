# Closure-Gate Controls for Live Session/Resume Incidents

Use this reference when a live stateful graph is compared with local source and upstream code before implementation or release.

## 1. Pin direct release evidence

At execution time, query the official releases API and resolve the annotated tag plus peeled commit with `git ls-remote`. Search-result snippets can be stale or contradictory. Record the direct API/tag result and keep it separate from the local/live SHA. A current release pin is a source-comparison input, not permission for a blanket upgrade.

## 2. Create an immutable SQLite baseline

Before source modification, create the first consistent snapshot with SQLite backup semantics, not a raw file copy:

```python
src = sqlite3.connect(f"file:{live_db}?mode=ro", uri=True)
dst = sqlite3.connect(backup_path)
src.backup(dst)
```

Record:

- source size and mtime before/after;
- backup size and SHA-256;
- read-only open result;
- `PRAGMA quick_check` result;
- snapshot timestamp and exact DB path.

Use this snapshot for all baseline counts and behavior tests. If the live database receives rows during the audit, do not mix later live counts into the same census; label them as a different snapshot.

If pinned source requires a migration, preserve the baseline unchanged and create a separately labelled migration copy. An error such as `no such column: s.hidden` is schema-compatibility evidence, not permission to mutate the baseline or call the behavior test a pass.

## 3. Prevent search self-contamination

Audit query strings can become durable messages before the backup is taken and later appear as false historical FTS hits. Define an audit cutoff/current lineage, exclude self-generated audit sessions where possible, and retain separate records for:

- raw FTS physical message ID and owning session ID;
- wrapper/search-tool returned session ID;
- lineage segment or reset boundary;
- expected historical identity.

A raw FTS match and a wrapper match are different evidence layers. If they disagree, report the identity mismatch; do not call search correct because both returned text.

## 4. Check durable route integrity independently

For each Telegram/WhatsApp lane:

1. Read the durable routing index.
2. Join its target session ID to the `sessions` table.
3. Find the newest open row for the same `session_key`.
4. Classify the route as:
   - durable route points to an open row;
   - durable route points to an ended row while a newer open row exists;
   - no durable route;
   - ambiguous identity.

A running gateway or an open session row does not prove that the durable route is current. A stale route blocks restart/channel acceptance claims until its root cause is proven and an owner-approved fix is tested. Do not repair routing during a read-only lineage audit.

## 5. Test the full upstream scope

A reset-aware upstream resolver may still contain fixed-depth walkers or schema-dependent listing code. Run a synthetic chain with more than 100 valid compression continuations and audit every caller, not only the headline resolver.

For the 2026-08-19 check, official v0.20.4 on a 105-node chain returned:

```text
get_compression_tip = s100
lineage length = 100
```

Therefore a release that fixes reset-boundary resume can still fail the long-lineage requirement. Separately compare:

- exact/title resume;
- `/sessions` and numeric `/resume` ordered physical IDs;
- recent-activity ordering;
- reset-segment search identity;
- Telegram and WhatsApp durable route targets.

## 6. Required status vocabulary

Use the lowest proven label:

- `LIVE` — observed from the running process, live log, routing index, or read-only live DB;
- `COPY-VERIFIED` — behavior run against an immutable SQLite backup;
- `MIGRATION-COPY` — behavior run after temporary schema initialization;
- `SOURCE-ONLY` — read from source/upstream metadata but not executed;
- `BLOCKED` — test could not run; preserve the exact error;
- `UNVERIFIED` — plausible interpretation without direct evidence.

Never upgrade a source plan, migration copy, unit test, or successful resolver call into `LIVE`, `DEPLOYED`, or `RELEASE-COMPLETE`.
