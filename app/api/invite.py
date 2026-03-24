from fastapi import APIRouter, Header, Depends, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match import Match
from app.core.firebase import verify_token

from app.api.chat import manager  # 🔥 for realtime

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 SEND INVITE
@router.post("/send")
async def send_invite(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    match = db.query(Match).filter(
        ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
        ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
    ).first()

    if not match:
        return {"error": "No match"}

    match.invite_sender = uid
    db.commit()

    # 🔥 REAL-TIME NOTIFICATION
    await manager.send_personal_message({
        "type": "invite",
        "from": uid
    }, other_uid)

    return {"msg": "Invite sent"}


# 🔥 ACCEPT INVITE
@router.post("/accept")
async def accept_invite(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    match = db.query(Match).filter(
        ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
        ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
    ).first()

    if not match:
        return {"error": "No match"}

    match.chat_enabled = True
    db.commit()

    # 🔥 notify sender
    await manager.send_personal_message({
        "type": "invite_accepted",
        "from": uid
    }, other_uid)

    return {"msg": "Chat enabled"}