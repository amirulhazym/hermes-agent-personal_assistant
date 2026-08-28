# Capability vs Instance State

Use this reference whenever a user asks whether a file, feature, format, or configuration "exists" in an agent installation.

## The two questions

Do not collapse these into one verdict:

1. **Capability/specification:** Does the installed product/source/docs support it?
2. **Instance state:** Is it present, configured, loaded, enabled, or active on this machine/profile right now?

A supported feature does not imply that an instance contains it. A file present on disk does not prove that the running process loaded it.

## Evidence matrix

| Claim | Minimum evidence | Safe label |
|---|---|---|
| Product supports the feature | Live installed source or primary official documentation | `CAPABILITY-VERIFIED` |
| Exact file is on disk | Direct path/stat or a filesystem enumeration that includes hidden paths | `PRESENT-ON-DISK` |
| Runtime loaded the file | Runtime discovery/output or direct process-level evidence | `ACTIVE/LOADED-VERIFIED` |
| No match was found | Exact search roots, filename set, and hidden-file scope | `ABSENT-IN-CHECKED-PATHS` |

Never upgrade `ABSENT-IN-CHECKED-PATHS` to a global `DOES-NOT-EXIST` claim unless the scan scope genuinely covers the whole relevant filesystem/profile.

## Reusable procedure

1. **Parse the noun exactly.** Preserve dots, case, suffixes, and profile names. `.hermes.md`, `HERMES.md`, and `hermes.md` are different filenames.
2. **Check the live implementation.** Inspect the installed resolver/loader and record the exact accepted names, precedence, traversal boundary, and fallback behavior. Use official docs as a second source where available.
3. **Check the actual instance separately.** Enumerate the relevant project roots, current working directory, `$HERMES_HOME`/profile directory, and hidden paths. A single glob/search result is not enough for a dot-prefixed file.
4. **Check activation only if asked.** A present file may not be loaded because of cwd, git-root boundaries, priority rules, cache/frozen prompt state, or a disabled feature.
5. **Report scope and raw evidence.** Include the exact roots, exact target names, relevant current cwd/profile, and the shortest raw output (`0 matches`, `path exists`, resolver line, or runtime result).
6. **If correcting an earlier answer, identify the scope error.** Say whether the original answer confused capability with presence, presence with activation, or one filename spelling with another. Then give both verdicts independently.

## Hermes context-file example

For Hermes project context, verify the implementation's accepted names before searching the filesystem. In the 2026.8.3 local source, the resolver declares `.hermes.md` and `HERMES.md`; bare `hermes.md` is a separate name and is not implied by that list. The resolver's support for those names is evidence of capability only. A current project still needs an actual file in a directory reachable under the resolver's cwd/git-root rules.

When a matching Hermes-native file is absent, inspect the documented fallback context source (for example `AGENTS.md`) separately. Do not call the fallback file an `.hermes.md` file or imply that the native file exists because the fallback loaded.

## Common failure modes

- **Docs-to-disk leap:** "The docs list the filename, so we have it." — Wrong evidence layer.
- **Disk-to-runtime leap:** "The file exists, so Hermes used it." — Check cwd, precedence, process/session reload, and runtime output.
- **Case/dot collapse:** Treating `hermes.md` as equivalent to `.hermes.md` or `HERMES.md`.
- **Search-scope overclaim:** Reporting global absence after checking only one cwd or a tool that may omit hidden paths.
- **Apology without diagnosis:** Saying "you're right" without naming the original scope error and showing the corrected evidence.

## Owner-facing answer shape

```text
VERDICT
- Capability: [label] — [exact source evidence]
- Instance presence: [label] — [scope + raw output]
- Active/loaded: [label or UNVERIFIED] — [runtime evidence or gap]

Why the apparent contradiction:
[Capability and instance state are different claims.]

Scope gap:
[What was not checked, if anything.]
```
