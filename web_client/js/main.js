/**
 * Wiring: settings persistence, composer, API calls, render loop.
 */

import { postAsk, getHealth, getReady } from "./api.js";
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

async function refreshView() {
  const thread = $("thread");
  const sourcesDetail = $("sourcesDetail");
  renderThread(thread, getConversation(), (sourceId, sources) => {
    const src = sources.find((s) => s.source_id === sourceId);
    renderSourceDetail(sourcesDetail, src || null);
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

  apiInput.value = await resolveInitialApiBase(statusLine);

  apiInput.addEventListener("change", () => {
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
  });

  btnClear.addEventListener("click", () => {
    clearConversation();
    setStatus(statusLine, "Chat cleared.");
    refreshView();
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
      await refreshView();
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
      await refreshView();
    } finally {
      btnSend.disabled = false;
    }
  });

  refreshView();
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
