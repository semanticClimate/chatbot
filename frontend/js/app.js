/**
 * Frontend bootstrap.
 *
 * Detailed note:
 * - This file stays intentionally small.
 * - It keeps the page wiring in one place while the real behavior lives in
 *   feature modules (book, tooltip, chat, sidebar, API base resolution).
 *
 * Simple note:
 * - Main bootstrap wires the pieces together.
 */

import { t, applyShellUiStrings } from "./ui/ui_strings.js";
import { normalizeChatLangId, loadChatLanguage } from "./ui/lang_prefs.js";
import { mountExampleQuestions } from "./examples/examples.js";
import { setStatus } from "./ui/render.js";
import { resolveInitialApiBase, isAcceptableApiBase, saveApiBase } from "./core/api_base.js";
import { $, apiOriginFromBase } from "./core/dom.js";
import { syncBookPanel, openEncyclopediaEntry, openExternalLinkModal } from "./features/book.js";
import { showTermPreviewTooltip } from "./features/tooltip.js";
import { initSidebarToggle } from "./features/sidebar.js";
import {
  wireChatLanguageSelect,
  wireLanguageChange,
  refreshView,
  clearChat,
  handleExportChat,
  handleExportLogs,
  handleHealthCheck,
  handleSubmitQuestion,
  fitSelectToLongestOption,
} from "./features/chat.js";

/**
 * Boot the client after the DOM is ready.
 * This is the only place where the different feature modules are connected.
 */
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
  const thread = $("thread");

  apiInput.value = await resolveInitialApiBase(statusLine);
  await syncBookPanel(apiInput.value.trim(), statusLine);

  const examplesHost = document.getElementById("examplesMount");
  let exampleControls = null;
  if (examplesHost) {
    exampleControls = mountExampleQuestions(examplesHost, {
      setQuestion: (q) => {
        question.value = q;
        question.focus();
      },
    });
  }

  // Keep language state, labels, and example chips aligned with one change handler.
  wireLanguageChange(
    langSelect,
    (lid) => applyShellUiStrings(lid),
    () => exampleControls?.refill()
  );
  if (langSelect) {
    langSelect.addEventListener("change", () => {
      fitSelectToLongestOption(langSelect);
      refreshView(thread, apiInput.value.trim());
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
      syncBookPanel(base, statusLine);
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
    clearChat(thread, statusLine, apiInput.value.trim());
  });

  btnExportChat.addEventListener("click", async () => {
    await handleExportChat(apiInput.value.trim(), statusLine);
  });

  btnExportLogs.addEventListener("click", async () => {
    await handleExportLogs(apiInput.value.trim(), statusLine);
  });

  btnHealth.addEventListener("click", async () => {
    const healthStatusLine = document.getElementById("healthStatusLine");
    const targetStatusEl = healthStatusLine || statusLine;
    await handleHealthCheck(apiInput.value.trim(), targetStatusEl);
  });

  composer.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    await handleSubmitQuestion(
      apiInput.value.trim(),
      question.value.trim(),
      langSelect,
      thread,
      btnSend,
      question
    );
  });

  refreshView(thread, apiInput.value.trim());

  // Sidebar remains separate from chat rendering and API wiring.
  initSidebarToggle();
}

document.addEventListener("DOMContentLoaded", () => {
  wire().catch((err) => {
    console.error(err);
    try {
      $("apiBaseUrl").value = "";
    } catch {
      /* ignore */
    }
  });
});
