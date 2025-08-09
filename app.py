# app.py (demo manager approve view)
import streamlit as st
import pandas as pd
from pathlib import Path
from db import init_db, get_pending_requests_for_dept, get_leave_request_by_id, approve_leave, get_requests_for_dept, get_audit_logs
from auth import verify_user

# Khởi tạo DB (chỉ gọi 1 lần an toàn)
init_db()

st.set_page_config(page_title="Quản lý phép - BV", layout="wide")

# --- simple login UI (session_state) ---
if 'user' not in st.session_state:
    st.sidebar.title("Đăng nhập")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Mật khẩu", type="password")
    if st.sidebar.button("Đăng nhập"):
        user = verify_user(username, password)
        if user:
            st.session_state['user'] = user
            st.experimental_rerun()
        else:
            st.sidebar.error("Sai username hoặc mật khẩu")
    st.stop()

user = st.session_state['user']
st.sidebar.write(f"Xin chào: **{user['name']}** — {user['role']} / {user['dept']}")
st.title("Quản lý đơn nghỉ phép")

# Navigation
page = st.sidebar.selectbox("Chọn trang", ["Nộp đơn (employee)", "Duyệt đơn (manager)", "Báo cáo / Xuất", "Audit logs"])

# --- Manager view ---
if page == "Duyệt đơn (manager)":
    if user['role'] != 'manager':
        st.warning("Bạn không có quyền truy cập trang duyệt đơn.")
        st.stop()

    st.header("Đơn chờ duyệt - Khoa: " + user['dept'])
    requests = get_pending_requests_for_dept(user['dept'])
    if not requests:
        st.info("Không có đơn chờ duyệt.")
    else:
        df = pd.DataFrame(requests)
        display = df[['id','employee_name','username','start_date','end_date','reason','created_at']]
        st.dataframe(display, use_container_width=True)

        sel_id = st.selectbox("Chọn ID đơn để xem chi tiết", options=df['id'].tolist())
        if sel_id:
            req = get_leave_request_by_id(sel_id)
            st.subheader(f"Đơn #{req['id']} — {req['start_date']} → {req['end_date']}")
            st.markdown(f"- **Người gửi (id):** {req['employee_id']}")
            st.markdown(f"- **Lý do:** {req['reason']}")
            st.markdown(f"- **Trạng thái:** {req['status']}")
            if req.get('attachment_path'):
                path = Path(req['attachment_path'])
                if path.exists():
                    with open(path, "rb") as f:
                        st.download_button("Tải tệp đính kèm", data=f.read(), file_name=path.name)
                else:
                    st.write("Tệp đính kèm không tìm thấy trên server:", req['attachment_path'])

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Duyệt (Approve)"):
                    approve_leave(req['id'], user['id'], approved=True, note="Duyệt bởi " + user['username'])
                    st.success("Đã duyệt đơn.")
                    st.experimental_rerun()
            with col2:
                if st.button("Từ chối (Reject)"):
                    reason = st.text_area("Ghi lý do từ chối (lưu vào audit):")
                    approve_leave(req['id'], user['id'], approved=False, note=reason)
                    st.warning("Đã từ chối đơn.")
                    st.experimental_rerun()

# --- Báo cáo / Xuất ---
if page == "Báo cáo / Xuất":
    st.header("Xuất báo cáo")
    dept = user['dept'] if user['role'] != 'hr' else st.selectbox("Chọn khoa", options=["Khoa A","Khoa B","Khoa C"])
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Từ ngày")
    with col2:
        end = st.date_input("Đến ngày")
    if st.button("Tải báo cáo CSV"):
        df = pd.DataFrame(get_requests_for_dept(dept, start_date=start.isoformat(), end_date=end.isoformat()))
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name=f"report_{dept}_{start}_{end}.csv", mime="text/csv")
from io import BytesIO

if st.button("Tải báo cáo Excel"):
    df = pd.DataFrame(get_requests_for_dept(dept, start_date=start.isoformat(), end_date=end.isoformat()))
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='report')
    st.download_button("Download Excel", data=buffer.getvalue(),
                       file_name=f"report_{dept}_{start}_{end}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Audit logs (HR/manager) ---
if page == "Audit logs":
    st.header("Audit logs")
    logs = get_audit_logs(limit=500)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True)
    else:
        st.info("Chưa có log.")
