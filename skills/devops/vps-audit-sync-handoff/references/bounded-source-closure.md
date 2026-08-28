# Bounded Source-Closure Reference

Use this after a live↔source census or preservation-branch review when an external reviewer supplies a proposed final count.

## Objective

Produce a file-level union without reopening the entire census and without converting runtime/private artifacts into public source.

## Evidence layers

Keep these separate:

1. **Raw records** — census rows, Git status records, directory entries.
2. **Known affected files** — current files that are live-only, live-newer, stale public tip files, or explicit preservation files.
3. **Release candidates** — affected files whose content/provenance is source-worthy and whose privacy/runtime treatment is known.
4. **Owner decisions** — files where intent, privacy, public exposure, or live-vs-main direction is unresolved.

Only layer 3 can become release `Y`.

## Normalization procedure

For each class, build an exact relative-path set:

```text
nested preservation paths
plugins/<relative-path>
hooks/<relative-path>
skills/<relative-path>
scripts/<relative-path>
agents/<relative-path>
config/<relative-path>
persona/<relative-path>
```

Then classify each path exactly once:

- `PORT` — source-worthy and safe to carry into the candidate, subject to later owner release approval.
- `SANITIZE` — potentially source-worthy but requires removal/redaction before public inclusion.
- `PRIVATE-RUNTIME` — never copy into public source.
- `STALE/BACKUP` — not a current source candidate unless separately justified.
- `ALREADY-REPRESENTED` — exact source representation exists; no new path delta.
- `OWNER-DECISION` — evidence does not establish intent or public-safe treatment.

## Counting rules

- Count files, never directories or prose groups.
- Exclude `SOURCE-MATCH` from change deltas.
- Exclude `*.bak*`, archived copies, and generated files unless the owner explicitly promotes one.
- Exclude `__pycache__/*.pyc` from plugin/source comparisons.
- A `LIVE-NEWER-DRIFT` file is one changed file, not proof that live should win over main.
- A directory containing 26 files is 26 records, not one plugin.
- A formula that includes owner decisions is an affected/action union, not final `Y`.

## Set equation

Return both values:

```text
known non-nested affected/action files = X
nested proven files + deduped non-nested files = bounded union
```

Then state separately:

```text
final candidate Y = NOT FINAL
owner blockers = <exact paths/groups>
```

Do not silently substitute the bounded union for release `Y`.

## Bounded current-live verification

A current check is allowed only when it answers a named set question. Examples:

- Compare current plugin non-generated files against the existing 26-path census set.
- Check exact existence of four previously identified current nested files.
- Parse live config and the committed template into key-path sets without printing values.
- Check public persona path names and live private path names without reading private contents.

Do not turn these into a fresh recursive census. Record the exact scope and the exclusions.

## Report template

```text
VERDICT: UNION-PARTIAL / FINAL-CANDIDATE / BLOCKED

Raw evidence:
- census records + artifact hash
- exact Git refs and status counts
- exact per-class path counts

Per-class disposition:
- hooks: <paths/counts>
- plugins: <paths/counts>
- skills: <paths/counts>
- scripts: <paths/counts + live/main direction evidence>
- agents: <private/owner/public split>
- config: <template path + key-path delta>
- persona: <public tip action; live private excluded>

Equation:
- nested proven set: N
- non-nested affected/action set: X
- deduped bounded union: Y_bounded
- final candidate Y: NOT FINAL unless zero owner blockers

No-change proof:
- no commit/push/fetch/checkout/edit/build/deploy/restart
```

## Common failure

Do not accept `68 live-only + 3 drift = 71` as a source count until checking whether one of the 68 is a backup, generated file, private runtime artifact, or already represented elsewhere. The arithmetic may be internally correct while the release interpretation is wrong.
