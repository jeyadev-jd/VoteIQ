# voteiq/tests/test_journey.py
"""Tests for journey progress routes (T5)."""
import pytest
from app import users_db


class TestProgressUpdate:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post('/api/progress/update', json={'step': 2})
        assert resp.status_code == 401

    def test_advancing_step_by_one_is_allowed(self, logged_in_client):
        users_db['test@example.com']['current_step'] = 1
        resp = logged_in_client.post('/api/progress/update', json={'step': 2})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_step'] == 2

    def test_advancing_by_more_than_one_is_clamped(self, logged_in_client):
        """S4 fix: large jumps must be clamped to current_step + 1."""
        users_db['test@example.com']['current_step'] = 1
        resp = logged_in_client.post('/api/progress/update', json={'step': 6})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_step'] == 2  # Clamped, not 6

    def test_going_backward_is_ignored(self, logged_in_client):
        users_db['test@example.com']['current_step'] = 4
        resp = logged_in_client.post('/api/progress/update', json={'step': 2})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_step'] == 4  # Unchanged

    def test_non_integer_step_is_ignored(self, logged_in_client):
        users_db['test@example.com']['current_step'] = 1
        resp = logged_in_client.post('/api/progress/update', json={'step': 'two'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_step'] == 1  # Unchanged


class TestJourneyRoute:
    def test_journey_returns_steps(self, client):
        resp = client.post('/journey', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'steps' in data
        assert len(data['steps']) > 0
        assert 'user_step' in data

    def test_logged_in_user_step_is_returned(self, logged_in_client):
        users_db['test@example.com']['current_step'] = 3
        resp = logged_in_client.post('/journey', json={})
        data = resp.get_json()
        assert data['user_step'] == 3


class TestMythRoute:
    def test_unauthenticated_returns_empty_myths(self, client):
        resp = client.get('/myth')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['myths'] == []
        assert data['unlocked'] == 0

    def test_logged_in_user_gets_unlocked_myths(self, logged_in_client):
        users_db['test@example.com']['unlocked_myths'] = [0, 1]
        resp = logged_in_client.get('/myth')
        data = resp.get_json()
        assert data['unlocked'] == 2
        assert len(data['myths']) == 2

    def test_out_of_bounds_myth_index_is_skipped(self, logged_in_client):
        users_db['test@example.com']['unlocked_myths'] = [0, 999]  # 999 is out of bounds
        resp = logged_in_client.get('/myth')
        data = resp.get_json()
        # The route renders only valid indices, so myths list has 1 item (index 0 only)
        # But unlocked count reflects all stored indices (2)
        assert len(data['myths']) == 1   # Only index 0 is valid and rendered
        assert data['total'] > 0         # Total myths count is always > 0
