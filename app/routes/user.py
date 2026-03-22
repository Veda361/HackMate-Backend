from fastapi import APIRouter, Header, Depends, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.firebase import verify_token
from app.services.match_engine import calculate_match

router = APIRouter()


# ✅ DB Dependency (with proper close)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 CREATE PROFILE (with username)
@router.post("/profile")
def create_profile(
    authorization: str = Header(...),
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded["uid"]
        email = decoded["email"]
        username = data.get("username", "")

        user = db.query(User).filter(User.firebase_uid == uid).first()

        if not user:
            user = User(
                firebase_uid=uid,
                email=email,
                username=username
            )
            db.add(user)
            db.commit()

        return {
            "msg": "User stored",
            "email": email,
            "username": username
        }

    except Exception as e:
        return {"error": str(e)}


# 🔥 GET CURRENT USER (IMPORTANT for Dashboard)
@router.get("/me")
def get_me(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded["uid"]

        user = db.query(User).filter(User.firebase_uid == uid).first()

        if not user:
            return {"error": "User not found"}

        return {
            "email": user.email,
            "username": user.username,
            "skills": user.skills
        }

    except Exception as e:
        return {"error": str(e)}


# 🔥 UPDATE SKILLS (FIXED: JSON body instead of query param)
@router.post("/update-skills")
def update_skills(
    data: dict = Body(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:
        print("📩 Request received")

        if not authorization:
            return {"error": "Missing Authorization"}

        token = authorization.split(" ")[1]

        decoded = verify_token(token)

        uid = decoded["uid"]
        skills = data.get("skills")

        print("🧠 Skills:", skills)

        user = db.query(User).filter(User.firebase_uid == uid).first()

        if not user:
            return {"error": "User not found"}

        user.skills = skills
        db.commit()

        print("✅ Skills updated")

        return {"msg": "Skills updated", "skills": skills}

    except Exception as e:
        print("❌ ERROR:", e)
        return {"error": str(e)}

# 🔥 MATCHING ENGINE
@router.get("/match")
def get_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded["uid"]

        current_user = db.query(User).filter(User.firebase_uid == uid).first()

        if not current_user:
            return {"error": "User not found"}

        users = db.query(User).all()

        results = []

        for u in users:
            if u.firebase_uid != uid and u.skills:
                score = calculate_match(current_user.skills or "", u.skills)

                results.append({
                    "email": u.email,
                    "username": u.username,
                    "skills": u.skills,
                    "score": score
                })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    except Exception as e:
        return {"error": str(e)}