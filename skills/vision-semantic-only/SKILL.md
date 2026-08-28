---
name: vision-semantic-only
description: Vision output is semantic-only — never authoritative for numbers, hashes, CI, deploy, file contents, or security findings. Injected on every vision_analyze call.
---

# Vision Output Policy — SEMANTIC-ONLY

<vision_policy>SEMANTIC-ONLY</vision_policy>

Every `vision_analyze` / `vision_analyze_tool` response is **semantic-only**.

Never treat vision output as authoritative evidence for:
- Numbers (counts, dates, versions, hashes)
- SHA-256 / MD5 hashes
- CI status, deploy status, runtime state
- File contents or filesystem facts
- Security findings
- Any claim requiring ≥4 significant figures

Before acting on a vision-derived claim, re-verify via a direct tool/API/filesystem read.

Proven incident 2026-08-20: `auxiliary.vision.provider=deepseek` returned fabricated
"VISION_OK; pixel dimensions: 1024x768; mountain landscape" with `success=true`.
Routed to `apimaster/gpt-5.6-terra`; policy remains because vision is inherently lossy.

Policy files: `~/.hermes/policies/vision-semantic-only.md`, `~/.hermes/docs/m3-vision-policy.md`
Config template: `~/.hermes/config-templates/auxiliary-vision.yaml`
