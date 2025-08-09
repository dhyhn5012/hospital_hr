import streamlit as st
import pandas as pd
from datetime import date

# ==============================
# CẤU HÌNH TRANG
# ==============================
st.set_page_config(
    page_title="Quản lý nhân lực bệnh viện",
    page_icon="🏥",
    layout="wide"
)

# ==============================
# THANH MENU
# ==============================
menu = ["Trang chủ", "Quản lý phép ốm"]
choice = st.sidebar.selectbox("Chọn chức năng", menu)

# ==============================
# TRANG CHỦ
# ==============================
if choice == "Trang chủ":
    st.title("🏥 Hệ thống quản lý nhân lực - Bệnh viện")
    st.write("Chào mừng bạn đến với hệ thống quản lý nhân lực!")
    st.info("Chọn chức năng ở menu bên trái để bắt đầu.")

# ==============================
# QUẢN LÝ PHÉP ỐM
# ==============================
elif choice == "Quản lý phép ốm":
    st.header("📄 Gửi đơn xin nghỉ ốm")

    # Form nhập liệu
    with st.form(key="leave_form"):
        name = st.text_input("Họ và tên")
        department = st.text_input("Khoa/Phòng")
        start_date = st.date_input("Ngày bắt đầu", value=date.today())
        end_date = st.date_input("Ngày kết thúc", value=date.today())
        reason = st.text_area("Lý do")
        attachment = st.file_uploader("Tải giấy xác nhận y tế (nếu có)", type=["pdf", "jpg", "png"])

        submit_button = st.form_submit_button("Gửi đơn")

    # Xử lý khi gửi đơn
    if submit_button:
        # Lưu dữ liệu vào file Excel
        new_data = {
            "Họ và tên": name,
            "Khoa/Phòng": department,
            "Ngày bắt đầu": start_date,
            "Ngày kết thúc": end_date,
            "Lý do": reason
        }

        try:
            df = pd.read_excel("leave_requests.xlsx")
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        except FileNotFoundError:
            df = pd.DataFrame([new_data])

        df.to_excel("leave_requests.xlsx", index=False)

        st.success("✅ Đã gửi đơn thành công!")

if 'user' not in st.session_state:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state['user'] = user
 



