# VoteIQ

VoteIQ is an educational election assistant designed to help users understand the democratic process safely. 

## Features
- **My Voter Journey:** Step-by-step guidance on how to participate in elections.
- **Myth Buster:** Defeats common election myths with factual realities.
- **Ask Anything:** Safe, AI-powered explanations of electoral concepts using Gemini.
- **Voter Card:** Generates a readiness score based on your interactions.

## Architecture
This project uses a simple, hackathon-friendly architecture:
- **Frontend:** HTML, CSS, JavaScript (Vanilla, no framework)
- **Backend:** Python Flask
- **AI:** Google Gemini API
- **Deployment:** Vercel (Optimized)

## Safety First
VoteIQ uses a strict safety boundary:
1. Exact match caching for common queries.
2. Pre-flight check to block result/outcome requests.
3. Safe educational prompt framing for Gemini.
4. Post-response scan to ensure no hallucinations regarding election winners.

## Running Locally
1. Clone the repository.
2. Export your Gemini API Key:
   ```bash
   export GEMINI_API_KEY="your_key"
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open `http://localhost:8080` in your browser.
