#!/usr/bin/env python3
"""Read-only diagnostic for NULL session_key rows in Hermes state.db.

Usage:
    python3 diagnose_null_keys.py <path-to-state.db> [cutoff-date YYYY-MM-DD]

Reports:
  - totals (sessions, messages, db size)
  - NULL session_key rows split by source and pre/post cutoff
  - per proven chat-lane: orphaned ancestor count

Proven chat-lane keys are gathered from BOTH:
  - ~/.hermes/sessions/sessions.json  (gateway routing mirror)
  - gateway_routing table (if present)

No writes. Safe to run on the live DB (opened read-only).
"""
import sqlite3
import sys
import os
import json

DEFAULT_CUTOFF = "2026-08-11"


def main():
    if len(sys.argv) < 2:
        print("Usage: diagnose_null_keys.py <state.db> [cutoff-date]")
        sys.exit(1)
    db_path = sys.argv[1]
    cutoff = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CUTOFF
    if not os.path.exists(db_path):
        print(f"ERROR: {db_path} not found")
        sys.exit(1)

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def cnt(sql, params=()):
        return cur.execute(sql, params).fetchone()[0]

    print(f"=== DB: {db_path} (cutoff={cutoff}) ===")
    print(f"  sessions total:   {cnt('SELECT COUNT(*) FROM sessions')}")
    print(f"  messages total:   {cnt('SELECT COUNT(*) FROM messages')}")
    print(f"  db size on disk:  {os.path.getsize(db_path)/1048576:.1f} MB")
    print()

    for src in ("telegram", "whatsapp"):
        older = cnt(
            "SELECT COUNT(*) FROM sessions WHERE session_key IS NULL AND source=? "
            "AND datetime(started_at,'unixepoch') < ?",
            (src, cutoff),
        )
        newer = cnt(
            "SELECT COUNT(*) FROM sessions WHERE session_key IS NULL AND source=? "
            "AND datetime(started_at,'unixepoch') >= ?",
            (src, cutoff),
        )
        print(f"  NULL {src}: older(<{cutoff})={older}  newer(>={cutoff})={newer}")
    print()

    # proven keys from sessions.json mirror
    proven = set()
    sj_path = os.path.join(os.path.dirname(db_path), "sessions", "sessions.json")
    if os.path.exists(sj_path):
        try:
            sj = json.load(open(sj_path))
            for k in sj:
                if k.startswith("agent:"):
                    proven.add(k)
        except Exception:
            pass
    # proven keys from gateway_routing
    try:
        for r in cur.execute("SELECT DISTINCT session_key FROM gateway_routing WHERE session_key IS NOT NULL"):
            proven.add(r["session_key"])
    except Exception:
        pass
    print(f"=== Proven chat-lane keys ({len(proven)}) ===")
    for k in sorted(proven):
        print(f"  {k}")
    print()

    children = {}
    for r in cur.execute("SELECT id, parent_session_id FROM sessions WHERE parent_session_id IS NOT NULL"):
        children.setdefault(r["parent_session_id"], []).append(r["id"])

    def walk(sid):
        chain = [sid]
        seen = set()
        while True:
            if sid in seen:
                break
            seen.add(sid)
            r = cur.execute("SELECT parent_session_id FROM sessions WHERE id=?", (sid,)).fetchone()
            if not r or r["parent_session_id"] is None:
                break
            sid = r["parent_session_id"]
            chain.append(sid)
        return chain

    print("=== Per proven DM/group key: orphaned ancestor rows ===")
    for key in sorted(proven):
        r = cur.execute(
            "SELECT id FROM sessions WHERE session_key=? ORDER BY started_at DESC LIMIT 1", (key,)
        ).fetchone()
        if not r:
            print(f"  {key}: no keyed row found")
            continue
        chain = walk(r["id"])
        orphans = [
            sid
            for sid in chain
            if cur.execute("SELECT session_key FROM sessions WHERE id=?", (sid,)).fetchone()["session_key"] is None
        ]
        print(f"  {key}\n     chain={len(chain)}  orphaned_NULL_rows={len(orphans)}")

    con.close()


if __name__ == "__main__":
    main()
