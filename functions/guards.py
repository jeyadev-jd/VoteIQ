# voteiq/guards.py
import re

RISKY_PHRASES = [
    "who won", "who lost", "seats", "vote share", "margins", 
    "party performance", "live results", "result trends", "outcome"
]

POST_SCAN_RISKY = [
    "won", "lost", "leads", "seats", "vote %", "party performance"
]

SAFE_REDIRECT_MESSAGE = "I am an educational assistant focused on explaining the election process. I do not provide election results, party performance, or winner claims. Please check the official Election Commission of India website for results."

def normalize_query(query: str) -> str:
    """Normalizes the query by lowercasing and removing non-alphanumeric chars."""
    q = query.lower().strip()
    q = re.sub(r'[^a-z0-9\s]', '', q)
    return q

def check_cache(query: str, preloaded_qa: dict) -> str:
    """Checks for an exact match or simple token overlap against the preloaded QA cache."""
    normalized = normalize_query(query)
    
    # Exact match on normalized keys
    for k, v in preloaded_qa.items():
        if normalize_query(k) == normalized:
            return v
            
    # Substring match for guaranteed demo queries
    if "nota" in normalized:
        return preloaded_qa.get("what is nota?")
    if "how" in normalized and "voting" in normalized:
        return preloaded_qa.get("how does voting work?")
    if "who won" in normalized and "2024" in normalized:
        return preloaded_qa.get("who won 2024?")
        
    return None

def is_risky_query(query: str) -> bool:
    """Returns True if the query asks about election results or outcomes."""
    normalized = normalize_query(query)
    for phrase in RISKY_PHRASES:
        if phrase in normalized:
            return True
    return False

def post_response_scan(response: str) -> bool:
    """Returns True if the AI response contains risky result-oriented language."""
    normalized = normalize_query(response)
    for phrase in POST_SCAN_RISKY:
        if phrase in normalized:
            return True
    return False
