#!/usr/bin/env bash
# Source-controlled bootstrap for a NEW / inactive RDC installation.
# Intentionally does not stop/start/restart or enable any systemd service.
set -euo pipefail
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET=/home/ubuntu/.local/share/chatgpt-rdc/0.2.51

if [ "${1:---check}" = --check ]; then
  node -e 'const p=require(process.argv[1]); if(p.dependencies["@wonderwhy-er/desktop-commander"]!=="0.2.51") process.exit(1)' "$SOURCE_DIR/package.json"
  node -e 'const p=require(process.argv[1]); if(p.packages["node_modules/@wonderwhy-er/desktop-commander"].version!=="0.2.51") process.exit(1)' "$SOURCE_DIR/package-lock.json"
  echo "RDC package manifest and lockfile verified (0.2.51). No changes made."
  exit 0
fi
if [ "${1:---check}" != --install ] || [ "$(id -un)" != ubuntu ]; then
  echo "Usage: $0 --check|--install (run --install as ubuntu)" >&2
  exit 2
fi
if systemctl --user is-active --quiet chatgpt-rdc.service; then
  echo "Refusing install while live RDC is running." >&2
  exit 3
fi
if [ -e "$TARGET/node_modules" ]; then
  echo "Refusing to overwrite an existing RDC runtime: $TARGET" >&2
  exit 4
fi
install -d -m 755 "$TARGET"
install -m 644 "$SOURCE_DIR/package.json" "$TARGET/package.json"
install -m 644 "$SOURCE_DIR/package-lock.json" "$TARGET/package-lock.json"
npm ci --prefix "$TARGET" --no-audit --no-fund
node -e 'const p=require(process.argv[1]); if(p.version!=="0.2.51") process.exit(5)' "$TARGET/node_modules/@wonderwhy-er/desktop-commander/package.json"
echo "Pinned runtime installed. Service installation/activation is a SEPARATE approval."
