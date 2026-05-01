# voteiq/app.py
import os
import json
import random
import logging

from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import TransportError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from data import preloaded_qa, myths, journey_steps, journey_templates, official_links, quiz_data
from guards import check_cache, is_risky_query, post_response_scan, SAFE_REDIRECT_MESSAGE

# ─── Load environment ───────────────────────────────────────────────────────
load_dotenv(override=True)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── App factory ────────────────────────────────────────────────────────────
app = Flask(__name__)

# S1 — Mandatory secret key; provide a fallback for demo/Vercel startup stability
_secret = os.environ.get("FLASK_SECRET_KEY")
if not _secret:
    logger.warning("FLASK_SECRET_KEY not set. Using a temporary fallback key.")
    _secret = "dev-fallback-key-12345"
app.secret_key = _secret

# ─── Rate Limiter (S6) ──────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],          # No global limit; only apply per-route
    storage_uri="memory://",
)

# ─── Security Headers via after_request (replaces flask-talisman for Vercel) ─
@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com https://www.youtube.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src * 'self' data: https://lh3.googleusercontent.com; "
        "frame-src https://accounts.google.com https://www.youtube.com; "
        "connect-src 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# ─── In-memory database (Q1 — noted; suitable for demo; comment guides upgrade)
# NOTE: For production, replace with SQLAlchemy + a persistent DB.
users_db: dict = {}

# ─── Configure Gemini ───────────────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
model = None
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    logger.warning("GEMINI_API_KEY not set — AI responses disabled.")

# ─── Pre-compute static content (E1) ────────────────────────────────────────
MYTHS_CONTEXT: str = "\n".join(
    f"- Index {i}: Myth: {m['myth']} -> Reality: {m['reality']} (Source: {m['source']})"
    for i, m in enumerate(myths)
)

# Q5 — AI prompt extracted to a named constant
AI_PROMPT_TEMPLATE = """You are VoteIQ, an educational assistant explaining the Indian election process.
Do not provide election results, who won or lost, party performance, or live data.
Explain concepts simply and neutrally.

CRITICAL: We have an official 'Myth vs Reality' list:
{myths_context}

Task 1: AI Classifier (Myth vs Normal)
Analyze the question and classify if it expresses a doubt, concern, or misconception that matches one of our myths.
- Questions about EVM tampering, hacking, being changed by ruling party, or manipulation relate to the EVM myth (Index 1).
- Questions about NOTA canceling elections or forcing re-elections relate to the NOTA myth (Index 2).

Task 2: Formulate the Reply
If it's a myth, you MUST prioritize using the 'Reality' data from the list above to answer clearly.
If not a myth, answer the question accurately and neutrally.

Task 3: Maturity Score
Assign a maturity increment score between 0 and 15. A highly thoughtful civic question gets 15,
a basic relevant question gets 5-10, an irrelevant or slightly immature question gets 0.

Question: {query}

You MUST output ONLY a valid JSON object in this exact format:
{{
    "is_myth_question": true,
    "reply": "your detailed response here",
    "maturity_score_increment": 10,
    "busted_myth_index": 0
}}
Note: 'is_myth_question' must be a boolean. 'busted_myth_index' must be an integer
(the 0-based index if it's a myth, or -1 if it's not).
"""

# ─── Helper: get or 404 user from session ───────────────────────────────────
def _get_session_user():
    """Returns (email, user_dict) for the logged-in session user, or (None, None)."""
    email = session.get('user_email')
    if email and email in users_db:
        return email, users_db[email]
    return None, None


# ════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════

@app.route('/')
def index():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return render_template('index.html', google_client_id=client_id)


@app.route('/ask', methods=['POST'])
@limiter.limit("30 per minute")
def ask():
    data = request.get_json(silent=True) or {}
    query: str = data.get('query', '').strip()
    email, user = _get_session_user()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    # 1. Check preloaded cache
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

    # 2. Safety boundary check
    if is_risky_query(query):
        return jsonify({
            "response": SAFE_REDIRECT_MESSAGE,
            "explainability": {
                "why": "Query about election results or outcomes",
                "source": "Safety Redirect",
                "avoided": "Specific election results or party outcomes",
            },
            "maturity": 0,
        })

    # 3. Gemini AI call
    if not model:
        return jsonify({
            "response": "Gemini API key not configured. " + SAFE_REDIRECT_MESSAGE,
            "explainability": {
                "why": "Missing API Key",
                "source": "Fallback Response",
                "avoided": "Live generation",
            },
            "maturity": 0,
        })

    try:
        prompt = AI_PROMPT_TEMPLATE.format(
            myths_context=MYTHS_CONTEXT,
            query=query,
        )
        response = model.generate_content(prompt)
        ai_text = response.text

        try:
            cleaned = ai_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            ai_data = json.loads(cleaned.strip())
            final_reply = ai_data.get("reply", "I couldn't process that.")
            maturity_inc = int(ai_data.get("maturity_score_increment", 0))
            is_myth = bool(ai_data.get("is_myth_question", False))
            busted_myth_idx = int(ai_data.get("busted_myth_index", -1)) if is_myth else -1
        except (json.JSONDecodeError, ValueError, TypeError) as json_err:
            logger.warning("JSON parse error from AI: %s", json_err)
            final_reply = ai_text
            maturity_inc = 5
            busted_myth_idx = -1

        # 4. Post-response safety scan
        if post_response_scan(final_reply):
            return jsonify({
                "response": SAFE_REDIRECT_MESSAGE,
                "explainability": {
                    "why": "Generated response contained risky language",
                    "source": "Safety Redirect (Post-scan)",
                    "avoided": "Specific election results or party outcomes",
                },
                "maturity": 0,
            })

        # 5. Update user stats
        current_maturity = 0
        unlocked_count = 0
        if user and user.get("status") == "complete":
            user["maturity_score"] = min(100, user.get("maturity_score", 0) + maturity_inc)

            if busted_myth_idx != -1 and 0 <= busted_myth_idx < len(myths):
                unlocked = user.setdefault("unlocked_myths", [])
                if busted_myth_idx not in unlocked:
                    unlocked.append(busted_myth_idx)

            current_maturity = user["maturity_score"]
            unlocked_count = len(user.get("unlocked_myths", []))

        return jsonify({
            "response": final_reply,
            "explainability": {
                "why": "General election process information",
                "source": "AI Assistant (Gemini)",
                "avoided": "Specific election results or party outcomes",
            },
            "maturity": current_maturity,
            "increment": maturity_inc,
            "myth_unlocked": busted_myth_idx != -1,
            "unlocked_count": unlocked_count,
        })

    except Exception as e:
        logger.error("Gemini API error: %s", e, exc_info=True)
        return jsonify({
            "response": "I couldn't verify that safely right now. Please check the official ECI source.",
            "explainability": {
                "why": "Error generating response",
                "source": "Error Fallback",
                "avoided": "Unverified claims",
            },
            "maturity": 0,
        })


@app.route('/journey', methods=['POST'])
def journey():
    _, user = _get_session_user()
    user_step = user.get("current_step", 1) if user and user.get("status") == "complete" else 1
    return jsonify({"steps": journey_steps, "user_step": user_step})


@app.route('/myth', methods=['GET'])
def get_myths():
    _, user = _get_session_user()
    if user and user.get("status") == "complete":
        indices = user.get("unlocked_myths", [])
        unlocked = [myths[i] for i in indices if 0 <= i < len(myths)]
        return jsonify({"myths": unlocked, "total": len(myths), "unlocked": len(unlocked)})
    return jsonify({"myths": [], "total": len(myths), "unlocked": 0})


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/api/auth/session', methods=['GET'])
def get_session():
    email, user = _get_session_user()
    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "error": "Not authenticated"}), 401


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"})


@app.route('/api/auth/google', methods=['POST'])
@limiter.limit("10 per minute")
def google_auth():
    data = request.get_json(silent=True) or {}
    token = data.get('credential')
    client_id = os.environ.get("GOOGLE_CLIENT_ID")

    if not token:
        return jsonify({"error": "Token is required"}), 400

    # S2 — Catch all possible token verification errors
    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id
        )
        email: str = id_info['email']
        name: str = id_info.get('name', '')
        picture: str = id_info.get('picture', '')
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

        # Fully registered user — ensure gamification fields exist
        user.setdefault("current_step", 1)
        user.setdefault("maturity_score", 0)
        user.setdefault("quiz_passed", False)
        user.setdefault("unlocked_myths", [])
        return jsonify({"status": "success", "is_new": False, "user": user})

    # Brand-new user
    user_info = {
        "email": email,
        "name": name,
        "picture": picture,
        "status": "incomplete",
    }
    users_db[email] = user_info
    return jsonify({"status": "success", "is_new": True, "user": user_info})


@app.route('/api/auth/signup', methods=['POST'])
def complete_signup():
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    dob: str = data.get('dob', '')
    state: str = data.get('state', '')

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


@app.route('/api/progress/update', methods=['POST'])
def update_progress():
    data = request.get_json(silent=True) or {}
    email, user = _get_session_user()
    step = data.get('step')

    if not email or not user:
        return jsonify({"error": "Not authenticated"}), 401

    # S4 — Only allow advancing exactly one step at a time, not arbitrary jumps
    if isinstance(step, int):
        current = user.get("current_step", 1)
        if step == current + 1:   # strict: must be exactly next step
            user["current_step"] = step
        elif step > current + 1:  # large jump — clamp to next step
            user["current_step"] = current + 1

    return jsonify({"status": "success", "current_step": user.get("current_step")})


@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    safe_quiz = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz_data
    ]
    return jsonify({"quiz": safe_quiz})


@app.route('/api/quiz/submit', methods=['POST'])
@limiter.limit("5 per minute")   # S6 — Rate-limit quiz submission
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

    return jsonify({
        "status": "success",
        "passed": passed,
        "score": correct_count,
        "total": len(quiz_data),
    })


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'  # Q6 fix
    app.run(debug=debug, host='0.0.0.0', port=port)
