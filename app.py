# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO

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

# --- Trang Nộp đơn ---
if page == "Nộp đơn (employee)":
    st.header("Nộp đơn nghỉ phép")

    # Số tối đa được nghỉ trong khoa
    max_allowed_on_leave = st.sidebar.number_input(
        "Số tối đa đồng thời được phép nghỉ trong khoa (ví dụ 2)", 
        min_value=1, 
        value=2
    )

    start = st.date_input("Bạn hãy nhập 'Từ ngày'")
    end = st.date_input("Bạn hãy nhập 'Đến ngày'")
    reason = st.text_area("Bạn hãy nhập 'Lý do' (VD: Việc cá nhân, khám bệnh...)")
    attachment = st.file_uploader("Tệp đính kèm (pdf/png/jpg) nếu có", type=['pdf','png','jpg','jpeg'])

    if st.button("Gửi đơn"):
        sd = start.isoformat()
        ed = end.isoformat()
        # validation cơ bản
        if ed < sd:
            st.error("Ngày kết thúc phải >= ngày bắt đầu.")
            st.stop()
        # check overlap cá nhân
        if check_employee_overlap(user['id'], sd, ed):
            st.error("Bạn đã có đơn (pending/approved) trùng thời gian này.")
            st.stop()
        # check số người đã được duyệt trong khoa
        current_count = dept_overlap_count(user['dept'], sd, ed)
        st.write(f"Số người đã được duyệt nghỉ trong khoa: {current_count}")
        if current_count >= max_allowed_on_leave:
            st.warning(f"Đã có {current_count} người nghỉ — bằng/vượt ngưỡng ({max_allowed_on_leave}). Liên hệ trưởng khoa trước khi nộp.")
            st.stop()
        # lưu file nếu có
        attach_path = None
        if attachment:
            try:
                attach_path = save_uploaded_file(attachment, user['username'])
            except Exception as e:
                st.error("Lỗi khi lưu file: " + str(e))
                st.stop()
        # tạo đơn
        req_id = create_leave_request(user['id'], sd, ed, reason, attachment_path=attach_path)
        st.success(f"Nộp đơn thành công. ID đơn: {req_id}")

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
                    st.write("Tệp đính kèm không tìm thấy:", req['attachment_path'])

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Duyệt (Approve)"):
                    approve_leave(req['id'], user['id'], approved=True, note="Duyệt bởi " + user['username'])
                    st.success("Đã duyệt đơn.")
                    # Gửi email cho người nộp
                    emp = get_user_by_id(req['employee_id'])
                    if emp and emp.get('email'):
                        subject = f"[Thông báo] Đơn nghỉ phép #{req['id']} của bạn đã được duyệt"
                        body = f"Xin chào {emp['name']},\n\nĐơn nghỉ phép #{req['id']} từ {req['start_date']} đến {req['end_date']} đã được duyệt.\n\nTrân trọng,\n{user['name']}"
                        ok = send_email(emp['email'], subject, body)
                        if ok:
                            st.info("Email thông báo đã gửi tới: " + emp['email'])
                        else:
                            st.warning("Không gửi được email (kiểm tra cấu hình SMTP).")
                    st.experimental_rerun()

            with col2:
                reason_reject = st.text_area("Lý do từ chối (sẽ gửi cho nhân viên):")
                if st.button("Từ chối (Reject)"):
                    approve_leave(req['id'], user['id'], approved=False, note=reason_reject)
                    st.warning("Đã từ chối đơn.")
                    # Gửi email cho người nộp
                    emp = get_user_by_id(req['employee_id'])
                    if emp and emp.get('email'):
                        subject = f"[Thông báo] Đơn nghỉ phép #{req['id']} của bạn đã bị từ chối"
                        body = f"Xin chào {emp['name']},\n\nĐơn nghỉ phép #{req['id']} từ {req['start_date']} đến {req['end_date']} đã bị từ chối.\nLý do: {reason_reject}\n\nTrân trọng,\n{user['name']}"
                        ok = send_email(emp['email'], subject, body)
                        if ok:
                            st.info("Email thông báo đã gửi tới: " + emp['email'])
                        else:
                            st.warning("Không gửi được email (kiểm tra cấu hình SMTP).")
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

    if st.button("Tải báo cáo Excel"):
        df = pd.DataFrame(get_requests_for_dept(dept, start_date=start.isoformat(), end_date=end.isoformat()))
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='report')
        st.download_button("Download Excel", data=buffer.getvalue(),
                           file_name=f"report_{dept}_{start}_{end}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Audit logs ---
if page == "Audit logs":
    st.header("Audit logs")
    logs = get_audit_logs(limit=500)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True)
    else:
        st.info("Chưa có log.")
