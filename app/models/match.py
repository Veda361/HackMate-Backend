from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Match(Base):
    __tablename__ = "hackMate_matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_uid = Column(String)
    user2_uid = Column(String)
    chat_enabled = Column(Boolean, default=False)
    invite_sender = Column(String, nullable=True)