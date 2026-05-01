# 🗳️ VoteIQ — AI-Powered Election Education Assistant

> **Helping citizens understand democracy, one question at a time.**

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://vote-iq.vercel.app)
[![Built with Flask](https://img.shields.io/badge/Backend-Flask-blue?logo=flask)](https://flask.palletsprojects.com/)
[![Powered by Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange?logo=google)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.11-yellow?logo=python)](https://python.org)

---

## 🌐 Live Demo

**🔗 [https://vote-iq.vercel.app](https://vote-iq.vercel.app)**

---

## 🚀 How This Project Was Built — Development Journey

This project was built using an **AI-first development workflow**, combining multiple Google AI tools with human-led system design and validation.

---

### 🤖 Google Gemini — The Brain of VoteIQ

[Google Gemini](https://ai.google.dev/) powers the entire conversational intelligence of VoteIQ.

- **Model Used:** `gemini-2.0-flash` via the `google-generativeai` Python SDK
- **What it does:**
  - Answers civic and electoral questions in a safe, factual, and neutral way
  - Classifies user questions as either a genuine query or a **myth attempt**
  - Generates a **civic maturity score** for each interaction
  - Dynamically generates follow-up quiz questions if a user fails the eligibility test
- **Safety Guardrails:** Gemini is prompted strictly — it will never predict election results, discuss party performance, or generate opinionated political content
- **Structured Output:** Gemini returns a validated JSON object per query, parsed to drive gamification logic (myth detection, score increments, etc.)

```python
# Example Gemini integration
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content(structured_prompt)
ai_data = json.loads(response.text)
```

---

### 🎨 Google Stitch — UI Design & Color Palette

[Google Stitch](https://stitch.withgoogle.com/) was used to design the visual identity of VoteIQ.

- **Color Palette:** The dark-mode, high-contrast palette (deep navy blues, electric indigos, soft whites) was generated and refined using Stitch's AI-assisted design system
- **Component Layouts:** The voter card, myth buster cards, journey steps, and progress tracker UI components were prototyped and inspired using Stitch's design recommendations
- **Typography & Spacing:** Stitch guided the use of `Inter` and `Outfit` from Google Fonts for a clean, civic, and trustworthy look
- **Theme System:** Both dark and light mode tokens were defined based on Stitch's color palette exports, then implemented as CSS custom properties

> The entire look and feel — from the glowing voter card to the step-by-step journey animations — originated from Stitch's AI design concepts and was then hand-coded into production-ready CSS.

---

### ⚡ Antigravity — AI Pair Programmer (Vibe Coding)

[Antigravity by Google DeepMind](https://deepmind.google/) served as the AI pair programmer throughout development.

- **Role:** Real-time coding assistant embedded directly in the development environment
- **Contributions:**
  - Wrote and iterated on the Flask backend (`app.py`) route-by-route
  - Debugged complex issues like Google OAuth token verification, JSON parsing errors, and Vercel serverless crashes
  - Suggested and implemented the gamification logic — step unlocking, maturity scores, quiz generation, and myth-busting tracking
  - Fixed the `flask-talisman` serverless incompatibility by replacing it with a custom `@app.after_request` security header handler
  - Set up the entire GitHub repository structure and Vercel deployment pipeline
  - Helped manage `.gitignore`, environment variable handling, and deployment configuration
- **Style:** This is **vibe coding** — natural language instructions translated into production-ready Python and JavaScript code in real-time

> Every route, every bug fix, and every feature was developed in a conversational, iterative loop with Antigravity — describe → generate → validate → ship.

---

### 🧠 System Architecture — Designed & Validated by Jeyadev

While AI tools accelerated the development, the **system architecture was entirely designed and validated by the developer, Jeyadev**.

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│   HTML + Vanilla JS + CSS  (Google Fonts, YouTube IFrame)   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│               VERCEL SERVERLESS (Python)                     │
│   Flask App  ──  Rate Limiter  ──  Session Management        │
│   Routes: /  /ask  /journey  /myth  /api/auth/*  /api/quiz   │
└──────────┬─────────────────────────┬───────────────────────┘
           │                         │
┌──────────▼──────┐       ┌──────────▼──────────────┐
│  SAFETY LAYER   │       │   GOOGLE GEMINI API      │
│  guards.py      │       │   gemini-2.0-flash       │
│  - cache check  │       │   - Myth classifier      │
│  - risky query  │       │   - Civic answers        │
│  - post-scan    │       │   - Maturity scoring     │
└─────────────────┘       └─────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────┐
│              GOOGLE OAUTH 2.0                        │
│  Token verification via google-auth + id_token       │
└─────────────────────────────────────────────────────┘
```

#### Key Design Decisions (by Jeyadev)

| Decision | Rationale |
|---|---|
| **Flask over FastAPI** | Simpler templating with Jinja2, better for single-page HTML app |
| **In-memory `users_db`** | Demo/hackathon scale — noted for production upgrade to PostgreSQL |
| **Vercel serverless** | Zero infrastructure management, instant global CDN |
| **No framework JS** | Vanilla JS keeps bundle size zero, faster load, no build step |
| **Gamification-first UX** | Steps, scores, and myths drive higher civic engagement vs static pages |
| **3-layer AI safety** | Pre-flight guard → Gemini prompt framing → Post-response scan |

#### Validation Performed

- ✅ All 5 API routes tested manually (auth, ask, journey, quiz, myths)
- ✅ Safety guardrails validated — Gemini correctly blocks result/outcome queries
- ✅ Myth classifier tested with EVM tampering and NOTA misconceptions
- ✅ Gamification progression tested end-to-end (register → journey → quiz)
- ✅ Google OAuth token flow validated across sign-in and profile completion
- ✅ Vercel deployment tested with environment variable injection

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗺️ **My Voter Journey** | 4-step guided path explaining registration, voting, counting, and results |
| 🧨 **Myth Buster** | Unlockable myth cards — revealed as users ask myth-related questions |
| 💬 **Ask Anything** | Safe Gemini-powered Q&A on the Indian election process |
| 🃏 **Voter Card** | Personal civic ID showing readiness score and quiz status |
| 📊 **Maturity Score** | AI-scored civic intelligence tracker, updated per interaction |
| 🏆 **Final Quiz** | 10-question eligibility quiz unlocked only after completing the journey |
| 🌙 **Dark/Light Mode** | Full theme toggle with persistent preference |
| 🔐 **Google Sign-In** | Secure OAuth 2.0 authentication with profile completion |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **Backend** | Python 3.11, Flask 3.0 |
| **AI** | Google Gemini (`gemini-2.0-flash`) |
| **Auth** | Google OAuth 2.0 (`google-auth`, `id_token`) |
| **Security** | Custom CSP headers, `flask-limiter`, session management |
| **Deployment** | Vercel Serverless |
| **Fonts** | Google Fonts (Inter, Outfit) |
| **Design** | Google Stitch (palette + layout concepts) |
| **AI Coding** | Antigravity by Google DeepMind |

---

## 🏗️ Project Structure

```
voteiq/
├── app.py              # Flask backend — all routes and business logic
├── data.py             # Static data: myths, journey steps, quiz questions
├── guards.py           # AI safety layer: cache, risky query filter, post-scan
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment configuration
├── .env.example        # Environment variable template
├── static/
│   ├── app.js          # Frontend JavaScript — UI logic and API calls
│   └── style.css       # Full CSS design system (dark/light themes)
└── templates/
    └── index.html      # Single-page application shell
```

---

## ⚙️ Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/jeyadev-jd/VoteIQ.git
cd VoteIQ
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

Required variables:
```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
FLASK_SECRET_KEY=your_random_secret_key
```

### 5. Run the app
```bash
python app.py
```

Open **http://localhost:8080** in your browser.

---

## 🔐 Safety Architecture

VoteIQ uses a **3-layer safety system** to ensure the AI never provides election results or biased political content:

```
User Query
    │
    ▼
[Layer 1] Pre-flight cache check → returns verified answer if matched
    │
    ▼
[Layer 2] Risky query filter → blocks result/outcome/winner queries
    │
    ▼
[Layer 3] Gemini with strict system prompt → educational answers only
    │
    ▼
[Layer 4] Post-response scan → flags any hallucinated result claims
    │
    ▼
Safe Response to User
```

---

## 🙌 Acknowledgements

| Tool | Role |
|---|---|
| [Google Gemini](https://ai.google.dev/) | AI backbone — Q&A, myth classification, maturity scoring |
| [Google Stitch](https://stitch.withgoogle.com/) | UI/UX design — color palette, component layouts |
| [Antigravity (Google DeepMind)](https://deepmind.google/) | AI pair programmer — vibe coding, debugging, deployment |
| [Vercel](https://vercel.com/) | Hosting and serverless deployment |
| [Google OAuth](https://developers.google.com/identity) | Secure user authentication |

---

## 👨‍💻 Developer

**Jeyadev** — System Architecture Design, Feature Definition, Integration & Validation

> *"I designed the system, defined what it must do, validated every feature, and guided the AI tools to build it exactly the way I envisioned."*

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.
