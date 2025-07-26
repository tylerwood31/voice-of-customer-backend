import sqlite3
from contextlib import contextmanager
from config import DB_PATH

def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # background thread safe
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

@contextmanager
def db_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()