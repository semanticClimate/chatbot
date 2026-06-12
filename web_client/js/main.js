/**
 * Wiring: settings persistence, composer, API calls, render loop.
 */

import {
  postAsk,
  getHealth,
  getReady,
  bookDocumentUrl,
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

/** COMMENTED OUT: Store the current sources for display in the modal */
// let currentSources = [];

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
 * @param {string | null} entryId  — if null, resets (closes) modal frame src
 */
function syncEncyclopediaPanel(apiBase, entryId) {
  const iframe = document.getElementById("encyclopediaFrame");
  if (!iframe) return;
  if (!apiBase || !isAcceptableApiBase(apiBase)) {
    iframe.removeAttribute("src");
    return;
  }
  // When resetting (entryId null), clear the modal iframe so it doesn't linger
  if (!entryId) {
    iframe.removeAttribute("src");
    return;
  }
  try {
    iframe.src = encyclopediaEntryUrl(apiBase, entryId);
  } catch {
    iframe.removeAttribute("src");
  }
}

/**
 * Opens the Encyclopedia modal overlay with the given entry.
 * @param {string} apiBase
 * @param {string} entryId
 */
function openEncyclopediaEntry(apiBase, entryId) {
  const id = String(entryId || "").trim();
  if (!id || !apiBase || !isAcceptableApiBase(apiBase)) return;

  // Load the entry into the modal iframe
  syncEncyclopediaPanel(apiBase, id);

  // Open the modal
  const overlay = document.getElementById("encyclopediaOverlay");
  const dialog = document.getElementById("encyclopediaModal");
  if (overlay && dialog) {
    overlay.classList.add("help-visible");
    dialog.classList.add("help-visible");
    dialog.focus();
  }
}

/**
 * Show/hide the global term-preview tooltip.
 * Coordinates come from the book iframe's postMessage and are in viewport space.
 * @param {string} text   — preview text to show
 * @param {number} x      — viewport X (px) from left of book iframe rect
 * @param {number} y      — viewport Y (px) from top  of book iframe rect
 * @param {boolean} visible
 */
function showTermPreviewTooltip(text, x, y, visible) {
  const tip = document.getElementById("appTooltip");
  if (!tip) return;
  if (!visible || !text) {
    tip.classList.remove("app-tooltip-visible");
    return;
  }
  const bookFrame = document.getElementById("bookFrame");
  const frameRect = bookFrame ? bookFrame.getBoundingClientRect() : { left: 0, top: 0 };

  // Position the tooltip relative to the viewport, offset slightly from cursor
  const vx = frameRect.left + x;
  const vy = frameRect.top + y;

  tip.textContent = text;
  // Place above the hovered term; shift right a little
  const GAP = 12;
  tip.style.left = `${vx + GAP}px`;
  tip.style.top = `${vy - GAP}px`;
  tip.classList.add("app-tooltip-visible");

  // Auto-position: if the tip would overflow right, flip left
  requestAnimationFrame(() => {
    const tw = tip.offsetWidth;
    if (vx + GAP + tw > window.innerWidth - 16) {
      tip.style.left = `${vx - tw - GAP}px`;
    }
    // If it would overflow top, show below instead
    const th = tip.offsetHeight;
    if (vy - GAP - th < 8) {
      tip.style.top = `${vy + GAP + 16}px`;
    } else {
      tip.style.top = `${vy - th - GAP}px`;
    }
  });
}

const WIKIPEDIA_LOGO = `<img src="images/wikipedia.png" alt="Wikipedia" class="modal-title-logo" />`;

const WIKIDATA_LOGO = `<img src="images/wikidata.svg" alt="Wikidata" class="modal-title-logo" />`;

function openExternalLinkModal(apiBase, url, source) {
  const overlay = document.getElementById("externalOverlay");
  const dialog = document.getElementById("externalModal");
  const titleEl = document.getElementById("externalModalTitle");
  const iframe = document.getElementById("externalFrame");
  if (!overlay || !dialog || !titleEl || !iframe) return;

  // ── Hierarchical navigation: if encyclopedia is open, hide it (don't unload)
  // and stamp a flag so the Back button can restore it without reloading.
  const encOverlay = document.getElementById("encyclopediaOverlay");
  const encDialog = document.getElementById("encyclopediaModal");
  if (encDialog && encDialog.classList.contains("help-visible")) {
    dialog.dataset.fromEncyclopedia = "1";
    if (encOverlay) encOverlay.classList.remove("help-visible");
    encDialog.classList.remove("help-visible");
    // Intentionally NOT clearing encyclopediaFrame src — preserve for instant restore
  } else {
    delete dialog.dataset.fromEncyclopedia;
  }

  if (source === "Wikipedia") {
    titleEl.innerHTML = `${WIKIPEDIA_LOGO} Wikipedia Article`;
  } else {
    titleEl.innerHTML = `${WIKIDATA_LOGO} Wikidata Entry`;
  }

  const proxyUrl = `${trimBaseUrl(apiBase)}/proxy?url=${encodeURIComponent(url)}`;
  iframe.src = proxyUrl;

  overlay.classList.add("help-visible");
  dialog.classList.add("help-visible");
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
  const origin = apiOriginFromBase(apiBase);
  renderThread(thread, getConversation(), (sourceId, sources) => {
    const src = sources.find((s) => s.source_id === sourceId);
    const sourcesDetailEl = document.getElementById("sourcesDetail");
    if (sourcesDetailEl && src) {
      renderSourceDetail(sourcesDetailEl, src);
    }
    jumpBookToSource(src, origin);
  });
  scrollThreadToBottom();
}

// COMMENTED OUT: Show source in external modal
/*
function showSourceInModal(source) {
  const extOverlay = document.getElementById("externalOverlay");
  const extDialog = document.getElementById("externalModal");
  const extModalTitle = document.getElementById("externalModalTitle");

  if (!extOverlay || !extDialog) return;

  // Render source detail as HTML
  let html = "";
  if (source) {
    const escapeHtml = (s) => {
      const d = document.createElement("div");
      d.textContent = String(s || "");
      return d.innerHTML;
    };
    const formatLines = (text) =>
      escapeHtml(String(text || "")).replace(/\n/g, "<br />");

    const rows = [];
    const addRow = (label, value) => {
      if (value == null || value === "") return;
      const labelEsc = escapeHtml(label);
      const valueEsc = formatLines(String(value));
      rows.push(`<dt>${labelEsc}</dt><dd>${valueEsc}</dd>`);
    };

    addRow(t("labelSourceId"), source.source_id);
    addRow(
      t("labelSection"),
      source.section_number
        ? `§ ${source.section_number} — ${source.section_title || ""}`
        : ""
    );
    addRow(t("labelChunk"), source.chunk_id);
    addRow(t("labelAnchor"), source.anchor_id);
    addRow(t("labelPassage"), source.document);

    if (rows.length > 0) {
      html = `<dl class="source-dl">${rows.join("")}</dl>`;
    }
  }

  if (!html) {
    html = `<p class="sources-empty">${t("sourcesEmpty")}</p>`;
  }

  // Update modal title and content
  if (extModalTitle) {
    extModalTitle.textContent = t("sourcesHeading");
  }

  // Set the content directly in the modal body
  const extModalBody = document.querySelector(".external-modal-body");
  if (extModalBody) {
    extModalBody.innerHTML = html;
  }

  // Open the modal
  extOverlay.classList.add("help-visible");
  extDialog.classList.add("help-visible");
}
*/

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
    if (ev.data?.type === "ca-external-link-open" && ev.data.url) {
      openExternalLinkModal(base, ev.data.url, ev.data.source || "Wikipedia");
    }
    if (ev.data?.type === "ca-encyclopedia-preview") {
      showTermPreviewTooltip(
        ev.data.text || "",
        ev.data.x ?? 0,
        ev.data.y ?? 0,
        ev.data.visible ?? false
      );
    }
  });

  btnClear.addEventListener("click", () => {
    clearConversation();
    setStatus(statusLine, t("chatCleared"));
    const sourcesDetailEl = document.getElementById("sourcesDetail");
    if (sourcesDetailEl) {
      renderSourceDetail(sourcesDetailEl, null);
    }
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
    const healthStatusLine = document.getElementById("healthStatusLine");
    const targetStatusEl = healthStatusLine || statusLine;
    if (!base) {
      setStatus(targetStatusEl, t("errSetApiFirst"), "error");
      return;
    }
    setStatus(targetStatusEl, t("checkingHealth"));
    try {
      const h = await getHealth(base);
      const r = await getReady(base);
      setStatus(
        targetStatusEl,
        `${t("labelHealth")}: ${JSON.stringify(h)} | ${t("labelReady")}: ${JSON.stringify(r)}`,
        "info"
      );
    } catch (e) {
      setStatus(targetStatusEl, String(e.message || e), "error");
    }
  });

  composer.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const base = apiInput.value.trim();
    const q = question.value.trim();
    if (!base || !q) return;

    const prior = getConversation();
    btnSend.disabled = true;
    // Commented out status updates for the input-area debug/status panel.
    // setStatus(statusLine, t("sending"));

    const abort = new AbortController();
    /** Optimistic user bubble — we render user + prior; API will reconcile */
    try {
      const tempConv = prior.slice();
      tempConv.push({ role: "user", content: q });
      tempConv.push({ role: "assistant", content: "Thinking...", isThinking: true });
      renderThread($("thread"), tempConv, () => { });
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
      // setStatus(statusLine, statusText, "info");
      question.value = "";
      await refreshView(apiInput.value.trim());
    } catch (e) {
      // setStatus(statusLine, String(e.message || e), "error");
      await refreshView(apiInput.value.trim());
    } finally {
      btnSend.disabled = false;
    }
  });

  refreshView(apiInput.value.trim());

  // COMMENTED OUT: Handle Sources button click
  /*
  const btnSourcesView = document.getElementById("btnSourcesView");
  if (btnSourcesView) {
    btnSourcesView.addEventListener("click", () => {
      const extOverlay = document.getElementById("externalOverlay");
      const extDialog = document.getElementById("externalModal");
      const extModalBody = document.querySelector(".external-modal-body");
      const extModalTitle = document.getElementById("externalModalTitle");

      if (!extOverlay || !extDialog) return;

      if (extModalTitle) {
        extModalTitle.textContent = t("sourcesHeading");
      }

      // If no sources, show empty state
      if (currentSources.length === 0) {
        if (extModalBody) {
          extModalBody.innerHTML = `<p class="sources-empty">${t("sourcesEmpty")}</p>`;
        }
      } else {
        // Show all sources
        let html = `<div class="sources-list">`;
        for (const src of currentSources) {
          const escapeHtml = (s) => {
            const d = document.createElement("div");
            d.textContent = String(s || "");
            return d.innerHTML;
          };
          const formatLines = (text) =>
            escapeHtml(String(text || "")).replace(/\n/g, "<br />");

          html += `<div class="source-item">`;
          if (src.source_id) {
            html += `<dt>${escapeHtml(t("labelSourceId"))}</dt><dd>${escapeHtml(src.source_id)}</dd>`;
          }
          if (src.section_number) {
            const section = `§ ${src.section_number}${src.section_title ? ` — ${src.section_title}` : ""}`;
            html += `<dt>${escapeHtml(t("labelSection"))}</dt><dd>${escapeHtml(section)}</dd>`;
          }
          if (src.chunk_id) {
            html += `<dt>${escapeHtml(t("labelChunk"))}</dt><dd>${escapeHtml(src.chunk_id)}</dd>`;
          }
          if (src.anchor_id) {
            html += `<dt>${escapeHtml(t("labelAnchor"))}</dt><dd>${escapeHtml(src.anchor_id)}</dd>`;
          }
          if (src.document) {
            html += `<dt>${escapeHtml(t("labelPassage"))}</dt><dd>${formatLines(src.document)}</dd>`;
          }
          html += `</div>`;
        }
        html += `</div>`;

        if (extModalBody) {
          extModalBody.innerHTML = html;
        }
      }

      // Open the modal
      extOverlay.classList.add("help-visible");
      extDialog.classList.add("help-visible");
    });
  }
  */
}

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('btnSidebarToggle');
  if (sidebar && toggle) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('expanded');
      sidebar.classList.toggle('collapsed');
    });
  }
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar && overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('collapsed');
      sidebar.classList.add('expanded');
    });
  }
  wire().catch((err) => {
    console.error(err);
    try {
      $("apiBaseUrl").value = fallbackApiBase();
    } catch {
      /* ignore */
    }
  });
});