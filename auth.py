# auth.py
import bcrypt
from db import get_user_by_username

def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_user(username, password):
    row = get_user_by_username(username)
    if not row:
        return None
    stored = row.get('password_hash')
    if stored is None:
        return None
    # stored string -> bytes
    try:
        stored_b = stored.encode()
    except Exception:
        stored_b = stored
    if bcrypt.checkpw(password.encode(), stored_b):
        return {"id": row['id'], "username": row['username'], "name": row['name'], "role": row['role'], "dept": row['dept'], "email": row.get('email')}
    return None
