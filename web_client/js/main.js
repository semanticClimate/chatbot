/**
 * Wiring: settings persistence, composer, API calls, render loop.
 */

import {
  postAsk,
  getHealth,
  getReady,
  getBookOutline,
  bookDocumentUrl,
  exportConversationCsv,
  fetchLogsCsvBlob,
} from "./api.js";
import {
  getConversation,
  clearConversation,
  applyConversationFull,
} from "./state.js";
import { renderThread, renderSourceDetail, setStatus } from "./render.js";

const STORAGE_KEY_API = "climate_web_client_api_base";

const DEFAULT_API_BASE = "http://127.0.0.1:8800";

function trimBaseUrl(baseUrl) {
  return String(baseUrl || "").trim().replace(/\/+$/, "");
}

function normalizedDefaultApiBase() {
  return trimBaseUrl(DEFAULT_API_BASE);
}

/** True when the chat UI is opened via a public tunnel hostname (not local dev). */
function isRemoteWebOrigin() {
  const h = window.location.hostname;
  if (!h) return false;
  return h !== "localhost" && h !== "127.0.0.1";
}

function isLoopbackApiBase(raw) {
  try {
    const u = new URL(String(raw || "").trim());
    return u.hostname === "127.0.0.1" || u.hostname === "localhost";
  } catch {
    return false;
  }
}

/** Prefer empty API base on remote tunnel pages over misleading localhost. */
function fallbackApiBase() {
  return isRemoteWebOrigin() ? "" : DEFAULT_API_BASE;
}

/**
 * Accept only absolute http(s) URLs. Paths like /Users/.../tunnel-api.log are
 * mistaken for URLs and resolve against the tunnel host, yielding 501 from
 * Python's static http.server on POST /ask.
 */
function isAcceptableApiBase(raw) {
  const s = String(raw || "").trim();
  if (!s) return false;
  try {
    const u = new URL(s);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function $(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
}

function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function apiOriginFromBase(base) {
  try {
    return new URL(trimBaseUrl(base)).origin;
  } catch {
    return "";
  }
}

/**
 * @param {object | null | undefined} source
 * @param {string} targetOrigin
 */
function jumpBookToSource(source, targetOrigin) {
  const iframe = document.getElementById("bookFrame");
  if (!iframe?.contentWindow || !targetOrigin || !source) return;
  const anchorId = source.anchor_id || "";
  const section = source.section_number || "";
  const headingId = source.heading_id || "";
  /** @type {object | null} */
  let payload = null;
  if (anchorId) {
    payload = { type: "ca-jump-para", anchor_id: anchorId, section };
  } else if (section) {
    payload = {
      type: "ca-jump",
      section,
      keywords: [],
      heading_id: headingId,
    };
  } else if (headingId) {
    payload = {
      type: "ca-jump",
      section: "",
      keywords: [],
      heading_id: headingId,
    };
  }
  if (payload) {
    iframe.contentWindow.postMessage(payload, targetOrigin);
  }
}

/**
 * @param {object} row
 * @param {string} targetOrigin
 */
function jumpBookToOutlineRow(row, targetOrigin) {
  const iframe = document.getElementById("bookFrame");
  if (!iframe?.contentWindow || !targetOrigin || !row) return;
  const section = row.section_number || "";
  const headingId = row.heading_id || "";
  const payload = section
    ? {
        type: "ca-jump",
        section,
        keywords: [],
        heading_id: headingId,
      }
    : headingId
      ? {
          type: "ca-jump",
          section: "",
          keywords: [],
          heading_id: headingId,
        }
      : null;
  if (payload) {
    iframe.contentWindow.postMessage(payload, targetOrigin);
  }
}

/**
 * @param {Array<{ section_number: string, title: string, heading_id: string, level: number }>} sections
 * @param {string} targetOrigin
 */
function renderOutlineRows(sections, targetOrigin) {
  const tbody = document.getElementById("outlineBody");
  const empty = document.getElementById("outlineEmpty");
  const table = document.getElementById("outlineTable");
  if (!tbody || !empty || !table) return;

  tbody.innerHTML = "";
  if (!sections.length) {
    empty.classList.remove("hidden");
    empty.textContent = "No outline sections returned.";
    table.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  table.classList.remove("hidden");

  for (const row of sections) {
    const tr = document.createElement("tr");
    const tdNum = document.createElement("td");
    tdNum.className = "outline-cell outline-cell-num";
    tdNum.textContent = row.section_number ? `§ ${row.section_number}` : "—";

    const tdTitle = document.createElement("td");
    tdTitle.className = "outline-cell outline-cell-title";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "outline-jump-btn";
    const lv = Number(row.level) || 1;
    btn.style.paddingLeft = `${8 + Math.max(0, lv - 1) * 10}px`;
    btn.textContent = row.title || "(untitled)";
    btn.title = row.title || "";
    btn.addEventListener("click", () => jumpBookToOutlineRow(row, targetOrigin));
    tdTitle.appendChild(btn);

    tr.appendChild(tdNum);
    tr.appendChild(tdTitle);
    tbody.appendChild(tr);
  }
}

/**
 * @param {string} apiBase
 * @param {HTMLElement} statusLine
 */
async function syncBookPanel(apiBase, statusLine) {
  const iframe = document.getElementById("bookFrame");
  const empty = document.getElementById("outlineEmpty");
  const table = document.getElementById("outlineTable");
  const tbody = document.getElementById("outlineBody");
  if (!iframe || !empty || !table || !tbody) return;

  const origin = apiOriginFromBase(apiBase);

  if (!apiBase || !isAcceptableApiBase(apiBase)) {
    iframe.removeAttribute("src");
    tbody.innerHTML = "";
    empty.classList.remove("hidden");
    empty.textContent =
      "Set a valid API base URL to load the book outline and viewer.";
    table.classList.add("hidden");
    return;
  }

  try {
    const data = await getBookOutline(apiBase);
    const sections = Array.isArray(data.sections) ? data.sections : [];
    renderOutlineRows(sections, origin);
    iframe.src = bookDocumentUrl(apiBase);
  } catch (e) {
    iframe.removeAttribute("src");
    tbody.innerHTML = "";
    empty.classList.remove("hidden");
    empty.textContent = String(e.message || e);
    table.classList.add("hidden");
    setStatus(statusLine, String(e.message || e), "error");
  }
}

async function fetchTunnelHintApiBase() {
  const attempt = async () => {
    try {
      const u = new URL("tunnel-api-base.txt", window.location.href);
      if (isRemoteWebOrigin()) {
        u.searchParams.set("cb", String(Date.now()));
      }
      const res = await fetch(u, { cache: "no-store" });
      if (!res.ok) return "";
      const text = (await res.text()).trim();
      return isAcceptableApiBase(text) ? text : "";
    } catch {
      return "";
    }
  };

  let hint = await attempt();
  if (!hint && isRemoteWebOrigin()) {
    await new Promise((r) => setTimeout(r, 450));
    hint = await attempt();
  }
  return hint;
}

/**
 * Prefer saved setting; else same-origin tunnel hint (written by start-quick-tunnel.sh);
 * else local dev default.
 */
async function resolveInitialApiBase(statusLine) {
  const stored = loadApiBase();
  const hinted = await fetchTunnelHintApiBase();

  if (stored && !isAcceptableApiBase(stored)) {
    saveApiBase("");
    const v = hinted || fallbackApiBase();
    const parts = [
      "Saved API base was not a valid http(s) URL (e.g. a file path was pasted). Reset.",
    ];
    if (!v && isRemoteWebOrigin()) {
      parts.push(
        "tunnel-api-base.txt was not found — paste the API tunnel URL or reload."
      );
    }
    setStatus(statusLine, parts.join(" "), "error");
    return v;
  }

  const storedTrim = stored ? trimBaseUrl(stored) : "";
  const storedIsDefaultLocal =
    storedTrim === normalizedDefaultApiBase();

  if (stored) {
    if (hinted) {
      if (isRemoteWebOrigin()) {
        if (isLoopbackApiBase(stored) || storedIsDefaultLocal) {
          saveApiBase(hinted);
          return hinted;
        }
        return stored;
      }
      if (storedIsDefaultLocal) {
        saveApiBase(hinted);
        return hinted;
      }
      return stored;
    }
    return stored;
  }

  const out = hinted || fallbackApiBase();
  if (!out && isRemoteWebOrigin()) {
    setStatus(
      statusLine,
      "Could not load tunnel-api-base.txt from this page. Paste the API tunnel URL or reload.",
      "error"
    );
  }
  return out;
}

function loadApiBase() {
  try {
    return localStorage.getItem(STORAGE_KEY_API) || "";
  } catch {
    return "";
  }
}

function saveApiBase(url) {
  try {
    localStorage.setItem(STORAGE_KEY_API, url.trim());
  } catch {
    /* ignore quota */
  }
}

function scrollThreadToBottom() {
  const thread = $("thread");
  thread.scrollTop = thread.scrollHeight;
}

async function refreshView(apiBase) {
  const thread = $("thread");
  const sourcesDetail = $("sourcesDetail");
  const origin = apiOriginFromBase(apiBase);
  renderThread(thread, getConversation(), (sourceId, sources) => {
    const src = sources.find((s) => s.source_id === sourceId);
    renderSourceDetail(sourcesDetail, src || null);
    jumpBookToSource(src, origin);
  });
  renderSourceDetail(sourcesDetail, null);
  scrollThreadToBottom();
}

async function wire() {
  const apiInput = $("apiBaseUrl");
  const statusLine = $("statusLine");
  const composer = $("composer");
  const question = $("question");
  const btnSend = $("btnSend");
  const btnHealth = $("btnHealth");
  const btnClear = $("btnClear");
  const btnExportChat = $("btnExportChat");
  const btnExportLogs = $("btnExportLogs");
  const btnResetBook = document.getElementById("btnResetBook");

  apiInput.value = await resolveInitialApiBase(statusLine);
  await syncBookPanel(apiInput.value.trim(), statusLine);

  apiInput.addEventListener("change", async () => {
    const v = apiInput.value.trim();
    if (v && !isAcceptableApiBase(v)) {
      setStatus(
        statusLine,
        "Use a full URL such as https://….trycloudflare.com or http://127.0.0.1:8800 — not a log file path.",
        "error"
      );
      return;
    }
    saveApiBase(apiInput.value);
    await syncBookPanel(v, statusLine);
  });

  if (btnResetBook) {
    btnResetBook.addEventListener("click", () => {
      const base = apiInput.value.trim();
      if (!base || !isAcceptableApiBase(base)) return;
      const iframe = document.getElementById("bookFrame");
      if (iframe) {
        iframe.src = bookDocumentUrl(base);
      }
    });
  }

  btnClear.addEventListener("click", () => {
    clearConversation();
    setStatus(statusLine, "Chat cleared.");
    refreshView(apiInput.value.trim());
  });

  btnExportChat.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base || !isAcceptableApiBase(base)) {
      setStatus(statusLine, "Set API base URL first.", "error");
      return;
    }
    const conv = getConversation();
    if (!conv.length) {
      setStatus(statusLine, "Nothing to export yet.", "error");
      return;
    }
    setStatus(statusLine, "Preparing CSV…");
    try {
      const blob = await exportConversationCsv(base, conv);
      triggerBrowserDownload(blob, "conversation.csv");
      setStatus(statusLine, "Saved conversation.csv", "info");
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
    }
  });

  btnExportLogs.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base || !isAcceptableApiBase(base)) {
      setStatus(statusLine, "Set API base URL first.", "error");
      return;
    }
    setStatus(statusLine, "Fetching logs…");
    try {
      const blob = await fetchLogsCsvBlob(base);
      triggerBrowserDownload(blob, "chatbot_logs.csv");
      setStatus(statusLine, "Saved chatbot_logs.csv", "info");
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
    }
  });

  btnHealth.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base) {
      setStatus(statusLine, "Set API base URL first.", "error");
      return;
    }
    setStatus(statusLine, "Checking…");
    try {
      const h = await getHealth(base);
      const r = await getReady(base);
      setStatus(
        statusLine,
        `Health: ${JSON.stringify(h)} | Ready: ${JSON.stringify(r)}`,
        "info"
      );
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
    }
  });

  composer.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const base = apiInput.value.trim();
    const q = question.value.trim();
    if (!base || !q) return;

    const prior = getConversation();
    btnSend.disabled = true;
    setStatus(statusLine, "Sending…");

    const abort = new AbortController();
    /** Optimistic user bubble — we render user + prior; API will reconcile */
    try {
      const tempConv = prior.slice();
      tempConv.push({ role: "user", content: q });
      renderThread($("thread"), tempConv, () => {});
      scrollThreadToBottom();

      const data = await postAsk(base, q, prior, { signal: abort.signal });
      applyConversationFull(data.conversation_full);
      const t =
        data.timings_ms && data.timings_ms.total != null
          ? `OK — ${data.timings_ms.total} ms total`
          : "OK";
      setStatus(statusLine, t, "info");
      question.value = "";
      await refreshView(apiInput.value.trim());
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
      await refreshView(apiInput.value.trim());
    } finally {
      btnSend.disabled = false;
    }
  });

  refreshView(apiInput.value.trim());
}

document.addEventListener("DOMContentLoaded", () => {
  wire().catch((err) => {
    console.error(err);
    try {
      $("apiBaseUrl").value = fallbackApiBase();
    } catch {
      /* ignore */
    }
  });
});
