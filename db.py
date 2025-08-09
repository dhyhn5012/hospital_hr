# db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "hr.db"
DB_PATH.parent.mkdir(exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE, name TEXT, role TEXT, dept TEXT, password_hash TEXT
      )
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER,
        start_date TEXT, end_date TEXT, reason TEXT,
        attachment_path TEXT, status TEXT, approver_id INTEGER, created_at TEXT
      )
    """)
    conn.commit()
    conn.close()