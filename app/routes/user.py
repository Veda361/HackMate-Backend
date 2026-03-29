from fastapi import APIRouter, Header, Depends, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.swipe import Swipe  # ✅ FIX: missing import
from app.models.match import Match  # ✅ FIX: missing import
from app.core.firebase import verify_token
from app.services.match_engine import calculate_match
from datetime import datetime

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
    db: Session = Depends(get_db),
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
            user = User(firebase_uid=uid, email=email, username=username)
            db.add(user)
            db.commit()

        return {"msg": "User stored", "email": email, "username": username}

    except Exception as e:
        print("❌ PROFILE ERROR:", e)
        return {"error": str(e)}


# 🔥 GET CURRENT USER
@router.get("/me")
def get_me(authorization: str = Header(...), db: Session = Depends(get_db)):
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
            "skills": user.skills or "",
        }

    except Exception as e:
        print("❌ GET ME ERROR:", e)
        return {"error": str(e)}


# 🔥 UPDATE SKILLS
@router.post("/update-skills")
def update_skills(
    data: dict = Body(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db),
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

        return {"msg": "Skills updated", "skills": skills}

    except Exception as e:
        print("❌ UPDATE SKILLS ERROR:", e)
        return {"error": str(e)}


# 🔥 SUGGESTION ENGINE (FINAL FIXED)
@router.get("/suggestions")
def get_suggestions(
    authorization: str = Header(...),
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        uid = decoded.get("uid")

        current_user = db.query(User).filter(User.firebase_uid == uid).first()
        if not current_user:
            return []

        # 🔥 SWIPED
        swiped_ids = {
            s[0]
            for s in db.query(Swipe.swiped_uid).filter(Swipe.swiper_uid == uid).all()
        }

        # 🔥 MATCHED
        matched_ids = set()
        matches = (
            db.query(Match)
            .filter((Match.user1_uid == uid) | (Match.user2_uid == uid))
            .all()
        )

        for m in matches:
            matched_ids.add(m.user1_uid if m.user2_uid == uid else m.user2_uid)

        # 🔥 USERS
        users = (
            db.query(User)
            .filter(
                User.firebase_uid != uid,
                ~User.firebase_uid.in_(swiped_ids),
                ~User.firebase_uid.in_(matched_ids),
            )
            .all()
        )

        results = []

        now = datetime.utcnow()

        for u in users:

            # =========================
            # 1️⃣ SKILL MATCH
            # =========================
            skill_score = 0
            if current_user.skills and u.skills:
                skill_score = calculate_match(current_user.skills, u.skills)

            # =========================
            # 2️⃣ ACTIVITY BOOST (NEW USERS)
            # =========================
            activity_score = 1 if not u.skills else 0.5

            # =========================
            # 3️⃣ FRESHNESS (if created_at exists)
            # =========================
            freshness_score = 0
            if hasattr(u, "created_at") and u.created_at:
                days_old = (now - u.created_at).days
                freshness_score = max(0, 1 - (days_old / 30))  # decay

            # =========================
            # 4️⃣ RANDOM DIVERSITY
            # =========================
            import random

            diversity_score = random.uniform(0, 1)

            # =========================
            # FINAL SCORE
            # =========================
            final_score = (
                skill_score * 0.6
                + activity_score * 0.2
                + freshness_score * 0.1
                + diversity_score * 0.1
            )

            results.append(
                {
                    "uid": u.firebase_uid,
                    "email": u.email,
                    "username": u.username,
                    "skills": u.skills,
                    "score": round(final_score, 3),
                }
            )

        # 🔥 SORT BY AI SCORE
        results.sort(key=lambda x: x["score"], reverse=True)

        # 🔥 PAGINATION
        return results[offset : offset + limit]

    except Exception as e:
        print("❌ AI SUGGESTION ERROR:", e)
        return []
