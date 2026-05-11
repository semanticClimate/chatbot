/**
 * Sample questions by language. UI shows one language at a time (select + chips).
 */

const STORAGE_KEY_EXAMPLE_LANG = "climate_web_client_example_lang";

export const EXAMPLE_LANGUAGES = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिन्दी" },
  { id: "fr", label: "Français" },
  { id: "pt", label: "Português" },
  { id: "es", label: "Español" },
];

export const EXAMPLES_BY_LANG = {
  en: [
    "What is the greenhouse effect?",
    "How does the book connect capitalism and ecological crisis?",
    "What is the difference between mitigation and adaptation?",
  ],
  hi: [
    "ग्रीनहाउस प्रभाव क्या है?",
    "पुस्तक पूंजीवाद और पारिस्थितिक संकट को कैसे जोड़ती है?",
    "निवारण और अनुकूलन में क्या अंतर है?",
  ],
  fr: [
    "Qu'est-ce que l'effet de serre ?",
    "Comment le livre relie-t-il capitalisme et crise écologique ?",
    "Quelle est la différence entre atténuation et adaptation ?",
  ],
  pt: [
    "O que é o efeito estufa?",
    "Como o livro liga capitalismo e crise ecológica?",
    "Qual é a diferença entre mitigação e adaptação?",
  ],
  es: [
    "¿Qué es el efecto invernadero?",
    "¿Cómo relaciona el libro capitalismo y crisis ecológica?",
    "¿Cuál es la diferencia entre mitigación y adaptación?",
  ],
};

function loadSavedExampleLang() {
  try {
    const v = localStorage.getItem(STORAGE_KEY_EXAMPLE_LANG);
    if (v && EXAMPLES_BY_LANG[v]) return v;
  } catch {
    /* ignore */
  }
  return "en";
}

function saveExampleLang(id) {
  try {
    localStorage.setItem(STORAGE_KEY_EXAMPLE_LANG, id);
  } catch {
    /* ignore */
  }
}

/**
 * @param {HTMLElement} chipsEl
 * @param {string} langId
 * @param {{ setQuestion: (q: string) => void }} hooks
 */
function fillChipsForLang(chipsEl, langId, hooks) {
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
 */
export function mountExampleQuestions(host, hooks) {
  host.innerHTML = "";
  host.className = "examples-mount";

  const det = document.createElement("details");
  det.className = "examples-details";

  const sum = document.createElement("summary");
  sum.className = "examples-details-summary";
  sum.textContent = "Sample questions";
  det.appendChild(sum);

  const inner = document.createElement("div");
  inner.className = "examples-details-body";

  const intro = document.createElement("p");
  intro.className = "examples-intro";
  intro.textContent =
    "Pick a language, then tap a line — replies match that language; the book stays in English.";
  inner.appendChild(intro);

  const pickerRow = document.createElement("div");
  pickerRow.className = "examples-picker-row";

  const lab = document.createElement("label");
  lab.className = "examples-lang-select-label";
  lab.htmlFor = "examplesLangSelect";
  lab.textContent = "Language";

  const sel = document.createElement("select");
  sel.id = "examplesLangSelect";
  sel.className = "examples-lang-select";
  sel.setAttribute("aria-label", "Language for sample questions");

  const initial = loadSavedExampleLang();
  for (const { id, label } of EXAMPLE_LANGUAGES) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = label;
    if (id === initial) opt.selected = true;
    sel.appendChild(opt);
  }

  pickerRow.appendChild(lab);
  pickerRow.appendChild(sel);
  inner.appendChild(pickerRow);

  const chips = document.createElement("div");
  chips.className = "examples-chips";
  inner.appendChild(chips);

  fillChipsForLang(chips, initial, hooks);

  sel.addEventListener("change", () => {
    const id = sel.value;
    saveExampleLang(id);
    fillChipsForLang(chips, id, hooks);
  });

  det.appendChild(inner);
  host.appendChild(det);
}
