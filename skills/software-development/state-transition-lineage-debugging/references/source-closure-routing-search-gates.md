# Source-Closure, Routing-Timing, and Search-Identity Gates

Use this reference when a session/resume incident spans **source provenance**, **durable gateway routing**, and **FTS/search projection**. These are separate failure classes. Do not create one broad "resume fix" from a plausible symptom.

## 1. Source-closure gate

A deployment manifest is not source closure when the canonical repository does not contain every runtime input needed to reconstruct the live process.

### Detect the gap

Inventory, read-only:

1. canonical application `main` tree and exact commit;
2. live source tree and exact commit;
3. required runtime paths by import/call graph;
4. candidate/worktree ancestry and status;
5. deployment/sync scripts and validators;
6. manifest rows, including `source-only` versus `runtime-deploy`.

For every required runtime file, classify it as:

- `CANONICAL-BLOB` — present at the approved application SHA;
- `PINNED-UPSTREAM` — supplied by an exact external/base commit;
- `CUSTOM-PATCH` — reconstructed by an ordered patch/overlay;
- `GENERATED` — reproducible from checked-in inputs and tool/version lock;
- `LIVE-ONLY / UNMAPPED` — present in the runtime but not reproducible from the approved SHA;
- `PRIVATE/RUNTIME-STATE` — intentionally excluded from source Git.

A row such as `source-only` with a Git blob hash proves only that the application repository contains that row's source. It does not prove that an untracked upstream dependency or nested runtime clone can be rebuilt.

### Preferred source model when core upstream files are absent

Use an exact-base patch model:

```text
approved application SHA
  -> official repository URL + immutable base SHA
  -> ordered official/custom patch series with hashes
  -> clean reconstructed source tree
  -> explicit destination manifest with per-file hashes
  -> live destination hashes
```

Never pin moving `main` or rely on a tag name without recording the peeled commit. Keep these identities separate:

- application candidate SHA;
- official base SHA;
- patch-series digest;
- reconstructed source-tree/file hashes;
- deployed destination hashes;
- process-loaded/live behavior.

Existing closure work can be reusable in parts. Reuse its ledger, manifest schema, guard, and provenance conventions only after checking ancestry and whether the manifest actually includes the upstream base and every runtime path. A candidate worktree or manifest commit that is not an ancestor of canonical `main` is not automatically part of the release.

## 2. Durable-route timing gate

A route pointing to an ended compression parent while a newer open child exists is not automatically a persistent routing defect.

Separate these events:

```text
compression child published
  -> active agent turn continues
  -> agent turn ends
  -> gateway observes session-id split
  -> SessionStore updates/persists the route
```

### Required evidence

Read-only, correlate the exact session IDs and timestamps from:

1. compression publication/rotation log;
2. `Turn ended` log;
3. gateway `Session split detected` log;
4. route persistence error log, if any;
5. durable `gateway_routing` row after completion;
6. newest open `sessions` row for the same `session_key`.

Classify:

- `EXPECTED-IN-FLIGHT-LAG` — stale route was observed before the active turn ended and the split-sync hook ran;
- `POST-COMPLETION-STALE` — route remained on the ended parent after `Turn ended` plus the split-sync hook;
- `PERSISTENCE-FAILURE` — the hook ran but durable write failed;
- `UNRESOLVED` — event ordering or writer identity is missing.

Do not repair a route during a read-only investigation. Do not treat an in-memory cache, `sessions.json`, `gateway_routing`, and the `sessions` table as interchangeable evidence layers.

Trace the writer exactly. In Hermes-style gateways, compression-row creation and route advancement may be different functions. The post-turn runner may update the in-memory `SessionEntry`, call the store save/peer-record path, and only then make the child durable as the active route. A next-inbound self-heal is fallback behavior, not proof that the original post-turn writer failed.

Also check the official race fix for interrupting a protected compression. A compression-in-flight guard that demotes `busy_input_mode=interrupt` to queue prevents competing sibling rotations; it does not necessarily make the route switch at child-publication time.

## 3. Search-identity gate

Do not call a search identity regression from a duplicated historical phrase or from a title/display mismatch.

### Choose a valid anchor

If a prior phrase appears in multiple later sessions:

1. reject it as a uniqueness anchor;
2. select a distinctive content fingerprint from the original physical session;
3. use the existing indexed FTS path to test global uniqueness;
4. join the raw FTS row back to the physical `messages` table;
5. record physical `message_id`, `session_id`, role, and owning lineage segment.

Avoid unindexed full-table `LIKE` scans on large SQLite stores as the primary method. If such a probe times out, preserve that as a failed method and retry with the indexed FTS path; a timeout is not a negative result.

### Compare the two identities

Run both:

```text
raw FTS search
Hermes session_search wrapper
```

Use `current_session_id=None` for a historical-anchor comparison unless the current-lineage exclusion is itself the subject of the test. Compare physical IDs first:

```text
raw FTS message_id/session_id
== wrapper match_message_id/session_id
```

If both identities match, **drop the standalone search-identity fix**. A different title, root ID, or display label is a separate projection issue.

### Test title projection separately

For a titled historical session, compare:

```text
physical sessions.id/title
resolve_session_by_title() result
session_search returned session_id/title
listing/resume displayed title
```

If the resolver returns the physical row but the wrapper displays a lineage-root/generated title, the bug is in title/lineage projection, not FTS. Fold it into the shared listing/resume/identity work when that commit owns the user-visible conversation projection. Do not duplicate a search fix for an identity that already matches.

## 4. Evidence and implementation boundary

Before proposing a commit, classify the finding:

- `LIVE` — current process, routing index, log, or live DB;
- `COPY-VERIFIED` — behavior against an immutable SQLite backup;
- `MIGRATION-COPY` — behavior after a separately labelled temporary schema change;
- `SOURCE-ONLY` — source inspection or upstream metadata;
- `BLOCKED` — the exact test could not run;
- `UNVERIFIED` — plausible but not directly evidenced.

A source-closure gap, route-timing finding, search-identity result, and title-projection result may produce different commit decisions. Keep them separate in the revised implementation table. Do not add a routing commit for an in-flight transient, and do not add a search commit when raw and wrapper physical identities agree.

## 5. Worked evidence pattern

A valid historical-anchor test may look like:

```text
fingerprint: distinctive content phrase
raw FTS: count=1, message_id=M, session_id=S
wrapper: count=1, match_message_id=M, session_id=S
verdict: search identity not disproven
```

A separate title test may look like:

```text
physical row title: Exact Title #204
resolver: physical session S
wrapper title: Exact Title
verdict: title projection loses the suffix; fix projection, not search identity
```

The concrete IDs and phrases from any one incident are evidence fixtures, not universal anchors. Preserve the method and the identity comparison contract.