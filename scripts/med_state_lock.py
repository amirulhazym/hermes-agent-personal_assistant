"""Shared cooperative file lock for medication state readers/writers.

All medication state/supply mutations must use exclusive_state_lock(). Nested
calls in same thread are re-entrant. The lock is advisory: every participating
writer must import this module.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

_LOCAL = threading.local()


def locked_mutation(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with exclusive_state_lock():
            return fn(*args, **kwargs)
    return wrapped


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


@contextmanager
def exclusive_state_lock():
    depth = getattr(_LOCAL, "depth", 0)
    if depth:
        _LOCAL.depth = depth + 1
        try:
            yield
        finally:
            _LOCAL.depth -= 1
        return

    path = _home() / ".med-confirm.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _LOCAL.depth = 1
        try:
            yield
        finally:
            _LOCAL.depth = 0
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
