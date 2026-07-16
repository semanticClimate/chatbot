/**
 * DOM rendering only. Escapes text to avoid HTML injection from model output.
 */

import { t } from "./ui_strings.js";

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function formatLinesAsHtml(text) {
  return escapeHtml(String(text || "")).replace(/\n/g, "<br />");
}

/**
 * @param {HTMLElement} el
 * @param {object} source
 */
export function renderSourceDetail(el, source) {
  el.innerHTML = "";
  if (!source) {
    const p = document.createElement("p");
    p.className = "sources-empty";
    p.textContent = t("sourcesEmpty");
    el.appendChild(p);
    return;
  }

  const dl = document.createElement("dl");
  dl.className = "source-dl";

  function row(label, value) {
    if (value == null || value === "") return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.innerHTML = formatLinesAsHtml(String(value));
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  row(t("labelSourceId"), source.source_id);
  row(
    t("labelSection"),
    source.section_number
      ? `§ ${source.section_number} — ${source.section_title || ""}`
      : ""
  );
  row(t("labelChunk"), source.chunk_id);
  row(t("labelAnchor"), source.anchor_id);
  row(t("labelPassage"), source.document);
  el.appendChild(dl);
}

/**
 * @param {HTMLElement} threadEl
 * @param {object[]} messages
 * @param {(sourceId: number, sources: object[]) => void} onPickSource
 */
export function renderThread(threadEl, messages, onPickSource) {
  threadEl.innerHTML = "";

  if (!messages.length) {
    const wrap = document.createElement("div");
    wrap.className = "thread-empty-welcome";

    const title = document.createElement("h3");
    title.className = "empty-title";
    title.textContent = "Hi, I'm your Climate Academy AI Assistant";

    const subtitle = document.createElement("p");
    subtitle.className = "empty-subtitle";
    subtitle.textContent = "Ask me anything about the Climate Academy student book.";

    const desc = document.createElement("p");
    desc.className = "empty-desc";
    desc.textContent = "Every answer is grounded in the student book and includes numbered citation chips. Click a citation chip ([1] [2] [3]) to jump directly to the supporting source in the book.";

    wrap.appendChild(title);
    wrap.appendChild(subtitle);
    wrap.appendChild(desc);
    threadEl.appendChild(wrap);
    return;
  }

  for (const msg of messages) {
    if (msg.role === "user") {
      const row = document.createElement("div");
      row.className = "msg msg-user";
      const bubble = document.createElement("div");
      bubble.className = "bubble bubble-user";
      bubble.textContent = msg.content || "";
      row.appendChild(bubble);
      threadEl.appendChild(row);
      continue;
    }

    if (msg.role === "assistant") {
      const row = document.createElement("div");
      row.className = "msg msg-assistant";
      const wrap = document.createElement("div");
      wrap.className = "assistant-wrap";

      if (msg.isThinking) {
        const card = document.createElement("article");
        card.className = "card card-thinking";
        const body = document.createElement("div");
        body.className = "card-body";
        body.innerHTML = `<span class="thinking-text">${msg.content}</span><span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span>`;
        card.appendChild(body);
        wrap.appendChild(card);
        row.appendChild(wrap);
        threadEl.appendChild(row);
        continue;
      }

      const blocks = msg.blocks || [];
      if (!blocks.length && msg.content) {
        const card = document.createElement("article");
        card.className = "card";
        const body = document.createElement("div");
        body.className = "card-body";
        body.innerHTML = formatLinesAsHtml(msg.content);
        card.appendChild(body);
        wrap.appendChild(card);
        row.appendChild(wrap);
        threadEl.appendChild(row);
        continue;
      }

      const sources = msg.sources || [];

      for (let bi = 0; bi < blocks.length; bi++) {
        const b = blocks[bi];
        const card = document.createElement("article");
        card.className = "card";
        const body = document.createElement("div");
        body.className = "card-body";
        body.innerHTML = formatLinesAsHtml(b.text || "");
        card.appendChild(body);

        const cites = b.citations || [];
        if (cites.length) {
          const chips = document.createElement("div");
          chips.className = "chips";
          for (const sid of cites) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "chip";
            btn.textContent = String(sid);
            // Build a descriptive tooltip from the matching source metadata
            const src = sources.find(s => s.source_id === sid);
            let tip = "";
            if (src) {
              const label = src.source_label || src.label || src.title;
              const secNum = src.section_number;
              const secTitle = src.section_title;
              if (label) {
                tip = `Jump to ${label}`;
                if (secNum) {
                  tip += ` [§ ${secNum}`;
                  if (secTitle) tip += ` — ${secTitle}`;
                  tip += `]`;
                }
              } else if (secNum) {
                tip = `Jump to § ${secNum}`;
                if (secTitle) tip += ` — ${secTitle}`;
              }
            }
            btn.title = tip || t("chipShowSource");
            btn.addEventListener("click", () => onPickSource(sid, sources));
            chips.appendChild(btn);
          }
          card.appendChild(chips);
        }
        wrap.appendChild(card);
      }

      if (msg.operator_detail) {
        const det = document.createElement("details");
        det.className = "operator-details";
        const sum = document.createElement("summary");
        sum.textContent = t("operatorDetails");
        const pre = document.createElement("pre");
        pre.className = "operator-pre";
        pre.textContent = msg.operator_detail;
        det.appendChild(sum);
        det.appendChild(pre);
        wrap.appendChild(det);
      }

      row.appendChild(wrap);
      threadEl.appendChild(row);
    }
  }
}

/**
 * @param {HTMLElement} el
 * @param {string} text
 * @param {"info"|"error"} kind
 */
export function setStatus(el, text, kind = "info") {
  el.textContent = text || "";
  el.dataset.kind = kind;
}
