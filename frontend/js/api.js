/**
 * CodeRAG API Service
 * Handles all communication with the FastAPI backend
 */

const API = (() => {

  const BASE_URL = 'http://localhost:8000';
  const TIMEOUT  = 300000; // 5 min for large uploads

  /* ── CORE FETCH WRAPPER ───────────────────────── */

  async function request(method, path, body = null, isFormData = false) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT);

    const options = {
      method,
      signal: controller.signal,
      headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    };

    if (body) {
      options.body = isFormData ? body : JSON.stringify(body);
    }

    try {
      const res = await fetch(`${BASE_URL}${path}`, options);
      clearTimeout(timer);

      // Parse response
      let data;
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        data = { detail: await res.text() };
      }

      if (!res.ok) {
        const msg = data?.detail || `HTTP ${res.status}: ${res.statusText}`;
        throw new APIError(msg, res.status, data);
      }

      return data;

    } catch (err) {
      clearTimeout(timer);

      if (err instanceof APIError) throw err;

      if (err.name === 'AbortError') {
        throw new APIError('Request timed out. Please try again.', 408);
      }
      if (err.message === 'Failed to fetch') {
        throw new APIError('Cannot connect to backend. Is it running on port 8000?', 0);
      }

      throw new APIError(err.message || 'Unknown error', 0);
    }
  }

  /* ── API ERROR CLASS ──────────────────────────── */

  class APIError extends Error {
    constructor(message, status = 0, data = null) {
      super(message);
      this.name    = 'APIError';
      this.status  = status;
      this.data    = data;
    }
  }

  /* ── ENDPOINTS ────────────────────────────────── */

  return {

    APIError,

    /**
     * Check backend health
     */
    async health() {
      return request('GET', '/health');
    },

    /**
     * Upload a ZIP file
     * @param {File} file
     * @param {function} onProgress - optional progress callback (0-100)
     */
    async uploadZip(file, onProgress) {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        };

        xhr.onload = () => {
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(data);
            } else {
              reject(new APIError(data?.detail || `Upload failed (${xhr.status})`, xhr.status));
            }
          } catch {
            reject(new APIError('Invalid response from server', xhr.status));
          }
        };

        xhr.onerror = () => reject(new APIError('Network error during upload', 0));
        xhr.ontimeout = () => reject(new APIError('Upload timed out', 408));

        xhr.timeout = TIMEOUT;
        xhr.open('POST', `${BASE_URL}/api/upload/zip`);
        xhr.send(formData);
      });
    },

    /**
     * Clone a GitHub repository
     * @param {string} repoUrl
     * @param {string} branch
     */
    async uploadGithub(repoUrl, branch = 'main') {
      return request('POST', '/api/upload/github', { repo_url: repoUrl, branch });
    },

    /**
     * Query the indexed codebase
     * @param {string} sessionId
     * @param {string} question
     */
    async query(sessionId, question) {
      return request('POST', '/api/query', { session_id: sessionId, question });
    },

    /**
     * Get session status
     * @param {string} sessionId
     */
    async sessionStatus(sessionId) {
      return request('GET', `/api/session/status?session_id=${encodeURIComponent(sessionId)}`);
    },

    /**
     * Delete / cleanup a session
     * @param {string} sessionId
     */
    async cleanupSession(sessionId) {
      return request('DELETE', '/api/session/cleanup', { session_id: sessionId });
    },
  };

})();


/* ── SESSION STORAGE HELPERS ──────────────────── */

const Session = {

  KEY: 'coderag_session',

  save(sessionId, metadata) {
    try {
      localStorage.setItem(this.KEY, JSON.stringify({ sessionId, metadata, savedAt: Date.now() }));
    } catch { /* storage full */ }
  },

  load() {
    try {
      const raw = localStorage.getItem(this.KEY);
      if (!raw) return null;

      const data = JSON.parse(raw);

      // Expire sessions older than 1 hour
      if (Date.now() - data.savedAt > 3600 * 1000) {
        this.clear();
        return null;
      }

      return data;
    } catch {
      return null;
    }
  },

  clear() {
    localStorage.removeItem(this.KEY);
  },

  get sessionId() {
    return this.load()?.sessionId || null;
  },

  get metadata() {
    return this.load()?.metadata || null;
  },
};


/* ── TOAST NOTIFICATION ───────────────────────── */

const Toast = {

  show(type, title, msg, duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        ${msg ? `<div class="toast-msg">${msg}</div>` : ''}
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(el);

    if (duration > 0) {
      setTimeout(() => {
        el.classList.add('hide');
        setTimeout(() => el.remove(), 300);
      }, duration);
    }
  },

  success(title, msg)  { this.show('success', title, msg); },
  error(title, msg)    { this.show('error',   title, msg); },
  warning(title, msg)  { this.show('warning', title, msg); },
  info(title, msg)     { this.show('info',    title, msg); },
};