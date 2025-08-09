# add_admin.py
from auth import hash_password
from db import create_user, init_db

# Khởi tạo DB (nếu chưa có)
init_db()

# Thông tin tài khoản
username = "admin"
password_plain = "123456"   # Bạn có thể đổi
name = "Admin"
role = "manager"            # Hoặc "hr"
dept = "Khoa A"
email = "admin@example.com"

# Mã hóa mật khẩu
password_hash = hash_password(password_plain)

# Thêm vào DB
create_user(username, name, role, dept, password_hash, email)

print(f"✅ Đã tạo tài khoản: {username} / {password_plain}")
