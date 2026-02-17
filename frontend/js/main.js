/**
 * main.js — Upload page logic (index.html)
 */

/* ── INIT ──────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
  checkExistingSession();
  await pingServer();
  setupDragDrop();
});

/* ── SERVER STATUS ─────────────────────────────── */

async function pingServer() {
  const dot  = document.querySelector('.badge-dot');
  const text = document.getElementById('serverStatus');

  try {
    await API.health();
    dot.className  = 'badge-dot online';
    text.textContent = 'Backend Online';
  } catch {
    dot.className  = 'badge-dot offline';
    text.textContent = 'Backend Offline';
    Toast.error('Backend Offline', 'Start your backend on port 8000 first');
  }
}

/* ── EXISTING SESSION CHECK ────────────────────── */

function checkExistingSession() {
  const session = Session.load();
  if (session?.sessionId) {
    // Session exists – ask user
    const banner = document.createElement('div');
    banner.className = 'session-banner';
    banner.innerHTML = `
      <span>You have an active session. Continue or start fresh?</span>
      <div style="display:flex;gap:8px">
        <button class="btn-banner-continue" onclick="goToChat()">Continue</button>
        <button class="btn-banner-new" onclick="clearOldSession(this)">New Upload</button>
      </div>
    `;
    banner.style.cssText = `
      background: rgba(0,212,255,0.08);
      border: 1px solid rgba(0,212,255,0.2);
      border-radius: 10px;
      padding: 14px 20px;
      margin: 0 24px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      font-size: 14px;
      color: var(--text2);
      animation: fadeIn 0.4s ease;
    `;

    const uploadSection = document.querySelector('.upload-section .container');
    if (uploadSection) uploadSection.insertAdjacentElement('beforebegin', banner);
  }
}

function clearOldSession(btn) {
  Session.clear();
  btn.closest('.session-banner')?.remove();
}

function goToChat() {
  window.location.href = 'chat.html';
}

/* ── TABS ──────────────────────────────────────── */

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

/* ── DRAG & DROP ───────────────────────────────── */

function setupDragDrop() {
  const zone = document.getElementById('dropZone');
  if (!zone) return;

  ['dragenter', 'dragover'].forEach(e => {
    zone.addEventListener(e, ev => {
      ev.preventDefault();
      zone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(e => {
    zone.addEventListener(e, ev => {
      ev.preventDefault();
      zone.classList.remove('drag-over');
    });
  });

  zone.addEventListener('drop', ev => {
    const file = ev.dataTransfer.files?.[0];
    if (file) {
      if (!file.name.endsWith('.zip')) {
        Toast.error('Invalid file', 'Only .zip files are supported');
        return;
      }
      setSelectedFile(file);
    }
  });
}

/* ── FILE SELECTION ────────────────────────────── */

let selectedFile = null;

function handleFileSelect(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  if (!file.name.endsWith('.zip')) {
    Toast.error('Invalid file', 'Only .zip files are supported');
    return;
  }

  if (file.size > 100 * 1024 * 1024) {
    Toast.error('File too large', 'Maximum file size is 100MB');
    return;
  }

  setSelectedFile(file);
}

function setSelectedFile(file) {
  selectedFile = file;

  // Show selected file
  document.getElementById('selectedFile').style.display = 'flex';
  document.getElementById('fileName').textContent = `${file.name} (${formatBytes(file.size)})`;

  // Hide drop zone, show file info
  document.getElementById('dropZone').style.display = 'none';

  // Enable button
  document.getElementById('uploadBtn').disabled = false;
}

function clearFile() {
  selectedFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('selectedFile').style.display = 'none';
  document.getElementById('dropZone').style.display = 'block';
  document.getElementById('uploadBtn').disabled = true;
}

/* ── GITHUB INPUT VALIDATION ───────────────────── */

function validateGithubInput() {
  const url = document.getElementById('repoUrl').value.trim();
  const btn = document.getElementById('githubBtn');
  const isValid = /^https?:\/\/(www\.)?github\.com\/.+\/.+/.test(url);
  btn.disabled = !isValid;
}

/* ── UPLOAD ZIP ────────────────────────────────── */

async function uploadZip() {
  if (!selectedFile) return;

  showProgress('Uploading ZIP file...', 'Reading and extracting your codebase');

  try {
    updateStep(1);
    const data = await API.uploadZip(selectedFile, (pct) => {
      setProgressBar(pct * 0.4); // 0–40%
    });

    updateStep(2);
    setProgressBar(60);
    updateProgressTitle('Parsing code...', 'Identifying functions, classes, and modules');
    await sleep(800);

    updateStep(3);
    setProgressBar(85);
    updateProgressTitle('Building index...', 'Creating vector embeddings for fast search');
    await sleep(1000);

    updateStep(4);
    setProgressBar(100);
    updateProgressTitle('Ready!', 'Your codebase has been indexed successfully');

    // Save session
    Session.save(data.session_id, data.metadata);

    await sleep(800);
    hideProgress();

    Toast.success('Upload complete!', `${data.metadata?.file_count || 0} files indexed`);

    await sleep(600);
    window.location.href = 'chat.html';

  } catch (err) {
    hideProgress();
    Toast.error('Upload failed', err.message);
    console.error('[Upload]', err);
  }
}

/* ── UPLOAD GITHUB ─────────────────────────────── */

async function uploadGithub() {
  const url    = document.getElementById('repoUrl').value.trim();
  const branch = document.getElementById('branchName').value.trim() || 'main';

  if (!url) return;

  showProgress('Cloning repository...', `Fetching from GitHub (branch: ${branch})`);

  try {
    updateStep(1);
    setProgressBar(20);

    const data = await API.uploadGithub(url, branch);

    updateStep(2);
    setProgressBar(50);
    updateProgressTitle('Parsing code...', 'Identifying functions, classes, and modules');
    await sleep(600);

    updateStep(3);
    setProgressBar(80);
    updateProgressTitle('Building index...', 'Creating vector embeddings for fast search');
    await sleep(800);

    updateStep(4);
    setProgressBar(100);
    updateProgressTitle('Ready!', 'Repository indexed successfully');

    Session.save(data.session_id, data.metadata);

    await sleep(800);
    hideProgress();

    Toast.success('Repository cloned!', `${data.metadata?.file_count || 0} files indexed`);

    await sleep(600);
    window.location.href = 'chat.html';

  } catch (err) {
    hideProgress();
    Toast.error('Clone failed', err.message);
    console.error('[GitHub]', err);
  }
}

/* ── PROGRESS HELPERS ──────────────────────────── */

function showProgress(title, sub) {
  document.getElementById('progressTitle').textContent = title;
  document.getElementById('progressSub').textContent   = sub;
  document.getElementById('progressBar').style.width   = '0%';
  document.getElementById('progressOverlay').style.display = 'flex';

  // Reset steps
  document.querySelectorAll('.step-dot').forEach(d => {
    d.classList.remove('active', 'done');
  });
}

function hideProgress() {
  document.getElementById('progressOverlay').style.display = 'none';
}

function updateProgressTitle(title, sub) {
  document.getElementById('progressTitle').textContent = title;
  document.getElementById('progressSub').textContent   = sub;
}

function setProgressBar(pct) {
  document.getElementById('progressBar').style.width = `${Math.min(pct, 100)}%`;
}

function updateStep(stepNum) {
  for (let i = 1; i <= 4; i++) {
    const dot = document.querySelector(`#step${i} .step-dot`);
    if (!dot) continue;
    if (i < stepNum) {
      dot.classList.remove('active');
      dot.classList.add('done');
    } else if (i === stepNum) {
      dot.classList.add('active');
      dot.classList.remove('done');
    } else {
      dot.classList.remove('active', 'done');
    }
  }
}

/* ── UTILITIES ─────────────────────────────────── */

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}