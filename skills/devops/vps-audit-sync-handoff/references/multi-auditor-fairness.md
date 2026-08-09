# Multi-Auditor Fairness & Provenance

## Provenance commands (run via terminal)
```bash
# Exact mtimes (authorship / completion)
ls -la --time-style=full-iso <dir>/*.md

# Which auditor's files contain a finding?
grep -rl "med-auto-confirm" <dir>/

# Coverage matrix across auditors
for f in <dir>/*/audit-02-findings.md; do echo "$f:"; grep -c "F-22" "$f"; done
```

**Signatures:**
- All 3 files share one identical mtime → batch dump (rate-limited / incomplete).
- Folder name ≠ author. `opencode-audit/` can be Gemini output (user pasted an
  OpenCode-context prompt, so Gemini labeled itself "Auditor: OpenCode").
  Verify by content + mtime, not folder name.
- Missing a finding another auditor has + smaller size → truncated audit.

## Aligned ADD-only instruction template
Send the SAME substance to all auditors. Only platform file paths differ.

**UNIFIED (paste to each auditor):**
> Post-Audit Addition — <Pattern X>. Discovered <date> via runtime analysis.
> Transparent info direct from system (sound, not speculative).
> Task: ADD this to your existing audit. Do NOT modify existing content/version.
> Keep all original findings intact.
> Placement: new finding (next ID) in findings file + 1-line cross-ref in
> system-context file. End-result: your audit contains <Pattern X>, consistent
> with the other auditors.

**Platform specifics (aligned, end-result identical):**
- Auditor A (root `audit-01/02/03.md`): already has F-22 → upgrade severity
  + append post-audit note. Don't rewrite F-22 body.
- Auditor B (`other-audit/`): missed it → ADD new finding. Don't modify existing.
- Auditor C (`third-audit/`): already included → confirm match, label as
  system-info. If partial, ADD missing details.

**Alignment check (end-result must be identical):**
- [ ] A: F-22 upgraded + post-audit note
- [ ] B: new finding added
- [ ] C: confirmed/consistent, labeled system-info
- [ ] All: NO existing content modified, only appended

## Contamination rule
Never create deliverable .md inside the audit folder (e.g. `mjay/audits/`).
Auditors auto-read it → breaks independence. Provide in chat response + send
isolated .md via MEDIA from `/tmp`.
