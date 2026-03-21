from fastapi import APIRouter, WebSocket, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.message import Message
from app.core.firebase import verify_token

router = APIRouter()

connections = {}
online_users = set()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/history/{other_uid}")
def get_chat_history(other_uid: str, authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.split(" ")[1]
    decoded = verify_token(token)
    uid = decoded["uid"]

    messages = db.query(Message).filter(
        ((Message.sender_uid == uid) & (Message.receiver_uid == other_uid)) |
        ((Message.sender_uid == other_uid) & (Message.receiver_uid == uid))
    ).order_by(Message.timestamp).all()

    return [
        {
            "from": m.sender_uid,
            "to": m.receiver_uid,
            "message": m.content,
            "time": str(m.timestamp)
        }
        for m in messages
    ]


@router.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await websocket.accept()

    connections[uid] = websocket
    online_users.add(uid)

    # broadcast online users
    for conn in connections.values():
        await conn.send_json({"online": list(online_users)})

    try:
        while True:
            data = await websocket.receive_json()
            receiver = data.get("to")

            if "message" in data:
                db = SessionLocal()
                db.add(Message(
                    sender_uid=uid,
                    receiver_uid=receiver,
                    content=data["message"]
                ))
                db.commit()
                db.close()

                if receiver in connections:
                    await connections[receiver].send_json({
                        "from": uid,
                        "message": data["message"]
                    })

            elif "typing" in data and receiver in connections:
                await connections[receiver].send_json({"typing": True})

            elif "call" in data and receiver in connections:
                await connections[receiver].send_json({"call": True, "from": uid})

            elif "call_accept" in data and receiver in connections:
                await connections[receiver].send_json({"call_accept": True, "from": uid})

            elif "call_reject" in data and receiver in connections:
                await connections[receiver].send_json({"call_reject": True})

            elif any(k in data for k in ["offer", "answer", "candidate"]):
                if receiver in connections:
                    await connections[receiver].send_json({**data, "from": uid})

    except Exception as e:
        print("WebSocket error:", e)

    finally:
        connections.pop(uid, None)
        online_users.discard(uid)

        for conn in connections.values():
            await conn.send_json({"online": list(online_users)})