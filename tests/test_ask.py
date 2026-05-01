# voteiq/tests/test_ask.py
"""Tests for the /ask route: cache, safety guards, myth unlock, and fallbacks (T1)."""
import pytest
from unittest.mock import patch, MagicMock
from app import users_db


class TestAskRoute:
    def test_empty_query_returns_400(self, client):
        resp = client.post('/ask', json={'query': ''})
        assert resp.status_code == 400

    def test_missing_query_returns_400(self, client):
        resp = client.post('/ask', json={})
        assert resp.status_code == 400

    def test_cached_nota_query_returns_response(self, client):
        resp = client.post('/ask', json={'query': 'What is NOTA?'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'response' in data
        assert 'NOTA' in data['response'] or 'None Of The Above' in data['response']

    def test_risky_query_is_blocked(self, client):
        resp = client.post('/ask', json={'query': 'Who won the 2024 election?'})
        assert resp.status_code == 200
        data = resp.get_json()
        # Safety redirect should be returned, not election results
        assert 'educational' in data['response'].lower() or 'official' in data['response'].lower()
        assert data.get('maturity', 0) == 0

    def test_no_model_returns_fallback(self, client):
        with patch('app.model', None):
            resp = client.post('/ask', json={'query': 'How do EVMs work?'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'Gemini' in data['response'] or 'configured' in data['response']

    def test_ai_response_myth_unlocks_for_logged_in_user(self, logged_in_client):
        mock_ai_response = MagicMock()
        mock_ai_response.text = '{"is_myth_question": true, "reply": "EVMs are secure.", "maturity_score_increment": 10, "busted_myth_index": 1}'

        with patch('app.model') as mock_model:
            mock_model.generate_content.return_value = mock_ai_response
            resp = logged_in_client.post('/ask', json={'query': 'Can EVMs be hacked?'})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['myth_unlocked'] is True
        assert 1 in users_db['test@example.com']['unlocked_myths']

    def test_maturity_score_increments_for_logged_in_user(self, logged_in_client):
        mock_ai_response = MagicMock()
        mock_ai_response.text = '{"is_myth_question": false, "reply": "Great question!", "maturity_score_increment": 12, "busted_myth_index": -1}'

        with patch('app.model') as mock_model:
            mock_model.generate_content.return_value = mock_ai_response
            resp = logged_in_client.post('/ask', json={'query': 'What is a Model Code of Conduct?'})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['maturity'] == 12
        assert users_db['test@example.com']['maturity_score'] == 12

    def test_maturity_score_capped_at_100(self, logged_in_client):
        users_db['test@example.com']['maturity_score'] = 95
        mock_ai_response = MagicMock()
        mock_ai_response.text = '{"is_myth_question": false, "reply": "Great!", "maturity_score_increment": 15, "busted_myth_index": -1}'

        with patch('app.model') as mock_model:
            mock_model.generate_content.return_value = mock_ai_response
            resp = logged_in_client.post('/ask', json={'query': 'How long has ECI existed?'})

        assert users_db['test@example.com']['maturity_score'] == 100

    def test_post_scan_risky_response_is_blocked(self, logged_in_client):
        mock_ai_response = MagicMock()
        mock_ai_response.text = '{"is_myth_question": false, "reply": "BJP won the most seats.", "maturity_score_increment": 5, "busted_myth_index": -1}'

        with patch('app.model') as mock_model:
            mock_model.generate_content.return_value = mock_ai_response
            resp = logged_in_client.post('/ask', json={'query': 'Tell me about election outcomes'})

        data = resp.get_json()
        assert 'official' in data['response'].lower() or 'educational' in data['response'].lower()

    def test_gemini_exception_returns_fallback(self, logged_in_client):
        with patch('app.model') as mock_model:
            mock_model.generate_content.side_effect = Exception("API error")
            resp = logged_in_client.post('/ask', json={'query': 'How are ballots counted?'})

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'official' in data['response'].lower() or "couldn't" in data['response'].lower()
