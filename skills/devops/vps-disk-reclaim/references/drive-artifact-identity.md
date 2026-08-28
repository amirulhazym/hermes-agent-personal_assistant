# Drive artifact identity and deletion gate

Use this reference when a user asks whether KEEP items are already backed up to Google Drive.

## Required classification

For each local path, compare against Drive and assign exactly one status:

- `EXACT COPY VERIFIED` — exact file/package identity proven by size + SHA-256, or directory manifest/path-set hash plus archive round-trip.
- `RECOVERY PACKAGE REPRESENTED` — Drive contains the required recovery components (for example manifest, metadata, encrypted runtime/database artifacts), but it is not a byte-for-byte copy of the local directory.
- `DIFFERENT ARTIFACT FOUND` — Drive has a related name/category or different date, but no identity mapping to the local path. Do not treat it as coverage.
- `NOT PROVEN UPLOADED` — no matching artifact found, or the search was only by generic filename/name contains.

## Evidence sequence

1. Run Drive auth check; auth success proves only credential availability.
2. Search the exact backup parent and relevant child folders with a raw parent query.
3. Search exact/local-derived names, but treat name search as discovery—not identity proof.
4. Retrieve metadata for candidate Drive files: ID, name, parent, owner, size, modified time.
5. Compare local size and SHA-256 against Drive metadata/manifest where applicable.
6. For directories, require a manifest or archive mapping; a folder name alone is insufficient.
7. Separate transfer integrity from recovery usability:
   - upload/presence;
   - owner-only permission;
   - download/hash round-trip;
   - decrypt/list/restore test;
   - restored manifest comparison.
8. Keep local recovery copies until the owner-side restore boundary is complete, unless the owner explicitly approves deletion after the remaining risk is stated.

## Common false equivalences

- A `whatsapp-full-YYYYMMDD` Drive artifact is not automatically the same as a local WhatsApp backup with another date.
- A `gate1` Drive folder containing metadata/evidence/encrypted components may represent the recovery package without being the raw local Gate1 directory.
- A generic search returning no filename match is evidence of `NOT PROVEN`, not absolute proof that no generically renamed upload exists.
- A successful OAuth check or Drive listing never proves an upload occurred.

## Owner-facing output

Answer the direct question first: “Tak, bukan semua.” Then provide a compact per-path table with exact Drive evidence and the remaining proof gap. Do not say “all backed up” when only some artifacts or a recovery package are present.
