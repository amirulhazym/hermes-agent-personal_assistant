# Cloud / Drive artifact verification and evidence delivery

Use this reference when a user points to a known Google Drive backup folder and a prior answer says an artifact is missing.

## Classification contract

| Label | Meaning | What may be claimed |
|---|---|---|
| `FOUND — PLAINTEXT STANDALONE` | The requested file is directly readable/downloadable | Attach it; quote size/hash only if directly evidenced |
| `FOUND — ENCRYPTED ARCHIVE` | The backup archive exists, but inner files are encrypted | Prove archive metadata and manifest entry; do not claim inner bytes were read |
| `FOUND — MANIFEST ONLY` | A manifest/README records path, size, hash, or Drive ID | Prove the recorded metadata; do not call it a live/restore proof |
| `MISSING / NOT RETAINED` | Not in the authoritative source and no retained local artifact | Say so plainly; do not recreate |
| `NOT IN CHECKED PATHS` | Search scope was limited | Never upgrade this to global absence |

## Read-only workflow

1. Preserve the owner's named source as the source-of-truth pointer. If the user says “it is in the Drive backup folder,” check that folder rather than relying only on an earlier local file search.
2. Read the local download record first if available. It often contains the exact Drive folder ID and prior child listing.
3. Query Drive metadata for the exact folder ID. Record `id`, `name`, `parents`, `modifiedTime`, owner, and `webViewLink` without changing permissions or contents.
4. List direct children with an exact parent query. If there are nested folders (for example, a pre-update source folder or Gate 1 folder), list each nested folder separately.
5. Read the preservation `manifest` and `README` before inspecting archive contents. A manifest can prove that a file was backed up without proving that it is available as plaintext.
6. For encrypted archives, report the archive's existence, recorded size/hash/Drive ID, and whether the manifest says decrypt/restore was tested. Do not extract or decrypt merely to make a stronger claim unless explicitly requested and authorized.
7. If an artifact is a source-recovery package, do not describe it as a complete runtime backup unless the package explicitly includes runtime/state paths.
8. For evidence delivery, attach the existing files or provide the exact Drive links. Then list each requested item that remains unavailable with `MISSING / NOT RETAINED`, `FOUND — ENCRYPTED ARCHIVE`, or `NOT IN CHECKED PATHS`.

## Auth and side-effect guard

Under a user instruction such as `READ-ONLY`, `DO NOT REFRESH GOOGLE AUTH`, do not use an auth preflight that may refresh the token. Prefer the already-authenticated read-only API client. If an auth check unexpectedly refreshes the OAuth token, stop repeating it and disclose:

- the command used;
- the exact side effect (`Token refreshed`);
- that no further auth call will be made.

Do not hide this as a harmless check.

## Evidence-delivery shape

Lead with the finding, then attach artifacts:

```text
FOUND — <folder/file>
<exact ID or path>
<what the artifact proves>
<what it does not prove>
MEDIA:/absolute/path/to/existing/artifact

MISSING / NOT RETAINED — <requested raw output>
```

For a reviewer request, prefer the raw manifest, patch, hash list, README, audit log, and state read-back over another prose synthesis. Preserve the distinction between:

- a current live file;
- a dated deployed copy;
- a candidate/source copy;
- a manifest entry;
- an encrypted recovery archive;
- an execution record.
