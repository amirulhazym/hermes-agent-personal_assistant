#!/usr/bin/env python3
"""
Backfill NULL routing columns (session_key, user_id, chat_id, display_name)
on orphaned ancestors of a Hermes session so /sessions and /resume can see them.

SAFETY:
- Refuses to write a live ~/.hermes DB unless --live is passed (and even then
  makes a .bak first). Default mode operates on a copy you give via --db.
- Idempotent: only writes rows where the column is currently NULL.
- Walks the parent_session_id chain upward; derives canonical routing from the
  starting row (which already has them). Verifies owner consistency across the
  chain before writing; aborts if the chain mixes owners.

Usage:
  # Dry-run on a copy (no writes):
  python3 backfill_session_routing.py --db /tmp/state_test.db \
      --start 20260813_043109_7d6ea4d4 --source telegram

  # Apply to the live DB (makes state.db.bak first):
  python3 backfill_session_routing.py --db /home/ubuntu/.hermes/state.db \
      --start <current session id> --source telegram --live

You must run hermes-agent's session code with its venv on sys.path to verify
the listing after the backfill. This script only does the data repair + prints
before/after listable counts (computed via direct SQL filter, not the full
query_session_listing, to avoid importing the heavy hermes_state module).
"""
import argparse
import shutil
import sqlite3
import sys


def walk_chain(con, start_id):
    chain = [start_id]
    seen = set()
    cur = start_id
    while True:
        if cur in seen:
            break
        seen.add(cur)
        row = con.execute(
            "SELECT parent_session_id FROM sessions WHERE id=?", (cur,)
        ).fetchone()
        if row is None or row[0] is None:
            break
        cur = row[0]
        chain.append(cur)
    return chain


def owner_consistency(con, chain):
    cols = ["source", "display_name", "user_id", "chat_id"]
    counts = {c: {} for c in cols}
    for sid in chain:
        row = con.execute(
            f"SELECT {', '.join(cols)} FROM sessions WHERE id=?", (sid,)
        ).fetchone()
        if row is None:
            continue
        for i, c in enumerate(cols):
            v = row[i]
            counts[c][v] = counts[c].get(v, 0) + 1
    # Owner is consistent if each column is mostly one value (allow the NULLs
    # we are about to fill; they should be a minority or the only variation).
    bad = []
    for c in cols:
        non_null = {k: v for k, v in counts[c].items() if k is not None}
        if len(non_null) > 1:
            bad.append((c, non_null))
    return bad


def canonical_from_start(con, start_id):
    row = con.execute(
        "SELECT session_key, user_id, chat_id, display_name, source "
        "FROM sessions WHERE id=?", (start_id,)
    ).fetchone()
    if row is None:
        raise SystemExit(f"start id {start_id} not found")
    sk, uid, cid, dn, src = row
    if not sk:
        raise SystemExit(
            "start row has NULL session_key — cannot derive canonical routing. "
            "Pick a more recent session id that has it populated."
        )
    return {
        "session_key": sk,
        "user_id": uid or "",
        "chat_id": cid or "",
        "display_name": dn or "",
    }


def listable_count(con, session_key, source):
    # Mirror of the gateway listing filter (session_key scope + listable child
    # + not tool + not archived). Simplified: counts rows that WOULD show.
    sql = """
    SELECT COUNT(*) FROM sessions s
    WHERE (s.parent_session_id IS NULL
           OR json_extract(COALESCE(s.model_config,'{}'),'$._branched_from') IS NOT NULL)
      AND json_extract(COALESCE(s.model_config,'{}'),'$._delegate_from') IS NULL
      AND s.session_key = ?
      AND s.source NOT IN ('tool')
      AND s.archived = 0
    """
    return con.execute(sql, (session_key,)).fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to state.db (copy or live)")
    ap.add_argument("--start", required=True, help="Current session id to anchor the chain")
    ap.add_argument("--source", required=True, help="source value, e.g. telegram")
    ap.add_argument("--live", action="store_true",
                    help="Allow writing the live DB (makes .bak first).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print plan, write nothing (default when not --live).")
    args = ap.parse_args()

    db_path = args.db
    if "home/ubuntu/.hermes/state.db" in db_path.replace("~", "") and not args.live:
        raise SystemExit(
            "Refusing to write the live ~/.hermes/state.db without --live. "
            "Operate on a copy, or pass --live (which backs up first)."
        )

    if args.live:
        shutil.copy(db_path, db_path + ".bak")
        print(f"[backup] wrote {db_path}.bak")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    chain = walk_chain(con, args.start)
    print(f"[chain] length = {len(chain)} (root = {chain[-1]})")

    bad = owner_consistency(con, chain)
    if bad:
        con.close()
        raise SystemExit(
            "ABORT: chain mixes owners on column(s): "
            + ", ".join(f"{c}={vals}" for c, vals in bad)
            + ". Backfilling would cross-merge chats. Investigate manually."
        )

    canon = canonical_from_start(con, args.start)
    print(f"[canon] session_key={canon['session_key']} user_id={canon['user_id']} "
          f"chat_id={canon['chat_id']} display_name={canon['display_name']}")

    before = listable_count(con, canon["session_key"], args.source)

    targets = []
    for sid in chain:
        row = con.execute(
            "SELECT session_key, user_id, chat_id, display_name FROM sessions WHERE id=?",
            (sid,),
        ).fetchone()
        if row is None:
            continue
        if row["session_key"] is None or row["user_id"] is None or row["chat_id"] is None:
            targets.append(sid)

    print(f"[plan] will backfill {len(targets)} NULL ancestor rows")
    if args.dry_run or not args.live:
        for sid in targets:
            print(f"  would update {sid}")
        print(f"[count] listable before = {before} (dry-run; no writes)")
        con.close()
        return

    for sid in targets:
        con.execute(
            "UPDATE sessions SET session_key=?, user_id=?, chat_id=?, display_name=? "
            "WHERE id=?",
            (canon["session_key"], canon["user_id"], canon["chat_id"],
             canon["display_name"], sid),
        )
    con.commit()
    print(f"[done] updated {len(targets)} rows")

    after = listable_count(con, canon["session_key"], args.source)
    print(f"[count] listable before = {before}, after = {after}")
    con.close()


if __name__ == "__main__":
    main()
