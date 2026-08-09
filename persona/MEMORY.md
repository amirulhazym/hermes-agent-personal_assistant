# Public Memory Structure (sanitized)

Durable memory is mutable private runtime state. This public file records the
representation policy, not the owner's memories.

## Rules

- Git may contain memory schema, migration code and safe dummy fixtures.
- Raw memory entries, session excerpts, personal facts, medical state,
  credentials and third-party data remain outside public Git.
- Runtime memory changes do not authorize source changes by themselves.
- A new/reset session may be required to reload a changed memory/persona
  policy.
