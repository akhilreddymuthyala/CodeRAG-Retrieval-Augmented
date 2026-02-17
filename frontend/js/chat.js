/**
 * chat.js  —  CodeRAG Chat Interface
 *
 * Key fix: Backend returns ALL content (including code blocks)
 * inside data.answer as markdown text. The data.code_snippets
 * array is used for ADDITIONAL referenced snippets only.
 * The markdown renderer must handle everything correctly.
 */

/* ═══════════════ STATE ════════════════════════ */
let sessionId  = null;
let metadata   = null;
let isLoading  = false;
let msgCounter = 0;

/* ═══════════════ INIT ═════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  loadSession();
  setupInputHandlers();
  window.addEventListener('beforeunload', handleUnload);
});

/* ═══════════════ LOAD SESSION ═════════════════ */
function loadSession() {
  const session = Session.load();
  if (!session?.sessionId) {
    Toast.error('No active session', 'Redirecting to upload page...');
    setTimeout(() => window.location.href = 'index.html', 1500);
    return;
  }

  sessionId = session.sessionId;
  metadata  = session.metadata;

  // Sidebar
  document.getElementById('sidebarSessionId').textContent =
    sessionId.replace('sess_', '').slice(0, 14) + '...';
  document.getElementById('sidebarFiles').textContent   = metadata?.file_count       ?? '—';
  document.getElementById('sidebarChunks').textContent  = metadata?.chunk_count      ?? '—';
  document.getElementById('sidebarLang').textContent    = metadata?.primary_language ?? '—';

  // Header subtitle
  document.getElementById('chatSubtitle').textContent =
    `${metadata?.file_count ?? 0} files · ${metadata?.chunk_count ?? 0} chunks indexed`;

  // Model badge
  setModelBadge(metadata?.model_used ?? 'AI Ready');

  // Enable input
  document.getElementById('chatInput').disabled = false;
  document.getElementById('sendBtn').disabled   = false;
  document.getElementById('chatInput').focus();
}

/* ═══════════════ INPUT ════════════════════════ */
function setupInputHandlers() {
  const input = document.getElementById('chatInput');
  input.addEventListener('input', () => {
    document.getElementById('sendBtn').disabled =
      input.value.trim().length === 0 || isLoading;
  });
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

/* ═══════════════ SEND MESSAGE ═════════════════ */
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const q     = input.value.trim();
  if (!q || isLoading || !sessionId) return;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('sendBtn').disabled = true;
  document.getElementById('welcomeMsg')?.remove();

  addUserBubble(q);

  const typingId = showTyping();
  isLoading      = true;
  const t0       = Date.now();

  try {
    const data = await API.query(sessionId, q);
    removeTyping(typingId);

    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

    /*
     * Backend response shape:
     *   data.answer         — full markdown text (may contain ```code``` blocks)
     *   data.code_snippets  — optional extra snippet objects [{file, code, language, lines}]
     *   data.relevant_files — list of referenced filenames
     *   data.model_used     — model name string
     *   data.tokens_used    — integer
     */
    if (data.model_used) setModelBadge(data.model_used);

    addAssistantBubble(
      data.answer         || 'No answer received.',
      data.code_snippets  || [],
      data.relevant_files || [],
      {
        model:  data.model_used,
        tokens: data.tokens_used ?? data.tokens,
        time:   elapsed,
      }
    );

  } catch (err) {
    removeTyping(typingId);
    addErrorBubble(err.message);
    Toast.error('Query failed', err.message);
    console.error('[Chat]', err);
  }

  isLoading = false;
  document.getElementById('sendBtn').disabled = false;
  input.focus();
}

/* ═══════════════ BUBBLE BUILDERS ══════════════ */

function addUserBubble(text) {
  const id   = `msg-${++msgCounter}`;
  const time = now();
  const wrap = document.createElement('div');
  wrap.className = 'message user';
  wrap.id = id;
  wrap.innerHTML = `
    <div class="msg-avatar">ME</div>
    <div class="msg-content">
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-time">${time}</div>
    </div>`;
  appendToChat(wrap);
}

function addAssistantBubble(answer, snippets, relFiles, meta) {
  const id   = `msg-${++msgCounter}`;
  const time = now();
  const wrap = document.createElement('div');
  wrap.className = 'message assistant';
  wrap.id = id;

  /* Render the answer markdown (contains embedded code blocks) */
  const bodyHtml = renderMarkdown(answer);

  /* Extra code snippets from backend (separate from answer text) */
  const snippetsHtml = snippets.length
    ? snippets.map((s, i) => buildCodeBlock(s, `${id}-s${i}`)).join('')
    : '';

  /* Referenced files */
  const filesHtml = relFiles.length
    ? `<div class="relevant-files">
         <span class="ref-label">Referenced:</span>
         ${relFiles.map(f => `<span class="rel-file">📄 ${f}</span>`).join('')}
       </div>`
    : '';

  /* Meta footer */
  const metaHtml = buildMeta(meta);

  wrap.innerHTML = `
    <div class="msg-avatar">⬡</div>
    <div class="msg-content">
      <div class="msg-header-row">
        <div class="msg-bubble" id="${id}-body">${bodyHtml}</div>
        <button class="copy-response-btn" title="Copy response"
          onclick="copyText(document.getElementById('${id}-body').innerText)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>
      ${snippetsHtml}
      ${filesHtml}
      ${metaHtml}
      <div class="msg-time">${time}</div>
    </div>`;
  appendToChat(wrap);
}

function addErrorBubble(msg) {
  const wrap = document.createElement('div');
  wrap.className = 'message error';
  wrap.innerHTML = `
    <div class="msg-avatar">⚠</div>
    <div class="msg-content">
      <div class="msg-bubble">
        <strong>Error:</strong> ${escapeHtml(msg)}
        <br><small style="color:var(--text3)">Check that the backend is running and try again.</small>
      </div>
      <div class="msg-time">${now()}</div>
    </div>`;
  appendToChat(wrap);
}

/* ═══════════════ CODE BLOCK BUILDER ═══════════ */
function buildCodeBlock(snippet, uid) {
  const lang = snippet.language || detectLang(snippet.file || '');
  const safe = escapeHtml(snippet.code || '');
  return `
    <div class="code-block">
      <div class="code-header">
        <span class="code-file">📄 ${snippet.file || 'snippet'}</span>
        <div style="display:flex;align-items:center;gap:8px">
          ${lang ? `<span class="code-lang">${lang}</span>` : ''}
          ${snippet.lines ? `<span class="code-lines">Lines ${snippet.lines}</span>` : ''}
          <button class="copy-btn" id="${uid}-btn"
            onclick="copyCode('${uid}-btn','${uid}-pre')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>Copy
          </button>
        </div>
      </div>
      <pre class="code-body" id="${uid}-pre">${safe}</pre>
    </div>`;
}

/* ═══════════════ META FOOTER ══════════════════ */
function buildMeta(meta) {
  if (!meta) return '';
  const parts = [];
  if (meta.model)  parts.push(`🤖 ${meta.model.split('/').pop()}`);
  if (meta.tokens) parts.push(`🔢 ${meta.tokens} tokens`);
  if (meta.time)   parts.push(`⏱ ${meta.time}s`);
  if (!parts.length) return '';
  return `<div class="msg-meta">${
    parts.map(p => `<span>${p}</span>`).join('<span class="meta-dot">·</span>')
  }</div>`;
}

/* ═══════════════ TYPING INDICATOR ═════════════ */
function showTyping() {
  const id = 'typing-' + Date.now();
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = id;
  el.innerHTML = `
    <div class="msg-avatar">⬡</div>
    <div class="typing-dots"><span></span><span></span><span></span></div>`;
  appendToChat(el);
  return id;
}
function removeTyping(id) { document.getElementById(id)?.remove(); }

/* ═══════════════ SUGGESTIONS ══════════════════ */
function askSuggestion(btn) {
  const input = document.getElementById('chatInput');
  input.value = btn.textContent.trim();
  input.focus();
  autoResize(input);
  document.getElementById('sendBtn').disabled = false;
}

/* ═══════════════ CONTROLS ═════════════════════ */
function toggleSidebar() { document.querySelector('.sidebar').classList.toggle('open'); }

async function newUpload() {
  if (sessionId) { try { await API.cleanupSession(sessionId); } catch {} }
  Session.clear();
  window.location.href = 'index.html';
}

function clearChat() {
  if (!confirm('Clear all messages?')) return;
  msgCounter = 0;
  document.getElementById('messagesArea').innerHTML = `
    <div class="welcome-msg" id="welcomeMsg">
      <div class="welcome-icon">⬡</div>
      <h3>Ready to explore your code!</h3>
      <p>Ask anything about your codebase in plain English.</p>
    </div>`;
}

/* ═══════════════ COPY HELPERS ═════════════════ */
function copyCode(btnId, preId) {
  const text = document.getElementById(preId)?.textContent || '';
  copyText(text, btnId);
}

function copyText(text, btnId) {
  navigator.clipboard.writeText(text).then(() => {
    Toast.success('Copied!', 'Copied to clipboard');
    if (btnId) {
      const btn = document.getElementById(btnId);
      if (!btn) return;
      const orig = btn.innerHTML;
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Done!`;
      btn.style.color = 'var(--accent3)';
      setTimeout(() => { btn.innerHTML = orig; btn.style.color = ''; }, 2000);
    }
  }).catch(() => Toast.error('Copy failed', 'Please copy manually'));
}

/* ═══════════════ HELPERS ══════════════════════ */
function setModelBadge(model) {
  const el = document.getElementById('modelName');
  if (el) el.textContent = model.includes('/') ? model.split('/').pop() : model;
}

function appendToChat(el) {
  const area = document.getElementById('messagesArea');
  area.appendChild(el);
  setTimeout(() => area.scrollTo({ top: area.scrollHeight, behavior: 'smooth' }), 50);
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function detectLang(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  return { py:'python', js:'javascript', ts:'typescript', jsx:'jsx', tsx:'tsx',
           java:'java', cpp:'cpp', c:'c', go:'go', rs:'rust', rb:'ruby',
           php:'php', cs:'csharp', html:'html', css:'css', json:'json',
           md:'markdown', sh:'bash', bat:'batch', yaml:'yaml', yml:'yaml' }[ext] || ext || '';
}

function handleUnload() {
  if (sessionId) {
    try {
      navigator.sendBeacon('http://localhost:8000/api/session/cleanup',
        new Blob([JSON.stringify({ session_id: sessionId })], { type: 'application/json' }));
    } catch {}
  }
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ═══════════════════════════════════════════════════════════
   MARKDOWN RENDERER
   ─────────────────────────────────────────────────────────
   Strategy (order matters!):
    1. Pull out fenced code blocks  → stash, insert placeholder
    2. Pull out inline code         → stash, insert placeholder
    3. Escape remaining HTML
    4. Apply block transforms       (headers, lists, hr, blockquote)
    5. Apply inline transforms      (bold, italic, links)
    6. Convert newlines → paragraphs
    7. Re-inject stashed code blocks
   ═══════════════════════════════════════════════════════════ */

function renderMarkdown(raw) {
  if (!raw) return '';

  const blocks  = [];   // fenced code blocks
  const inlines = [];   // inline code spans

  /* ①  Extract fenced code blocks  ``` … ``` */
  let text = raw.replace(/```([\w+-]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx  = blocks.length;
    const safe = escapeHtml(code.trimEnd());
    const tag  = lang.trim();
    blocks.push(
      `<div class="md-code-block">` +
      (tag ? `<div class="md-code-lang">${escapeHtml(tag)}</div>` : '') +
      `<div class="md-code-copy-wrap">` +
        `<button class="md-copy-btn" onclick="copyMdBlock(this)">Copy</button>` +
      `</div>` +
      `<pre class="code-body md-pre">${safe}</pre>` +
      `</div>`
    );
    return `\x02BLOCK${idx}\x03`;
  });

  /* ②  Extract inline code  ` … ` */
  text = text.replace(/`([^`\n]+)`/g, (_, code) => {
    const idx = inlines.length;
    inlines.push(`<code class="md-inline">${escapeHtml(code)}</code>`);
    return `\x02INLINE${idx}\x03`;
  });

  /* ③  Escape remaining HTML */
  text = text
    .replace(/&(?!amp;|lt;|gt;|quot;|#\d+;)/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  /* ④  Block-level transforms */

  // ATX headers
  text = text
    .replace(/^#{4,6} (.+)$/gm,'<h4 class="md-h4">$1</h4>')
    .replace(/^### (.+)$/gm,  '<h3 class="md-h3">$1</h3>')
    .replace(/^## (.+)$/gm,   '<h2 class="md-h2">$1</h2>')
    .replace(/^# (.+)$/gm,    '<h1 class="md-h1">$1</h1>');

  // Horizontal rule
  text = text.replace(/^[-*_]{3,}$/gm, '<hr class="md-hr">');

  // Blockquote
  text = text.replace(/^&gt; (.+)$/gm,
    '<blockquote class="md-blockquote">$1</blockquote>');

  // Unordered lists — collect consecutive bullet lines into one <ul>
  text = text.replace(/((?:^[ \t]*[-*+] .+(?:\n|$))+)/gm, match => {
    const items = match.trim().split('\n')
      .filter(l => l.trim())
      .map(l => `<li>${l.replace(/^[ \t]*[-*+] /, '').trim()}</li>`)
      .join('');
    return `<ul class="md-ul">${items}</ul>\n`;
  });

  // Ordered lists — collect consecutive numbered lines
  text = text.replace(/((?:^\d+\. .+(?:\n|$))+)/gm, match => {
    const items = match.trim().split('\n')
      .filter(l => l.trim())
      .map(l => `<li>${l.replace(/^\d+\. /, '').trim()}</li>`)
      .join('');
    return `<ol class="md-ol">${items}</ol>\n`;
  });

  /* ⑤  Inline transforms */
  text = text
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g,     '<em>$1</em>')
    .replace(/__(.+?)__/g,         '<strong>$1</strong>')
    .replace(/_([^_\s][^_\n]*)_/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>');

  /* ⑥  Build paragraphs from plain lines */
  const isBlockTag = s =>
    /^<(h[1-6]|ul|ol|li|blockquote|hr|pre|div|table)\b/.test(s.trim()) ||
    /^<\/(ul|ol|blockquote|div|table)>/.test(s.trim()) ||
    s.includes('\x02BLOCK');

  const lines  = text.split('\n');
  const result = [];
  let   para   = [];

  const flushPara = () => {
    if (para.length) {
      result.push(`<p class="md-p">${para.join('<br>')}</p>`);
      para = [];
    }
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      flushPara();
    } else if (isBlockTag(t)) {
      flushPara();
      result.push(t);
    } else {
      para.push(t);
    }
  }
  flushPara();
  text = result.join('\n');

  /* ⑦  Restore code blocks & inline code */
  blocks.forEach((b, i)  => { text = text.replace(`\x02BLOCK${i}\x03`,  b); });
  inlines.forEach((c, i) => { text = text.replace(`\x02INLINE${i}\x03`, c); });

  return text;
}

/* Copy button inside markdown code blocks */
function copyMdBlock(btn) {
  const pre = btn.closest('.md-code-block')?.querySelector('pre');
  if (!pre) return;
  navigator.clipboard.writeText(pre.textContent).then(() => {
    btn.textContent = 'Copied!';
    btn.style.color = 'var(--accent3)';
    setTimeout(() => { btn.textContent = 'Copy'; btn.style.color = ''; }, 2000);
  });
}