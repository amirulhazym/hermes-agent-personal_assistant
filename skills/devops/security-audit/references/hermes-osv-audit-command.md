# hermes security audit — inline supply-chain scan (OSV.dev)

Verified live 2026-08-11 on the VPS. `hermes security audit` is the
first-party, zero-cost way to scan the Hermes stack for known
vulnerabilities. It complements (does not replace) the git secret-scanning
methodology in the main SKILL.md.

## What it covers

- The Hermes venv (installed PyPI dists)
- Python deps declared by plugins under `~/.hermes/plugins/`
- Pinned npx/uvx MCP servers in config.yaml

It does NOT scan globally-installed packages or editor/browser extensions.

## Output format

```
[venv]
  MODERATE  h2==4.3.0  GHSA-6hr6-w5qg-qmwg
           h2: Duplicate Host header could facilitate request smuggling
           fixed in: 4.4.1
  ...
  UNKNOWN   pip==24.0  PYSEC-2026-1796
```

- Three source families: **GHSA** (GitHub advisories, rated), **PYSEC**
  (OSV records — often seve uncharted, listed as UNKNOWN).
- **UNKNOWN rows are usually duplicates of the same advisory** with a PYSEC
  ID — do not count them as extra findings. Count unique packages/versions.
- Exit code 0 even when findings exist — it is a report, not a gate.

## Interpretation (rank before acting)

1. Zero HIGH / zero CRITICAL does NOT mean "clean" — report the MODERATE/LOW
   counts explicitly.
2. Map each finding to actual runtime exposure, not CVSS severity:
   - h2 request smuggling — only exploitable serving untrusted HTTP/2; local
     bridges (WA port 3000, adapter channels) don't expose it.
   - pip / setuptools — only reachable during install/update operations.
   - pydantic-settings symlink issue — needs attacker control of
     secrets_dir/values.
3. Deferral pattern (fit for single-user VPS): no urgent action → record as
   TBC note (`status: TBC`) in the wiki with advisory IDs + fixed-in
   versions + deferral rationale; execute upgrades at the NEXT deploy/update
   cycle via the normal release flow (not ad-hoc pip bumps inside a managed
   venv — coordinate with the Hermes updater).
4. After upgrade: re-run `hermes security audit`; expect zero MODERATE; then
   supersede the TBC note.

## Companion: `hermes insights --days N`

Read-only usage telemetry (token totals per platform/model, tool-call
counts, skill loads, activity patterns). Caveat when reporting: model names
in the output include HISTORICAL sessions — a deprecated model (e.g.
deepseek-chat) appearing there is past data, not live config. Verify current
config separately (`hermes status` / config.yaml) before flagging anything
as a live issue.

## Vault/record-keeping

Worked example (2026-08-11): findings written to
`~/wiki/wiki/security-upgrade-tbc.md` with frontmatter per SCHEMA.md,
index.md updated, git commit. Follow the vault's hard rules: frontmatter on
every file, commit after every write, evidence_tier: evidence for live audit
output.