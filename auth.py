# auth.py (rút gọn)
import bcrypt
from db import get_conn

def verify_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, role, dept, password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    pwd_hash = row[4].encode()
    if bcrypt.checkpw(password.encode(), pwd_hash):
        return {"id": row[0], "username": username, "name": row[1], "role": row[2], "dept": row[3]}
    return None
