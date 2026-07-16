/**
 * Chat interaction helpers.
 *
 * Detailed note:
 * - This file gathers the UI actions that belong to the chat workspace:
 *   language selection, view refresh, export, health checks, and message submit.
 * - Keeping these workflows here reduces the size of main.js without changing
 *   the underlying behavior.
 *
 * Simple note:
 * - Chat actions live here.
 */

import {
  postAsk,
  getHealth,
  getReady,
  exportConversationCsv,
  fetchLogsCsvBlob,
} from "../api/api.js";
import {
  getConversation,
  clearConversation,
  applyConversationFull,
} from "../state/state.js";
import { renderThread, renderSourceDetail, setStatus } from "../ui/render.js";
import {
  CHAT_LANGUAGES,
  loadChatLanguage,
  normalizeChatLangId,
  saveChatLanguage,
} from "../ui/lang_prefs.js";
import { t } from "../ui/ui_strings.js";
import { apiOriginFromBase, triggerBrowserDownload } from "../core/dom.js";
import { jumpBookToSource } from "./book.js"; // /features

/**
 * Size a <select> to fit the longest visible option text.
 * This keeps the language picker compact while still readable.
 * @param {HTMLSelectElement} sel
 */
export function fitSelectToLongestOption(sel) {
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

/**
 * Create the language select options and restore the saved language.
 * @returns {HTMLSelectElement | null}
 */
export function wireChatLanguageSelect() {
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

/**
 * Scroll the thread to the bottom so the latest turn is visible.
 * @param {HTMLElement} thread
 */
export function scrollThreadToBottom(thread) {
  thread.scrollTop = thread.scrollHeight;
}

/**
 * Refresh the main thread and source panel from the current conversation state.
 * @param {HTMLElement} thread
 * @param {string} apiBase
 */
export function refreshView(thread, apiBase) {
  const origin = apiOriginFromBase(apiBase);

  renderThread(thread, getConversation(), (sourceId, sources) => {
    const src = sources.find((s) => s.source_id === sourceId);
    const sourcesDetailEl = document.getElementById("sourcesDetail");
    if (sourcesDetailEl && src) {
      renderSourceDetail(sourcesDetailEl, src);
    }
    jumpBookToSource(src, origin);
  });

  scrollThreadToBottom(thread);
}

/**
 * Clear the conversation and reset the visible thread/source panel.
 * @param {HTMLElement} thread
 * @param {HTMLElement} statusLine
 * @param {string} apiBase
 */
export function clearChat(thread, statusLine, apiBase) {
  clearConversation();
  setStatus(statusLine, t("chatCleared"));

  const sourcesDetailEl = document.getElementById("sourcesDetail");
  if (sourcesDetailEl) {
    renderSourceDetail(sourcesDetailEl, null);
  }

  refreshView(thread, apiBase);
}

/**
 * Check backend health and readiness.
 * @param {string} base
 * @param {HTMLElement} targetStatusEl
 */
export async function handleHealthCheck(base, targetStatusEl) {
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
}

/**
 * Export the current conversation as CSV.
 * @param {string} base
 * @param {HTMLElement} statusLine
 */
export async function handleExportChat(base, statusLine) {
  if (!base) {
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
}

/**
 * Export backend logs as CSV.
 * @param {string} base
 * @param {HTMLElement} statusLine
 */
export async function handleExportLogs(base, statusLine) {
  if (!base) {
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
}

/**
 * Submit a question using the current chat language and conversation state.
 * This keeps the optimistic render + reconciliation flow in one place.
 *
 * @param {string} base
 * @param {string} question
 * @param {HTMLSelectElement | null} langSelect
 * @param {HTMLElement} thread
 * @param {HTMLButtonElement} sendButton
 * @param {HTMLInputElement | HTMLTextAreaElement | null} questionInput
 */
export async function handleSubmitQuestion(base, question, langSelect, thread, sendButton, questionInput = null) {
  const q = String(question || "").trim();
  if (!base || !q) return;

  const prior = getConversation();
  sendButton.disabled = true;

  try {
    // Render the user's message immediately so the UI feels responsive.
    const tempConv = prior.slice();
    tempConv.push({ role: "user", content: q });
    tempConv.push({ role: "assistant", content: "Thinking", isThinking: true });
    renderThread(thread, tempConv, () => {});
    scrollThreadToBottom(thread);

    const lang = langSelect
      ? normalizeChatLangId(langSelect.value)
      : loadChatLanguage();

    const data = await postAsk(base, q, prior, {
      response_language: lang,
    });

    applyConversationFull(data.conversation_full);

    // The original UI intentionally kept submit status feedback muted.
    // We keep that behavior here so the refactor does not change the UX.
    if (questionInput) {
      questionInput.value = "";
    }
  } catch (e) {
    // Preserve the original quiet failure behavior for submit errors.
  } finally {
    sendButton.disabled = false;
    refreshView(thread, base);
  }
}

/**
 * Persist the chosen chat language and update the visible UI strings.
 * @param {HTMLSelectElement | null} sel
 * @param {(langId: string) => void} applyShellUiStrings
 * @param {() => void | undefined} refillExamples
 */
export function wireLanguageChange(sel, applyShellUiStrings, refillExamples) {
  if (!sel) return;
  sel.addEventListener("change", () => {
    const lid = normalizeChatLangId(sel.value);
    saveChatLanguage(lid);
    applyShellUiStrings(lid);
    fitSelectToLongestOption(sel);
    if (refillExamples) refillExamples();
  });
}
