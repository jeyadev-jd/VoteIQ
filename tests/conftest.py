# voteiq/tests/conftest.py
import pytest
import os
from unittest.mock import MagicMock, patch

# Set mandatory env vars before importing app
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("GEMINI_API_KEY", "")   # Empty — disables real API calls
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

# Import AFTER env vars are set
from app import app as flask_app, users_db


@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-pytest-only",
    })
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_users_db():
    """Reset the in-memory DB before every test to ensure isolation."""
    users_db.clear()
    yield
    users_db.clear()


@pytest.fixture
def logged_in_client(client):
    """A test client with a logged-in complete user session."""
    users_db["test@example.com"] = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "status": "complete",
        "current_step": 1,
        "maturity_score": 0,
        "quiz_passed": False,
        "unlocked_myths": [],
        "dob": "2000-01-01",
        "state": "KA",
        "id": "VOTEIQ-KA-2026-1234",
    }
    with client.session_transaction() as sess:
        sess['user_email'] = "test@example.com"
    return client
