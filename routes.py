import os
import random
import logging
from flask import Blueprint, render_template, request, jsonify, session, current_app
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import TransportError

from data import preloaded_qa, myths, journey_steps, quiz_data
from guards import check_cache, SAFE_REDIRECT_MESSAGE
from db_service import users_db, save_user_score
from ai_service import generate_voter_readiness_score

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

MYTHS_CONTEXT = "\n".join(
    f"- Index {i}: Myth: {m['myth']} -> Reality: {m['reality']} (Source: {m['source']})"
    for i, m in enumerate(myths)
)

def _get_session_user():
    email = session.get('user_email')
    if email and email in users_db:
        return email, users_db[email]
    return None, None

@main_bp.route('/')
def index():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return render_template('index.html', google_client_id=client_id)

@main_bp.route('/ask', methods=['POST'])
def ask():
    # Note: rate limiter is applied in app.py via the limiter instance on the app
    # but we can also just apply it directly to the app. Here we just keep the logic.
    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    email, user = _get_session_user()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    cached = check_cache(query, preloaded_qa)
    if cached:
        current_maturity = 0
        if user and user.get("status") == "complete":
            user["maturity_score"] = min(100, user.get("maturity_score", 0) + 3)
            current_maturity = user["maturity_score"]
        return jsonify({
            "response": cached,
            "explainability": {
                "why": "Matched a pre-verified educational answer",
                "source": "VoteIQ Knowledge Base",
                "avoided": "Specific election results or party outcomes",
            },
            "maturity": current_maturity,
            "increment": 3,
        })

    # Call AI Service
    ai_result = generate_voter_readiness_score(query, MYTHS_CONTEXT, user)
    
    if ai_result.get("maturity") == 0 and "response" in ai_result:
        # Fallbacks or safety redirects usually return maturity: 0 early
        return jsonify(ai_result)

    current_maturity = 0
    unlocked_count = 0
    maturity_inc = ai_result.get("increment", 0)
    busted_myth_idx = ai_result.get("busted_myth_idx", -1)

    if user and user.get("status") == "complete":
        user["maturity_score"] = min(100, user.get("maturity_score", 0) + maturity_inc)

        if busted_myth_idx != -1 and 0 <= busted_myth_idx < len(myths):
            unlocked = user.setdefault("unlocked_myths", [])
            if busted_myth_idx not in unlocked:
                unlocked.append(busted_myth_idx)

        current_maturity = user["maturity_score"]
        unlocked_count = len(user.get("unlocked_myths", []))
        
        # Save score to Firestore whenever maturity updates
        save_user_score(user.get("id"), current_maturity)

    return jsonify({
        "response": ai_result.get("response"),
        "explainability": ai_result.get("explainability"),
        "maturity": current_maturity,
        "increment": maturity_inc,
        "myth_unlocked": ai_result.get("myth_unlocked", False),
        "unlocked_count": unlocked_count,
    })

@main_bp.route('/journey', methods=['POST'])
def journey():
    _, user = _get_session_user()
    user_step = user.get("current_step", 1) if user and user.get("status") == "complete" else 1
    return jsonify({"steps": journey_steps, "user_step": user_step})

@main_bp.route('/myth', methods=['GET'])
def get_myths():
    _, user = _get_session_user()
    if user and user.get("status") == "complete":
        indices = user.get("unlocked_myths", [])
        unlocked = [myths[i] for i in indices if 0 <= i < len(myths)]
        return jsonify({"myths": unlocked, "total": len(myths), "unlocked": len(unlocked)})
    return jsonify({"myths": [], "total": len(myths), "unlocked": 0})

@main_bp.route('/api/auth/session', methods=['GET'])
def get_session():
    email, user = _get_session_user()
    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "error": "Not authenticated"}), 401

@main_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@main_bp.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json(silent=True) or {}
    token = data.get('credential')
    client_id = os.environ.get("GOOGLE_CLIENT_ID")

    if not token:
        return jsonify({"error": "Token is required"}), 400

    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id
        )
        email = id_info['email']
        name = id_info.get('name', '')
        picture = id_info.get('picture', '')
    except (ValueError, TransportError, Exception) as e:
        logger.warning("Google token verification failed: %s", e)
        return jsonify({"error": "Invalid or expired token"}), 401

    session['user_email'] = email

    if email in users_db:
        user = users_db[email]
        if user.get('status') == 'incomplete':
            user['name'] = name
            user['picture'] = picture
            return jsonify({"status": "success", "is_new": True, "user": user})

        user.setdefault("current_step", 1)
        user.setdefault("maturity_score", 0)
        user.setdefault("quiz_passed", False)
        user.setdefault("unlocked_myths", [])
        return jsonify({"status": "success", "is_new": False, "user": user})

    user_info = {
        "email": email,
        "name": name,
        "picture": picture,
        "status": "incomplete",
    }
    users_db[email] = user_info
    return jsonify({"status": "success", "is_new": True, "user": user_info})

@main_bp.route('/api/auth/signup', methods=['POST'])
def complete_signup():
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    dob = data.get('dob', '')
    state = data.get('state', '')

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    state_code = state if state else "XX"
    demo_id = f"VOTEIQ-{state_code}-2026-{random.randint(1000, 9999)}"

    user.update({
        "dob": dob,
        "state": state,
        "id": demo_id,
        "status": "complete",
        "current_step": 1,
        "maturity_score": 0,
        "quiz_passed": False,
        "unlocked_myths": [],
    })

    return jsonify({"status": "success", "user": user})

@main_bp.route('/api/progress/update', methods=['POST'])
def update_progress():
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    step = data.get('step')

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    if isinstance(step, int):
        current = user.get("current_step", 1)
        if step == current + 1:
            user["current_step"] = step
        elif step > current + 1:
            user["current_step"] = current + 1

    return jsonify({"status": "success", "current_step": user.get("current_step")})

@main_bp.route('/api/quiz', methods=['GET'])
def get_quiz():
    safe_quiz = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz_data
    ]
    return jsonify({"quiz": safe_quiz})

@main_bp.route('/api/quiz/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    answers = data.get('answers')

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    if not isinstance(answers, list) or len(answers) != len(quiz_data):
        return jsonify({"error": "Incomplete or malformed answers"}), 400

    correct_count = sum(
        1 for i, ans in enumerate(answers)
        if isinstance(ans, int) and ans == quiz_data[i]["answer"]
    )

    pass_threshold = max(1, int(len(quiz_data) * 0.75))
    passed = correct_count >= pass_threshold
    if passed:
        user["quiz_passed"] = True
        
    # Save score to Firestore
    save_user_score(user.get("id"), correct_count)

    return jsonify({
        "status": "success",
        "passed": passed,
        "score": correct_count,
        "total": len(quiz_data),
    })
