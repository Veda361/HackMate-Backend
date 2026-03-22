from dotenv import load_dotenv
import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException

# 🔥 Load environment variables
load_dotenv()


def init_firebase():
    firebase_json = os.getenv("FIREBASE_CREDENTIALS")

    print("🔥 Initializing Firebase...")

    if not firebase_json:
        print("❌ FIREBASE_CREDENTIALS NOT FOUND")
        raise ValueError("FIREBASE_CREDENTIALS not set")

    try:
        # Remove extra quotes if present
        if firebase_json.startswith("'") or firebase_json.startswith('"'):
            firebase_json = firebase_json.strip("'\"")

        cred_dict = json.loads(firebase_json)

        # Fix private key formatting
        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

        # Initialize Firebase only once
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully")

    except json.JSONDecodeError as e:
        print("❌ JSON ERROR:", str(e))
        raise ValueError(f"Invalid FIREBASE_CREDENTIALS JSON: {str(e)}")

    except Exception as e:
        print("❌ FIREBASE INIT ERROR:", str(e))
        raise ValueError(f"Firebase initialization failed: {str(e)}")


# 🔥 Initialize Firebase on startup
init_firebase()


# 🔥 VERIFY TOKEN (WITH FULL DEBUG)
def verify_token(token: str):
    try:
        print("🔐 Verifying token...")

        if not token:
            raise HTTPException(status_code=401, detail="No token")

        decoded = auth.verify_id_token(token)

        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
        }

    except Exception as e:
        print("❌ TOKEN ERROR:", str(e))

        # 🔥 IMPORTANT: ALWAYS RETURN RESPONSE (DON'T HANG)
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )