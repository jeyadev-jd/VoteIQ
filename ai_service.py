import os
import json
import logging
import google.generativeai as genai
from guards import is_risky_query, post_response_scan, SAFE_REDIRECT_MESSAGE

logger = logging.getLogger(__name__)

# Global model instance
model = None

# S1 — AI prompt extracted to a named constant
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

def configure_ai():
    """Configures the Gemini AI model with the provided API key."""
    global model
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
    else:
        logger.warning("GEMINI_API_KEY not set — AI responses disabled.")

def generate_voter_readiness_score(query, myths_context, user=None):
    """
    Generates an AI response for the user's query, calculating a maturity score increment.
    Returns a dictionary containing the response data and user status updates.
    """
    if is_risky_query(query):
        return {
            "response": SAFE_REDIRECT_MESSAGE,
            "explainability": {
                "why": "Query about election results or outcomes",
                "source": "Safety Redirect",
                "avoided": "Specific election results or party outcomes",
            },
            "maturity": 0,
        }

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
        prompt = AI_PROMPT_TEMPLATE.format(
            myths_context=myths_context,
            query=query,
        )
        response = model.generate_content(prompt)
        ai_text = response.text

        try:
            cleaned = ai_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            ai_data = json.loads(cleaned.strip())
            final_reply = ai_data.get("reply", "I couldn't process that.")
            maturity_inc = int(ai_data.get("maturity_score_increment", 0))
            is_myth = bool(ai_data.get("is_myth_question", False))
            busted_myth_idx = int(ai_data.get("busted_myth_index", -1)) if is_myth else -1
        except (json.JSONDecodeError, ValueError, TypeError) as json_err:
            logger.warning("JSON parse error from AI: %s", json_err)
            final_reply = ai_text
            maturity_inc = 5
            busted_myth_idx = -1

        if post_response_scan(final_reply):
            return {
                "response": SAFE_REDIRECT_MESSAGE,
                "explainability": {
                    "why": "Generated response contained risky language",
                    "source": "Safety Redirect (Post-scan)",
                    "avoided": "Specific election results or party outcomes",
                },
                "maturity": 0,
            }

        return {
            "response": final_reply,
            "explainability": {
                "why": "General election process information",
                "source": "AI Assistant (Gemini)",
                "avoided": "Specific election results or party outcomes",
            },
            "increment": maturity_inc,
            "busted_myth_idx": busted_myth_idx,
            "myth_unlocked": busted_myth_idx != -1,
        }

    except Exception as e:
        logger.error("Gemini API error: %s", e, exc_info=True)
        return {
            "response": "I couldn't verify that safely right now. Please check the official ECI source.",
            "explainability": {
                "why": "Error generating response",
                "source": "Error Fallback",
                "avoided": "Unverified claims",
            },
            "maturity": 0,
        }
