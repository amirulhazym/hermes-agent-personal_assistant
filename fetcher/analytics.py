"""Analytics DB — extended telemetry storage for self-optimization.

Stores per-fetch metadata: tool, latency, success, cache, retry, fallback,
response size, extraction/normalization duration. Feeds Domain Memory and Router.
"""
import sqlite3
import json
import os
import time
from typing import Optional


class AnalyticsDB:
    def __init__(self, path: str = "~/.hermes/fetcher/analytics.db"):
        self.path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS fetches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                executor TEXT,
                success INTEGER,
                latency REAL,
                ts REAL,
                response_size INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                fallback_count INTEGER DEFAULT 0,
                cache_hit INTEGER DEFAULT 0,
                proxy_used TEXT DEFAULT '',
                browser_profile TEXT DEFAULT '',
                extraction_ms REAL DEFAULT 0,
                normalization_ms REAL DEFAULT 0,
                error TEXT DEFAULT '',
                memory_mb REAL DEFAULT 0,
                cpu_pct REAL DEFAULT 0,
                cost_estimate REAL DEFAULT 0
            )"""
        )
        self.conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_fetches_domain_executor
               ON fetches(domain, executor)"""
        )
        self.conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_fetches_ts ON fetches(ts)"""
        )
        self.conn.commit()

    def log(
        self,
        domain: str,
        executor: str,
        success: bool,
        latency: float,
        response_size: int = 0,
        retry_count: int = 0,
        fallback_count: int = 0,
        cache_hit: bool = False,
        proxy_used: str = "",
        browser_profile: str = "",
        extraction_ms: float = 0,
        normalization_ms: float = 0,
        error: str = "",
        memory_mb: float = 0,
        cpu_pct: float = 0,
        cost_estimate: float = 0,
    ):
        self.conn.execute(
            """INSERT INTO fetches
               (domain, executor, success, latency, ts, response_size,
                retry_count, fallback_count, cache_hit, proxy_used,
                browser_profile, extraction_ms, normalization_ms, error,
                memory_mb, cpu_pct, cost_estimate)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                domain, executor, 1 if success else 0, latency, time.time(),
                response_size, retry_count, fallback_count,
                1 if cache_hit else 0, proxy_used, browser_profile,
                extraction_ms, normalization_ms, error,
                memory_mb, cpu_pct, cost_estimate,
            ),
        )
        self.conn.commit()

    def get_stats(self, domain: str = None, executor: str = None, window: int = 100) -> dict:
        """Return aggregate stats for domain/executor over recent window."""
        if domain and executor:
            cur = self.conn.execute(
                """SELECT COUNT(*), SUM(success), AVG(latency), AVG(response_size)
                   FROM (SELECT * FROM fetches
                         WHERE domain=? AND executor=?
                         ORDER BY ts DESC LIMIT ?)""",
                (domain, executor, window),
            )
        elif domain:
            cur = self.conn.execute(
                """SELECT COUNT(*), SUM(success), AVG(latency), AVG(response_size)
                   FROM (SELECT * FROM fetches
                         WHERE domain=? ORDER BY ts DESC LIMIT ?)""",
                (domain, window),
            )
        elif executor:
            cur = self.conn.execute(
                """SELECT COUNT(*), SUM(success), AVG(latency), AVG(response_size)
                   FROM (SELECT * FROM fetches
                         WHERE executor=? ORDER BY ts DESC LIMIT ?)""",
                (executor, window),
            )
        else:
            cur = self.conn.execute(
                """SELECT COUNT(*), SUM(success), AVG(latency), AVG(response_size)
                   FROM (SELECT * FROM fetches ORDER BY ts DESC LIMIT ?)""",
                (window,),
            )
        row = cur.fetchone()
        if row and row[0]:
            return {
                "total": row[0],
                "success": int(row[1] or 0),
                "avg_latency": round(row[2] or 0, 3),
                "avg_response_size": int(row[3] or 0),
                "success_rate": round((row[1] or 0) / row[0], 3),
            }
        return {}

    def get_best_executor(self, domain: str) -> Optional[str]:
        """Return executor with highest success rate for domain (min 3 tries)."""
        cur = self.conn.execute(
            """SELECT executor, SUM(success) as s, COUNT(*) as total
               FROM fetches WHERE domain=?
               GROUP BY executor HAVING total >= 3
               ORDER BY s DESC, total DESC LIMIT 1""",
            (domain,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def close(self):
        self.conn.close()
