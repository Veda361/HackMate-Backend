from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.routes import user
from fastapi.middleware.cors import CORSMiddleware
from app.api import swipe
from app.api import chat, upload
from fastapi.staticfiles import StaticFiles
from app.api import matching

app = FastAPI(title="HackMate API 🚀")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # ✅ FIX THIS
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(swipe.router, prefix="/swipe", tags=["Swipe"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(upload.router, prefix="/upload")
app.include_router(matching.router, prefix="/match", tags=["Match"])


app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def home():
    return {"msg": "HackMate Running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}