"""
app.py — VoteIQ Flask application factory and entry point.

Wires together all application components:
  - Flask app configuration and secret-key management.
  - Rate limiter (flask-limiter) with per-route policies.
  - Strict Content-Security-Policy and security response headers.
  - Firebase Admin SDK initialisation (db_service).
  - Gemini AI model configuration (ai_service).
  - Blueprint registration (routes).
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ai_service import configure_ai
from db_service import init_firebase
from routes import main_bp

# ─── Load environment variables ─────────────────────────────────────────────
load_dotenv(override=True)

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Flask application ───────────────────────────────────────────────────────
app = Flask(__name__)

# S1 — Secret key is mandatory for signed sessions; fail loudly in production
_secret: str = os.environ.get("FLASK_SECRET_KEY", "")
if not _secret:
    logger.warning("FLASK_SECRET_KEY not set — using a temporary key for demo.")
    _secret = "dev-fallback-key-12345"
app.secret_key = _secret

# Harden session cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

# ─── Rate Limiter (S6) ───────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],       # No blanket limit; each route opts in explicitly
    storage_uri="memory://",
)

# ─── Security Headers ─────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response: Response) -> Response:
    """
    Attach security headers to every outgoing response.

    Implements a strict Content-Security-Policy that whitelists only the
    external origins required by the application (Google Accounts, YouTube,
    Google Fonts, Bootstrap CDN, and Firebase/gstatic for analytics).
    """
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com https://www.youtube.com "
        "https://cdn.jsdelivr.net https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://accounts.google.com "
        "https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src * 'self' data: https://lh3.googleusercontent.com "
        "https://upload.wikimedia.org; "
        "frame-src https://accounts.google.com https://www.youtube.com; "
        "connect-src 'self' https://region1.google-analytics.com "
        "https://firestore.googleapis.com;"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# ─── Initialise external services ───────────────────────────────────────────
init_firebase()   # Firebase Admin SDK + Firestore client
configure_ai()    # Google Gemini generative model

# ─── Register Blueprint ──────────────────────────────────────────────────────
app.register_blueprint(main_bp)

# Apply per-route rate limits after registration so view-function names resolve
_rate_limits = {
    "main.ask": "30 per minute",
    "main.google_auth": "10 per minute",
    "main.submit_quiz": "5 per minute",
}
for endpoint, limit_str in _rate_limits.items():
    view_fn = app.view_functions.get(endpoint)
    if view_fn:
        limiter.limit(limit_str)(view_fn)

# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port: int = int(os.environ.get("PORT", 8080))
    debug: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)
