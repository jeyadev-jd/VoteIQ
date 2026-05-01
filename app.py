# voteiq/app.py
import os
import logging
from flask import Flask
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from routes import main_bp
from db_service import init_firebase
from ai_service import configure_ai

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

# Apply rate limits manually since we use blueprints

# ─── Security Headers via after_request (replaces flask-talisman for Vercel) ─
@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com https://www.youtube.com https://cdn.jsdelivr.net https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src * 'self' data: https://lh3.googleusercontent.com; "
        "frame-src https://accounts.google.com https://www.youtube.com; "
        "connect-src 'self' https://region1.google-analytics.com;"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# ─── Initialize Services ────────────────────────────────────────────────────
init_firebase()
configure_ai()

# ─── Register Blueprint ─────────────────────────────────────────────────────
app.register_blueprint(main_bp)

# Apply rate limits manually since we use blueprints
if app.view_functions.get('main.ask'): limiter.limit("30 per minute")(app.view_functions.get('main.ask'))
if app.view_functions.get('main.google_auth'): limiter.limit("10 per minute")(app.view_functions.get('main.google_auth'))
if app.view_functions.get('main.submit_quiz'): limiter.limit("5 per minute")(app.view_functions.get('main.submit_quiz'))

# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
