---
name: hermes-model-catalog-maintenance
description: Safely remove, deprecate, or rename a model ID across the Hermes agent codebase — picker, typed routing, normalization, provider profiles, pricing, metadata, disk caches — without leftovers or billing leaks. Use when a provider retires/renames a model, the user asks to remove a model from the picker, or requests a full purge ("no leftovers") of a model ID.
---

# Hermes Model Catalog Maintenance

Removing a model from Hermes is NOT a one-line curated-list edit. A model ID can be
referenced in 10+ surfaces; miss one and it resurfaces (stale cache), breaks
normalization, or leaks to another provider's catalog (billing surprise).

Proven 2026-08-07/08: full purge of `deepseek-chat` / `deepseek-reasoner` (DeepSeek
discontinued them 2026-07-24; they still worked server-side mapped to
`deepseek-v4-flash` but vanished from live `/v1/models`). 121 references purged
across code + tests, 1447 tests green.

## Terminology

- **Requested model** — the ID the user picked / picker sent (may be a legacy alias).
- **Canonical model** — the ID the provider actually served (`response.model` /
  first stream `chunk.model`); may differ from requested (deepseek-chat → v4-flash).
- **Deprecated alias** — curated ID removed from the provider's live catalog.

## Full-purge checklist (scan ALL surfaces)

1. **Curated list** — `hermes_cli/models.py` `_PROVIDER_MODELS[provider]`: remove the
   IDs. Verify nothing else re-adds them (see 2).
2. **Live-catalog merge** — `provider_model_ids()` merges the static curated list
   back into the live `/v1/models` result, so removed models REAPPEAR in the picker.
   Fix: a `_DEPRECATED_MODEL_ALIASES: dict[provider, frozenset[ids]]` registry + a
   `_filter_deprecated_aliases(provider, ids, live_ids=None)` applied to EVERY
   return path: live merge, `fallback_models`, models.dev merge, final curated
   return, AND cache reads in `cached_provider_model_ids()` (a stale cache file can
   otherwise serve the removed model for the whole TTL).
3. **Typed routing** — `hermes_cli/model_switch.py` `_BUILTIN_DIRECT_ALIASES`,
   `MODEL_ALIASES[provider]`, and `hermes_cli/models.py` `detect_provider_for_model`.
   DANGER: with routing removed, a typed alias falls through to the OpenRouter
   catalog check and can reroute to the aggregator (billing surprise). Keep a deny
   guard: in `detect_provider_for_model`, before the OpenRouter step, return None if
   the name is in any `_DEPRECATED_MODEL_ALIASES` set → "no model detected" (fail
   loud, no leak).
4. **Normalization** — `hermes_cli/model_normalize.py`: check the provider's
   normalize function's fallback target. DeepSeek's folded EVERYTHING unknown into
   `deepseek-chat`; after purge it must fall back to a live model
   (`deepseek-v4-flash`). Check `_DEEPSEEK_CANONICAL_MODELS`-style frozensets and
   keyword folding (reasoner keywords must not map to removed models).
5. **Provider profile** — `plugins/model-providers/<provider>/__init__.py`:
   `aliases=()` (remove alias strings), thinking/reasoning gating functions that
   special-case the removed IDs, `fallback_models`, `default_aux_model`.
6. **Aggregator + tool lists** — grep the WHOLE repo, not just the provider dir:
   openrouter `fallback_models`, other providers' lists, optional skills
   (`optional-skills/security/godmode/scripts/godmode_race.py` had the alias).
7. **Pricing** — `agent/usage_pricing.py`: remove legacy pricing entries for the
   removed IDs; ADD a pricing entry for the canonical serving model if missing
   (deepseek-v4-flash had NONE → cost status "unknown" for the recommended model).
8. **Context metadata** — `agent/model_metadata.py` `DEFAULT_CONTEXT_LENGTHS`:
   remove exact alias entries. Keep the family fallback (e.g. `"deepseek": 128000`)
   and update comments; verify `get_model_context_length()` resolves the surviving
   models correctly.
9. **Test fixtures** — bulk-replace the removed ID in tests that merely use it as a
   generic fixture (aux client, insights, transport parity, web server, custom
   providers). KEEP/ADD tests that ASSERT the deny behavior (typed alias →
   detect/resolve/normalize all reject or fall back). Update doctests in
   normalize (they encode expected fallback values).
10. **Disk caches** — at deploy time clear the provider entry from
    `~/.hermes/provider_models_cache.json` (see verification-before-completion
    reference `gateway-restart-and-dirty-merge.md`). A pre-fix cache resurrects the
    model in the picker despite correct code.

## "No leftovers" ≠ zero string references

Some references MUST remain after a full purge:
- the `_DEPRECATED_MODEL_ALIASES` registry (stale-cache filter + deny guard);
- history notes/comments explaining the removal (they prevent re-adding);
- guard tests asserting the ID is rejected.
"Full purge" means: no path that SELECTS, ROUTES, or RESOLVES the ID accepts it.
Explain this to the user when they ask for "no leftovers" — removing the deny
guard itself would let the model leak back through stale caches or aggregators.

## Canonical-identity capture (companion fix, P2/P3)

When a provider serves a different model than requested, capture it: after each API
call set `agent.response_model = getattr(response, "model", None)` (streaming: the
helpers already extract `chunk.model` into the final response object), log
` served=<canonical>` when it differs, persist via `update_token_counts(..., response_model=...)`
to a `canonical_model` column (feature-detect the column; SQLite declarative
column reconcile auto-adds it), and render `/status` as
`Model: <requested> → <canonical> (<provider>)` only when no session override is
active (override = fresh switch, cached canonical is stale).

## Verification

```bash
grep -rn '<removed-id>' --include='*.py' . | grep -v .git   # expect: guards + history notes + deny tests ONLY
grep -rn '<removed-id>' --include='*.json' --include='*.yaml' --include='*.yml' .   # expect: empty (or docs history)
# guard tests (deny behavior):
pytest tests/hermes_cli/test_models.py -k 'Purge or Deprecated or Alias' -q
# full relevant suite: models, normalize, providers, profiles, pricing, hermes_state, status display
```

Live deploy: files on disk ≠ active code — gateway restart required for code
activation; cache clearing is immediate. Report "deployed to disk" vs "live
verified" separately.

## Pitfalls

- Editing only `_PROVIDER_MODELS` — the curated-first merge silently re-adds the
  model on next picker render.
- Removing routing without a deny guard — typed alias leaks to OpenRouter's stale
  catalog (billing surprise).
- Forgetting normalize fallback — unknown inputs still resolve to the removed ID.
- Forgetting the disk cache — removed model appears in the picker from cache.
- Updating fixtures but keeping assertions that EXPECT the alias to resolve.
