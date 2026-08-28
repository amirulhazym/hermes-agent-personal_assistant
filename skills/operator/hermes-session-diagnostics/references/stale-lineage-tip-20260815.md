# Non-empty but stale `/sessions` / `/resume` — lineage-tip diagnosis

## Scope
Use this reference when `/sessions` returns plausible named rows, but the list remains frozen at an old title/ID, or `/resume <number>` loads an older response. This is distinct from the empty-list/NULL-routing-column class documented in `session-listing-empty-20260813.md`.

## Verified failure pattern
A Telegram DM lane was correctly scoped and had current data, but the user-visible list still surfaced:

```text
Hermes Integration Reconciliation Review #108 — 20260810_144912_43bf68
```

Live DB facts at the time of diagnosis:

- caller lane: `agent:main:telegram:dm:679729206`
- lineage root: `20260808_040236_9eee6992`
- current open row: `20260815_130611_c1bff7`, titled `Verify last 10 words of response`
- root-to-current distance: 218 edges
- listed `#108` row position: edge 100
- lineage reasons: 215 `compression`, 3 `session_reset`, 1 open row

The exact code-path reproduction returned:

```text
TIP_ROOT = 20260810_144912_43bf68
RESUME_ITEM_2 = 20260813_081126_6fbe73
OPEN_ROW = 20260815_130611_c1bff7
```

Therefore the old `#108` output was deterministic, not a cache guess.

## Causal chain

```text
/sessions
  -> query_session_listing()
  -> list_sessions_rich(project_compression_tips=True)
  -> get_compression_tip(root)
  -> fixed 100-hop loop stops at edge 100
  -> #108 is displayed

/resume 2
  -> numbered picker selects displayed #108 ID
  -> resolve_resume_session_id(#108) returns an ancestor/partial tip
  -> transcript loader calls get_compression_tip() again
  -> an older branch can be loaded instead of the current open row
```

The resolver also had two independent lineage hazards:

1. It only follows children when the parent has `end_reason='compression'`; `session_reset` boundaries are not treated as one logical continuation by that projection path.
2. Its child ordering prioritizes a child whose `end_reason='compression'` over a newer live sibling. A parent can therefore have an old closed compression branch and a current open child, with the old branch winning.

## Read-only reproduction recipe

Run against the live DB only when the inspection is guaranteed read-only; otherwise copy the DB first. Use the exact runtime source, not a reimplemented SQL approximation:

```python
import pathlib, sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent')
from hermes_state import SessionDB
from hermes_cli.session_listing import query_session_listing

db = SessionDB(pathlib.Path('/home/ubuntu/.hermes/state.db'), read_only=True)
rows = query_session_listing(
    db,
    source='telegram',
    session_key='agent:main:telegram:dm:679729206',
    current_session_id='<CURRENT_ID>',
    limit=10,
)
print([(r['id'], r.get('title')) for r in rows])
print('tip(root)=', db.get_compression_tip('<ROOT_ID>'))
print('resume(listed)=', db.resolve_resume_session_id('<LISTED_ID>'))
```

Also query `gateway_routing.entry_json.session_id`; do not treat `sessions.json` as the full session list. Walk the parent chain and report the requested ID, resolved ID, live routing ID, open row, loaded transcript ID, and listed row position separately.

## Acceptance criteria

A diagnosis or fix is not proven by `rows > 0`. Require all of:

- `/sessions` returns the expected latest logical conversation ID/title, or intentionally excludes the active conversation for a documented reason;
- `/resume <number>` resolves to the expected effective descendant;
- transcript loading returns a known latest message/content marker from that descendant;
- a long chain beyond the previous hop cap passes;
- a fork with an old closed compression child plus a newer live sibling passes;
- a `session_reset` boundary has an explicit, tested semantic;
- current source/runtime and DB evidence agree.

## Pitfalls

- Live DB reads can still produce the wrong user result when the lineage resolver is wrong; "reads live DB" is not latest-tip proof.
- A 10-row page limit is a separate display limit, not proof that the underlying projection is current.
- Increasing `100` to a larger constant is only a band-aid if forks and reset boundaries remain unresolved.
- Do not mutate routing or send `/resume` just to test an identity hypothesis; pure resolver calls and transcript-ID inspection are safer first.
- Exact quoted response provenance requires a stored message ID. If FTS/content search cannot locate it, label the origin UNVERIFIED rather than assigning it to the nearest-looking session.
