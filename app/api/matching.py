from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match import Match
from app.models.user import User
from app.core.firebase import verify_token

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_my_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded["uid"]

        matches = db.query(Match).filter(
            (Match.user1_uid == uid) | (Match.user2_uid == uid)
        ).all()

        results = []

        for m in matches:
            other_uid = m.user2_uid if m.user1_uid == uid else m.user1_uid

            user = db.query(User).filter(
                User.firebase_uid == other_uid
            ).first()

            if user:
                results.append({
                    "uid": user.firebase_uid,
                    "email": user.email,
                    "username": user.username,
                    "skills": user.skills,

                    # 🔥 CORE HYBRID LOGIC
                    "chat_enabled": getattr(m, "chat_enabled", False),
                    "invite_sender": getattr(m, "invite_sender", None),

                    # 👉 useful flags
                    "is_sender": getattr(m, "invite_sender", None) == uid,
                    "can_accept": getattr(m, "invite_sender", None) not in [None, uid],
                })

        return results

    except Exception as e:
        print("❌ MATCH ERROR:", e)
        return []