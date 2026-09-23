# Antigravity Provider — Custom Overlays & Deployment Spec

This directory is the authoritative SSOT representation for personal customizations of the third-party dependency `jaeyeopme/antigravity-provider` deployed at `~/.hermes/plugins/antigravity-provider`.

## Upstream dependency

- Remote: `https://github.com/jaeyeopme/antigravity-provider.git`
- Pinned reconstruction base: `097db5303a610d7e5d75a2fef58d4aefb18436d6`
- Role: consumed third-party runtime plugin only; never a personal publication target.
- Live checkout currently carries two dependency commits on top of that upstream base:
  - `e7e1833` — `feat(catalog): support live model catalog and quota fetching`
  - `8cccbb6` — `feat(chat): support /usage agy slash command and rewrite hook`

## Ordered authoritative patch chain

Apply these patches, in this exact order, to a clean checkout of the pinned upstream base:

1. `2026-09-23_local_dependency_commits_base.patch`
   - SHA-256: `50ed309a7a9a9a542aec6b361c0280f9317ac839e8d1c8e44ba9b766d1e102c3`
   - Reconstructs the two intentional local dependency commits listed above.
2. `2026-09-04_custom_antigravity_features.patch`
   - SHA-256: `f5f726808dd1935f9551dea258432c2450be2a013798dd393273042002844520`
   - Captures the uncommitted personal overlay currently represented in the live plugin.
3. `2026-09-23_gemini_3_8_default.patch`
   - SHA-256: `35fa5040e7886cf233614ee2248fcf5cb86d152d905efb8f77f251b7d8c6d016`
   - Moves the plugin default from `gemini-3.7-flash` to `gemini-3.8-flash` and adds the regression test.

## Custom behavior represented by the chain

- Live model catalog and quota fetching via `/v1internal:fetchAvailableModels`.
- `/usage agy` rewrite hook and `/agy quota` chat command with MYT quota/reset display.
- Model picker integration using stable logical IDs, including `gemini-3.8-flash`.
- Reasoning-effort clamping and wire-route normalization.
- Claude on Vertex AI extended-thinking compatibility fixes.
- Terminal `notify` JSON schema normalization.
- Current owner target default: `gemini-3.8-flash`.

The managed-agent ID `antigravity-preview-09-2026` is intentionally not a Hermes model-picker ID.

## Deterministic reconstruction

```bash
git clone https://github.com/jaeyeopme/antigravity-provider.git /tmp/antigravity-provider-check
git -C /tmp/antigravity-provider-check checkout 097db5303a610d7e5d75a2fef58d4aefb18436d6
git -C /tmp/antigravity-provider-check apply /home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-23_local_dependency_commits_base.patch
git -C /tmp/antigravity-provider-check apply /home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch
git -C /tmp/antigravity-provider-check apply /home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-23_gemini_3_8_default.patch
```

Before final release, the live plugin is expected to remain at the pre-release state: dependency commits + the 2026-09-04 custom overlay, with `DEFAULT_MODEL = "gemini-3.7-flash"`. The Gemini 3.8 default patch is promoted to live only through the final approved release/deploy flow.
