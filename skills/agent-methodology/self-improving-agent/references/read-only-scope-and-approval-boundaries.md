# Read-only scope and approval boundaries

Use this when an implementation/release conversation changes into audit, explanation, or read-only verification.

## Core rule

A later explicit owner instruction overrides an earlier plan or approval. `Proceed with the repair` does not authorize later commits, edits, deletes, write-capable tests, deployment, or restart after the owner says `read-only`, `HOLD`, or `do not execute`.

Keep these states separate:

```text
historical approval -> candidate work -> read-only audit -> release approval -> live deployment
```

Do not carry approval across a boundary without a new explicit instruction.

## Action classification

Before every tool call, classify the action:

- **READ-ONLY:** read/search, hashes, Git/process/file metadata, and isolated inspection with no persistent writes;
- **CANDIDATE WRITE:** edit, stage, commit, amend, create/delete candidate files, or tests that mutate the candidate tree;
- **RUNTIME WRITE:** live code/config/state/log changes, marker deletion, reload, or restart;
- **EXTERNAL WRITE:** push, upload, publish, or third-party communication.

Under read-only scope, execute only the first class. A test that writes `/tmp` or an isolated fixture is still a write; label it explicitly instead of calling the whole operation read-only. If platform housekeeping requires a write, disclose it as an exception before doing it.

## Recovery after an unauthorized write

1. Stop the original plan immediately.
2. List the exact command, path, and write class.
3. Re-check candidate identity/status and live hashes, metadata, process state, and mutable-state metadata.
4. Do not make additional “cleanup” writes or silently roll back; preserve evidence and ask for scope if recovery itself needs mutation.
5. Report candidate, live, and external boundaries separately.

## Semantic contract gate

A passing regression test proves that code follows its chosen interpretation. It does not prove that the interpretation matches the owner’s clinical/business source of truth.

When config fields, comments, mappings, wiki notes, or runtime consumers disagree:

- preserve the contradiction verbatim;
- label the contract `UNRESOLVED` / `UNSUPPORTED`;
- block interpretation-dependent release/deployment;
- inspect all authoritative consumers and ask for the one owner decision that changes behavior;
- invalidate tests and candidate SHA after the contract decision changes bytes.

Never infer a domain mapping solely from field names, list position, or a passing internal test when another active source says the slot is deactivated.

## Evidence report

```text
Scope: READ-ONLY / candidate write / runtime write / external write
Executed: exact commands/actions
Not executed: exact exclusions
Candidate: path + SHA + dirty state
Live: hashes/metadata + process state
Semantic gaps: contradictions blocking interpretation
Next gate: one explicit owner decision or approval
```
