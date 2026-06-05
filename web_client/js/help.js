/**
 * Help Tool — Standalone module for the help modal.
 *
 * This module is loaded as a separate <script type="module"> and does NOT
 * export anything consumed by main.js or any other existing module.
 * If this module fails to load or errors during init, the chatbot continues
 * to function normally — there simply won't be a help button visible.
 *
 * Safety:
 *   - All DOM lookups use null guards (no throwing $ helper).
 *   - Entire init is wrapped in try/catch.
 *   - Only reads t() from ui_strings.js (no side-effects on other modules).
 */

import { t } from "./ui_strings.js";

/* ------------------------------------------------------------------ */
/*  Lightweight Markdown → HTML converter (no external dependencies)  */
/* ------------------------------------------------------------------ */

/**
 * Convert a subset of Markdown to HTML.
 * Supports: headings (h1–h3), bold, inline code, code blocks,
 * unordered/ordered lists, horizontal rules, paragraphs.
 * @param {string} md
 * @returns {string}
 */
function markdownToHtml(md) {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let inUl = false;
  let inOl = false;
  let inCode = false;
  let codeBuf = [];

  function closeList() {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  }

  function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /** Apply inline formatting: bold, inline code */
  function inlineFmt(s) {
    // inline code first (so bold inside code is not processed)
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    // bold: **text** or __text__
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__(.+?)__/g, "<strong>$1</strong>");
    return s;
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];

    // Fenced code blocks
    if (raw.trimStart().startsWith("```")) {
      if (inCode) {
        out.push(escHtml(codeBuf.join("\n")));
        out.push("</code></pre>");
        codeBuf = [];
        inCode = false;
      } else {
        closeList();
        inCode = true;
        out.push("<pre><code>");
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(raw);
      continue;
    }

    const trimmed = raw.trim();

    // Blank line closes list
    if (!trimmed) {
      closeList();
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      closeList();
      out.push("<hr>");
      continue;
    }

    // Headings
    const hMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
    if (hMatch) {
      closeList();
      const level = hMatch[1].length;
      out.push(`<h${level}>${inlineFmt(escHtml(hMatch[2]))}</h${level}>`);
      continue;
    }

    // Unordered list item
    const ulMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (ulMatch) {
      if (inOl) { out.push("</ol>"); inOl = false; }
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li>${inlineFmt(escHtml(ulMatch[1]))}</li>`);
      continue;
    }

    // Ordered list item
    const olMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (olMatch) {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (!inOl) { out.push("<ol>"); inOl = true; }
      out.push(`<li>${inlineFmt(escHtml(olMatch[1]))}</li>`);
      continue;
    }

    // Default: paragraph
    closeList();
    out.push(`<p>${inlineFmt(escHtml(trimmed))}</p>`);
  }

  // Close any dangling state
  closeList();
  if (inCode) {
    out.push(escHtml(codeBuf.join("\n")));
    out.push("</code></pre>");
  }

  return out.join("\n");
}

/* ------------------------------------------------------------------ */
/*  DOM creation helpers                                              */
/* ------------------------------------------------------------------ */

/**
 * Create an element with optional class and attributes.
 * @param {string} tag
 * @param {string} [className]
 * @param {Record<string,string>} [attrs]
 * @returns {HTMLElement}
 */
function el(tag, className, attrs) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  }
  return e;
}

/* ------------------------------------------------------------------ */
/*  Module state                                                      */
/* ------------------------------------------------------------------ */

/** @type {string|null} Cached rendered HTML from the markdown file */
let cachedHtml = null;

/** @type {HTMLElement|null} */
let overlayEl = null;
/** @type {HTMLElement|null} */
let modalEl = null;
/** @type {HTMLElement|null} */
let bodyEl = null;

/* ------------------------------------------------------------------ */
/*  Open / close logic                                                */
/* ------------------------------------------------------------------ */

function openHelp() {
  if (!overlayEl || !modalEl) return;

  // Show overlay and modal
  overlayEl.classList.add("help-visible");
  modalEl.classList.add("help-visible");

  // Load content on first open (or if cache was cleared)
  if (!cachedHtml) {
    loadHelpContent();
  }
}

function closeHelp() {
  if (!overlayEl || !modalEl) return;
  overlayEl.classList.remove("help-visible");
  modalEl.classList.remove("help-visible");
}

function isHelpOpen() {
  return modalEl?.classList.contains("help-visible") ?? false;
}

/* ------------------------------------------------------------------ */
/*  Markdown fetch + render                                           */
/* ------------------------------------------------------------------ */

/**
 * Path to the markdown file, relative to the web_client directory.
 * The file lives inside web_client/docs/client/ so it is reachable
 * from the static file server that serves web_client/ as its root.
 */
const HELP_MD_PATH = "docs/client/help-tool.md";

async function loadHelpContent() {
  if (!bodyEl) return;

  // Show loading state
  bodyEl.innerHTML = `<div class="help-loading">Loading…</div>`;

  try {
    const res = await fetch(HELP_MD_PATH, { cache: "no-cache" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const md = await res.text();
    cachedHtml = markdownToHtml(md);
    bodyEl.innerHTML = `<div class="help-content">${cachedHtml}</div>`;
  } catch (err) {
    console.warn("[help] Failed to load help content:", err);
    bodyEl.innerHTML = `<div class="help-error">${t("helpLoadError")}</div>`;
    // Don't cache the error so user can retry on next open
    cachedHtml = null;
  }
}

/* ------------------------------------------------------------------ */
/*  Initialization                                                    */
/* ------------------------------------------------------------------ */

function init() {
  // -- 1. Find the header to inject the help button --
  const header = document.querySelector(".app-header");
  if (!header) {
    console.warn("[help] .app-header not found, skipping help button.");
    return;
  }

  let headerEnd = header.querySelector(".app-header-end");
  if (!headerEnd) {
    headerEnd = el("div", "app-header-end");
    header.appendChild(headerEnd);
  }

  // -- 2. Create the help button --
  const btn = el("button", "help-btn", {
    type: "button",
    id: "btnHelp",
    title: t("helpBtnTitle"),
    "aria-label": t("helpBtnTitle"),
  });
  btn.textContent = "?";
  headerEnd.appendChild(btn);

  // -- 3. Find the app container to append overlay + modal --
  const app = document.querySelector(".app");
  if (!app) {
    console.warn("[help] .app container not found, skipping help modal.");
    return;
  }

  // -- 4. Create overlay --
  overlayEl = el("div", "help-overlay", { id: "helpOverlay" });
  app.appendChild(overlayEl);

  // -- 5. Create modal --
  modalEl = el("div", "help-modal", {
    id: "helpModal",
    role: "dialog",
    "aria-modal": "true",
    "aria-labelledby": "helpModalTitle",
  });

  // Modal header
  const modalHeader = el("div", "help-modal-header");
  const titleEl = el("h2", "help-modal-title", { id: "helpModalTitle" });
  titleEl.textContent = t("helpModalTitle");
  const closeBtn = el("button", "help-close-btn", {
    type: "button",
    "aria-label": t("helpCloseLabel"),
  });
  closeBtn.textContent = "✕";
  modalHeader.appendChild(titleEl);
  modalHeader.appendChild(closeBtn);
  modalEl.appendChild(modalHeader);

  // Modal body (scrollable content area)
  bodyEl = el("div", "help-modal-body");
  modalEl.appendChild(bodyEl);

  app.appendChild(modalEl);

  // -- 6. Event listeners --

  // Open on help button click
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    openHelp();
  });

  // Close on close button click
  closeBtn.addEventListener("click", () => {
    closeHelp();
  });

  // Close on overlay click
  overlayEl.addEventListener("click", () => {
    closeHelp();
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isHelpOpen()) {
      closeHelp();
    }
  });
}

/* ------------------------------------------------------------------ */
/*  Bootstrap — wait for DOM, then init inside a try/catch            */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
  try {
    init();
  } catch (err) {
    // Log but never let help initialization break the chatbot
    console.error("[help] Initialization failed:", err);
  }
});
