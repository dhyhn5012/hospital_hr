# seed_data.py
from db import init_db, create_user, get_conn
import bcrypt

init_db()

def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

# Tạo manager & employee
create_user("manager1", "Trưởng khoa A", "manager", "Khoa A", hash_pw("managerpass"), "managerA@bv.local")
create_user("user1", "Bác sĩ A", "employee", "Khoa A", hash_pw("userpass"), "userA@bv.local")

# Tạo 1 đơn mẫu (employee id will likely be 2)
conn = get_conn()
cur = conn.cursor()
cur.execute("""INSERT INTO leave_requests (employee_id, start_date, end_date, reason, attachment_path, status)
               VALUES (?,?,?,?,?,?)""",
            (2, "2025-08-20", "2025-08-22", "Việc cá nhân", None, "pending"))
conn.commit()
conn.close()
print("Seed xong. Manager: manager1/managerpass | Employee: user1/userpass")
