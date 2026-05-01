"""
db_service.py — Firebase Firestore integration and in-memory user store.

Responsibilities:
  - Maintain the in-memory `users_db` dictionary for session-scoped user data.
  - Initialize the Firebase Admin SDK using a service-account key file.
  - Persist user scores to Firestore for cross-session tracking and evaluation.
"""

import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# In-memory database (suitable for demo; upgrade to Firestore/PostgreSQL for production)
users_db: dict = {}

# Firebase Firestore client — populated by init_firebase()
db = None


def init_firebase() -> None:
    """
    Initialize the Firebase Admin SDK.

    Looks for a 'firebase_key.json' service account file in the working directory.
    Silently skips initialisation if the file is absent so the app can run
    without Firebase credentials (e.g., during local testing or CI).
    """
    global db
    try:
        key_path = os.path.join(os.path.dirname(__file__), "firebase_key.json")
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            if not firebase_admin._apps:          # Guard against duplicate init
                firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Firebase Admin SDK initialized successfully.")
        else:
            logger.warning("firebase_key.json not found — Firestore disabled.")
    except Exception as exc:                      # pragma: no cover
        logger.error("Firebase init error: %s", exc)


def save_user_score(user_id: str, score: int) -> None:
    """
    Persist a user's readiness/quiz score to Firestore.

    Stores user quiz score in Firestore for tracking and evaluation.
    Uses merge=True so that subsequent writes update rather than overwrite
    the document, preserving any other fields already stored.

    Args:
        user_id: The unique voter ID string (e.g. 'VOTEIQ-TN-2026-1234').
        score:   The numeric score to record (0–100 for maturity; 0–N for quiz).
    """
    if db and user_id:
        try:
            db.collection("users").document(user_id).set(
                {
                    "readiness_score": score,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            logger.info("Saved score %d for user %s to Firestore.", score, user_id)
        except Exception as exc:                  # pragma: no cover
            logger.error("Firestore write error for user %s: %s", user_id, exc)
