"""Content Cache — stores markdown + JSON + screenshots + metadata per URL.

Uses ETag/Last-Modified validation. On cache hit, returns full Document data
without re-fetching. Stores everything Crawl4AI generates — markdown,
structured data, screenshots, metadata — not just raw HTML.
"""
import json
import os
import sqlite3
import time
from typing import Optional
from urllib.parse import urlparse
from fetcher.base import Document


class ContentCache:
    def __init__(self, path: str = "~/.hermes/fetcher/cache.db"):
        self.path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT,
                executor_cache_buster TEXT,
                ts REAL,
                ttl INTEGER,
                etag TEXT,
                last_modified TEXT,
                status_code INTEGER,
                metadata TEXT,
                has_header INTEGER DEFAULT 0
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS content_cache (
                url_hash TEXT PRIMARY KEY,
                raw_html TEXT,
                markdown TEXT,
                structured_data TEXT,
                screenshots TEXT,
                links TEXT,
                images TEXT
            )"""
        )
        self.conn.commit()

    def get(self, url: str) -> Optional[dict]:
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cur = self.conn.execute(
            "SELECT * FROM cache WHERE url_hash=? AND ts+ttl > ?",
            (url_hash, time.time()),
        )
        row = cur.fetchone()
        if not row:
            return None
        # Fetch content
        cur2 = self.conn.execute(
            "SELECT * FROM content_cache WHERE url_hash=?", (url_hash,)
        )
        content_row = cur2.fetchone()
        return {
            "etag": row[4],
            "last_modified": row[5],
            "status_code": row[6],
            "metadata": json.loads(row[7]) if row[7] else {},
            "raw_html": content_row[1] if content_row else None,
            "markdown": content_row[2] if content_row else None,
            "structured_data": json.loads(content_row[3]) if content_row and content_row[3] else None,
        }

    def set(self, url: str, doc: Document, ttl: int, etag: str = None, last_modified: str = None):
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.conn.execute(
            """INSERT OR REPLACE INTO cache
               (url_hash, url, ts, ttl, etag, last_modified, status_code, metadata)
               VALUES (?,?,?,?,?,?,?,?)""",
            (url_hash, url, time.time(), ttl, etag or "", last_modified or "",
             doc.raw_response.get("status") if doc.raw_response else 0,
             json.dumps({
                 "verification_status": doc.verification_status,
                 "confidence": doc.confidence,
                 "executor": doc.executor,
             })),
        )
        self.conn.execute(
            """INSERT OR REPLACE INTO content_cache
               (url_hash, raw_html, markdown, structured_data, screenshots, links, images)
               VALUES (?,?,?,?,?,?,?)""",
            (url_hash, doc.content, doc.markdown,
             json.dumps(doc.structured_data) if doc.structured_data else None,
             json.dumps(doc.screenshots) if doc.screenshots else None,
             json.dumps(doc.links) if doc.links else None,
             json.dumps(doc.images) if doc.images else None),
        )
        self.conn.commit()

    def invalidate(self, url: str):
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.conn.execute("DELETE FROM cache WHERE url_hash=?", (url_hash,))
        self.conn.execute("DELETE FROM content_cache WHERE url_hash=?", (url_hash,))
        self.conn.commit()

    def close(self):
        self.conn.close()
