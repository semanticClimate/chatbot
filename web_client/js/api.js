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
 * @param {{ signal?: AbortSignal, top_k?: number, response_language?: string }} [opts]
 */
export async function postAsk(baseUrl, question, conversation, opts = {}) {
  const root = trimBaseUrl(baseUrl);
  const url = `${root}/ask`;
  const body = {
    question: String(question).trim(),
    conversation: Array.isArray(conversation) ? conversation : [],
  };
  if (opts.top_k != null) body.top_k = opts.top_k;
  if (opts.response_language != null && String(opts.response_language).trim()) {
    body.response_language = String(opts.response_language).trim().toLowerCase();
  }

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

/**
 * Absolute URL for the annotated HTML document (iframe src).
 * @param {string} baseUrl
 */
export function bookDocumentUrl(baseUrl) {
  return `${trimBaseUrl(baseUrl)}/book/document`;
}

/**
 * @param {string} baseUrl
 * @param {object[]} conversation
 */
export async function exportConversationCsv(baseUrl, conversation) {
  const root = trimBaseUrl(baseUrl);
  const res = await fetch(`${root}/conversation/export`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ conversation, format: "csv" }),
  });
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const data = text ? JSON.parse(text) : {};
      detail = data.detail ?? data.message ?? text;
    } catch {
      /* plain-text error */
    }
    throw new Error(typeof detail === "string" ? detail : text.slice(0, 200));
  }
  return new Blob([text], { type: "text/csv;charset=utf-8" });
}

/**
 * @param {string} baseUrl
 */
export async function fetchLogsCsvBlob(baseUrl) {
  const root = trimBaseUrl(baseUrl);
  const res = await fetch(`${root}/logs/export`);
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const data = text ? JSON.parse(text) : {};
      detail = data.detail ?? text;
    } catch {
      /* use raw */
    }
    throw new Error(
      typeof detail === "string" ? detail : text.slice(0, 200) || res.statusText
    );
  }
  return res.blob();
}
