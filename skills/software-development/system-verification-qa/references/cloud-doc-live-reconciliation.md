# Cloud Documentation vs Live Runtime Reconciliation

Use this reference when an audit must compare authenticated Google Docs/Drive material with a live Hermes runtime, local candidate source, or recovery bundle.

## Authority model

Keep these roles separate throughout the report:

- **Live runtime:** strongest evidence for what is configured/loaded now. Direct read-back can prove current state; it cannot prove why a file was written.
- **Google Doc / runbook:** historical intent, design contract, or recovery procedure. A document never upgrades a live claim by itself.
- **Candidate source / local Git ref:** implementation content on that ref. It is not deployed state.
- **Remote Git ref:** pushed lineage only. It is not deployment proof.
- **Drive recovery artifact:** preservation/recovery evidence. It is not automatically complete source closure and is not authorization.
- **User’s latest literal correction:** current conversational evidence for what the user is saying now. It is not proof that the runtime ingested or logged it.

Use explicit labels: `LIVE-VERIFIED`, `LOCAL-VERIFIED`, `REMOTE-VERIFIED`, `DOC-INTENT`, `HISTORICAL`, `CANDIDATE`, `UNVERIFIED`, `DATA GAP`.

## Procedure

1. **Define scope and write boundary.** State whether the task is read-only. Do not deploy, restart, resolve a hold, edit runtime state, or modify Drive content unless separately authorized.
2. **Authenticate through the configured Google Workspace path.** A token refresh may touch local OAuth metadata; disclose that side effect separately from Drive/Docs content writes.
3. **Export the supplied Google Docs directly.** Prefer full text export over browser preview. Record document ID, title, MIME type, modified time, export path, byte count, and hash.
4. **Enumerate the exact Drive folder.** Query children with the folder’s `parents` relation and `trashed=false`; do not infer contents from a search hit. Record each child’s ID, MIME type, size, and modified time.
5. **Select necessary artifacts from the documentation.** Read runbooks/manifests first. For large snapshots or tarballs, inspect metadata and the relevant small manifests before downloading gigabytes. Do not claim archive members unless listing/extraction actually returns usable output.
6. **Hash-check small preservation files.** When a checksum manifest exists, compare every downloaded support file against its listed SHA-256. Report large payload hashes as unverified if the payload was not downloaded.
7. **Compare five layers:** document claim → live config/state → live consuming code → candidate/Git content → end-to-end/runtime output. A design statement and a passing candidate test do not prove live behavior.
8. **Trace provenance separately from behavior.** If a live file is ignored/untracked and has no writer audit, say the current value is proven but its origin is a `DATA GAP`. Do not attribute it to a merge/rebase merely because the dates are close.
9. **Use a claim matrix.** For each important claim record: exact claim, source quote/path, current evidence, contradiction, status (`RESOLVED`, `PARTIAL`, `UNRESOLVED`, `UNVERIFIED`), and missing boundary.
10. **For stateful records, preserve literal user corrections.** If the user corrects `12:43` to `12:44`, use the latest literal in the report and do not ask the same question again. Separately run a read-only resolver and state check; distinguish conversational evidence from a live write. Never silently overwrite the earlier source event.
11. **Package non-trivial research deterministically.** Use the Stage 6 writer with the full pipeline payload, include failed/blocked extraction attempts in `stage_log`, verify returned artifact and trace paths, then hash/stat the final report.

## Failure boundaries and wording

- `configured value` ≠ `clinical/owner-authorized rule`.
- `candidate fix exists` ≠ `live fix loaded`.
- `local commit exists` ≠ `pushed` ≠ `deployed` ≠ `live`.
- `folder contains a recovery archive` ≠ `archive contains the required path` unless the archive is actually listed/extracted.
- `document says implemented` ≠ `implementation currently works`.
- `read-only resolver maps a drug/time` ≠ `medication status was written`.
- `pending` or `HOLD` from a broken live path is evidence of system state, not evidence that the user’s intake did not happen.

Use wording such as:

> `LIVE CONFIGURED LEGACY VALUE — NOT VERIFIED CLINICAL RULE`

> `Candidate/design aligned; live runtime not aligned`

> `Current content RESOLVED; writer/provenance UNVERIFIED`

> `Extraction blocked; no archive-content claim made`

## Reusable report structure

1. Direct verdict
2. Scope and read/write boundary
3. Source inventory and evidence tiers
4. Document-by-document comparison
5. Live runtime/code read-back
6. Git/merge/rebase provenance
7. Claim matrix
8. Root-cause chain
9. User-state correction versus runtime-state status
10. Unverified gaps and blocked attempts
11. Artifact hash/path
12. Clickable source URLs

## Pitfalls captured from prior audits

- Do not turn a legacy JSON reminder window into a medical rule just because the safety gate consumes it.
- Do not use a recovery runbook as release authorization.
- Do not treat a preservation manifest that omits private/runtime JSON as proof that the JSON was merged or preserved.
- Do not retry a blocked archive extraction merely to make the report look complete; record the boundary and avoid claims about its contents.
- Do not repeatedly ask for an exact medication time the user already corrected. Acknowledge the latest value, resolve it read-only, and report whether the live state actually contains it.
- Disclose OAuth-token metadata refreshes and local report writes, while clearly stating whether live application/Drive content changed.
