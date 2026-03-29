from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.message import Message
from app.core.firebase import verify_token

router = APIRouter()


# 🔥 DB DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 CONNECTION MANAGER
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.online_users = set()

    async def connect(self, uid: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[uid] = websocket
        self.online_users.add(uid)

        print(f"🔌 Connected: {uid}")
        await self.broadcast_online()

    def disconnect(self, uid: str):
        self.active_connections.pop(uid, None)
        self.online_users.discard(uid)

        print(f"❌ Disconnected: {uid}")

    async def send(self, uid: str, message: dict):
        ws = self.active_connections.get(uid)
        if ws:
            await ws.send_json(message)

    async def broadcast_online(self):
        users = list(self.online_users)
        for ws in self.active_connections.values():
            try:
                await ws.send_json({
                    "type": "online",
                    "users": users
                })
            except:
                pass


manager = ConnectionManager()


# 🔥 WEBSOCKET
@router.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await manager.connect(uid, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            receiver = data.get("to")
            msg_type = data.get("type")

            # 💬 MESSAGE
            if msg_type == "message":
                db: Session = SessionLocal()

                db.add(Message(
                    sender_uid=uid,
                    receiver_uid=receiver,
                    content=data["message"]  # ✅ FIXED
                ))
                db.commit()
                db.close()

                await manager.send(receiver, {
                    "type": "message",
                    "from": uid,
                    "message": data["message"]
                })

            # ✍️ TYPING
            elif msg_type == "typing":
                await manager.send(receiver, {
                    "type": "typing",
                    "from": uid
                })

            # 📞 CALL
            elif msg_type in ["call", "call_accept", "call_reject", "call_end"]:
                await manager.send(receiver, {
                    "type": msg_type,
                    "from": uid
                })

            # 🎥 WEBRTC
            elif msg_type in ["offer", "answer", "candidate"]:
                await manager.send(receiver, {
                    "type": msg_type,
                    "from": uid,
                    **data
                })

    except WebSocketDisconnect:
        manager.disconnect(uid)
        await manager.broadcast_online()


# 🔥 CHAT HISTORY (FIXED)
@router.get("/history/{other_uid}")
def get_chat_history(
    other_uid: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(authorization.split(" ")[1])["uid"]

        messages = db.query(Message).filter(
            ((Message.sender_uid == uid) & (Message.receiver_uid == other_uid)) |
            ((Message.sender_uid == other_uid) & (Message.receiver_uid == uid))
        ).order_by(Message.timestamp).all()

        return [
            {
                "from": m.sender_uid,
                "message": m.content,  # ✅ FIXED
                "time": m.timestamp
            }
            for m in messages
        ]

    except Exception as e:
        print("❌ HISTORY ERROR:", e)
        return []