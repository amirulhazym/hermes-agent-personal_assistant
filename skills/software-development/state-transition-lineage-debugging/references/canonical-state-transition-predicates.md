# Canonical State-Transition Predicates: Hermes `/resume` Case Study

## Verified source pattern

In the Hermes repository at `/home/ubuntu/.hermes/hermes-agent`, the `/resume` resolver is `SessionDB.resolve_resume_session_id()` in `hermes_state.py`. It first delegates to `get_compression_tip()`, then historically performed a second generic child walk. The generic walk accepted any child with a matching `parent_session_id` after excluding only branch/delegate markers and `source == "tool"`; it did not require the parent to have `end_reason == "compression"`. That makes it able to cross ordinary lifecycle boundaries.

The smallest behavior fix is to keep one canonical forward traversal and remove the second generic walk. A broader consolidation may then make all relevant traversals reuse one edge fragment/predicate.

## Canonical eligibility matrix

| Candidate edge | Parent state | Child role/marker | Follow? |
|---|---|---|---|
| compression continuation | `end_reason == "compression"` | not branch/delegate/tool of this parent | yes |
| ordinary child | any non-compression boundary or live parent | ordinary | no |
| session reset/switch child | `session_reset` / `session_switch` | ordinary | no |
| idle/cron completion child | `idle` / `cron_complete` | ordinary | no |
| intentional boundary child | project-specific intentional reason | ordinary | no |
| branch | any | `_branched_from == parent.id` | no |
| delegate/subagent | any | `_delegate_from == parent.id` | no |
| tool | any | `source == "tool"` | no |
| inherited foreign marker | compression parent | marker points to another parent | eligible if project semantics permit inheritance |

Eligibility is based on lifecycle state and role, not timestamp ordering. Timestamps may be used only to choose deterministically among already-eligible candidates.

## Tests to add or repair

- `tests/hermes_state/test_resolve_resume_session_id.py::test_follows_compression_tip_when_parent_retains_messages`: positive parent-with-messages case.
- `tests/hermes_state/test_resolve_resume_session_id.py::test_walks_from_middle_of_chain`: make all traversed edges explicit compression continuations.
- `tests/hermes_state/test_resolve_resume_session_id.py`: add boundary-reason parameterization and ordinary-child-after-tip regression.
- `tests/hermes_state/test_resolve_resume_session_id.py::test_prefers_most_recent_child_when_fork_exists`: stop modeling ordinary unmarked children as implicit compression forks; use explicit valid/invalid roles.
- `tests/gateway/test_resume_command.py::TestHandleResumeCommand::test_resume_follows_compression_continuation`: exact-title positive path; add exact-ID twin and boundary negatives.
- `tests/state/test_compression_lineage_guard.py`: extend foreign-marker and branch/delegate/tool cases to the resolver that `/resume` actually calls.
- `tests/hermes_state/test_session_md_export.py::test_fork_children_created_before_continuation_do_not_hijack_lineage`: keep as export-lineage coverage, but ensure its fixtures distinguish explicit delegates/tools from valid continuations.
- `tests/test_hermes_state.py::TestCompressionChainProjection::test_get_compression_tip_walks_full_chain`: multi-hop projection coverage; its `delegate1` fixture should model a real delegate if it is intended to be one.

## Hidden call surface

`resolve_resume_session_id()` is used by CLI startup and mid-turn resume, gateway `/resume`, TUI resume paths, WebUI session-message resolution, and CLI delegation-notification ownership. `get_compression_tip()` is also used by gateway session healing, list/sidebar projection, cron/gateway paths, and compression recovery. A shared predicate change must preserve read-only resolver behavior and must not weaken caller ownership/security checks.

## Read-only verification

The resolver should only SELECT/read. The command handler may later mutate state by ending the old session, switching routing, and reopening the target. Keep those side effects outside the resolver. For a regression, snapshot `sessions` rows and routing rows before and after the resolver call and assert byte/field equality.
