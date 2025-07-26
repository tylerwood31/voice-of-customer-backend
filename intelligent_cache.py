# intelligent_cache.py
import os
import time
import traceback
import json
from datetime import datetime
from typing import Iterable, Dict, Any

from db_connection import db_conn
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, DEBUG_REFRESH
from airtable import fetch_all_records  # you'll write this (below)

def init_schema():
    with db_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_cache (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            modified_at TEXT,
            fields_json TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_update TEXT,
            total_records INTEGER,
            last_error TEXT,
            last_run_type TEXT,
            running INTEGER DEFAULT 0
        )
        """)
        # ensure singleton row
        conn.execute("""
        INSERT INTO cache_status (id, last_update, total_records, last_error, last_run_type, running)
        VALUES (1, '1970-01-01T00:00:00Z', 0, NULL, NULL, 0)
        ON CONFLICT(id) DO NOTHING
        """)

def _update_status(**kwargs):
    keys = ", ".join([f"{k} = :{k}" for k in kwargs.keys()])
    kwargs["id"] = 1
    with db_conn() as conn:
        conn.execute(f"UPDATE cache_status SET {keys} WHERE id = :id", kwargs)

def get_status():
    with db_conn() as conn:
        row = conn.execute("SELECT last_update, total_records, last_error, last_run_type, running FROM cache_status WHERE id = 1").fetchone()
    if not row:
        return None
    return {
        "last_update": row[0],
        "total_records": row[1],
        "last_error": row[2],
        "last_run_type": row[3],
        "running": bool(row[4]),
    }

def refresh_full():
    return _do_refresh(mode="full")

def refresh_incremental(since_iso: str):
    return _do_refresh(mode="incremental", since=since_iso)

def _do_refresh(mode: str, since: str | None = None):
    started = datetime.utcnow().isoformat() + "Z"
    _update_status(running=1, last_run_type=mode, last_error=None)

    try:
        if DEBUG_REFRESH:
            print(f"[cache] starting {mode} refresh at {started}, since={since}")

        records = fetch_all_records(
            api_key=AIRTABLE_API_KEY,
            base_id=AIRTABLE_BASE_ID,
            table_name=AIRTABLE_TABLE_NAME,
            since=since if mode == "incremental" else None
        )

        total = 0
        with db_conn() as conn:
            # speed: transaction is already open (context manager)
            # UPSERT each record
            for r in records:
                rid = r["id"]
                created = r["createdTime"]
                modified = r.get("fields", {}).get("Last Modified", created)  # or your own LAST_MODIFIED_TIME
                payload = json.dumps(r["fields"], ensure_ascii=False)

                conn.execute("""
                    INSERT INTO feedback_cache (id, created_at, modified_at, fields_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        created_at = excluded.created_at,
                        modified_at = excluded.modified_at,
                        fields_json = excluded.fields_json
                """, (rid, created, modified, payload))
                total += 1
                if DEBUG_REFRESH and total % 500 == 0:
                    print(f"[cache] {total}...")

        _update_status(
            last_update=datetime.utcnow().isoformat() + "Z",
            total_records=total,
            last_error=None,
            running=0
        )
        if DEBUG_REFRESH:
            print(f"[cache] {mode} refresh done, total={total}")
        return {"ok": True, "total": total, "mode": mode}
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[cache] ERROR in {mode} refresh: {e}\n{tb}")
        _update_status(
            last_error=f"{e}\n{tb}",
            running=0
        )
        raise