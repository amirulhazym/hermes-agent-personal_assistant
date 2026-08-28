# Recovery Runbook → Google Doc Delivery Pattern

Use this reference when documenting deleted temporary artifacts before an upgrade, migration, cleanup, or deployment.

## Required evidence model

Keep these statuses separate:

```text
DOCUMENT-PASS
ARTIFACT-PRESENT
DOWNLOAD-PASS
HASH-PASS
LIST-PASS
DECRYPT-PASS
RESTORE-PASS
LIVE-SMOKE-PASS
```

A document can be `DOCUMENT-PASS` while the project remains blocked and the restore remains untested.

## Archive-to-path mapping

An archive filename or top-level directory is not proof of the original deleted filesystem path. To document a recovery mapping:

1. Record the exact Drive file ID, local download path, size, SHA-256, archive root, and regular-file/symlink member count.
2. Normalize archive member paths by removing only the archive root.
3. Compare path sets and content hashes between related archives.
4. Label the result `INFERENCE / recovery mapping` unless an original manifest or byte-level identity record proves the old path.
5. Keep `archive-equivalent reconstruction` separate from `original-folder byte-identical restore`.

## Safe restore command pattern

Always stage outside live first:

```bash
set -eu
ARCHIVE=/tmp/recovery-input.tar.gz
TARGET=/tmp/recovery-staging-$(date +%Y%m%d-%H%M%S)
mkdir -p "$TARGET"

python3 - "$ARCHIVE" <<'PY'
import sys, tarfile
from pathlib import PurePosixPath
with tarfile.open(sys.argv[1], 'r:gz') as tf:
    bad = []
    for m in tf.getmembers():
        p = PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts:
            bad.append(m.name)
    if bad:
        print('\n'.join(bad))
        raise SystemExit(2)
print('ARCHIVE_MEMBERS_SAFE')
PY

tar --no-same-owner -xzf "$ARCHIVE" -C "$TARGET"
printf 'STAGED_RESTORE=%s\n' "$TARGET"
```

Only after inspection may an exact old temporary target be reconstructed, and the command must refuse an existing target rather than overwrite it.

## Google Docs delivery gate

After Markdown is written:

```text
md2ops.py → format_doc_v2.py → verify_doc.py
```

Then verify the Google container separately:

- document ID;
- title;
- MIME type `application/vnd.google-apps.document`;
- exact Drive parent ID;
- owner-only permissions;
- source/provenance marker re-read from Docs API;
- final `verify_doc.py` verdict and defects array.

If the wrapper lacks a `drive move` action, the direct Drive API fallback is:

```python
service.files().update(
    fileId=document_id,
    addParents=destination_folder_id,
    removeParents=','.join(old_parent_ids),
    fields='id,name,parents,mimeType,webViewLink,permissions(type,role,emailAddress)',
).execute()
```

The fallback is not complete until the resulting parent and permissions are read back.

## C1 heading gate

`verify_doc.py` C1 flags a heading with no body paragraph before the next heading. If a section is a structural divider followed immediately by a subsection, add one plain introductory sentence. Rerun the full render and verify pipeline; do not call the first FAIL a successful document.

## Operational boundary

Creating and verifying the runbook does not authorize the update, deployment, service restart, WhatsApp change, or live restore. End the owner-facing status with one exact next action and one explicit approval sentence when the operational gate remains blocked.
