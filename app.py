# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
import pytz
from datetime import datetime

# --- import từ các module khác ---
from db import (
    init_db, 
    get_pending_requests_for_dept, 
    get_leave_request_by_id, 
    approve_leave, 
    get_requests_for_dept, 
    get_audit_logs,
    check_employee_overlap, 
    dept_overlap_count, 
    create_leave_request, 
    get_user_by_id
)
from auth import verify_user
from utils import save_uploaded_file
from notify import send_email

# Khởi tạo DB (chỉ gọi 1 lần an toàn)
init_db()

# Cấu hình giao diện
st.set_page_config(page_title="Quản lý phép - BV", layout="wide")

st.markdown("""
    <style>
        h1, h2, h3, h4 { color: #2a5d84; }
        .stButton>button {
            border-radius: 8px;
            background-color: #2a5d84;
            color: white;
        }
        .stButton>button:hover {
            background-color: #1f4561;
            color: white;
        }
        .main > div { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- simple login UI (session_state) ---
if 'user' not in st.session_state:
    st.sidebar.title("🔐 Đăng nhập")
    username = st.sidebar.text_input("Tên đăng nhập")
    password = st.sidebar.text_input("Mật khẩu", type="password")
    if st.sidebar.button("Đăng nhập"):
        user = verify_user(username, password)
        if user:
            st.session_state['user'] = user
            st.rerun()
        else:
            st.sidebar.error("❌ Sai tên đăng nhập hoặc mật khẩu")
    st.stop()


# Lấy thông tin user từ session
user = st.session_state['user']

# Sidebar thông tin user + logout
with st.sidebar:
    st.write(f"👋 Xin chào **{user['name']}**")
    st.caption(f"Vai trò: {user['role']} | Khoa: {user['dept']}")
    if st.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

st.title("📄 Quản lý đơn nghỉ phép")

# Tính ngày phép còn lại
def tinh_ngay_phep_con_lai(user_id):
    YEAR = datetime.now().year
    TOTAL = 12
    df_all = pd.DataFrame(get_requests_for_dept(user['dept']))
    df_user = df_all[(df_all['employee_id'] == user_id) & (df_all['status'] == 'approved')]
    df_user['start_date'] = pd.to_datetime(df_user['start_date'])
    df_user = df_user[df_user['start_date'].dt.year == YEAR]
    da_nghi = sum((pd.to_datetime(df_user['end_date']) - pd.to_datetime(df_user['start_date'])).dt.days + 1)
    con_lai = TOTAL - da_nghi
    return TOTAL, da_nghi, con_lai

# Navigation menu (ẩn "Duyệt đơn" nếu là employee)
menu_items = ["📝 Nộp đơn", "📊 Báo cáo / Xuất", "📜 Lịch sử thao tác"]
if user['role'] == 'manager':
    menu_items.insert(1, "✅ Duyệt đơn")

page = st.sidebar.radio("📌 Chọn chức năng", menu_items)

# Hiển thị ngày phép còn lại
total_phep, da_nghi, con_lai = tinh_ngay_phep_con_lai(user['id'])
st.sidebar.markdown(f"**📆 Ngày phép trong năm:** {total_phep} ngày")
st.sidebar.markdown(f"**✅ Đã nghỉ:** {da_nghi} ngày")
st.sidebar.markdown(f"**🕒 Còn lại:** {con_lai} ngày")

# --- Trang Nộp đơn ---
if page.startswith("📝"):
    st.header("📝 Nộp đơn nghỉ phép")

    max_allowed_on_leave = st.number_input(
        "Số tối đa đồng thời được nghỉ trong khoa", 
        min_value=1, 
        value=2
    )

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Từ ngày")
    with col2:
        end = st.date_input("Đến ngày")

    reason = st.text_area("Lý do")
    attachment = st.file_uploader("Tệp đính kèm (pdf/png/jpg)", type=['pdf','png','jpg','jpeg'])

    if st.button("📤 Gửi đơn"):
        sd = start.isoformat()
        ed = end.isoformat()
        if ed < sd:
            st.error("❌ Ngày kết thúc phải >= ngày bắt đầu.")
            st.stop()

        if check_employee_overlap(user['id'], sd, ed):
            st.error("⚠️ Bạn đã có đơn trùng thời gian này.")
            st.stop()

        current_count = dept_overlap_count(user['dept'], sd, ed)
        if current_count >= max_allowed_on_leave:
            st.warning(f"⚠️ Đã có {current_count} người nghỉ — bằng/vượt ngưỡng ({max_allowed_on_leave}).")
            st.stop()

        attach_path = None
        if attachment:
            try:
                attach_path = save_uploaded_file(attachment, user['username'])
            except Exception as e:
                st.error("❌ Lỗi khi lưu file: " + str(e))
                st.stop()

        req_id = create_leave_request(user['id'], sd, ed, reason, attachment_path=attach_path)
        st.success(f"✅ Nộp đơn thành công. ID đơn: {req_id}")

# --- Manager view ---
elif page.startswith("✅"):
    st.header(f"📌 Đơn chờ duyệt - Khoa: {user['dept']}")
    requests = get_pending_requests_for_dept(user['dept'])
    if not requests:
        st.info("Không có đơn chờ duyệt.")
    else:
        df = pd.DataFrame(requests)
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
        display = df[['id','employee_name','username','start_date','end_date','reason','created_at']]
        st.dataframe(display, use_container_width=True)

        sel_id = st.selectbox("Chọn ID đơn để xem chi tiết", options=df['id'].tolist())
        if sel_id:
            req = get_leave_request_by_id(sel_id)
            st.subheader(f"Đơn #{req['id']} — {req['start_date']} → {req['end_date']}")
            st.markdown(f"- **Người gửi:** {req['employee_id']}")
            st.markdown(f"- **Lý do:** {req['reason']}")
            st.markdown(f"- **Trạng thái:** {req['status']}")
            if req.get('attachment_path'):
                path = Path(req['attachment_path'])
                if path.exists():
                    with open(path, "rb") as f:
                        st.download_button("📎 Tải tệp đính kèm", data=f.read(), file_name=path.name)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Duyệt"):
                    approve_leave(req['id'], user['id'], approved=True, note="Duyệt bởi " + user['username'])
                    emp = get_user_by_id(req['employee_id'])
                    if emp and emp.get('email'):
                        send_email(emp['email'], f"[Thông báo] Đơn #{req['id']} đã được duyệt", f"Xin chào {emp['name']}, đơn nghỉ phép của bạn đã được duyệt.")
                    st.success("Đã duyệt đơn.")
                    st.rerun()

            with col2:
                reason_reject = st.text_area("Lý do từ chối")
                if st.button("❌ Từ chối"):
                    approve_leave(req['id'], user['id'], approved=False, note=reason_reject)
                    emp = get_user_by_id(req['employee_id'])
                    if emp and emp.get('email'):
                        send_email(emp['email'], f"[Thông báo] Đơn #{req['id']} bị từ chối", f"Xin chào {emp['name']}, đơn nghỉ phép của bạn đã bị từ chối.\nLý do: {reason_reject}")
                    st.warning("Đã từ chối đơn.")
                    st.rerun()

# --- Báo cáo / Xuất ---
elif page.startswith("📊"):
    st.header("📊 Xuất báo cáo")
    dept = user['dept'] if user['role'] != 'hr' else st.selectbox("Chọn khoa", options=["Khoa A","Khoa B","Khoa C"])
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Từ ngày")
    with col2:
        end = st.date_input("Đến ngày")

    if st.button("⬇️ Tải báo cáo CSV"):
        df = pd.DataFrame(get_requests_for_dept(dept, start_date=start.isoformat(), end_date=end.isoformat()))
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Tải CSV", data=csv, file_name=f"report_{dept}_{start}_{end}.csv", mime="text/csv")

    if st.button("⬇️ Tải báo cáo Excel"):
        df = pd.DataFrame(get_requests_for_dept(dept, start_date=start.isoformat(), end_date=end.isoformat()))
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='report')
        st.download_button("Tải Excel", data=buffer.getvalue(),
                           file_name=f"report_{dept}_{start}_{end}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Audit logs ---
elif page.startswith("📜"):
    st.header("📜 Lịch sử thao tác")
    logs = get_audit_logs(limit=500)
    if logs:
        df = pd.DataFrame(logs)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có log.")
