// Follow the Money — Frontend Logic

let currentAudio = null;
let playQueue = [];
let isPlaying = false;
let currentTurnIndex = -1;
let revealTimeout = null;

const AGENT_IMAGES = {
    'Street Reporter': '/static/assets/reporter.png',
    'Insider': '/static/assets/insider.webp',
};

const AGENT_NAMES = {
    'Street Reporter': 'Andrew',
    'Insider': 'FJ',
};

const AGENT_LABELS = {
    'Street Reporter': 'Reporter',
    'Insider': 'Insider',
};

const INVESTIGATING_MESSAGES = [
    'Searching ownership records...',
    'Following the money trail...',
    'Cross-referencing sources...',
    'Pulling corporate filings...',
    'Checking recent acquisitions...',
    'Analyzing conflicts of interest...',
    'Reviewing editorial changes...',
    'Verifying with web sources...',
];

document.addEventListener('DOMContentLoaded', loadPublications);

async function loadPublications() {
    const res = await fetch('/api/publications');
    const pubs = await res.json();
    const grid = document.getElementById('pub-grid');

    grid.innerHTML = pubs.map(p => `
        <div class="pub-card" onclick="investigate('${p.id}', '${esc(p.name)}', '${esc(p.owner)}', '${esc(p.bias)}', '${esc(p.factuality)}', '${esc(p.category)}')">
            <div class="pub-name">${p.name}</div>
            <div class="pub-owner">${p.owner}</div>
            <div class="pub-bias">${p.bias}</div>
            <span class="pub-arrow">&rarr;</span>
        </div>
    `).join('');
}

async function investigate(pubId, name, owner, bias, factuality, category) {
    document.querySelector('.selector').classList.add('hidden');
    document.querySelector('.characters').classList.add('hidden');
    document.getElementById('investigation').classList.remove('hidden');

    document.getElementById('pub-title').textContent = name;
    document.getElementById('pub-owner').textContent = owner;
    document.getElementById('pub-meta').innerHTML = `
        <span class="badge">${bias}</span>
        <span class="badge">Factuality: ${factuality}</span>
        <span class="badge">${category}</span>
    `;

    document.getElementById('conversation').innerHTML = '';
    document.getElementById('play-all-btn').classList.add('hidden');
    document.getElementById('stop-btn').classList.add('hidden');

    // Show initial investigating state
    showInvestigating();

    let data = null;
    try {
        const demoRes = await fetch(`/api/demo/${pubId}`);
        if (demoRes.ok) data = await demoRes.json();
    } catch (e) {}

    if (data) {
        // Simulate investigation delay for pre-baked demos
        await simulateInvestigation();
        hideInvestigating();
        revealTurnsSequentially(data.turns);
        return;
    }

    // Actual live generation
    try {
        const res = await fetch(`/api/investigate/${pubId}`, { method: 'POST' });
        if (!res.ok) throw new Error('Investigation failed');
        data = await res.json();
        hideInvestigating();
        revealTurnsSequentially(data.turns);
    } catch (e) {
        hideInvestigating();
        document.getElementById('conversation').innerHTML = `
            <div class="turn">
                <div class="turn-text" style="color: var(--insider-color);">
                    Investigation failed: ${e.message}
                </div>
            </div>
        `;
    }
}

function showInvestigating() {
    document.getElementById('loading').classList.remove('hidden');
    cycleInvestigatingMessage();
}

function hideInvestigating() {
    document.getElementById('loading').classList.add('hidden');
    if (revealTimeout) { clearTimeout(revealTimeout); revealTimeout = null; }
}

function cycleInvestigatingMessage() {
    const el = document.querySelector('#loading p');
    if (!el) return;
    const msg = INVESTIGATING_MESSAGES[Math.floor(Math.random() * INVESTIGATING_MESSAGES.length)];
    el.textContent = msg;
    revealTimeout = setTimeout(cycleInvestigatingMessage, 1800);
}

function simulateInvestigation() {
    // Random delay between 3-5 seconds to feel real
    const delay = 3000 + Math.random() * 2000;
    return new Promise(resolve => setTimeout(resolve, delay));
}

async function revealTurnsSequentially(turns) {
    const container = document.getElementById('conversation');
    playQueue = [];
    container.innerHTML = '';

    for (let i = 0; i < turns.length; i++) {
        const turn = turns[i];
        const cls = turn.agent === 'Street Reporter' ? 'reporter' : 'insider';
        const img = AGENT_IMAGES[turn.agent] || '';
        const name = AGENT_NAMES[turn.agent] || turn.agent;
        const label = AGENT_LABELS[turn.agent] || turn.agent;
        const hasAudio = !!turn.audio_path;

        if (hasAudio) playQueue.push({ index: i, path: '/' + turn.audio_path });

        // Show investigating indicator for this agent
        const loader = document.createElement('div');
        loader.className = `turn-loader ${cls}`;
        loader.innerHTML = `
            <span class="turn-agent">
                <img src="${img}" alt="${label}">
                <span class="turn-agent-name">${name}</span>
                <span class="turn-agent-role">investigating...</span>
            </span>
            <span class="turn-loader-dots"><span>.</span><span>.</span><span>.</span></span>
        `;
        container.appendChild(loader);
        loader.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Wait to simulate thinking
        await new Promise(r => setTimeout(r, 1500 + Math.random() * 1500));

        // Remove loader, add real turn
        loader.remove();

        const turnEl = document.createElement('div');
        turnEl.className = `turn ${cls} collapsed`;
        turnEl.id = `turn-${i}`;
        turnEl.onclick = () => toggleTurn(i);
        turnEl.innerHTML = `
            <div class="turn-header">
                <span class="turn-agent">
                    <img src="${img}" alt="${label}">
                    <span class="turn-agent-name">${name}</span>
                    <span class="turn-agent-role">${label}</span>
                </span>
                <span class="turn-status">ready</span>
                <span class="turn-expand">+</span>
            </div>
            <div class="turn-body">
                <div class="turn-text">${turn.text}</div>
                ${hasAudio ? `<button class="turn-play" onclick="event.stopPropagation(); playSingle(${i})" title="Play">&#9654;</button>` : ''}
            </div>
        `;

        container.appendChild(turnEl);
        turnEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Brief pause before next agent starts investigating
        if (i < turns.length - 1) {
            await new Promise(r => setTimeout(r, 800));
        }
    }

    // All turns loaded — show play button
    if (playQueue.length > 0) {
        document.getElementById('play-all-btn').classList.remove('hidden');
    }
}

function renderConversation(turns) {
    // Fallback for direct render (not used in normal flow anymore)
    revealTurnsSequentially(turns);
}

function toggleTurn(i) {
    const el = document.getElementById(`turn-${i}`);
    if (el) el.classList.toggle('collapsed');
}

function expandTurn(i) {
    const el = document.getElementById(`turn-${i}`);
    if (el) el.classList.remove('collapsed');
}

function collapseTurn(i) {
    const el = document.getElementById(`turn-${i}`);
    if (el) el.classList.add('collapsed');
}

function playSingle(turnIndex) {
    stopPlayback();
    const item = playQueue.find(q => q.index === turnIndex);
    if (!item) return;

    expandTurn(turnIndex);
    highlightTurn(turnIndex);
    currentAudio = new Audio(item.path);
    currentAudio.onended = () => { unhighlightTurn(turnIndex); currentAudio = null; };
    currentAudio.play();
}

function playAll() {
    if (!playQueue.length) return;
    stopPlayback();

    // Collapse all turns first
    document.querySelectorAll('.turn').forEach(el => el.classList.add('collapsed'));

    isPlaying = true;
    document.getElementById('play-all-btn').classList.add('hidden');
    document.getElementById('stop-btn').classList.remove('hidden');
    playNext(0);
}

function playNext(qi) {
    if (!isPlaying || qi >= playQueue.length) {
        stopPlayback();
        return;
    }
    const item = playQueue[qi];

    expandTurn(item.index);
    highlightTurn(item.index);
    currentTurnIndex = item.index;

    currentAudio = new Audio(item.path);
    currentAudio.onended = () => {
        unhighlightTurn(item.index);
        setTimeout(() => playNext(qi + 1), 600);
    };
    currentAudio.play();
}

function stopPlayback() {
    isPlaying = false;
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    if (currentTurnIndex >= 0) { unhighlightTurn(currentTurnIndex); currentTurnIndex = -1; }
    document.getElementById('play-all-btn').classList.remove('hidden');
    document.getElementById('stop-btn').classList.add('hidden');
}

function highlightTurn(i) {
    const el = document.getElementById(`turn-${i}`);
    if (el) { el.classList.add('playing'); el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
}

function unhighlightTurn(i) {
    const el = document.getElementById(`turn-${i}`);
    if (el) el.classList.remove('playing');
}

function backToSelector() {
    stopPlayback();
    hideInvestigating();
    document.getElementById('conversation').innerHTML = '';
    document.getElementById('investigation').classList.add('hidden');
    document.querySelector('.selector').classList.remove('hidden');
    document.querySelector('.characters').classList.remove('hidden');
}

function esc(s) { return s.replace(/'/g, "\\'").replace(/"/g, '&quot;'); }
