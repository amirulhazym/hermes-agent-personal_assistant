"""Cookie & Session Store — persists cf_clearance, session, JWT, ETag across requests.

Goal: solve Cloudflare / auth ONCE, reuse until expiry. Avoids re-solving on
every request (major efficiency win for Fragrantica, Parfumo, etc.).
"""
import sqlite3
import json
import time
import os
from urllib.parse import urlparse


class CookieStore:
    def __init__(self, path: str = "~/.hermes/fetcher/cookies.db"):
        self.path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS cookies (
                domain TEXT,
                name TEXT,
                value TEXT,
                expiry REAL,
                meta TEXT,
                PRIMARY KEY (domain, name)
            )"""
        )
        self.conn.commit()

    def save(self, domain: str, cookies: list):
        """cookies: list of dicts with keys name, value, expiry(optional), meta(optional)."""
        now = time.time()
        for c in cookies:
            expiry = c.get("expiry", now + 86400)
            self.conn.execute(
                "INSERT OR REPLACE INTO cookies (domain, name, value, expiry, meta) VALUES (?,?,?,?,?)",
                (domain, c["name"], str(c["value"]), expiry, json.dumps(c.get("meta", {}))),
            )
        self.conn.commit()

    def get(self, domain: str) -> list:
        cur = self.conn.execute(
            "SELECT name, value, expiry, meta FROM cookies WHERE domain=? AND expiry>?",
            (domain, time.time()),
        )
        return [
            {"name": r[0], "value": r[1], "expiry": r[2], "meta": json.loads(r[3])}
            for r in cur.fetchall()
        ]

    def get_valid(self, domain: str) -> dict:
        """Returns {name: value} for fresh cookies — directly usable in requests."""
        return {c["name"]: c["value"] for c in self.get(domain)}

    def is_fresh(self, domain: str, name: str) -> bool:
        cur = self.conn.execute(
            "SELECT expiry FROM cookies WHERE domain=? AND name=? AND expiry>?",
            (domain, name, time.time()),
        )
        return cur.fetchone() is not None

    def purge(self, domain: str = None):
        if domain:
            self.conn.execute("DELETE FROM cookies WHERE domain=?", (domain,))
        else:
            self.conn.execute("DELETE FROM cookies")
        self.conn.commit()

    def close(self):
        self.conn.close()
