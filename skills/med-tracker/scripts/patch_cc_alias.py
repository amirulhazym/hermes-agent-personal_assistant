#!/usr/bin/env python3
"""
Patch med_resolve.py to add CC alias.
Run once: python3 /tmp/patch_cc_alias.py

Adds 'cc' alias to ALIASES dict in ~/.hermes/scripts/med_resolve.py
so that med_resolve.py CC --time 13:00 resolves to calcium instead of UNKNOWN.
"""
import re
from pathlib import Path

TARGET = Path.home() / ".hermes" / "scripts" / "med_resolve.py"
ALIAS_BLOCK = '''    # Compound shorthands
    "cc": "calcium",  # CC = Calcium + Calcitriol (compound). Agent must ALSO confirm calcitriol.
    # PRN (as needed)
    "panto": "pantoprazole",'''

OLD_BLOCK = '''    # PRN (as needed)
    "panto": "pantoprazole",'''

def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    content = TARGET.read_text()

    if '"cc": "calcium"' in content:
        print("Already patched — CC alias exists")
        return 0

    if OLD_BLOCK not in content:
        print("ERROR: Could not find insertion point in med_resolve.py")
        print("Expected PRN comment block not found — file may have changed")
        return 1

    new_content = content.replace(OLD_BLOCK, ALIAS_BLOCK)
    TARGET.write_text(new_content)
    print(f"SUCCESS: Added CC alias to {TARGET}")
    print("Verify: python3 med_resolve.py cc --time 13:00 --slot C")
    return 0

if __name__ == "__main__":
    exit(main())
