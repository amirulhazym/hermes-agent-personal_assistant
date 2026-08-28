# Current Working-Tree Checkpoint and Overlay Cleanup

Use this procedure when a live/nested repository has dirty state and temporary overlays may later be deleted. It preserves current bytes without implying public-source closure, release readiness, or independent disaster recovery.

## 1. Pin the snapshot boundary

```bash
ROOT=/path/to/repo
OUT=/path/to/private/checkpoint-YYYYMMDD_HHMMSS
mkdir -m 700 "$OUT"

TS=$(date '+%Y-%m-%d %H:%M:%S %z')
git -C "$ROOT" rev-parse HEAD > "$OUT/HEAD"
git -C "$ROOT" branch --show-current > "$OUT/BRANCH"
git -C "$ROOT" rev-parse --git-dir > "$OUT/GIT_DIR"
git -C "$ROOT" rev-parse --git-common-dir > "$OUT/GIT_COMMON_DIR"
git -C "$ROOT" status --porcelain=v2 --untracked-files=all > "$OUT/status.porcelain-v2"
```

Record the exact status mode and separate:

- tracked modified/staged records;
- untracked records (`? `);
- ignored records (`! `).

Never infer path deltas from counts.

## 2. Capture only the approved current scope

Tracked modifications:

```bash
git -C "$ROOT" diff --binary > "$OUT/dirty.patch"
```

Non-ignored untracked files:

```bash
git -C "$ROOT" ls-files --others --exclude-standard -z > "$OUT/untracked.paths"
tar -czf "$OUT/untracked.tar.gz" \
  -C "$ROOT" --null --verbatim-files-from \
  --files-from="$OUT/untracked.paths"
```

Do not include ignored files in this archive unless their individual classification proves that they are source-worthy or required runtime recovery material.

Create a per-record manifest containing:

```text
path | regular/symlink/directory | mode | lstat size | SHA-256
```

For symlinks, hash the link target as metadata rather than dereferencing arbitrary paths. Hash the patch, archive, status, path list, and manifest in a separate checksum file. Keep raw contents out of chat output.

## 3. At-rest handling

Preferred order:

1. encrypted private archive;
2. encrypted off-device copy with independently verified SHA-256;
3. if that is unavailable and immediate destructive cleanup is otherwise blocked, owner-only same-device checkpoint (`0700` directory, `0600` artifacts) with an explicit `SAME-DEVICE-ONLY` limitation.

The third option is a preservation barrier, not an independent backup. Do not call it immutable, encrypted, off-device, or disaster-recovery-proven without direct evidence.

## 4. Stability and verification gate

After capture, run the same HEAD and complete porcelain commands again. The checkpoint is stable only when:

```text
post HEAD == pre HEAD
post porcelain bytes == pre porcelain bytes
```

Then verify all of the following:

```bash
sha256sum -c "$OUT/SHA256SUMS"
tar -tzf "$OUT/untracked.tar.gz" >/dev/null
```

Also verify:

- archive member set exactly equals the recorded untracked path set;
- manifest paths are unique and have the expected count;
- current hashes match manifest hashes;
- source status remains unchanged;
- artifact permissions are restrictive;
- no service/runtime mutation was caused by the capture.

A changing status produces an `INCONSISTENT` checkpoint. Do not round it up to a valid snapshot.

## 5. Classify ignored records without wholesale archiving

Use:

```bash
git -C "$ROOT" status --porcelain=v2 --ignored=matching --untracked-files=all
```

Parse only lines beginning with `! `. Do not include `? ` rows in the ignored count.

For each ignored path:

```bash
git -C "$ROOT" check-ignore -v -- "$path"
du -s --bytes -- "$ROOT/$path"
du -s --apparent-size --bytes -- "$ROOT/$path"
```

The `git check-ignore -v` output is tab-separated as:

```text
source:line:pattern<TAB>matched-path
```

Parse the first field with a maximum-two-colon split. Store rule source, line, pattern, type, mode, lstat size, allocated bytes, apparent bytes, source-like status, runtime-affecting status, sensitivity, and proposed disposition.

Conservative dispositions:

- generated/cache: do not archive as source;
- dependency/environment: preserve lockfiles/source, not installed bytes;
- build/asset/export: do not archive wholesale;
- private/runtime/sensitive: keep raw bytes private; source representation may need sanitization;
- source-review-required: inspect individually before exclusion;
- unclassified: owner/manual review, not automatic deletion.

## 6. Overlay deletion package

Before asking for deletion approval, collect per overlay:

- exact path, mtime, apparent bytes, allocated bytes;
- HEAD, branch, git-dir/common-dir, `.git` marker type;
- staged/unstaged diff byte size and SHA-256;
- exact untracked path list and path-list SHA-256;
- common untracked-file content hashes and differing paths;
- ignored path list and rule provenance;
- refs and registered worktree list;
- active process cwd/open-file descriptor hits;
- unique logs, test reports, caches, and sole evidence files;
- hardlink/inode overlap across candidate roots.

A clean overlay is only a cleanup candidate. It is not disposable until unique refs/objects, evidence, ignored material, worktree registrations, process usage, and recoverability have been checked.

## 7. Disk projection

Use one timestamped `df -B1` snapshot and report the displayed value separately from computed ratios. For each candidate, report both apparent and allocated bytes. To avoid double-counting hardlinked data, compare `(st_dev, st_ino)` across all candidate roots before calling bytes reclaimable.

The actual post-deletion `df` result is the final authority. A theoretical projection must never be reported as actual disk relief.
