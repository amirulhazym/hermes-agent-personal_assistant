# Antigravity Provider — Custom Overlays & Deployment Spec

This directory contains the authoritative personal customizations for the third-party dependency `jaeyeopme/antigravity-provider` (`~/.hermes/plugins/antigravity-provider`).

## Upstream Dependency
- Remote: `https://github.com/jaeyeopme/antigravity-provider.git`
- Role: Consumed third-party runtime plugin only. Never treated as a publication target.

## Custom Features Captured in Patch:
1. `feat(catalog)`: Support live model catalog and quota fetching via `/v1internal:fetchAvailableModels`.
2. `feat(chat)`: Support `/usage agy` rewrite hook and `/agy quota` custom chat command displaying live account quota & reset times in MYT.
3. `feat(models)`: Model picker integration for short logical IDs (`gemini-3.7-flash`, `gemini-3.8-flash`), reasoning effort clamping, and wire routing.
4. `fix(compat)`: Claude on Vertex AI extended thinking invariant fixes and terminal `notify` JSON schema normalization.

## Deterministic Application / Verification:
To verify or redeploy to a clean upstream clone of `antigravity-provider`:
```bash
git -C ~/.hermes/plugins/antigravity-provider apply /home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch
```
