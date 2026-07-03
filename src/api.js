export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// One session per page-load. The backend's SessionStore keys on this header,
// so every request in a single session must share the same ID — otherwise a
// freshly-uploaded source disappears from the next /session call.
let _sessionId = null;
function getSessionId() {
  if (_sessionId) return _sessionId;
  _sessionId =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;
  return _sessionId;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('x-session-id', getSessionId());

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json();
}

export function getSession() {
  return request('/session');
}

export function getHistory() {
  return request('/history');
}

export function sendChat(query, knowledgeMode) {
  return request('/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, knowledge_mode: knowledgeMode }),
  });
}

export function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/upload', {
    method: 'POST',
    body: formData,
  });
}

export function addWikipediaSource(urlOrTopic) {
  return request('/wiki', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ url_or_topic: urlOrTopic }),
  });
}

export function deleteSource(sourceId) {
  return request(`/source/${encodeURIComponent(sourceId)}`, {
    method: 'DELETE',
  });
}

export function searchArticles(topic) {
  return request(`/articles?topic=${encodeURIComponent(topic)}`);
}

export function selectArticle(article) {
  return request('/select-article', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ article }),
  });
}
