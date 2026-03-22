from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.message import Message

router = APIRouter()

connections = {}
online_users = set()


@router.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await websocket.accept()

    connections[uid] = websocket
    online_users.add(uid)

    # 🔥 broadcast online users
    for conn in connections.values():
        await conn.send_json({"online": list(online_users)})

    try:
        while True:
            data = await websocket.receive_json()
            receiver = data.get("to")

            # 💬 MESSAGE
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

            # ✍️ TYPING
            elif "typing" in data and receiver in connections:
                await connections[receiver].send_json({
                    "typing": True,
                    "from": uid
                })

            # 📞 CALL
            elif "call" in data and receiver in connections:
                await connections[receiver].send_json({
                    "call": True,
                    "from": uid
                })

            elif "call_accept" in data and receiver in connections:
                await connections[receiver].send_json({
                    "call_accept": True,
                    "from": uid
                })

            elif "call_reject" in data and receiver in connections:
                await connections[receiver].send_json({
                    "call_reject": True,
                    "from": uid
                })

            # 🎥 WEBRTC SIGNALING
            elif any(k in data for k in ["offer", "answer", "candidate"]):
                if receiver in connections:
                    await connections[receiver].send_json({
                        **data,
                        "from": uid
                    })

    except WebSocketDisconnect:
        print(f"❌ {uid} disconnected")

    finally:
        connections.pop(uid, None)
        online_users.discard(uid)

        for conn in connections.values():
            await conn.send_json({"online": list(online_users)})