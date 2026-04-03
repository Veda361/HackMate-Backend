from fastapi import APIRouter, UploadFile, File, Header, Depends
from sqlalchemy.orm import Session
import shutil
import os
import uuid

from app.db.session import SessionLocal
from app.models.user import User
from app.core.firebase import verify_token

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# DB DEP
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# 📷 GENERIC FILE UPLOAD (IMAGE + AUDIO)
# =========================
@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    token = authorization.split(" ")[1]
    decoded = verify_token(token)
    uid = decoded["uid"]

    # 🔥 unique filename
    ext = file.filename.split(".")[-1]
    filename = f"{uid}_{uuid.uuid4().hex}.{ext}"

    file_path = f"{UPLOAD_DIR}/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ IMPORTANT: return URL for frontend
    return {
        "url": f"/uploads/{filename}"
    }


# =========================
# 👤 AVATAR UPLOAD (UNCHANGED + SAFE)
# =========================
@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    decoded = verify_token(token)
    uid = decoded["uid"]

    ext = file.filename.split(".")[-1]
    filename = f"{uid}_avatar.{ext}"

    file_path = f"{UPLOAD_DIR}/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user = db.query(User).filter(User.firebase_uid == uid).first()
    if user:
        user.avatar = file_path
        db.commit()

    return {
        "avatar_url": file_path
    }