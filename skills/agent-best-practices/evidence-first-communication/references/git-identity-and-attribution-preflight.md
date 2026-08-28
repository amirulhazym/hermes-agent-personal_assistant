# Git Identity and Attribution Preflight

Reusable reference for VPS/automation commits.

## Why the check exists

Git stores author and committer name/email inside each commit. Remote authentication is a separate layer: it controls whether a push is accepted, but does not rewrite those fields. A host with no configured `user.name`/`user.email` may fall back to the Unix username and hostname, producing an identity such as `Ubuntu <user@example.invalid>`.

## Pre-commit probe

Run in the exact destination repository/worktree:

```bash
git config --show-origin --get-regexp '^user\.(name|email)$' || true
git branch --show-current
git rev-parse --show-toplevel
git remote -v
```

If identity is absent or auto-generated, stop. Compare the intended identity with a known-good commit:

```bash
git log -1 --format='known-good=%H%nAuthor=%an <%ae>%nCommitter=%cn <%ce>' <known-good-ref>
```

For a personal repository, configure narrowly rather than globally:

```bash
git config user.name 'KNOWN PERSONAL NAME'
git config user.email 'KNOWN VERIFIED EMAIL'
```

Do not copy the placeholder values above without owner-provided/known-good evidence.

## Post-commit proof

```bash
git show -s --format='commit=%H%nAuthor=%an <%ae>%nCommitter=%cn <%ce>%nSubject=%s' HEAD
git status --short --branch
git ls-remote <remote> refs/heads/<branch>
```

Keep these states separate:

- local commit exists;
- local commit has the intended identity;
- remote ref contains that commit;
- runtime has loaded/deployed it.

## History audit shape

For the destination ref, count and list identities directly:

```bash
git log <remote>/<branch> --format='%H%x09%aI%x09%an <%ae>%x09%cn <%ce>%x09%s'
```

Report separately:

1. total commits reachable from the destination ref;
2. known-good personal identity count;
3. auto-generated identity count and earliest occurrence;
4. other automation identities;
5. unpushed local commits.

Do not infer that every commit created on a VPS has the VPS identity. Git metadata records the identity written at commit time, not the creation machine. Likewise, a personal push credential does not prove the author field is personal.

## Wrong identity before push

If a wrong-identity commit is local only:

1. hold the push;
2. configure the correct repository-scoped identity;
3. amend/recreate the commit or recreate the commit from the same staged content;
4. record the new SHA;
5. rerun post-commit validators that inspect the commit object;
6. invalidate any approval tied to the old SHA;
7. request approval for the new exact SHA only.

Do not rewrite already-pushed history merely to cosmetically normalize names. That requires explicit owner scope, a history-rewrite risk decision, and a separate force-push gate.

## Incident pattern captured

A personal repository can have mostly owner-authored history while a small number of VPS/automation commits use `Ubuntu <user@example.invalid>`. The correct report is the exact count and earliest recorded occurrence—not “all commits were Ubuntu.” If a new local candidate repeats the identity, treat it as a candidate metadata defect even when its source bytes and tests are otherwise correct.
