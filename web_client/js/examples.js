/**
 * Sample questions; language list comes from lang_prefs (synced with Chat language in settings).
 */

import { EXAMPLES_BY_LANG } from "./examples_data.js";
import { loadChatLanguage } from "./lang_prefs.js";
import { t } from "./ui_strings.js";

/**
 * @param {HTMLElement} chipsEl
 * @param {string} langId
 * @param {{ setQuestion: (q: string) => void }} hooks
 */
export function fillChipsForLang(chipsEl, langId, hooks) {
  chipsEl.innerHTML = "";
  const items = EXAMPLES_BY_LANG[langId] || EXAMPLES_BY_LANG.en || [];
  for (const q of items) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn btn-secondary examples-chip";
    b.textContent = q;
    b.title = q;
    b.addEventListener("click", () => hooks.setQuestion(q));
    chipsEl.appendChild(b);
  }
}

/**
 * @param {HTMLElement} host
 * @param {{ setQuestion: (q: string) => void }} hooks
 * @returns {{ refill: () => void }}
 */
export function mountExampleQuestions(host, hooks) {
  host.innerHTML = "";
  host.className = "examples-mount";

  const det = document.createElement("details");
  det.className = "examples-details";

  const sum = document.createElement("summary");
  sum.className = "examples-details-summary";
  sum.textContent = t("sampleQuestionsSummary");
  det.appendChild(sum);

  const inner = document.createElement("div");
  inner.className = "examples-details-body";

  const intro = document.createElement("p");
  intro.className = "examples-intro";
  intro.textContent = t("sampleQuestionsIntro");

  const chips = document.createElement("div");
  chips.className = "examples-chips";

  inner.appendChild(intro);
  inner.appendChild(chips);
  det.appendChild(inner);
  host.appendChild(det);

  function refill() {
    sum.textContent = t("sampleQuestionsSummary");
    intro.textContent = t("sampleQuestionsIntro");
    fillChipsForLang(chips, loadChatLanguage(), hooks);
  }

  refill();
  return { refill };
}
