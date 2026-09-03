"""Domain Memory — behavioral learning per domain.

NOT just statistics. Stores:
  - best_executor (from analytics + manual override)
  - avg_latency
  - last_success_ts
  - common_failures (list of observed failure patterns)
  - best_extraction_strategy
  - recommended_cache_ttl
  - login_frequency (if site requires auth)
  - rate_limit_pattern (observed throttling)

Router consults Domain Memory before Capability Registry fallback.
"""
import json
import sqlite3
import os
import time
from typing import Optional


class DomainMemory:
    def __init__(self, path: str = "~/.hermes/fetcher/domain_memory.db"):
        self.path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS memory (
                domain TEXT PRIMARY KEY,
                best_executor TEXT,
                avg_latency REAL DEFAULT 0,
                last_success_ts REAL DEFAULT 0,
                common_failures TEXT DEFAULT '[]',
                best_extraction_strategy TEXT DEFAULT '',
                cache_ttl INTEGER DEFAULT 3600,
                login_frequency INTEGER DEFAULT 0,
                rate_limit_pattern TEXT DEFAULT '',
                observed_rate_limit REAL DEFAULT 0,
                first_seen REAL DEFAULT (strftime('%s','now')),
                last_seen REAL DEFAULT (strftime('%s','now')),
                total_requests INTEGER DEFAULT 0
            )"""
        )
        self.conn.commit()

    def record(self, domain: str, executor: str, success: bool,
               latency: float, failures: list = None, cache_ttl: int = 3600):
        """Record a fetch outcome for a domain."""
        existing = self.conn.execute(
            "SELECT * FROM memory WHERE domain=?", (domain,)
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE memory SET
                    last_seen=strftime('%%s','now'),
                    total_requests=total_requests+1,
                    avg_latency=(avg_latency * (total_requests-1) + ?) / total_requests,
                    last_success_ts=CASE WHEN ? THEN strftime('%%s','now') ELSE last_success_ts END,
                    cache_ttl=?,
                    common_failures=?
                 WHERE domain=?""",
                (latency, success, cache_ttl,
                 json.dumps(failures or []), domain),
            )
        else:
            self.conn.execute(
                """INSERT INTO memory
                   (domain, best_executor, avg_latency, last_success_ts,
                    common_failures, cache_ttl, total_requests)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (domain, executor, latency,
                 time.time() if success else 0,
                 json.dumps(failures or []), cache_ttl),
            )

        # Update best executor based on success
        if success:
            self.conn.execute(
                "UPDATE memory SET best_executor=? WHERE domain=? AND (best_executor IS NULL OR best_executor='')",
                (executor, domain),
            )
        self.conn.commit()

    def get(self, domain: str) -> Optional[dict]:
        cur = self.conn.execute("SELECT * FROM memory WHERE domain=?", (domain,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "best_executor": row[1],
            "avg_latency": row[2],
            "last_success_ts": row[3],
            "common_failures": json.loads(row[4]) if row[4] else [],
            "cache_ttl": row[6],
            "observed_rate_limit": row[9],
            "total_requests": row[12],
        }

    def set_cache_ttl(self, domain: str, ttl: int):
        self.conn.execute("UPDATE memory SET cache_ttl=? WHERE domain=?", (ttl, domain))
        self.conn.commit()

    def close(self):
        self.conn.close()
