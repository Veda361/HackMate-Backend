from fastapi import APIRouter, Header, Depends, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.firebase import verify_token
from app.services.match_engine import calculate_match

router = APIRouter()


# ✅ DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 CREATE PROFILE
@router.post("/profile")
def create_profile(
    authorization: str = Header(...),
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded.get("uid")
        email = decoded.get("email")
        username = data.get("username", "")

        if not uid:
            return {"error": "Invalid token"}

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
        print("❌ PROFILE ERROR:", e)
        return {"error": str(e)}


# 🔥 GET CURRENT USER
@router.get("/me")
def get_me(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded.get("uid")

        user = db.query(User).filter(User.firebase_uid == uid).first()

        if not user:
            return {"error": "User not found"}

        return {
            "email": user.email,
            "username": user.username,
            "skills": user.skills or ""
        }

    except Exception as e:
        print("❌ GET ME ERROR:", e)
        return {"error": str(e)}


# 🔥 UPDATE SKILLS
@router.post("/update-skills")
def update_skills(
    data: dict = Body(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:
        if not authorization:
            return {"error": "Missing Authorization"}

        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded.get("uid")
        skills = data.get("skills", "")

        user = db.query(User).filter(User.firebase_uid == uid).first()

        if not user:
            return {"error": "User not found"}

        user.skills = skills
        db.commit()

        return {
            "msg": "Skills updated",
            "skills": skills
        }

    except Exception as e:
        print("❌ UPDATE SKILLS ERROR:", e)
        return {"error": str(e)}


# 🔥 SUGGESTION ENGINE (Tinder-style swipe users)
@router.get("/suggestions")
def get_suggestions(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded.get("uid")

        current_user = db.query(User).filter(User.firebase_uid == uid).first()

        if not current_user:
            return []

        # ✅ allow even without skills 
        users = db.query(User).filter(
            User.firebase_uid != uid
        ).all()

        users = db.query(User).filter(
            User.firebase_uid != uid,
            User.skills != None,
            User.skills != ""
        ).all()

        results = []

        for u in users:
            score = 0
            if current_user.skills and u.skills:
                score = calculate_match(current_user.skills, u.skills)

            results.append({
                "uid": u.firebase_uid,
                "email": u.email,
                "username": u.username,
                "skills": u.skills,
                "score": score
            })

        # 🔥 sort highest match first
        results.sort(key=lambda x: x["score"], reverse=True)

        return results

    except Exception as e:
        print("❌ SUGGESTION ERROR:", e)
        return []