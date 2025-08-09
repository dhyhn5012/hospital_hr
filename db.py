# db.py
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "hr.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # users
    cur.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        name TEXT,
        role TEXT,
        dept TEXT,
        email TEXT,
        password_hash TEXT
      )
    """)
    # leave_requests
    cur.execute("""
      CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        reason TEXT,
        attachment_path TEXT,
        status TEXT DEFAULT 'pending',
        approver_id INTEGER,
        approved_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
      )
    """)
    # audit logs
    cur.execute("""
      CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        user_id INTEGER,
        obj_type TEXT,
        obj_id INTEGER,
        note TEXT,
        timestamp TEXT DEFAULT (datetime('now'))
      )
    """)
    conn.commit()
    conn.close()

# ----- helper DB API used by app -----
def create_user(username, name, role, dept, password_hash, email=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""INSERT OR IGNORE INTO users (username,name,role,dept,email,password_hash)
                   VALUES(?,?,?,?,?,?)""",
                (username, name, role, dept, email, password_hash))
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_pending_requests_for_dept(dept):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      SELECT lr.id, lr.employee_id, u.name as employee_name, u.username, u.dept,
             lr.start_date, lr.end_date, lr.reason, lr.status, lr.attachment_path, lr.created_at
      FROM leave_requests lr
      JOIN users u ON lr.employee_id = u.id
      WHERE u.dept = ? AND lr.status = 'pending'
      ORDER BY lr.created_at DESC
    """, (dept,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_requests_for_dept(dept, status=None, start_date=None, end_date=None):
    conn = get_conn()
    cur = conn.cursor()
    sql = """
      SELECT lr.id, lr.employee_id, u.name as employee_name, u.username, u.dept,
             lr.start_date, lr.end_date, lr.reason, lr.status, lr.attachment_path, lr.created_at
      FROM leave_requests lr
      JOIN users u ON lr.employee_id = u.id
      WHERE u.dept = ?
    """
    params = [dept]
    if status:
        sql += " AND lr.status = ?"
        params.append(status)
    if start_date and end_date:
        sql += " AND NOT (lr.end_date < ? OR lr.start_date > ?)"
        params.extend([start_date, end_date])
    sql += " ORDER BY lr.created_at DESC"
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_leave_request_by_id(request_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leave_requests WHERE id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def approve_leave(request_id, approver_id, approved=True, note=None):
    status = 'approved' if approved else 'rejected'
    approved_at = datetime.utcnow().isoformat()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE leave_requests SET status=?, approver_id=?, approved_at=? WHERE id=?",
                (status, approver_id, approved_at, request_id))
    conn.commit()
    log_audit(action=('approve' if approved else 'reject'),
              user_id=approver_id, obj_type='leave_request', obj_id=request_id, note=note)
    conn.close()

def log_audit(action, user_id, obj_type, obj_id, note=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO audit_logs(action,user_id,obj_type,obj_id,note,timestamp) VALUES(?,?,?,?,?,?)",
                (action, user_id, obj_type, obj_id, note, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_audit_logs(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---- overlap checks (business validation) ----
def check_employee_overlap(employee_id, start_date, end_date):
    """
    Trả về True nếu có đơn pending/approved trùng khoảng thời gian (same employee).
    start_date & end_date format: 'YYYY-MM-DD'
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      SELECT id FROM leave_requests
      WHERE employee_id = ? AND status IN ('approved','pending')
        AND NOT (end_date < ? OR start_date > ?)
    """, (employee_id, start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    return len(rows) > 0

def dept_overlap_count(dept, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      SELECT COUNT(*) FROM leave_requests lr
      JOIN users u ON lr.employee_id = u.id
      WHERE u.dept = ? AND lr.status = 'approved'
        AND NOT (lr.end_date < ? OR lr.start_date > ?)
    """, (dept, start_date, end_date))
    count = cur.fetchone()[0]
    conn.close()
    return count
