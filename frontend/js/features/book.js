/**
 * Book, encyclopedia, and external-link helpers.
 *
 * Detailed note:
 * - This file collects the iframe-based viewer behavior that used to live in
 *   the big main bootstrap file.
 * - Keeping the book/encyclopedia logic together makes the hierarchy easier to
 *   reason about: book -> encyclopedia -> external link.
 *
 * Simple note:
 * - Book-related modal logic lives here.
 */

import { bookDocumentUrl, encyclopediaEntryUrl } from "../api/api.js";
import { setStatus } from "../ui/render.js";
import { trimBaseUrl } from "../core/dom.js";
import { isAcceptableApiBase } from "../core/api_base.js";

const WIKIPEDIA_LOGO = `<img src="assets/images/wikipedia.png" alt="Wikipedia" class="modal-title-logo" />`;
const WIKIDATA_LOGO = `<img src="assets/images/wikidata.svg" alt="Wikidata" class="modal-title-logo" />`;

export { WIKIPEDIA_LOGO, WIKIDATA_LOGO };

/**
 * Jump the embedded book iframe to a source anchor or section.
 * @param {object | null | undefined} source
 * @param {string} targetOrigin
 */
export function jumpBookToSource(source, targetOrigin) {
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
 * Load or clear the book iframe based on the current API base.
 * @param {string} apiBase
 * @param {HTMLElement} statusLine
 */
export async function syncBookPanel(apiBase, statusLine) {
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
 * Load or clear the encyclopedia modal iframe.
 * Passing null removes the iframe src so the modal opens cleanly next time.
 * @param {string} apiBase
 * @param {string | null} entryId
 */
export function syncEncyclopediaPanel(apiBase, entryId) {
  const iframe = document.getElementById("encyclopediaFrame");
  if (!iframe) return;

  if (!apiBase || !isAcceptableApiBase(apiBase)) {
    iframe.removeAttribute("src");
    return;
  }

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
 * Open the encyclopedia modal with a single entry loaded.
 * @param {string} apiBase
 * @param {string} entryId
 */
export function openEncyclopediaEntry(apiBase, entryId) {
  const id = String(entryId || "").trim();
  if (!id || !apiBase || !isAcceptableApiBase(apiBase)) return;

  syncEncyclopediaPanel(apiBase, id);

  const overlay = document.getElementById("encyclopediaOverlay");
  const dialog = document.getElementById("encyclopediaModal");
  if (overlay && dialog) {
    overlay.classList.add("help-visible");
    dialog.classList.add("help-visible");
    dialog.focus();
  }
}

/**
 * Open the external Wikipedia/Wikidata modal and preserve hierarchy state.
 * @param {string} apiBase
 * @param {string} url
 * @param {string} source
 */
export function openExternalLinkModal(apiBase, url, source) {
  const overlay = document.getElementById("externalOverlay");
  const dialog = document.getElementById("externalModal");
  const titleEl = document.getElementById("externalModalTitle");
  const iframe = document.getElementById("externalFrame");
  if (!overlay || !dialog || !titleEl || !iframe) return;

  // If the encyclopedia is already open, temporarily hide it and remember that
  // the external modal came from there. The Back button restores the hierarchy.
  const encOverlay = document.getElementById("encyclopediaOverlay");
  const encDialog = document.getElementById("encyclopediaModal");
  if (encDialog && encDialog.classList.contains("help-visible")) {
    dialog.dataset.fromEncyclopedia = "1";
    if (encOverlay) encOverlay.classList.remove("help-visible");
    encDialog.classList.remove("help-visible");
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

/**
 * Route the book iframe's preview tooltip message to the on-page tooltip.
 * The actual tooltip display logic is isolated in tooltip.js.
 * @param {string} text
 * @param {number} x
 * @param {number} y
 * @param {boolean} visible
 */
export function showTermPreviewTooltip(text, x, y, visible) {
  const tip = document.getElementById("appTooltip");
  if (!tip) return;

  if (!visible || !text) {
    tip.classList.remove("app-tooltip-visible");
    return;
  }

  const bookFrame = document.getElementById("bookFrame");
  const frameRect = bookFrame ? bookFrame.getBoundingClientRect() : { left: 0, top: 0 };

  const vx = frameRect.left + x;
  const vy = frameRect.top + y;

  tip.textContent = text;

  // Small offset so the tooltip does not sit directly on top of the hover point.
  const GAP = 12;
  tip.style.left = `${vx + GAP}px`;
  tip.style.top = `${vy - GAP}px`;
  tip.classList.add("app-tooltip-visible");

  requestAnimationFrame(() => {
    const tw = tip.offsetWidth;
    if (vx + GAP + tw > window.innerWidth - 16) {
      tip.style.left = `${vx - tw - GAP}px`;
    }

    const th = tip.offsetHeight;
    if (vy - GAP - th < 8) {
      tip.style.top = `${vy + GAP + 16}px`;
    } else {
      tip.style.top = `${vy - th - GAP}px`;
    }
  });
}

