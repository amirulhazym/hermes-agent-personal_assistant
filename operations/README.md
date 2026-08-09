# Operations metadata policy

`operations/` contains durable schema/examples and sanitized release evidence only.
The mutable cross-channel coordination ledger lives in the runtime and is not
copied wholesale into public Git.

## Authority

`owner instruction > AGENTS.md > tested release manifest/procedure > ledger`

The ledger coordinates tasks and records observations. It never authorizes a
mutation, release, message, credential privilege change or deployment. A stale
`active`, `approved` or `in-progress` value must yield to an explicit owner
`HOLD`/`PAUSE`.

See `ledger.schema.json` and `ledger.example.json`. Runtime values, sessions,
messages, secrets and medical/account state remain private.
