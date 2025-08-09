# notify.py
import smtplib
from email.message import EmailMessage
import streamlit as st

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Trả về True nếu gửi thành công, False nếu thất bại.
    Cấu hình SMTP lấy từ st.secrets["smtp"].
    """
    smtp = st.secrets.get("smtp")
    if not smtp:
        print("No SMTP configured in st.secrets. To test locally, run a debug SMTP server.")
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = smtp.get("from")
        msg['To'] = to_email

        host = smtp.get("host")
        port = int(smtp.get("port", 587))
        starttls = smtp.get("starttls", True)

        with smtplib.SMTP(host, port, timeout=10) as s:
            if starttls:
                s.starttls()
            user = smtp.get("user")
            pwd = smtp.get("pass")
            if user:
                s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        print("send_email error:", e)
        return False
