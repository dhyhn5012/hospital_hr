import streamlit as st
import pandas as pd
from datetime import datetime

# Cấu hình trang
st.set_page_config(page_title="Lịch trực", layout="wide")
st.title("📅 Lịch trực")

# Hiển thị ngày hôm nay
now = datetime.now().date()
st.write(f"Hôm nay: {now.strftime('%d/%m/%Y')}")

# Đọc dữ liệu lịch trực
@st.cache_data
def load_data():
    df = pd.read_csv('duty_schedule.csv', parse_dates=['date'])
    return df

data = load_data()

# Danh sách khoa
departments = sorted(data['department'].unique().tolist())

# Form tìm kiếm
with st.sidebar:
    st.header("🔍 Tìm kiếm")
    selected_date = st.date_input("Ngày", value=now)
    dept = st.selectbox("Khoa", options=["Tất cả"] + departments)
    doctor = st.text_input("Bác sĩ")

# Lọc dữ liệu
filtered = data.copy()
if selected_date:
    filtered = filtered[filtered['date'] == pd.Timestamp(selected_date)]
if dept != "Tất cả":
    filtered = filtered[filtered['department'] == dept]
if doctor:
    filtered = filtered[filtered['doctor'].str.contains(doctor, case=False, na=False)]

# Thêm cột thứ và ngày
weekday_map = {
    0: "Thứ hai",
    1: "Thứ ba",
    2: "Thứ tư",
    3: "Thứ năm",
    4: "Thứ sáu",
    5: "Thứ bảy",
    6: "Chủ nhật",
}
filtered['Thứ'] = filtered['date'].dt.weekday.map(weekday_map)
filtered['Ngày'] = filtered['date'].dt.strftime('%d/%m/%Y')

# Hiển thị kết quả
if filtered.empty:
    st.info("Không tìm thấy lịch trực phù hợp.")
else:
    show = filtered[['Thứ', 'Ngày', 'department', 'doctor', 'nurse']].rename(
        columns={'department': 'Khoa trực', 'doctor': 'Bác sĩ trực', 'nurse': 'Điều dưỡng trực'}
    )
    st.dataframe(show, use_container_width=True)
