/**
 * Wiring: settings persistence, composer, API calls, render loop.
 */

import {
  postAsk,
  getHealth,
  getReady,
  bookDocumentUrl,
  encyclopediaEmptyUrl,
  encyclopediaEntryUrl,
  exportConversationCsv,
  fetchLogsCsvBlob,
} from "./api.js";
import {
  getConversation,
  clearConversation,
  applyConversationFull,
} from "./state.js";
import { renderThread, renderSourceDetail, setStatus } from "./render.js";
import { mountExampleQuestions } from "./examples.js";
import {
  CHAT_LANGUAGES,
  loadChatLanguage,
  normalizeChatLangId,
  saveChatLanguage,
} from "./lang_prefs.js";
import { applyShellUiStrings, t } from "./ui_strings.js";

const STORAGE_KEY_API = "climate_web_client_api_base";

/** Empty default: quick-tunnel run fills web_client/tunnel-api-base.txt (trycloudflare API URL). */
const DEFAULT_API_BASE = "";

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

/** Prefer empty API base on remote tunnel pages; same-machine dev may use loopback. */
function fallbackApiBase() {
  if (isRemoteWebOrigin()) return "";
  return DEFAULT_API_BASE || "http://127.0.0.1:8800";
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
 * @param {string} apiBase
 * @param {HTMLElement} statusLine
 */
async function syncBookPanel(apiBase, statusLine) {
  const iframe = document.getElementById("bookFrame");
  if (!iframe) return;

  if (!apiBase || !isAcceptableApiBase(apiBase)) {
    iframe.removeAttribute("src");
    syncEncyclopediaPanel(apiBase, null);
    return;
  }

  try {
    iframe.src = bookDocumentUrl(apiBase);
    syncEncyclopediaPanel(apiBase, null);
  } catch (e) {
    iframe.removeAttribute("src");
    syncEncyclopediaPanel(apiBase, null);
    setStatus(statusLine, String(e.message || e), "error");
  }
}

/**
 * @param {string} apiBase
 * @param {string | null} entryId
 */
function syncEncyclopediaPanel(apiBase, entryId) {
  const iframe = document.getElementById("encyclopediaFrame");
  if (!iframe) return;
  if (!apiBase || !isAcceptableApiBase(apiBase)) {
    iframe.removeAttribute("src");
    return;
  }
  try {
    iframe.src = entryId
      ? encyclopediaEntryUrl(apiBase, entryId)
      : encyclopediaEmptyUrl(apiBase);
  } catch {
    iframe.removeAttribute("src");
  }
}

/**
 * @param {string} apiBase
 * @param {string} entryId
 */
function openEncyclopediaEntry(apiBase, entryId) {
  const id = String(entryId || "").trim();
  if (!id || !apiBase || !isAcceptableApiBase(apiBase)) return;
  syncEncyclopediaPanel(apiBase, id);
  const iframe = document.getElementById("encyclopediaFrame");
  iframe?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
    const parts = [t("errApiBaseInvalidSaved")];
    if (!v && isRemoteWebOrigin()) {
      parts.push(t("errTunnelNotFound"));
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
    setStatus(statusLine, t("errTunnelBaseNotFound"), "error");
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

function fitSelectToLongestOption(sel) {
  if (!(sel instanceof HTMLSelectElement)) return;
  const probe = document.createElement("span");
  probe.style.cssText =
    "position:absolute;visibility:hidden;white-space:nowrap;pointer-events:none;";
  const font = getComputedStyle(sel).font;
  probe.style.font = font;
  document.body.appendChild(probe);
  let max = 0;
  for (const opt of sel.options) {
    probe.textContent = opt.textContent || "";
    max = Math.max(max, probe.offsetWidth);
  }
  probe.remove();
  sel.style.width = `${Math.ceil(max) + 26}px`;
}

function wireChatLanguageSelect() {
  const sel = document.getElementById("chatLangSelect");
  if (!sel || !(sel instanceof HTMLSelectElement)) return null;
  sel.replaceChildren();
  const initial = loadChatLanguage();
  for (const { id, label } of CHAT_LANGUAGES) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = label;
    if (id === initial) opt.selected = true;
    sel.appendChild(opt);
  }
  fitSelectToLongestOption(sel);
  return sel;
}

async function wire() {
  const langSelect = wireChatLanguageSelect();
  applyShellUiStrings(
    langSelect ? normalizeChatLangId(langSelect.value) : loadChatLanguage()
  );
  if (langSelect) fitSelectToLongestOption(langSelect);

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

  const examplesHost = document.getElementById("examplesMount");
  /** @type {{ refill: () => void } | null} */
  let exampleControls = null;
  if (examplesHost) {
    exampleControls = mountExampleQuestions(examplesHost, {
      setQuestion: (q) => {
        question.value = q;
        question.focus();
      },
    });
  }
  if (langSelect) {
    langSelect.addEventListener("change", () => {
      const lid = normalizeChatLangId(langSelect.value);
      saveChatLanguage(lid);
      applyShellUiStrings(lid);
      fitSelectToLongestOption(langSelect);
      exampleControls?.refill();
      refreshView(apiInput.value.trim());
    });
  }

  apiInput.addEventListener("change", async () => {
    const v = apiInput.value.trim();
    if (v && !isAcceptableApiBase(v)) {
      setStatus(statusLine, t("errUseFullUrl"), "error");
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
      syncEncyclopediaPanel(base, null);
    });
  }

  window.addEventListener("message", (ev) => {
    const base = apiInput.value.trim();
    const origin = apiOriginFromBase(base);
    if (!origin || ev.origin !== origin) return;
    if (ev.data?.type === "ca-encyclopedia-open" && ev.data.entry_id) {
      openEncyclopediaEntry(base, ev.data.entry_id);
    }
  });

  btnClear.addEventListener("click", () => {
    clearConversation();
    setStatus(statusLine, t("chatCleared"));
    refreshView(apiInput.value.trim());
  });

  btnExportChat.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base || !isAcceptableApiBase(base)) {
      setStatus(statusLine, t("errSetApiFirst"), "error");
      return;
    }
    const conv = getConversation();
    if (!conv.length) {
      setStatus(statusLine, t("nothingToExport"), "error");
      return;
    }
    setStatus(statusLine, t("preparingCsv"));
    try {
      const blob = await exportConversationCsv(base, conv);
      triggerBrowserDownload(blob, "conversation.csv");
      setStatus(statusLine, t("savedConversationCsv"), "info");
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
    }
  });

  btnExportLogs.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base || !isAcceptableApiBase(base)) {
      setStatus(statusLine, t("errSetApiFirst"), "error");
      return;
    }
    setStatus(statusLine, t("fetchingLogs"));
    try {
      const blob = await fetchLogsCsvBlob(base);
      triggerBrowserDownload(blob, "chatbot_logs.csv");
      setStatus(statusLine, t("savedLogsCsv"), "info");
    } catch (e) {
      setStatus(statusLine, String(e.message || e), "error");
    }
  });

  btnHealth.addEventListener("click", async () => {
    const base = apiInput.value.trim();
    if (!base) {
      setStatus(statusLine, t("errSetApiFirst"), "error");
      return;
    }
    setStatus(statusLine, t("checkingHealth"));
    try {
      const h = await getHealth(base);
      const r = await getReady(base);
      setStatus(
        statusLine,
        `${t("labelHealth")}: ${JSON.stringify(h)} | ${t("labelReady")}: ${JSON.stringify(r)}`,
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
    setStatus(statusLine, t("sending"));

    const abort = new AbortController();
    /** Optimistic user bubble — we render user + prior; API will reconcile */
    try {
      const tempConv = prior.slice();
      tempConv.push({ role: "user", content: q });
      renderThread($("thread"), tempConv, () => {});
      scrollThreadToBottom();

      const lang = langSelect
        ? normalizeChatLangId(langSelect.value)
        : loadChatLanguage();
      const data = await postAsk(base, q, prior, {
        signal: abort.signal,
        response_language: lang,
      });
      applyConversationFull(data.conversation_full);
      const statusText =
        data.timings_ms && data.timings_ms.total != null
          ? t("okMs", { ms: data.timings_ms.total })
          : t("ok");
      setStatus(statusLine, statusText, "info");
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
