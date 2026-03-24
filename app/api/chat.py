from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.message import Message

router = APIRouter()


# 🔥 CONNECTION MANAGER (NEW)
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}  # uid -> websocket
        self.online_users = set()

    async def connect(self, uid: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[uid] = websocket
        self.online_users.add(uid)

        print(f"🔌 Connected: {uid}")

        # 🔥 broadcast online users
        await self.broadcast({"online": list(self.online_users)})

    def disconnect(self, uid: str):
        self.active_connections.pop(uid, None)
        self.online_users.discard(uid)

        print(f"❌ Disconnected: {uid}")

    async def send_personal_message(self, message: dict, uid: str):
        ws = self.active_connections.get(uid)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)


# 🔥 GLOBAL INSTANCE (IMPORTANT)
manager = ConnectionManager()


# 🔥 WEBSOCKET ROUTE
@router.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await manager.connect(uid, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            receiver = data.get("to")

            # 💬 MESSAGE
            if "message" in data:
                db: Session = SessionLocal()

                db.add(Message(
                    sender_uid=uid,
                    receiver_uid=receiver,
                    content=data["message"]
                ))
                db.commit()
                db.close()

                await manager.send_personal_message({
                    "from": uid,
                    "message": data["message"]
                }, receiver)

            # ✍️ TYPING
            elif "typing" in data:
                await manager.send_personal_message({
                    "typing": True,
                    "from": uid
                }, receiver)

            # 📞 CALL
            elif "call" in data:
                await manager.send_personal_message({
                    "call": True,
                    "from": uid
                }, receiver)

            elif "call_accept" in data:
                await manager.send_personal_message({
                    "call_accept": True,
                    "from": uid
                }, receiver)

            elif "call_reject" in data:
                await manager.send_personal_message({
                    "call_reject": True,
                    "from": uid
                }, receiver)

            # 🎥 WEBRTC SIGNALING
            elif any(k in data for k in ["offer", "answer", "candidate"]):
                await manager.send_personal_message({
                    **data,
                    "from": uid
                }, receiver)

    except WebSocketDisconnect:
        manager.disconnect(uid)

        # 🔥 broadcast updated online users
        await manager.broadcast({"online": list(manager.online_users)})