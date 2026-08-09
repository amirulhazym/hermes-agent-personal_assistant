# Public User-Profile Structure (sanitized)

The live user profile is private runtime state. This public file documents the
schema boundary only; it intentionally contains no identity, contact, health,
account, location or preference values.

## Reconstructive fields

- communication style and language preference
- technical role and project context
- approval and safety preferences
- timezone/region metadata
- durable non-sensitive workflow preferences

Populate these fields only in the private runtime profile or an approved
sanitized fixture. Never copy raw live `USER.md` into public Git.
