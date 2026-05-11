/**
 * Sample questions by language (mirrors former Streamlit sidebar examples; adds PT & ES).
 * Retrieval uses the same embedding model as the API; short climate-book-style questions.
 */

export const EXAMPLE_LANGUAGES = [
  { id: "en", label: "English" },
  { id: "hi", label: "हिन्दी" },
  { id: "fr", label: "Français" },
  { id: "pt", label: "Português" },
  { id: "es", label: "Español" },
];

/** @type {Record<string, string[]>} */
/** Short empty-thread hints (same languages as sample questions). */
export const EMPTY_THREAD_HINTS = [
  {
    label: "EN",
    text: "Ask in any language — answers follow your language. Citations jump to the English book.",
  },
  {
    label: "HI",
    text: "किसी भी भाषा में पूछें — उत्तर आपकी भाषा में होंगे। उद्धरण अंग्रेज़ी पुस्तक पर ले जाते हैं।",
  },
  {
    label: "FR",
    text: "Posez votre question dans la langue de votre choix — la réponse sera dans cette langue. Les sources renvoient au livre en anglais.",
  },
  {
    label: "PT",
    text: "Pergunte em qualquer idioma — a resposta segue o seu idioma. As citações abrem o livro em inglês.",
  },
  {
    label: "ES",
    text: "Pregunta en el idioma que quieras — la respuesta irá en ese idioma. Las citas enlazan con el libro en inglés.",
  },
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

/**
 * @param {HTMLElement} host
 * @param {{ setQuestion: (q: string) => void }} hooks
 */
export function mountExampleQuestions(host, hooks) {
  host.innerHTML = "";
  host.className = "examples-panel";

  const intro = document.createElement("p");
  intro.className = "examples-intro";
  intro.textContent =
    "Sample questions — the assistant answers in the same language you type (book sources are in English).";
  host.appendChild(intro);

  for (const { id, label } of EXAMPLE_LANGUAGES) {
    const row = document.createElement("div");
    row.className = "examples-lang-block";

    const h = document.createElement("div");
    h.className = "examples-lang-label";
    h.textContent = label;
    row.appendChild(h);

    const chips = document.createElement("div");
    chips.className = "examples-chips";
    const items = EXAMPLES_BY_LANG[id] || [];
    for (const q of items) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-secondary examples-chip";
      b.textContent = q;
      b.title = q;
      b.addEventListener("click", () => hooks.setQuestion(q));
      chips.appendChild(b);
    }
    row.appendChild(chips);
    host.appendChild(row);
  }
}
