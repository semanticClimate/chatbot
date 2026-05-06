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

function $(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
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

function wire() {
  const apiInput = $("apiBaseUrl");
  const statusLine = $("statusLine");
  const composer = $("composer");
  const question = $("question");
  const btnSend = $("btnSend");
  const btnHealth = $("btnHealth");
  const btnClear = $("btnClear");

  apiInput.value = loadApiBase() || "http://127.0.0.1:8800";
  apiInput.addEventListener("change", () => saveApiBase(apiInput.value));

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

document.addEventListener("DOMContentLoaded", wire);
