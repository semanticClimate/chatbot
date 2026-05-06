/**
 * HTTP layer for the Climate RAG API. No UI dependencies.
 */

const JSON_HEADERS = { "Content-Type": "application/json" };

function trimBaseUrl(baseUrl) {
  return String(baseUrl || "").trim().replace(/\/+$/, "");
}

/**
 * @param {string} baseUrl
 * @param {string} question
 * @param {object[]} conversation  API-shaped history (previous turns only; current question passed separately).
 * @param {{ signal?: AbortSignal, top_k?: number }} [opts]
 */
export async function postAsk(baseUrl, question, conversation, opts = {}) {
  const root = trimBaseUrl(baseUrl);
  const url = `${root}/ask`;
  const body = {
    question: String(question).trim(),
    conversation: Array.isArray(conversation) ? conversation : [],
  };
  if (opts.top_k != null) body.top_k = opts.top_k;

  const res = await fetch(url, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    signal: opts.signal,
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Invalid JSON from /ask (${res.status}): ${text.slice(0, 200)}`);
  }

  if (!res.ok) {
    const detail = data.detail ?? data.message ?? text;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

/**
 * @param {string} baseUrl
 */
export async function getHealth(baseUrl) {
  const root = trimBaseUrl(baseUrl);
  const res = await fetch(`${root}/health`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

/**
 * @param {string} baseUrl
 */
export async function getReady(baseUrl) {
  const root = trimBaseUrl(baseUrl);
  const res = await fetch(`${root}/ready`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}
