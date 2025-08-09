# utils.py
from pathlib import Path
from datetime import datetime

UPLOAD_DIR = Path(__file__).parent / "uploads"

ALLOWED = {".pdf",".png",".jpg",".jpeg"}

def save_uploaded_file(uploaded_file, username):
    if uploaded_file is None:
        return None
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError("File không được phép.")
    safe_dir = UPLOAD_DIR / username
    safe_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{ts}_{Path(uploaded_file.name).name}"
    target = safe_dir / filename
    # viết xuống đĩa
    with open(target, "wb") as f:
        f.write(uploaded_file.read())
    return str(target)
