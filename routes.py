"""
routes.py — Flask Blueprint containing all HTTP route handlers for VoteIQ.

Route groups:
  - Public:   GET /   — renders the single-page application shell.
  - AI Chat:  POST /ask — query the Gemini AI with safety guardrails.
  - Journey:  POST /journey — return voter-journey step data.
  - Myths:    GET /myth — return unlocked myth/reality cards for the user.
  - Auth:     /api/auth/* — Google OAuth sign-in, sign-up, session, logout.
  - Progress: POST /api/progress/update — advance the user's journey step.
  - Quiz:     GET /api/quiz, POST /api/quiz/submit — eligibility quiz flow.
"""

import logging
import os
import random
from typing import Optional, Tuple

from flask import Blueprint, jsonify, render_template, request, session
from google.auth.exceptions import TransportError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from ai_service import generate_voter_readiness_score
from data import journey_steps, myths, preloaded_qa, quiz_data
from db_service import save_user_score, users_db
from guards import SAFE_REDIRECT_MESSAGE, check_cache

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)

# Pre-compute static myth context string once at module load (efficiency)
MYTHS_CONTEXT: str = "\n".join(
    f"- Index {i}: Myth: {m['myth']} -> Reality: {m['reality']} (Source: {m['source']})"
    for i, m in enumerate(myths)
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_session_user() -> Tuple[Optional[str], Optional[dict]]:
    """
    Retrieve the authenticated user from the server-side session.

    Returns:
        A (email, user_dict) tuple, or (None, None) if not authenticated.
    """
    email: Optional[str] = session.get("user_email")
    if email and email in users_db:
        return email, users_db[email]
    return None, None


def _sanitize_string(value: str, max_length: int = 512) -> str:
    """
    Trim and length-cap a user-supplied string to prevent oversized inputs.

    Args:
        value:      Raw string from request JSON.
        max_length: Maximum number of characters to allow.

    Returns:
        The sanitized string, stripped of leading/trailing whitespace.
    """
    return str(value).strip()[:max_length]


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@main_bp.route("/")
def index():
    """Render the VoteIQ single-page application shell."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return render_template("index.html", google_client_id=client_id)


# ---------------------------------------------------------------------------
# AI Chat
# ---------------------------------------------------------------------------

@main_bp.route("/ask", methods=["POST"])
def ask():
    """
    Accept a civic question, run it through the safety pipeline, and return
    an AI-generated educational response with explainability metadata.

    Rate-limited to 30 requests/minute per IP (applied in app.py).

    Request JSON:
        query (str): The user's question (max 512 chars).

    Returns:
        JSON with keys: response, explainability, maturity, increment,
        myth_unlocked (bool), unlocked_count (int).
    """
    data = request.get_json(silent=True) or {}
    raw_query: str = data.get("query", "")
    query = _sanitize_string(raw_query)
    email, user = _get_session_user()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    # 1. Fast-path: pre-verified cache
    cached = check_cache(query, preloaded_qa)
    if cached:
        current_maturity = 0
        if user and user.get("status") == "complete":
            user["maturity_score"] = min(100, user.get("maturity_score", 0) + 3)
            current_maturity = user["maturity_score"]
        return jsonify(
            {
                "response": cached,
                "explainability": {
                    "why": "Matched a pre-verified educational answer",
                    "source": "VoteIQ Knowledge Base",
                    "avoided": "Specific election results or party outcomes",
                },
                "maturity": current_maturity,
                "increment": 3,
            }
        )

    # 2. AI generation (includes risky-query filter + post-scan inside service)
    ai_result = generate_voter_readiness_score(query, MYTHS_CONTEXT, user)

    # Safety redirects always carry maturity == 0 and no 'increment' key
    if "increment" not in ai_result:
        return jsonify(ai_result)

    # 3. Update in-memory user stats
    current_maturity = 0
    unlocked_count = 0
    maturity_inc: int = ai_result.get("increment", 0)
    busted_myth_idx: int = ai_result.get("busted_myth_idx", -1)

    if user and user.get("status") == "complete":
        user["maturity_score"] = min(100, user.get("maturity_score", 0) + maturity_inc)

        if 0 <= busted_myth_idx < len(myths):
            unlocked: list = user.setdefault("unlocked_myths", [])
            if busted_myth_idx not in unlocked:
                unlocked.append(busted_myth_idx)

        current_maturity = user["maturity_score"]
        unlocked_count = len(user.get("unlocked_myths", []))

        # Persist updated maturity to Firestore
        save_user_score(user.get("id"), current_maturity)

    return jsonify(
        {
            "response": ai_result.get("response"),
            "explainability": ai_result.get("explainability"),
            "maturity": current_maturity,
            "increment": maturity_inc,
            "myth_unlocked": ai_result.get("myth_unlocked", False),
            "unlocked_count": unlocked_count,
        }
    )


# ---------------------------------------------------------------------------
# Voter Journey
# ---------------------------------------------------------------------------

@main_bp.route("/journey", methods=["POST"])
def journey():
    """
    Return the structured voter-journey steps and the user's current progress.

    Returns:
        JSON with keys: steps (list), user_step (int).
    """
    _, user = _get_session_user()
    user_step: int = (
        user.get("current_step", 1) if user and user.get("status") == "complete" else 1
    )
    return jsonify({"steps": journey_steps, "user_step": user_step})


# ---------------------------------------------------------------------------
# Myth Buster
# ---------------------------------------------------------------------------

@main_bp.route("/myth", methods=["GET"])
def get_myths():
    """
    Return the user's unlocked myth/reality cards.

    Unauthenticated users receive an empty list so the UI can display
    a prompt to sign in and start exploring.

    Returns:
        JSON with keys: myths (list), total (int), unlocked (int).
    """
    _, user = _get_session_user()
    if user and user.get("status") == "complete":
        indices: list = user.get("unlocked_myths", [])
        unlocked = [myths[i] for i in indices if 0 <= i < len(myths)]
        return jsonify({"myths": unlocked, "total": len(myths), "unlocked": len(unlocked)})
    return jsonify({"myths": [], "total": len(myths), "unlocked": 0})


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@main_bp.route("/api/auth/session", methods=["GET"])
def get_session():
    """
    Return the current authenticated user's profile if a valid session exists.

    Returns:
        200 JSON with user profile, or 401 if not authenticated.
    """
    email, user = _get_session_user()
    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "error": "Not authenticated"}), 401


@main_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    Invalidate the server-side session, effectively signing the user out.

    Returns:
        JSON {"status": "success"}.
    """
    session.clear()
    return jsonify({"status": "success"})


@main_bp.route("/api/auth/google", methods=["POST"])
def google_auth():
    """
    Verify a Google One-Tap credential and create or retrieve a user record.

    Rate-limited to 10 requests/minute per IP (applied in app.py).

    Request JSON:
        credential (str): The Google ID-token JWT.

    Returns:
        200 JSON with user profile and is_new flag, or 400/401 on failure.
    """
    data = request.get_json(silent=True) or {}
    token: str = data.get("credential", "")
    client_id: Optional[str] = os.environ.get("GOOGLE_CLIENT_ID")

    if not token:
        return jsonify({"error": "Token is required"}), 400

    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id
        )
        email: str = id_info["email"]
        name: str = id_info.get("name", "")
        picture: str = id_info.get("picture", "")
    except (ValueError, TransportError, Exception) as exc:
        logger.warning("Google token verification failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    session["user_email"] = email

    if email in users_db:
        user = users_db[email]
        if user.get("status") == "incomplete":
            user.update({"name": name, "picture": picture})
            return jsonify({"status": "success", "is_new": True, "user": user})

        # Ensure gamification fields exist on returning users
        user.setdefault("current_step", 1)
        user.setdefault("maturity_score", 0)
        user.setdefault("quiz_passed", False)
        user.setdefault("unlocked_myths", [])
        return jsonify({"status": "success", "is_new": False, "user": user})

    # First-time sign-in — record incomplete profile awaiting DOB + state
    new_user: dict = {
        "email": email,
        "name": name,
        "picture": picture,
        "status": "incomplete",
    }
    users_db[email] = new_user
    return jsonify({"status": "success", "is_new": True, "user": new_user})


@main_bp.route("/api/auth/signup", methods=["POST"])
def complete_signup():
    """
    Complete the user's profile by recording their date of birth and state.

    Requires an active authenticated session (partial sign-in).

    Request JSON:
        dob   (str): ISO-format date of birth (YYYY-MM-DD).
        state (str): Two-letter Indian state code.

    Returns:
        200 JSON with the completed user profile, or 401 if not authenticated.
    """
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    dob: str = _sanitize_string(data.get("dob", ""), 20)
    state: str = _sanitize_string(data.get("state", ""), 10)
    state_code = state if state else "XX"
    demo_id = f"VOTEIQ-{state_code}-2026-{random.randint(1000, 9999)}"

    user.update(
        {
            "dob": dob,
            "state": state,
            "id": demo_id,
            "status": "complete",
            "current_step": 1,
            "maturity_score": 0,
            "quiz_passed": False,
            "unlocked_myths": [],
        }
    )
    return jsonify({"status": "success", "user": user})


# ---------------------------------------------------------------------------
# Progress Tracking
# ---------------------------------------------------------------------------

@main_bp.route("/api/progress/update", methods=["POST"])
def update_progress():
    """
    Advance the authenticated user's voter-journey step by exactly one increment.

    Enforces sequential progression — large jumps are clamped to the next step
    to prevent users from skipping journey content.

    Request JSON:
        step (int): The step number the client is requesting to unlock.

    Returns:
        200 JSON with the updated current_step, or 401 if not authenticated.
    """
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    step = data.get("step")

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    if isinstance(step, int):
        current: int = user.get("current_step", 1)
        if step == current + 1:
            user["current_step"] = step
        elif step > current + 1:          # Prevent arbitrary jumps
            user["current_step"] = current + 1

    return jsonify({"status": "success", "current_step": user.get("current_step")})


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

@main_bp.route("/api/quiz", methods=["GET"])
def get_quiz():
    """
    Return the eligibility quiz questions and answer options (answers omitted).

    Returns:
        JSON with key: quiz (list of {question, options} dicts).
    """
    safe_quiz = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz_data
    ]
    return jsonify({"quiz": safe_quiz})


@main_bp.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    """
    Grade a quiz submission and update the user's quiz_passed status.

    Rate-limited to 5 requests/minute per IP (applied in app.py).
    Requires a pass threshold of 75 % correct answers.
    Persists the quiz score to Firestore on every submission attempt.

    Request JSON:
        answers (list[int]): Zero-based option indices, one per question.

    Returns:
        200 JSON with {status, passed, score, total}, or 400/401 on error.
    """
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    answers = data.get("answers")

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    if not isinstance(answers, list) or len(answers) != len(quiz_data):
        return jsonify({"error": "Incomplete or malformed answers"}), 400

    correct_count: int = sum(
        1
        for i, ans in enumerate(answers)
        if isinstance(ans, int) and ans == quiz_data[i]["answer"]
    )

    pass_threshold: int = max(1, int(len(quiz_data) * 0.75))
    passed: bool = correct_count >= pass_threshold
    if passed:
        user["quiz_passed"] = True

    # Persist quiz score to Firestore for evaluation tracking
    save_user_score(user.get("id"), correct_count)

    return jsonify(
        {
            "status": "success",
            "passed": passed,
            "score": correct_count,
            "total": len(quiz_data),
        }
    )
