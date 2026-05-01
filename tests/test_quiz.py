# voteiq/tests/test_quiz.py
"""Tests for quiz retrieval and scoring routes (T3)."""
import json
import pytest
from app import users_db


class TestGetQuiz:
    def test_quiz_returns_questions(self, client):
        resp = client.get('/api/quiz')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'quiz' in data
        assert len(data['quiz']) > 0

    def test_quiz_does_not_expose_answers(self, client):
        resp = client.get('/api/quiz')
        data = resp.get_json()
        for q in data['quiz']:
            assert 'answer' not in q
            assert 'question' in q
            assert 'options' in q


class TestSubmitQuiz:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post('/api/quiz/submit',
                           json={'answers': [0, 0, 0, 0]})
        assert resp.status_code == 401

    def test_incomplete_answers_returns_400(self, logged_in_client):
        # Send no answers at all
        resp = logged_in_client.post('/api/quiz/submit', json={'answers': []})
        assert resp.status_code == 400

    def test_correct_quiz_marks_passed(self, logged_in_client):
        """Passing all questions should set quiz_passed = True."""
        from data import quiz_data
        correct_answers = [q['answer'] for q in quiz_data]
        resp = logged_in_client.post('/api/quiz/submit',
                                     json={'answers': correct_answers})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['passed'] is True
        assert data['score'] == data['total']
        assert users_db['test@example.com']['quiz_passed'] is True

    def test_all_wrong_answers_fails(self, logged_in_client):
        from data import quiz_data
        wrong_answers = [(q['answer'] + 1) % len(q['options']) for q in quiz_data]
        resp = logged_in_client.post('/api/quiz/submit',
                                     json={'answers': wrong_answers})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['passed'] is False
        assert data['score'] == 0

    def test_pass_threshold_is_75_percent(self, logged_in_client):
        """Exactly 75% correct should pass."""
        from data import quiz_data
        answers = [q['answer'] for q in quiz_data]
        total = len(quiz_data)
        # Flip the last 25% to wrong
        fail_count = total - max(1, int(total * 0.75))
        for i in range(fail_count):
            answers[-(i + 1)] = (answers[-(i + 1)] + 1) % len(quiz_data[-(i + 1)]['options'])

        resp = logged_in_client.post('/api/quiz/submit', json={'answers': answers})
        data = resp.get_json()
        assert data['passed'] is True
