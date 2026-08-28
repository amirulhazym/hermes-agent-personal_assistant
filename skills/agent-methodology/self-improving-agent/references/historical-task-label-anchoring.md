# Historical Task-Label Anchoring

## Purpose

Use this reference when a user names a task by a short label (`A5`, `P4`, `G7`, `Task 3`) after a long conversation, merge, audit, or context handoff. The same label may be reused in later documents.

## Retrieval recipe

1. Search the exact label with the domain term the user supplied.
2. Search the nearest task-list entry and inspect its surrounding messages.
3. Read the source session/plan around the match far enough to capture predecessor and successor gates.
4. Collect every same-label definition found later. Build a collision table:

| Label | Source boundary | Owner-defined meaning | Status |
|---|---|---|---|
| A5 | roadmap/task list | [meaning] | [status] |
| A5 | later operations record | [meaning] | [status] |

5. Select the meaning from the source boundary named or implied by the user. If the user says “during the merge plan,” prefer the merge-plan task entry over a later operational record.
6. Only after anchoring the task, derive approaches and acceptance gates.

## Evidence fields

Keep these separate in the working note:

- `task_label`
- `task_source_session_or_doc`
- `owner_objective`
- `related_findings`
- `approach_candidates`
- `acceptance_gates`
- `unresolved_inputs`

## Incident pattern captured

The label `A5` was reused:

- In the earlier merge/update roadmap, it meant: change Hermes’s WhatsApp bot number from the old number to a new number after the Hermes update, then smoke-test Telegram and WhatsApp.
- In a later operations record, it was used for a LID/JID identity-field correction.

The agent answered the later label instead of the owner’s earlier roadmap task and asked the user to choose between migration modes as if the task identity itself were unknown. The correct recovery was to retrieve the exact roadmap entry, restate the bot-number migration scope, and treat account/pairing choices as approach candidates inside A5.

## Stop conditions

Stop and re-anchor before replying if any of these are true:

- the same label appears in more than one plan or document;
- the user says “that is not the A5 I meant”;
- the proposed clarification changes the task’s actor/objective rather than only its implementation path;
- a later document’s label is being used as evidence against an earlier owner-defined objective.

Do not create a new narrow skill for each label or incident. Add reusable label-resolution rules here and keep individual IDs/session links in the session record or a project-specific evidence ledger.
