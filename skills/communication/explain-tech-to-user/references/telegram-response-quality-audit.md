# Telegram Response Quality — Phase-A Audit (2026-08-21)

Read-only verification of gateway internals after owner complained replies were
"berserabut". All items VERIFIED against live files/state.db. Use this as the
evidence base for any future Phase-B fix proposal.

## Root causes of "messy" (measured)

1. **Model regeneration after cut-offs** — 30 of last 200 assistant msgs in
   session f50eb7 ended `finish_reason=length`; the `[System: cut off]` retry
   made the model REGENERATE and re-pour identical closing lines. Gateway did
   NOT re-deliver (each dup line sits in a different message row).
2. **My own footer stacking** — multiple sign-off lines per turn.
3. Repeat metrics over 40 consecutive TG assistant messages:
   "standing by" ×62, "awaiting" ×22, "tunggu" ×18, identical PR deeplink ×6,
   "— standing by." ×4, "— awaiting your call…" ×4.
4. Bubble health: n=40, avg 849 chars, max 3981, ZERO over 4096 → chunking fine.
   Tool-trace emoji lines delivered: 0.

## Verified gateway facts (for future fixes)

- Split limit: Telegram mirrored at 4096 by gateway relay
  (`gateway/relay/descriptor.py:113-121`, `relay/adapter.py:186`).
- Tool-trace streaming IS config-controlled and TG default is OFF
  (`gateway/display_config.py:132`); live config overrides with top-level
  `display.tool_progress: all`. Real keys:
  `display.platforms.<platform>.{tool_progress, busy_ack_detail, streaming,
  show_reasoning}`, `display.tool_progress_grouping`
  ("accumulate" = edit one bubble | "separate" = one msg per tool),
  `display.runtime_footer.enabled` (live: false).
- NO post-send dedup or generic max-length config key exists (NOT FOUND in
  `gateway/config.py`, `delivery.py`). Only delivery_ledger recovery +
  MEDIA-tag dedup (`run.py:1713`).
- `/reset`, `/compress`, `/context` ALL exist in live CLI
  (`cli.py:10413`, `cli.py:10446`, `cli.py:11943`) even if rarely used.
- Skill injection is metadata-only until triggered: index block measured
  18,811 chars / 228 lines (~4.7k tokens) via
  `agent.prompt_builder.build_skills_system_prompt()`; skills tree itself is
  75MB on disk but only descriptions enter the prompt.
- Per-platform model routing is SUPPORTED (`gateway/profile_routing.py`,
  `profiles:` config section) but NOT configured live — model set globally via
  /model. Observed same-day models: TG x-preview-f-free, WS gpt-5.6-luna /
  muse-spark / x-preview-f-free.
- Persistent homes: persona/output rules → `~/.hermes/SOUL.md` (10,770 bytes);
  procedures → skills. Both survive sessions.

## Fix levers ranked (Phase-B candidates, NOT applied)

1. Behavioral: one-closing-line rule + never re-pour pre-cut content
   (cheapest, zero config; embedded in this SKILL.md).
2. Config: ensure `display.platforms.telegram.tool_progress: off` explicitly
   (currently inherits top-level `all`).
3. Model: shorter/more disciplined model for TG, or raise max output tokens to
   cut `finish_reason=length` regenerations.
4. NOT possible today: post-send dedup key does not exist — do not propose it.