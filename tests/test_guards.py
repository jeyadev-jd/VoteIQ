# voteiq/tests/test_guards.py
"""Unit tests for the safety guard functions (T2)."""
import pytest
from guards import (
    normalize_query,
    check_cache,
    is_risky_query,
    post_response_scan,
    SAFE_REDIRECT_MESSAGE,
)

SAMPLE_QA = {
    "what is nota?": "NOTA stands for None Of The Above...",
    "how does voting work?": "Voting in India involves registering...",
    "who won 2024?": SAFE_REDIRECT_MESSAGE,
}


class TestNormalizeQuery:
    def test_lowercases_input(self):
        assert normalize_query("HELLO") == "hello"

    def test_strips_whitespace(self):
        assert normalize_query("  hello  ") == "hello"

    def test_removes_punctuation(self):
        assert normalize_query("What is NOTA?") == "what is nota"

    def test_empty_string(self):
        assert normalize_query("") == ""


class TestCheckCache:
    def test_exact_match(self):
        result = check_cache("what is nota?", SAMPLE_QA)
        assert result == SAMPLE_QA["what is nota?"]

    def test_nota_substring_match(self):
        result = check_cache("Tell me about NOTA please", SAMPLE_QA)
        assert result == SAMPLE_QA["what is nota?"]

    def test_voting_keyword_match(self):
        result = check_cache("How does the voting process work?", SAMPLE_QA)
        assert result == SAMPLE_QA["how does voting work?"]

    def test_no_match_returns_none(self):
        result = check_cache("What is the capital of France?", SAMPLE_QA)
        assert result is None

    def test_who_won_2024_match(self):
        result = check_cache("who won the 2024 election?", SAMPLE_QA)
        assert result == SAFE_REDIRECT_MESSAGE


class TestIsRiskyQuery:
    @pytest.mark.parametrize("query", [
        "who won the election?",
        "which party won seats?",
        "tell me live results",
        "show me vote share",
        "party performance in 2024",
    ])
    def test_risky_queries_detected(self, query):
        assert is_risky_query(query) is True

    @pytest.mark.parametrize("query", [
        "how do I register to vote?",
        "what is NOTA?",
        "explain the EVM process",
        "when is the next election?",
    ])
    def test_safe_queries_allowed(self, query):
        assert is_risky_query(query) is False


class TestPostResponseScan:
    def test_detects_won_in_response(self):
        assert post_response_scan("The BJP won the election.") is True

    def test_detects_seats_in_response(self):
        assert post_response_scan("They secured 200 seats.") is True

    def test_safe_response_passes(self):
        assert post_response_scan("The election process involves multiple stages.") is False

    def test_empty_response_is_safe(self):
        assert post_response_scan("") is False
