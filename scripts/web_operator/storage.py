from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class StateStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks(
                  task_id TEXT PRIMARY KEY,
                  owner_id TEXT NOT NULL,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals(
                  approval_id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  owner_id TEXT NOT NULL,
                  binding_digest TEXT NOT NULL,
                  state TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  consumed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS nonces(
                  nonce TEXT PRIMARY KEY,
                  scope TEXT NOT NULL,
                  expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices(
                  device_id TEXT PRIMARY KEY,
                  public_key BLOB NOT NULL,
                  fingerprint TEXT NOT NULL,
                  revoked_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions(
                  identity_digest TEXT PRIMARY KEY,
                  metadata_json TEXT NOT NULL,
                  expires_at TEXT,
                  revoked_at TEXT
                );
                """
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_task(self, task_id: str, owner_id: str, state: str) -> None:
        now = _utc_now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO tasks(task_id, owner_id, state, created_at, updated_at) VALUES (?,?,?,?,?)",
                (task_id, owner_id, state, now, now),
            )

    def update_task(self, task_id: str, state: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE tasks SET state=?, updated_at=? WHERE task_id=?",
                (state, _utc_now(), task_id),
            )

    def get_task(self, task_id: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()

    def record_nonce(self, nonce: str, scope: str, expires_at: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO nonces(nonce, scope, expires_at) VALUES (?,?,?)",
                (nonce, scope, expires_at),
            )

    def nonce_seen(self, nonce: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM nonces WHERE nonce=?", (nonce,)
            ).fetchone()
            return row is not None
