'use strict';

/* ─────────────────────────────────────────────────────────
   STATE  (declared first so helpers can reference it safely)
───────────────────────────────────────────────────────── */
const _cachedProfile = (() => {
    try { return JSON.parse(localStorage.getItem('voteiq_profile')); } catch { return null; }
})();

const state = {
    questions: parseInt(localStorage.getItem('voteiq_questions')) || 0,
    mythsReviewed: _cachedProfile?.unlocked_myths?.length || 0,
    journeySteps: 6, // Q10 — default to known journey length, not 0
    historyCount: 0,
    profile: null // Will be populated by initializeApp
};

/* ─────────────────────────────────────────────────────────
   INITIALIZATION
───────────────────────────────────────────────────────── */
async function initializeApp() {
    try {
        const res = await fetch('/api/auth/session');
        if (res.ok) {
            const data = await res.json();
            state.profile = data.user;
        }
    } catch (e) {
        console.log("No active session found.");
        state.profile = null;
    }
    syncVoterCard();
}

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
/** Q9 — null-safe getElementById wrapper */
const $ = id => {
    const el = document.getElementById(id);
    if (!el) console.warn(`[VoteIQ] Element #${id} not found in DOM`);
    return el;
};

function escHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

/* ─────────────────────────────────────────────────────────
   DARK MODE  (persisted to localStorage)
───────────────────────────────────────────────────────── */
function applyTheme(dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    $('theme-icon').className = dark ? 'bi bi-sun' : 'bi bi-moon-stars';
    const label = $('theme-toggle').querySelector('span');
    if (label) label.textContent = dark ? 'Light Mode' : 'Dark Mode';
    // Sync Bootstrap modals – swap bg-dark / bg-light on form controls
    document.querySelectorAll('.modal-form-ctrl').forEach(el => {
        el.classList.toggle('bg-dark', dark);
        el.classList.toggle('bg-light', !dark);
        el.classList.toggle('text-white', dark);
        el.classList.toggle('text-dark', !dark);
    });
    localStorage.setItem('voteiq_theme', dark ? 'dark' : 'light');
}

/**
 * A10 — Toast helper with role="alert" so screen readers announce notifications.
 * @param {string} msg
 * @param {'info'|'success'} type
 */
function showToast(msg, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast-item ${type} animate__animated animate__fadeInUp`;
    toast.setAttribute('role', 'alert');           // A10
    toast.setAttribute('aria-live', 'assertive'); // A10
    toast.setAttribute('aria-atomic', 'true');    // A10
    toast.innerHTML = `<i class="bi ${type === 'success' ? 'bi-check-circle-fill' : 'bi-info-circle-fill'}" aria-hidden="true"></i> ${msg}`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.replace('animate__fadeInUp', 'animate__fadeOutDown');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

function createToastContainer() {
    const div = document.createElement('div');
    div.id = 'toast-container';
    div.className = 'toast-container-custom';
    div.setAttribute('aria-live', 'assertive'); // A10
    document.body.appendChild(div);
    return div;
}

// Apply on load
(function () {
    const saved = localStorage.getItem('voteiq_theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(saved ? saved === 'dark' : prefersDark);
})();

$('theme-toggle').addEventListener('click', e => {
    e.preventDefault();
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    applyTheme(!isDark);
});

/* ─────────────────────────────────────────────────────────
   MODE / TAB SWITCHING
───────────────────────────────────────────────────────── */
const modeBtns = document.querySelectorAll('.mode-btn');
const views = document.querySelectorAll('.view');
const modeLabels = { ask: 'AI Chat Helper', journey: 'My Voter Journey', myth: 'Myth Buster', stats: 'Learning Statistics' };

// E3 — Merged into a single forEach (journey + myth lazy loads handled here)
modeBtns.forEach(btn => {
    btn.addEventListener('click', e => {
        e.preventDefault();
        const mode = btn.dataset.mode;
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        views.forEach(v => v.classList.add('d-none'));
        const target = document.getElementById(`${mode}-mode`);
        if (target) target.classList.remove('d-none');

        // A1 — Announce tab switch to screen readers
        const titleEl = $('current-mode-title');
        if (titleEl) titleEl.textContent = modeLabels[mode] ?? mode;

        document.body.classList.toggle('hide-history', mode !== 'ask');

        if (mode === 'journey' && !journeyLoaded) loadJourney();
        if (mode === 'myth'    && !mythsLoaded)   loadMyths();
        if (mode === 'stats')                      syncVoterCard();
    });
});

/* ─────────────────────────────────────────────────────────
   SUGGESTION CHIPS
───────────────────────────────────────────────────────── */
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        $('query-input').value = chip.textContent.trim();
        $('query-input').focus();
    });
});

/* ─────────────────────────────────────────────────────────
   ASK / CHAT
───────────────────────────────────────────────────────── */
$('query-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
});
$('ask-btn').addEventListener('click', sendQuestion);

async function sendQuestion() {
    const query = $('query-input').value.trim();
    if (!query) return;

    const welcome = $('welcome-state');
    if (welcome) welcome.remove();

    appendMessage('user', query);
    appendHistoryItem(query);
    $('query-input').value = '';

    $('loading').classList.remove('d-none');
    scrollChat();

    try {
        const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }) // Email is handled by server session
        });
        const data = await res.json();

        $('loading').classList.add('d-none');
        appendMessage('bot', data.response, data.explainability);

        if (state.profile && data.maturity !== undefined) {
            state.profile.maturity_score = data.maturity;
            localStorage.setItem('voteiq_profile', JSON.stringify(state.profile));
            // Live-update the maturity bar in the stats modal
            const matBar = $('modal-maturity-bar');
            if (matBar) {
                matBar.style.width = `${data.maturity}%`;
                matBar.textContent = `${data.maturity}%`;
                if (data.maturity >= 80) matBar.classList.replace('bg-warning', 'bg-success');
            }
        }

        if (state.profile && data.unlocked_count !== undefined) {
            const oldVal = state.mythsReviewed;
            state.mythsReviewed = data.unlocked_count;
            if (data.myth_unlocked && data.unlocked_count > oldVal) {
                showToast("🔍 Myth Busted! New electoral reality added to your Myth Buster tab.", "success");
            }
        }

        state.questions++;
        localStorage.setItem('voteiq_questions', state.questions);
        syncVoterCard();
    } catch (e) {
        console.error("Chat error", e);
        $('loading').classList.add('d-none');
        appendMessage('bot', 'Something went wrong — please try again.');
    }
}

/**
 * S7 — Sanitize Google picture URL: only allow known Google CDN domain.
 * @param {string} url
 * @returns {string}
 */
function sanitizePictureUrl(url) {
    try {
        const u = new URL(url);
        if (u.protocol === 'https:' && u.hostname === 'lh3.googleusercontent.com') return url;
    } catch {}
    return ''; // Reject anything unexpected
}

function appendMessage(role, text, explainability = null) {
    const wrap = document.createElement('div');
    wrap.className = `chat-message ${role}`;
    wrap.setAttribute('aria-label', role === 'user' ? 'Your message' : 'VoteIQ response');

    let userLabel = '<i class="bi bi-person-circle" aria-hidden="true"></i> You';
    if (role === 'user' && state.profile && state.profile.picture && state.profile.name) {
        const safePic = sanitizePictureUrl(state.profile.picture);
        userLabel = safePic
            ? `<img src="${safePic}" style="width: 20px; height: 20px; border-radius: 50%; object-fit: cover; margin-right: 6px;" alt=""> ${escHtml(state.profile.name)}`
            : `<i class="bi bi-person-circle" aria-hidden="true"></i> ${escHtml(state.profile.name)}`;
    }

    const label = role === 'user'
        ? userLabel
        : '<i class="bi bi-hand-index-thumb-fill"></i> VoteIQ';

    let html = `<div class="msg-label">${label}</div>
                <div class="message-bubble">${escHtml(text)}</div>`;

    if (role === 'bot') {
        if (explainability) {
            html += `
            <div class="trust-panel">
                <div class="trust-panel-hd">
                    <span><i class="bi bi-shield-check"></i>&ensp;Trust Check</span>
                    <button class="trust-toggle" onclick="
                        var b=this.closest('.trust-panel').querySelector('.trust-body');
                        b.classList.toggle('open');
                        this.textContent=b.classList.contains('open')?'Hide':'Show';
                    ">Show</button>
                </div>
                <div class="trust-body">
                    <p><strong>Why I answered:</strong> ${escHtml(explainability.why)}</p>
                    <p><strong>Source basis:</strong> ${escHtml(explainability.source)}</p>
                    <p><strong>What I avoided:</strong> ${escHtml(explainability.avoided)}</p>
                </div>
            </div>`;
        }
        html += `
        <div class="msg-actions">
            <button class="msg-action-btn" title="Helpful"><i class="bi bi-hand-thumbs-up"></i></button>
            <button class="msg-action-btn" title="Not helpful"><i class="bi bi-hand-thumbs-down"></i></button>
        </div>`;
    }

    wrap.innerHTML = html;
    $('chat-container').appendChild(wrap);
    scrollChat();
}

function scrollChat() {
    const cf = $('chat-container');
    cf.scrollTop = cf.scrollHeight;
}

/* ─────────────────────────────────────────────────────────
   HISTORY
───────────────────────────────────────────────────────── */
function appendHistoryItem(query) {
    const empty = $('history-empty');
    if (empty) empty.style.display = 'none';

    state.historyCount = Math.min(state.historyCount + 1, 50);
    $('history-count').textContent = `${state.historyCount} / 50`;

    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
        <div class="history-item-title">${escHtml(query.length > 32 ? query.slice(0, 32) + '…' : query)}</div>
        <div class="history-item-sub">Just now</div>
    `;
    $('history-list').prepend(item);
}

$('clear-history').addEventListener('click', () => {
    document.querySelectorAll('.history-item').forEach(el => el.remove());
    const empty = $('history-empty');
    if (empty) empty.style.display = '';
    state.historyCount = 0;
    $('history-count').textContent = '0 / 50';
});

/* ─────────────────────────────────────────────────────────
   JOURNEY  — auto-loads on first visit to the tab
───────────────────────────────────────────────────────── */
let journeyLoaded = false;
let ytPlayers = {};
let stepProgress = {}; // Tracks { videoDone: false, linkDone: false } for each step

// Global callback for YouTube Iframe API
window.onYouTubeIframeAPIReady = function () {
    if (journeyLoaded) initAllYoutubePlayers();
};

/** E7 — Inject YouTube API script lazily when journey first loads */
function loadYouTubeAPI() {
    if (document.getElementById('yt-api-script')) return;
    const s = document.createElement('script');
    s.id = 'yt-api-script';
    s.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(s);
}

async function loadJourney() {
    // E7 — Load YouTube API lazily on first journey visit
    loadYouTubeAPI();

    try {
        const res = await fetch('/journey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await res.json();
        const list = $('journey-list');

        const loadingEl = $('journey-loading');
        if (loadingEl) loadingEl.remove();

        const currentStep = state.profile?.current_step || 1;
        state.journeySteps = data.steps ? data.steps.length : 6;

        (data.steps || []).forEach(step => {
            stepProgress[step.step] = { videoDone: false, linkDone: false };

            const isLocked = step.step > currentStep;
            const card = document.createElement('div');
            card.className = `journey-step-card ${isLocked ? 'locked' : ''}`;
            card.id = `journey-step-${step.step}`;
            if (step.yt_id) card.dataset.ytid = step.yt_id;

            let mediaContent = '';
            if (!isLocked && step.yt_id) {
                mediaContent = `<div class="yt-container"><div id="yt-player-${step.step}" data-ytid="${step.yt_id}"></div></div>`;
            } else if (isLocked) {
                mediaContent = `<div class="locked-overlay"><i class="bi bi-lock-fill" aria-hidden="true"></i> Complete previous step to unlock</div>`;
            }

            card.innerHTML = `
                <div class="jsc-num" aria-hidden="true">
                    <i class="bi ${escHtml(step.icon)}"></i>
                </div>
                <div class="jsc-body">
                    <div class="jsc-header">
                        <div>
                            <div class="jsc-step-label">Step ${step.step}</div>
                            <h3 class="jsc-title">${escHtml(step.title)}</h3>
                        </div>
                        <span class="jsc-stat" aria-label="Duration: ${escHtml(step.stat)}">${escHtml(step.stat)}</span>
                    </div>
                    <p class="jsc-desc">${escHtml(step.description)}</p>
                    <div class="jsc-tip"><i class="bi bi-lightbulb-fill" aria-hidden="true"></i> <strong>Tip:</strong> ${escHtml(step.tip)}</div>
                    ${mediaContent}
                    <div class="jsc-footer mt-3">
                        <a href="${escHtml(step.link)}" target="_blank" rel="noopener noreferrer"
                           class="jsc-link ${isLocked ? 'disabled' : ''}"
                           data-step="${step.step}"
                           ${isLocked ? 'aria-disabled="true" tabindex="-1"' : ''}>
                            <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> ${escHtml(step.link_label)}
                        </a>
                        <div class="progress-status" id="prog-status-${step.step}" aria-live="polite">
                            <span class="badge ${isLocked ? 'bg-secondary' : 'bg-warning text-dark'}">Pending</span>
                        </div>
                    </div>
                </div>`;
            list.appendChild(card);
        });

        // Attach link click handlers
        document.querySelectorAll('.jsc-link').forEach(link => {
            link.addEventListener('click', () => {
                if (link.classList.contains('disabled')) return;
                const stepNum = parseInt(link.dataset.step);
                stepProgress[stepNum].linkDone = true;
                checkStepUnlock(stepNum);
            });
        });

        journeyLoaded = true;

        if (window.YT && YT.Player) initAllYoutubePlayers();
        if (currentStep > state.journeySteps) checkQuizUnlock();

        syncVoterCard();
    } catch (err) {
        console.error('Journey load error:', err);
        const loadingEl = $('journey-loading');
        if (loadingEl) loadingEl.textContent = 'Could not load journey steps.';
    }
}

function initAllYoutubePlayers() {
    const currentStep = state.profile?.current_step || 1;
    document.querySelectorAll('[id^="yt-player-"]').forEach(el => {
        const stepNum = parseInt(el.id.replace('yt-player-', ''));
        const ytId = el.dataset.ytid;

        if (ytPlayers[stepNum]) return; // Already initialized

        ytPlayers[stepNum] = new YT.Player(el.id, {
            height: '100%',
            width: '100%',
            videoId: ytId,
            playerVars: {
                'playsinline': 1,
                'rel': 0,
                'controls': 0,
                'disablekb': 1
            },
            events: {
                'onStateChange': (event) => onPlayerStateChange(event, stepNum)
            }
        });
    });
}

function onPlayerStateChange(event, stepNum) {
    // Only mark the video as done when it fully finishes (0 = ENDED).
    if (event.data == YT.PlayerState.ENDED) {
        if (!stepProgress[stepNum].videoDone) {
            stepProgress[stepNum].videoDone = true;
            checkStepUnlock(stepNum);
        }
    }
}

async function checkStepUnlock(stepNum) {
    const prog = stepProgress[stepNum];
    const statusEl = $(`prog-status-${stepNum}`);

    if (prog.videoDone && prog.linkDone) {
        if (statusEl) statusEl.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle-fill"></i> Completed</span>';

        const nextStep = stepNum + 1;
        if (nextStep <= state.journeySteps) {
            const nextCard = $(`journey-step-${nextStep}`);
            if (nextCard && nextCard.classList.contains('locked')) {
                nextCard.classList.remove('locked');

                // Remove locked overlay
                const body = nextCard.querySelector('.jsc-body');
                const overlay = body ? body.querySelector('.locked-overlay') : null;
                if (overlay) overlay.remove();

                // Unlock the external link and bypass button
                const lnk = nextCard.querySelector('.jsc-link');
                if (lnk) lnk.classList.remove('disabled');

                const bypassBtn = nextCard.querySelector('.demo-bypass-btn');
                if (bypassBtn) bypassBtn.classList.remove('d-none');

                // Inject YT player div before the footer
                const ytId = nextCard.dataset.ytid;
                if (ytId && !$(`yt-player-${nextStep}`)) {
                    const footer = nextCard.querySelector('.jsc-footer');
                    const ytWrap = document.createElement('div');
                    ytWrap.className = 'yt-container';
                    ytWrap.innerHTML = `<div id="yt-player-${nextStep}" data-ytid="${ytId}"></div>`;
                    if (footer) body.insertBefore(ytWrap, footer);
                    else if (body) body.appendChild(ytWrap);

                    // Initialize YT player immediately if API is ready
                    if (window.YT && YT.Player && !ytPlayers[nextStep]) {
                        ytPlayers[nextStep] = new YT.Player(`yt-player-${nextStep}`, {
                            height: '100%', width: '100%', videoId: ytId,
                            playerVars: { playsinline: 1, rel: 0, controls: 0, disablekb: 1 },
                            events: { onStateChange: (ev) => onPlayerStateChange(ev, nextStep) }
                        });
                    }
                }

                // Reset progress badge for the new step
                const nextStatus = $(`prog-status-${nextStep}`);
                if (nextStatus) nextStatus.innerHTML = '<span class="badge bg-warning text-dark">Pending</span>';

                // Persist to backend (fire-and-forget, no reload)
                updateProgressBackend(nextStep);
            }
        } else {
            // All steps done — unlock quiz
            updateProgressBackend(stepNum + 1);
            checkQuizUnlock();
        }
    } else if (prog.videoDone) {
        if (statusEl) statusEl.innerHTML = '<span class="badge bg-info">Video Done — Click Link</span>';
    } else if (prog.linkDone) {
        if (statusEl) statusEl.innerHTML = '<span class="badge bg-info">Link Clicked — Watch Video</span>';
    }
}

async function updateProgressBackend(newStep) {
    if (!state.profile) return; // Rely on server session
    try {
        const res = await fetch('/api/progress/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: state.profile.email, step: newStep })
        });
        const data = await res.json();
        if (data.status === 'success') {
            state.profile.current_step = data.current_step;
            localStorage.setItem('voteiq_profile', JSON.stringify(state.profile));
            syncVoterCard();
        }
    } catch (e) {
        console.error('Failed to update progress', e);
    }
}

async function showQuizSection() {
    if ($('quiz-locked-msg')) $('quiz-locked-msg').classList.add('d-none');

    if ($('quiz-container')) {
        $('quiz-container').classList.remove('d-none');
        document.querySelectorAll('.journey-step-card').forEach(el => el.classList.add('d-none'));
        if ($('take-quiz-return-btn')) $('take-quiz-return-btn').classList.add('d-none');
        return;
    }

    // Hide journey cards
    document.querySelectorAll('.journey-step-card').forEach(el => el.classList.add('d-none'));

    const container = document.createElement('div');
    container.id = 'quiz-container';
    container.className = 'mt-3 mb-5';

    container.innerHTML = `
        <div class="mb-4">
            <button id="back-to-videos-btn" class="btn btn-outline-secondary px-3 py-2" style="border-radius: var(--radius-sm); font-weight: 600; border-color: var(--border); color: var(--text-2); background: var(--surface);"><i class="bi bi-arrow-left me-2"></i>Back to Videos</button>
        </div>
        <div class="quiz-header-card">
            <h3 class="mb-2" style="color: var(--text-1); font-weight: 700;"><i class="bi bi-patch-question-fill text-warning"></i> Final Challenge: Voter Eligibility Quiz</h3>
            <p class="mb-0" style="color: var(--text-2)">You've completed the journey! Now prove your knowledge to unlock your Voter ID.</p>
        </div>
        <div id="quiz-questions"></div>
        <button id="submit-quiz-btn" class="btn w-100 mt-2 py-3" style="background: var(--accent); color: white; border: none; border-radius: var(--radius-md); font-weight: 600; font-size: 1.1rem; box-shadow: var(--shadow-sm); transition: all 0.2s ease;">Submit Answers</button>
        <div id="quiz-feedback" class="mt-3 text-center fw-bold" style="font-size: 1.1rem;"></div>
    `;

    $('journey-list').appendChild(container);

    $('back-to-videos-btn').addEventListener('click', () => {
        document.querySelectorAll('.journey-step-card').forEach(el => el.classList.remove('d-none'));
        $('quiz-container').classList.add('d-none');

        let tqb = $('take-quiz-return-btn');
        if (!tqb) {
            tqb = document.createElement('button');
            tqb.id = 'take-quiz-return-btn';
            tqb.className = 'btn w-100 mt-2 mb-4 py-3';
            tqb.style.cssText = 'background: var(--accent); color: white; border: none; border-radius: var(--radius-md); font-weight: 600; font-size: 1.1rem; box-shadow: var(--shadow-sm); transition: all 0.2s ease;';
            tqb.innerHTML = '<i class="bi bi-clipboard-check-fill me-2 fs-5" style="vertical-align: middle;"></i><span style="vertical-align: middle;">Go to Final Quiz</span>';
            tqb.addEventListener('click', () => {
                checkQuizUnlock();
            });
            $('journey-list').appendChild(tqb);
        }
        tqb.classList.remove('d-none');
    });

    try {
        const res = await fetch('/api/quiz');
        const data = await res.json();

        const qContainer = $('quiz-questions');
        data.quiz.forEach((q, qIndex) => {
            const qDiv = document.createElement('div');
            qDiv.className = 'quiz-question-card';

            let optionsHtml = q.options.map((opt, oIndex) => `
                <div class="modern-quiz-option">
                    <input class="modern-quiz-input" type="radio" name="q${qIndex}" id="q${qIndex}o${oIndex}" value="${oIndex}">
                    <label class="modern-quiz-label" for="q${qIndex}o${oIndex}">
                        <div class="modern-quiz-radio"></div>
                        <div class="modern-quiz-text">${escHtml(opt)}</div>
                    </label>
                </div>
            `).join('');

            qDiv.innerHTML = `
                <div class="fw-bold mb-3" style="color: var(--text-1); font-size: 1.15rem; line-height: 1.4;">${qIndex + 1}. ${escHtml(q.question)}</div>
                <div class="d-flex flex-column gap-2">
                    ${optionsHtml}
                </div>
            `;
            qContainer.appendChild(qDiv);
        });

        $('submit-quiz-btn').addEventListener('click', async () => {
            if (!state.profile) {
                $('quiz-feedback').innerHTML = '<span class="text-danger">Please log in to submit the quiz!</span>';
                return;
            }

            const answers = [];
            for (let i = 0; i < data.quiz.length; i++) {
                const checked = document.querySelector(`input[name="q${i}"]:checked`);
                if (!checked) {
                    $('quiz-feedback').innerHTML = '<span class="text-danger">Please answer all questions!</span>';
                    return;
                }
                answers.push(parseInt(checked.value));
            }

            $('quiz-feedback').innerHTML = '<span class="text-info">Submitting...</span>';

            const submitRes = await fetch('/api/quiz/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answers }) // Email is handled by server session
            });
            const result = await submitRes.json();

            if (result.passed) {
                // Success animation
                const qc = $('quiz-container');
                if (qc) {
                    qc.style.transition = 'box-shadow 0.5s ease';
                    qc.style.boxShadow = '0 0 0 3px #22c55e, 0 10px 40px rgba(34,197,94,0.3)';
                }
                $('quiz-feedback').innerHTML = `
                    <div style="animation: fadeInUp 0.5s ease;">
                        <div style="font-size:2.5rem;">🎉</div>
                        <div class="text-success fw-bold fs-5"><i class="bi bi-patch-check-fill"></i> You Passed!</div>
                        <div class="text-muted small">Score: ${result.score}/${result.total} — You are now an Eligible Voter!</div>
                    </div>`;
                $('submit-quiz-btn').disabled = true;
                document.querySelectorAll('#quiz-questions input').forEach(el => el.disabled = true);
                if (state.profile) {
                    state.profile.quiz_passed = true;
                    localStorage.setItem('voteiq_profile', JSON.stringify(state.profile));
                    syncVoterCard();
                }
            } else {
                const needed = Math.ceil(result.total * 0.75);
                $('quiz-feedback').innerHTML = `<span class="text-danger"><i class="bi bi-x-circle-fill"></i> You scored ${result.score}/${result.total}. Need ${needed}+ to pass. Try again!</span>`;
            }
        });

        // If already passed, show success state immediately
        if (state.profile?.quiz_passed) {
            $('quiz-feedback').innerHTML = `<span class="text-success"><i class="bi bi-check-circle-fill"></i> You have already passed this quiz!</span>`;
            $('submit-quiz-btn').disabled = true;
            document.querySelectorAll('#quiz-questions input').forEach(el => el.disabled = true);
        }

    } catch (e) {
        console.error("Failed to load quiz", e);
    }
}


/* ─────────────────────────────────────────────────────────
   QUIZ UNLOCK LOGIC
───────────────────────────────────────────────────────── */
function checkQuizUnlock() {
    const q = state.questions || 0;
    const m = state.mythsReviewed || 0;
    const j = state.journeySteps || 6;
    let completed_steps = 0;
    if (state.profile && state.profile.current_step) {
        completed_steps = Math.min(state.profile.current_step - 1, j);
    }

    if (completed_steps >= j && q >= 3 && m >= 5) {
        showQuizSection();
    } else {
        showQuizLockedMessage(completed_steps, j, q, m);
    }
}

function showQuizLockedMessage(c, j, q, m) {
    if ($('quiz-container')) $('quiz-container').classList.add('d-none');

    document.querySelectorAll('.journey-step-card').forEach(el => el.classList.add('d-none'));

    let msgContainer = $('quiz-locked-msg');
    if (!msgContainer) {
        msgContainer = document.createElement('div');
        msgContainer.id = 'quiz-locked-msg';
        msgContainer.className = 'mt-3 mb-5 p-4 rounded-4 text-center';
        msgContainer.style.background = 'var(--surface)';
        msgContainer.style.border = '1px solid var(--border)';
        $('journey-list').appendChild(msgContainer);
    }
    msgContainer.classList.remove('d-none');

    // Q13 / A7 — Use text + icon; replace inline onclick with event listener
    const checkIcon = (ok) => ok
        ? '<i class="bi bi-check-circle-fill text-success me-2" aria-hidden="true"></i><span class="visually-hidden">Done:</span>'
        : '<i class="bi bi-x-circle text-danger me-2" aria-hidden="true"></i><span class="visually-hidden">Incomplete:</span>';

    msgContainer.innerHTML = `
        <i class="bi bi-lock-fill fs-1 text-warning mb-3 d-block" aria-hidden="true"></i>
        <h4 class="fw-bold mb-3" style="color: var(--text-1);">Final Quiz Locked</h4>
        <p style="color: var(--text-2);" class="mb-4">Complete all tasks below to unlock the final eligibility quiz:</p>
        <div class="d-flex flex-column align-items-center gap-2 mb-4 text-start" role="list">
            <div style="width: 250px;" role="listitem">${checkIcon(c >= j)} <span style="color: var(--text-1);">Watch ${j} Journey Videos</span></div>
            <div style="width: 250px;" role="listitem">${checkIcon(q >= 3)} <span style="color: var(--text-1);">Ask 3 AI Questions (${q}/3)</span></div>
            <div style="width: 250px;" role="listitem">${checkIcon(m >= 5)} <span style="color: var(--text-1);">Review 5 Myths (${m}/5)</span></div>
        </div>
        <button id="quiz-locked-back-btn" class="btn btn-outline-secondary">
            <i class="bi bi-arrow-left me-2" aria-hidden="true"></i>Back to Videos
        </button>
    `;

    // Q13 — Event listener instead of inline onclick
    const backBtn = msgContainer.querySelector('#quiz-locked-back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            msgContainer.classList.add('d-none');
            document.querySelectorAll('.journey-step-card').forEach(el => el.classList.remove('d-none'));
        });
    }

    const tqb = $('take-quiz-return-btn');
    if (tqb) tqb.classList.add('d-none');
}

/* ─────────────────────────────────────────────────────────
   MYTH BUSTER — auto-loads on first visit
───────────────────────────────────────────────────────── */
let mythsLoaded = false;

// Note: myth lazy-load is now handled inside the merged modeBtns.forEach above (E3 fix)

async function loadMyths() {
    try {
        const url = '/myth'; // Email is handled by server session
        const res = await fetch(url);
        const data = await res.json();
        const myths = data.myths || [];

        const loadingEl = $('myths-loading');
        if (loadingEl) loadingEl.remove();

        // Update badge
        const badge = $('myth-count-badge');
        if (badge) badge.innerHTML = `<i class="bi bi-shield-check"></i> ${myths.length} Myths`;

        const container = $('myths-container');
        container.innerHTML = '';

        if (myths.length > 0) {
            container.style.display = 'grid';
            // Hide the empty state if myths are found
            const emptyState = document.querySelector('.empty-state');
            if (emptyState) emptyState.style.display = 'none';

            myths.forEach(item => {
                const card = document.createElement('div');
                card.className = 'myth-card';
                card.innerHTML = `
                    <span class="myth-tag myth-lbl"><i class="bi bi-x-circle"></i> Myth</span>
                    <h6>${escHtml(item.myth)}</h6>
                    <hr>
                    <span class="myth-tag fact-lbl"><i class="bi bi-check-circle"></i> Reality</span>
                    <p>${escHtml(item.reality)}</p>
                    <div class="myth-source"><i class="bi bi-info-circle"></i> ${escHtml(item.source)}</div>`;
                container.appendChild(card);
            });
        } else {
            container.style.display = 'none';
            const emptyState = document.querySelector('.empty-state');
            if (emptyState) emptyState.style.display = 'block';
        }

        // Count = number of distinct myths shown
        state.mythsReviewed = myths.length;
        if (state.profile) {
            state.profile.unlocked_myths_count = myths.length; // Local sync
        }
        mythsLoaded = true;
        syncVoterCard();
    } catch (err) {
        console.error('Myth load error:', err);
        const loadingEl = $('myths-loading');
        if (loadingEl) loadingEl.textContent = 'Could not load myths.';
    }
}

/* ─────────────────────────────────────────────────────────
   VOTER CARD + STATISTICS SYNC
───────────────────────────────────────────────────────── */
function syncVoterCard() {
    const q = state.questions;
    const total_j = state.journeySteps || 6;
    let m = state.mythsReviewed;

    if (state.profile && state.profile.unlocked_myths) {
        m = Math.max(m, state.profile.unlocked_myths.length);
    }

    let completed_steps = 0;
    if (state.profile && state.profile.current_step) {
        completed_steps = Math.min(state.profile.current_step - 1, total_j);
    }

    // Evaluate new eligibility criteria
    let isJourneyComplete = false;
    let isQuizPassed = false;
    let maturityScore = 0;

    if (state.profile) {
        isJourneyComplete = state.profile.current_step > total_j && total_j > 0;
        isQuizPassed = state.profile.quiz_passed === true;
        maturityScore = state.profile.maturity_score || 0;
    }

    const isEligible = isJourneyComplete && isQuizPassed && maturityScore >= 80;

    // Task-based Granular Progression
    const total_myths = 5; // From data.py
    const total_steps = total_j;
    const total_questions_target = 3;

    const tasks_done = Math.min(q, total_questions_target) + m + completed_steps;
    const total_tasks = total_questions_target + total_myths + total_steps;

    let pct = Math.round((tasks_done / total_tasks) * 100);
    if (pct < 10) pct = 10; // Start at 10%
    if (pct > 95 && !isEligible) pct = 95; // Cap before final quiz

    // Level Titles
    let score = 'Beginner';
    if (tasks_done >= 3) score = 'Learner';
    if (tasks_done >= 8) score = 'Informed Voter';
    if (tasks_done >= 12) score = 'Civilian Pro';

    if (isEligible) {
        score = 'Eligible Voter';
        pct = 100;
        $('voter-progress').classList.add('bg-success');
    }

    // Sidebar card
    $('readiness-score').innerHTML = isEligible ? `<span class="text-success fw-bold"><i class="bi bi-patch-check-fill"></i> Eligible Voter</span>` : score;
    $('voter-progress').style.width = `${pct}%`;
    $('stat-q').textContent = q;
    $('stat-m').textContent = m;

    // Statistics modal
    $('modal-stat-q').textContent = q;
    $('modal-stat-m').textContent = m;
    $('modal-stat-j').textContent = completed_steps;
    $('modal-readiness').textContent = score;
    $('modal-pct').textContent = `${pct}%`;
    $('modal-progress-bar').style.width = `${pct}%`;

    // Update Maturity Progress in modal
    const maturityBar = $('modal-maturity-bar');
    if (maturityBar) {
        maturityBar.style.width = `${maturityScore}%`;
        maturityBar.textContent = `${maturityScore}%`;
        if (maturityScore >= 80) maturityBar.classList.replace('bg-warning', 'bg-success');
    }

    // Activity labels
    $('modal-q-pill').textContent = q;
    $('modal-m-pill').textContent = m;
    $('modal-j-pill').textContent = completed_steps;

    $('modal-q-label').textContent = q > 0
        ? `You have asked ${q} question${q > 1 ? 's' : ''} so far. Keep exploring!`
        : "You haven't asked any questions yet. Try the AI Chat Helper!";

    $('modal-m-label').textContent = m > 0
        ? `You have reviewed ${m} electoral myth${m > 1 ? 's' : ''}. Great work!`
        : 'Open the Myth Buster to learn what is fact vs fiction.';

    $('modal-j-label').textContent = completed_steps > 0
        ? `You have explored ${completed_steps} out of ${total_j} steps in the Voter Journey guide.`
        : 'Open Voter Journey to explore the step-by-step voting guide.';

    // Profile Card Sync
    if (state.profile && state.profile.status === 'complete') {
        $('card-name').textContent = state.profile.name;
        const stateSelect = $('prof-state');
        const stateName = stateSelect.querySelector(`option[value="${state.profile.state}"]`)?.textContent || state.profile.state;
        $('card-state').textContent = stateName;

        // simple age calculation logic for status if needed, 
        // but for now we just show it
        const dob = new Date(state.profile.dob);
        const ageDifMs = Date.now() - dob.getTime();
        const ageDate = new Date(ageDifMs);
        const age = Math.abs(ageDate.getUTCFullYear() - 1970);

        $('card-status').innerHTML = isEligible ? '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Eligible to Vote</span>' : 'Future Voter';
        $('card-id').textContent = isEligible ? state.profile.id : 'Pending Eligibility';
        $('card-progress-bar').style.width = `${pct}%`;
        $('card-progress-text').textContent = `${pct}% Ready`;
        $('card-dob').textContent = dob.toLocaleDateString();

        if (state.profile.picture) {
            $('card-avatar').src = state.profile.picture;
        }

        $('auth-step-1').classList.add('d-none');
        $('signup-form').classList.add('d-none');
        $('shareable-card-container').classList.remove('d-none');
    } else if (state.profile && state.profile.status === 'incomplete') {
        $('auth-step-1').classList.add('d-none');
        $('signup-form').classList.remove('d-none');
        $('shareable-card-container').classList.add('d-none');

        $('signup-avatar').src = state.profile.picture || '';
        $('signup-name').textContent = state.profile.name || '';
        $('signup-email').textContent = state.profile.email || '';
    } else {
        // Reset to Step 1
        $('auth-step-1').classList.remove('d-none');
        $('signup-form').classList.add('d-none');
        $('shareable-card-container').classList.add('d-none');
    }

    // Sync Topbar Avatar
    const topbarAvatar = $('topbar-avatar');
    const topbarIcon = $('topbar-default-icon');
    if (topbarAvatar && topbarIcon) {
        if (state.profile && state.profile.picture) {
            topbarAvatar.src = state.profile.picture;
            topbarAvatar.classList.remove('d-none');
            topbarIcon.classList.add('d-none');
        } else {
            topbarAvatar.classList.add('d-none');
            topbarIcon.classList.remove('d-none');
        }
    }

    // Live update the locked message if it's currently visible
    const lockedMsg = $('quiz-locked-msg');
    if (lockedMsg && !lockedMsg.classList.contains('d-none')) {
        if (completed_steps >= total_j && q >= 3 && m >= 5) {
            showQuizSection();
        } else {
            showQuizLockedMessage(completed_steps, total_j, q, m);
        }
    }
}

/* ─────────────────────────────────────────────────────────
   PROFILE & DEMO ID (GOOGLE AUTH FLOW)
───────────────────────────────────────────────────────── */
const profileModal = document.getElementById('profileModal');
if (profileModal) {
    profileModal.addEventListener('show.bs.modal', () => {
        syncVoterCard(); // ensure card is up to date and correct step is shown
        if (!state.profile && window.google) {
            const clientId = document.querySelector('meta[name="google-client-id"]').content;
            google.accounts.id.initialize({
                client_id: clientId,
                callback: handleGoogleAuth
            });
            google.accounts.id.renderButton(
                document.querySelector('.g_id_signin'),
                { theme: 'outline', size: 'large', width: 250 }
            );
        }
    });
}

window.handleGoogleAuth = async function (response) {
    console.log("Google Auth Callback Triggered!");

    try {
        if (!response || !response.credential) {
            console.error("No credential received from Google!");
            return;
        }

        // Authenticate with backend
        console.log("Sending credential to backend for verification...");
        const res = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential })
        });

        console.log("Backend response status:", res.status);
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || 'Backend authentication failed');
        }

        const data = await res.json();

        state.profile = data.user;
        localStorage.setItem('voteiq_profile', JSON.stringify(state.profile)); // Still useful for non-critical UI state
        syncVoterCard();

        if (data.user.status === 'complete') {
            console.log("Existing complete user signed in:", data.user);
            const modalEl = document.getElementById('profileModal');
            if (modalEl) {
                const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
                if (modalInstance) modalInstance.hide();
            }
        } else {
            console.log("New or incomplete user. Showing signup form.");
        }
    } catch (err) {
        console.error('Google Auth Error:', err);
        alert('Authentication failed: ' + err.message);
    }
}

$('signup-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const stateCode = $('prof-state').value;
    const dob = $('prof-dob').value;

    if (!stateCode || !dob) return;

    try {
        const res = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: stateCode, dob }) // Email is from server session
        });
        const data = await res.json();

        if (data.status === 'success') {
            state.profile = data.user;
            localStorage.setItem('voteiq_profile', JSON.stringify(state.profile));
            syncVoterCard();

            // Close modal after completing signup
            const modalEl = document.getElementById('profileModal');
            if (modalEl) {
                const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
                if (modalInstance) modalInstance.hide();
            }
        } else {
            alert('Signup failed: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Signup Error:', err);
    }
});

$('logout-btn')?.addEventListener('click', async () => {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        state.profile = null;
        localStorage.removeItem('voteiq_profile');
        syncVoterCard(); // This will show the sign-in view
    } catch (e) {
        console.error("Logout failed", e);
    }
});

$('share-card-btn')?.addEventListener('click', async () => {
    const btn = $('share-card-btn');
    const ogText = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Copied to Clipboard!';
    btn.classList.add('btn-success');
    btn.classList.remove('btn-outline-secondary');

    try {
        const shareText = `🗳️ VoteIQ Card\nName: ${state.profile.name}\nState: ${state.profile.state}\nID: ${state.profile.id}\nI'm ready for the elections!`;
        await navigator.clipboard.writeText(shareText);
    } catch (e) { }

    setTimeout(() => {
        btn.innerHTML = ogText;
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
    }, 2000);
});

// Q17 — Event listener for the myth-buster empty-state button (replaces inline onclick)
const mythGoToChatBtn = document.getElementById('myth-go-to-chat-btn');
if (mythGoToChatBtn) {
    mythGoToChatBtn.addEventListener('click', () => {
        const askBtn = document.querySelector('[data-mode="ask"]');
        if (askBtn) askBtn.click();
    });
}

// Initialize the app on page load
document.addEventListener('DOMContentLoaded', initializeApp);
