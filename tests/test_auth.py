# voteiq/tests/test_auth.py
"""Tests for Google OAuth, signup, session, and logout routes (T4)."""
import json
import pytest
from unittest.mock import patch, MagicMock
from app import users_db


class TestGetSession:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get('/api/auth/session')
        assert resp.status_code == 401

    def test_authenticated_returns_user(self, logged_in_client):
        resp = logged_in_client.get('/api/auth/session')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['user']['email'] == 'test@example.com'


class TestLogout:
    def test_logout_clears_session(self, logged_in_client):
        resp = logged_in_client.post('/api/auth/logout')
        assert resp.status_code == 200
        # After logout, session endpoint should return 401
        resp2 = logged_in_client.get('/api/auth/session')
        assert resp2.status_code == 401


class TestGoogleAuth:
    def test_missing_credential_returns_400(self, client):
        resp = client.post('/api/auth/google', json={})
        assert resp.status_code == 400

    def test_invalid_token_returns_401(self, client):
        with patch('app.id_token.verify_oauth2_token', side_effect=ValueError("bad token")):
            resp = client.post('/api/auth/google', json={'credential': 'bad-token'})
        assert resp.status_code == 401

    def test_new_user_created_with_incomplete_status(self, client):
        mock_id_info = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'picture': 'https://lh3.googleusercontent.com/photo.jpg',
        }
        with patch('app.id_token.verify_oauth2_token', return_value=mock_id_info):
            resp = client.post('/api/auth/google', json={'credential': 'valid-token'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_new'] is True
        assert data['user']['status'] == 'incomplete'
        assert 'newuser@example.com' in users_db

    def test_existing_complete_user_returns_is_new_false(self, client):
        users_db['existing@example.com'] = {
            'email': 'existing@example.com',
            'name': 'Existing',
            'picture': '',
            'status': 'complete',
            'current_step': 1,
            'maturity_score': 50,
            'quiz_passed': False,
            'unlocked_myths': [],
        }
        mock_id_info = {
            'email': 'existing@example.com',
            'name': 'Existing',
            'picture': '',
        }
        with patch('app.id_token.verify_oauth2_token', return_value=mock_id_info):
            resp = client.post('/api/auth/google', json={'credential': 'valid-token'})
        data = resp.get_json()
        assert data['is_new'] is False


class TestCompleteSignup:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post('/api/auth/signup', json={'state': 'KA', 'dob': '2000-01-01'})
        assert resp.status_code == 401

    def test_signup_completes_user_profile(self, client):
        # Simulate an incomplete user in session
        users_db['new@example.com'] = {
            'email': 'new@example.com',
            'name': 'New',
            'picture': '',
            'status': 'incomplete',
        }
        with client.session_transaction() as sess:
            sess['user_email'] = 'new@example.com'

        resp = client.post('/api/auth/signup', json={'state': 'TN', 'dob': '1998-05-15'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['user']['status'] == 'complete'
        assert data['user']['state'] == 'TN'
        assert data['user']['dob'] == '1998-05-15'
        assert 'quiz_passed' in data['user']
        assert data['user']['maturity_score'] == 0
