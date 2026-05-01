"""
ai_service.py — Google Gemini AI integration for VoteIQ.

Responsibilities:
  - Configure the Gemini generative model from an environment variable.
  - Provide generate_voter_readiness_score() as the single AI entry point,
    returning a structured dict consumed by the /ask route.
  - Apply pre- and post-response safety scanning to prevent the AI from
    surfacing election results, partisan claims, or harmful content.
"""

import json
import logging
import os
from typing import Any

import google.generativeai as genai

from guards import SAFE_REDIRECT_MESSAGE, is_risky_query, post_response_scan

logger = logging.getLogger(__name__)

# Gemini model singleton — initialised once in configure_ai()
model: Any = None

# ---------------------------------------------------------------------------
# Prompt template (extracted as a constant for auditability and easy updates)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Explainability payloads — centralised so every exit path is consistent
# ---------------------------------------------------------------------------
_EXPL_SAFETY_REDIRECT = {
    "why": "Query about election results or outcomes",
    "source": "Safety Redirect",
    "avoided": "Specific election results or party outcomes",
}
_EXPL_POST_SCAN = {
    "why": "Generated response contained risky language",
    "source": "Safety Redirect (Post-scan)",
    "avoided": "Specific election results or party outcomes",
}
_EXPL_AI = {
    "why": "General election process information",
    "source": "AI Assistant (Gemini)",
    "avoided": "Specific election results or party outcomes",
}
_EXPL_ERROR = {
    "why": "Error generating response",
    "source": "Error Fallback",
    "avoided": "Unverified claims",
}


def configure_ai() -> None:
    """
    Configure the Gemini generative model using the GEMINI_API_KEY environment variable.

    Must be called once at application startup before any calls to
    generate_voter_readiness_score().  Logs a warning and leaves the model
    as None if the key is absent so the app degrades gracefully.
    """
    global model
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini AI model configured successfully.")
    else:
        logger.warning("GEMINI_API_KEY not set — AI responses disabled.")


def _parse_ai_response(ai_text: str) -> tuple[str, int, int]:
    """
    Parse the structured JSON payload returned by Gemini.

    Strips optional markdown fences before JSON decoding.  Falls back to
    returning the raw text with a default maturity increment of 5 if parsing
    fails, so the user still receives a response rather than an error.

    Args:
        ai_text: Raw string returned by model.generate_content().

    Returns:
        A tuple of (final_reply, maturity_increment, busted_myth_index).
    """
    try:
        cleaned = ai_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        ai_data = json.loads(cleaned.strip())

        reply = str(ai_data.get("reply", "I couldn't process that."))
        maturity_inc = int(ai_data.get("maturity_score_increment", 0))
        is_myth = bool(ai_data.get("is_myth_question", False))
        busted_idx = int(ai_data.get("busted_myth_index", -1)) if is_myth else -1
        return reply, maturity_inc, busted_idx
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("JSON parse error from Gemini response: %s", exc)
        return ai_text, 5, -1


def generate_voter_readiness_score(
    query: str,
    myths_context: str,
    user: dict | None = None,
) -> dict:
    """
    Generate a safe, educational AI response and compute a civic maturity score.

    Applies a three-stage safety pipeline:
      1. Pre-flight risky-query filter (blocks result/winner/outcome queries).
      2. Gemini generation with a strict educational system prompt.
      3. Post-response scan to catch any hallucinated partisan content.

    Args:
        query:          The user's raw question string.
        myths_context:  Pre-rendered myth/reality context injected into the prompt.
        user:           The current user dict (unused here but accepted for future use).

    Returns:
        A dict with keys: 'response', 'explainability', and optionally
        'increment', 'busted_myth_idx', 'myth_unlocked'.
    """
    # Stage 1 — pre-flight safety check
    if is_risky_query(query):
        return {
            "response": SAFE_REDIRECT_MESSAGE,
            "explainability": _EXPL_SAFETY_REDIRECT,
            "maturity": 0,
        }

    # Stage 2 — model availability guard
    if not model:
        return {
            "response": "Gemini API key not configured. " + SAFE_REDIRECT_MESSAGE,
            "explainability": {
                "why": "Missing API Key",
                "source": "Fallback Response",
                "avoided": "Live generation",
            },
            "maturity": 0,
        }

    try:
        prompt = AI_PROMPT_TEMPLATE.format(myths_context=myths_context, query=query)
        response = model.generate_content(prompt)
        final_reply, maturity_inc, busted_myth_idx = _parse_ai_response(response.text)

        # Stage 3 — post-response safety scan
        if post_response_scan(final_reply):
            return {
                "response": SAFE_REDIRECT_MESSAGE,
                "explainability": _EXPL_POST_SCAN,
                "maturity": 0,
            }

        return {
            "response": final_reply,
            "explainability": _EXPL_AI,
            "increment": maturity_inc,
            "busted_myth_idx": busted_myth_idx,
            "myth_unlocked": busted_myth_idx != -1,
        }

    except Exception as exc:  # pragma: no cover
        logger.error("Gemini API error: %s", exc, exc_info=True)
        return {
            "response": "I couldn't verify that safely right now. Please check the official ECI source.",
            "explainability": _EXPL_ERROR,
            "maturity": 0,
        }
