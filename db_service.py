import os
import firebase_admin
from firebase_admin import credentials, firestore

# In-memory database
users_db = {}

# Firebase Firestore client
db = None

def init_firebase():
    """Initialize Firebase Admin SDK using the service account key if available."""
    global db
    try:
        if os.path.exists("firebase_key.json"):
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Firebase init error: {e}")

def save_user_score(user_id, score):
    """
    Stores user quiz score in Firestore for tracking and evaluation.
    """
    if db:
        try:
            db.collection("users").document(user_id).set({
                "score": score,
                "timestamp": firestore.SERVER_TIMESTAMP
            }, merge=True)
            print(f"User {user_id} score saved to Firestore.")
        except Exception as e:
            print(f"Error saving to firestore: {e}")
