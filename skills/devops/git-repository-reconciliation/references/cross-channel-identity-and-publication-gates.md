# Cross-Channel Identity and Publication Gates

Use when one work item spans a canonical application repository, a provider/plugin repository, multiple GitHub owner namespaces, and more than one authentication route.

## Core distinctions

Keep these fields separate:

- `CONFIGURED-REMOTE`: exact URL returned by `git remote get-url <remote>`.
- `REPOSITORY-OWNER`: owner namespace returned by direct repository metadata.
- `HUMAN-OWNER-RELATION`: whether the owner namespace belongs to the same human/operator; `UNVERIFIED` unless directly proven.
- `AUTHENTICATED-IDENTITY`: identity/key shown by the active SSH/API/credential route.
- `WRITE-PERMISSION`: whether that credential can mutate this exact repository.
- `REMOTE-HEAD`: direct `git ls-remote` result after the operation.

A different GitHub owner namespace is not proof of a third-party repository. A permission denial is not proof of third-party ownership; it proves only that the current credential cannot write there.

## Pre-publication matrix

For each repository involved:

1. Record the exact sanitized remote URL and repository owner.
2. Record local HEAD, branch, working-tree status, and intended ref.
3. Query the direct remote head without fetching.
4. Check the intended local-to-remote ancestry before pushing.
5. Identify the credential route without printing secrets: HTTPS helper/token, SSH key/deploy key, API token, or browser session.
6. Keep repository ownership and credential authorization as separate verdicts.

## Publication sequence

```text
preflight local SHA + direct remote SHA + ancestry
  → publish exact ref
  → query direct remote SHA again
  → query PR object/API
  → only then perform approved ref cleanup
```

For a provider dependency and application PR:

- Application branch pushed ≠ provider commit published.
- Provider commit published ≠ application PR created.
- PR created ≠ reviewed or merged.
- A `/pull/new/<branch>` URL is a creation form, not a PR object.

## Failure stop gate

If push/auth/API publication fails:

1. Preserve the exact error.
2. Do not switch remotes, create a fork, or select an alternate destination silently.
3. Re-read local HEAD, direct remote HEAD, working-tree status, and PR object.
4. Label the operation `NOT-PUBLISHED` if the remote SHA is unchanged.
5. Do not continue to dependent PR/merge/cleanup steps unless the owner explicitly approves a new route.
6. Never request or print a secret as an ad hoc workaround.

An alternate fork or destination is a new source-of-truth decision, not a routine fallback.

## Raw-byte comparison gate

When proving that a live filesystem file equals a Git tree path, hash raw bytes with the same algorithm on both sides:

- filesystem: SHA-256 over the file bytes;
- Git: SHA-256 over bytes emitted by `git cat-file blob <ref>:<path>`.

Do not compare a filesystem SHA-256 directly with a Git blob object ID; Git blob IDs include Git's object header and are a different digest.

## Evidence labels

Use the lowest proven state:

- `OWNER-RELATION UNVERIFIED`
- `CREDENTIAL READ-AUTHENTICATED / WRITE-DENIED`
- `COMMITTED-LOCAL-ONLY`
- `PUSHED-BRANCH`
- `PR-NOT-FOUND`
- `NOT-PUBLISHED / REMOTE-UNCHANGED`
- `CLEANUP-HOLD`

Never collapse these into “wrong repo,” “all pushed,” or “ready to merge.”
