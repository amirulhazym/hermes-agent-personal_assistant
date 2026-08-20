#!/usr/bin/env python3
"""Resolve a GitHub Actions diff base without accepting an unknown range."""
from __future__ import annotations

import sys

ZERO_SHA = '0' * 40


def resolve_base(before: str, current: str) -> str:
    before = before.strip()
    current = current.strip()
    if not current:
        raise ValueError('current SHA is empty')
    if before == ZERO_SHA:
        return f'{current}^'
    if not before:
        raise ValueError('event before SHA is empty')
    return before


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: ci-base-sha.py BEFORE_SHA CURRENT_SHA', file=sys.stderr)
        return 2
    try:
        print(resolve_base(sys.argv[1], sys.argv[2]))
    except ValueError as exc:
        print(f'CI-BASE ERROR: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())