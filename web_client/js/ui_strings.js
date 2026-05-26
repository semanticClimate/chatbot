/**
 * Client UI copy for en / fr / es / pt / hi. Chat language drives shell + status strings.
 */

import { normalizeChatLangId } from "./lang_prefs.js";

/** @type {string} */
let _lang = "en";

/** @param {string} code */
export function setUiLanguage(code) {
  _lang = normalizeChatLangId(code);
}

/** @returns {string} */
export function getUiLanguage() {
  return _lang;
}

/** @param {string} key
 * @param {Record<string, string | number>=} vars */
export function t(key, vars) {
  const row = STRINGS[_lang] || STRINGS.en;
  let s = row[key] ?? STRINGS.en[key] ?? key;
  if (vars) {
    for (const [vk, val] of Object.entries(vars)) {
      s = s.split(`{{${vk}}}`).join(String(val));
    }
  }
  return s;
}

/**
 * @param {string} lang
 * @returns {string} html `lang` attribute
 */
export function htmlLangFor(lang) {
  const c = normalizeChatLangId(lang);
  if (c === "hi") return "hi";
  return c;
}

/**
 * Apply `[data-i18n="key"]`, `title`, `placeholder`, `aria-label` from STRINGS.
 * @param {string} lang
 */
export function applyShellUiStrings(lang) {
  const code = normalizeChatLangId(lang);
  setUiLanguage(code);
  document.documentElement.lang = htmlLangFor(code);
  const row = STRINGS[code] || STRINGS.en;

  document.title = row.docTitle ?? STRINGS.en.docTitle;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key || !(key in STRINGS.en)) return;
    const text = t(key);
    if (
      el instanceof HTMLInputElement ||
      el instanceof HTMLTextAreaElement
    ) {
      if (el.hasAttribute("placeholder")) el.placeholder = text;
    } else {
      el.textContent = text;
    }
  });

  const q = document.getElementById("question");
  if (q && "placeholder" in q) {
    q.placeholder = t("placeholderQuestion");
  }

  const conv = document.getElementById("conversationPanel");
  if (conv) conv.setAttribute("aria-label", t("ariaConversation"));
  const ex = document.getElementById("examplesMount");
  if (ex) ex.setAttribute("aria-label", t("ariaSampleMount"));
  const sp = document.getElementById("sourcesPanel");
  if (sp) sp.setAttribute("aria-label", t("ariaSources"));
  const pb = document.getElementById("panelBookShell");
  if (pb) pb.setAttribute("aria-label", t("ariaStudentBook"));
  const bf = document.getElementById("bookFrame");
  if (bf) bf.setAttribute("title", t("bookIframeTitle"));
  const ef = document.getElementById("encyclopediaFrame");
  if (ef) ef.setAttribute("title", t("encyclopediaIframeTitle"));

  const ls = document.getElementById("chatLangSelect");
  if (ls instanceof HTMLSelectElement) {
    const prev = normalizeChatLangId(ls.value || "en");
    for (const opt of ls.querySelectorAll("option")) {
      const id = opt.value;
      const lk = `langName_${id}`;
      if (id && lk in STRINGS.en) {
        opt.textContent = t(lk);
      }
    }
    ls.value = prev;
  }
}

/** @type {Record<string, Record<string, string>>} */
const STRINGS = {
  en: {
    docTitle: "Climate Academy — chat",
    appTitle: "Climate Academy chat",
    appSubtitle: "Book-grounded answers via your API below.",
    labelChatLang: "Chat language",
    hintChatLang:
      "Answers use this language only. Ask in the same language. The Climate Academy student book stays in English.",
    labelApiUrl: "API base URL",
    placeholderApiUrl: "https://your-api.trycloudflare.com",
    btnHealth: "Check health",
    btnClear: "Clear chat",
    exportCsvSummary: "Export CSV…",
    btnExportChat: "Download chat",
    btnExportLogs: "Server logs",
    ariaConversation: "Conversation",
    srQuestionLabel: "Your question",
    placeholderQuestion: "Ask about the book…",
    btnSend: "Send",
    ariaSampleMount: "Sample questions",
    sourcesHeading: "Sources",
    settingsHeading: "Settings",
    queryHeading: "Query",
    sourcesHint: "Click a citation number on an answer.",
    ariaSources: "Sources",
    bookHeading: "Student book",
    btnResetBook: "Reset highlight",
    ariaStudentBook: "Student book",
    bookIframeTitle: "Climate Academy Student Book",
    encyclopediaHeading: "Encyclopedia",
    encyclopediaIframeTitle: "Climate Academy encyclopedia entry",
    sampleQuestionsSummary: "Sample questions",
    sampleQuestionsIntro:
      "Lines match Chat language above; book text stays English.",
    sourcesEmpty: "No source selected.",
    labelSourceId: "Source ID",
    labelSection: "Section",
    labelChunk: "Chunk",
    labelAnchor: "Anchor",
    labelPassage: "Passage",
    threadEmptyWelcome:
      "Choose chat language above, then ask in that language. Citations open the English book.",
    chipShowSource: "Show source",
    operatorDetails: "Operator details",
    errApiBaseInvalidSaved:
      "Saved API base was not a valid http(s) URL (for example a file path was pasted). Reset.",
    errTunnelNotFound:
      "tunnel-api-base.txt was not found — paste the API tunnel URL or reload.",
    errTunnelBaseNotFound:
      "Could not load tunnel-api-base.txt from this page. Paste the API tunnel URL or reload.",
    errUseFullUrl:
      "Use a full URL such as https://….trycloudflare.com (from start-quick-tunnel.sh) — not a log file path.",
    errSetApiFirst: "Set API base URL first.",
    nothingToExport: "Nothing to export yet.",
    preparingCsv: "Preparing CSV…",
    savedConversationCsv: "Saved conversation.csv",
    fetchingLogs: "Fetching logs…",
    savedLogsCsv: "Saved chatbot_logs.csv",
    checkingHealth: "Checking…",
    sending: "Sending…",
    chatCleared: "Chat cleared.",
    okMs: "OK — {{ms}} ms total",
    ok: "OK",
    labelHealth: "Health",
    labelReady: "Ready",
    langName_en: "English",
    langName_fr: "Français",
    langName_es: "Español",
    langName_pt: "Português",
    langName_hi: "हिन्दी",
    helpBtnTitle: "Help",
    helpModalTitle: "How to use this chatbot",
    helpCloseLabel: "Close help",
    helpLoadError: "Could not load help content. Please try again later.",
  },

  fr: {
    docTitle: "Climate Academy — chat",
    appTitle: "Chat Climate Academy",
    appSubtitle:
      "Réponses ancrées dans le livre, via votre URL d’API ci-dessous.",
    labelChatLang: "Langue du chat",
    hintChatLang:
      "Les réponses utilisent uniquement cette langue ; posez vos questions dans cette langue. Le manuel Climate Academy reste en anglais.",
    labelApiUrl: "URL de base de l’API",
    placeholderApiUrl: "https://your-api.trycloudflare.com",
    btnHealth: "Vérifier l’état",
    btnClear: "Effacer le chat",
    exportCsvSummary: "Exporter CSV…",
    btnExportChat: "Télécharger le chat",
    btnExportLogs: "Journaux serveur",
    ariaConversation: "Conversation",
    srQuestionLabel: "Votre question",
    placeholderQuestion: "Posez une question sur le livre…",
    btnSend: "Envoyer",
    ariaSampleMount: "Exemples de questions",
    sourcesHeading: "Sources",
    settingsHeading: "Paramètres",
    queryHeading: "Requête",
    sourcesHint: "Cliquez sur un numéro de citation dans une réponse.",
    ariaSources: "Sources",
    bookHeading: "Manuel étudiant",
    btnResetBook: "Réinitialiser le surlignage",
    ariaStudentBook: "Manuel étudiant",
    bookIframeTitle: "Manuel Climate Academy",
    encyclopediaHeading: "Encyclopédie",
    encyclopediaIframeTitle: "Entrée encyclopédie Climate Academy",
    sampleQuestionsSummary: "Exemples de questions",
    sampleQuestionsIntro:
      "Les lignes suivent la langue ci-dessus ; le livre reste en anglais.",
    sourcesEmpty: "Aucune source sélectionnée.",
    labelSourceId: "ID source",
    labelSection: "Section",
    labelChunk: "Fragment",
    labelAnchor: "Ancrage",
    labelPassage: "Extrait",
    threadEmptyWelcome:
      "Choisissez la langue ci-dessus, puis posez votre question dans cette langue. Les citations ouvrent le livre en anglais.",
    chipShowSource: "Afficher la source",
    operatorDetails: "Détails (opérateur)",
    errApiBaseInvalidSaved:
      "L’URL API enregistrée n’est pas une URL http(s) valide (p. ex. chemin fichier). Réinitialisée.",
    errTunnelNotFound:
      "tunnel-api-base.txt introuvable — collez l’URL tunnel de l’API ou rechargez la page.",
    errTunnelBaseNotFound:
      "Impossible de charger tunnel-api-base.txt. Collez l’URL tunnel de l’API ou rechargez.",
    errUseFullUrl:
      "Utilisez une URL complète (https://….trycloudflare.com), pas un chemin de fichier journal.",
    errSetApiFirst: "Indiquez d’abord l’URL de base de l’API.",
    nothingToExport: "Rien à exporter pour le moment.",
    preparingCsv: "Préparation du CSV…",
    savedConversationCsv: "Fichier conversation.csv enregistré",
    fetchingLogs: "Récupération des journaux…",
    savedLogsCsv: "Fichier chatbot_logs.csv enregistré",
    checkingHealth: "Vérification…",
    sending: "Envoi…",
    chatCleared: "Chat effacé.",
    okMs: "OK — {{ms}} ms au total",
    ok: "OK",
    labelHealth: "État",
    labelReady: "Prêt",
    langName_en: "Anglais",
    langName_fr: "Français",
    langName_es: "Espagnol",
    langName_pt: "Portugais",
    langName_hi: "Hindi",
    helpBtnTitle: "Aide",
    helpModalTitle: "Comment utiliser ce chatbot",
    helpCloseLabel: "Fermer l'aide",
    helpLoadError: "Impossible de charger le contenu d'aide. Réessayez plus tard.",
  },

  es: {
    docTitle: "Climate Academy — chat",
    appTitle: "Chat de Climate Academy",
    appSubtitle: "Respuestas basadas en el libro mediante la URL de la API.",
    labelChatLang: "Idioma del chat",
    hintChatLang:
      "Las respuestas solo usan este idioma ; pregunte en ese idioma. El libro del estudiante Climate Academy permanece en inglés.",
    labelApiUrl: "URL base de la API",
    placeholderApiUrl: "https://your-api.trycloudflare.com",
    btnHealth: "Comprobar estado",
    btnClear: "Borrar chat",
    exportCsvSummary: "Exportar CSV…",
    btnExportChat: "Descargar chat",
    btnExportLogs: "Registros del servidor",
    ariaConversation: "Conversación",
    srQuestionLabel: "Tu pregunta",
    placeholderQuestion: "Pregunta sobre el libro…",
    btnSend: "Enviar",
    ariaSampleMount: "Preguntas de ejemplo",
    sourcesHeading: "Fuentes",
    settingsHeading: "Configuración",
    queryHeading: "Consulta",
    sourcesHint: "Haz clic en un número de cita en una respuesta.",
    ariaSources: "Fuentes",
    bookHeading: "Libro del estudiante",
    btnResetBook: "Restablecer resaltado",
    ariaStudentBook: "Libro del estudiante",
    bookIframeTitle: "Libro Climate Academy",
    encyclopediaHeading: "Enciclopedia",
    encyclopediaIframeTitle: "Entrada de la enciclopedia Climate Academy",
    sampleQuestionsSummary: "Preguntas de ejemplo",
    sampleQuestionsIntro:
      "Las líneas coinciden con el idioma de arriba ; el libro sigue en inglés.",
    sourcesEmpty: "Ninguna fuente seleccionada.",
    labelSourceId: "ID de fuente",
    labelSection: "Sección",
    labelChunk: "Fragmento",
    labelAnchor: "Ancla",
    labelPassage: "Extracto",
    threadEmptyWelcome:
      "Elige el idioma arriba y pregunta en ese idioma. Las citas abren el libro en inglés.",
    chipShowSource: "Ver fuente",
    operatorDetails: "Detalles (operador)",
    errApiBaseInvalidSaved:
      "La API guardada no es una URL http(s) válida (p. ej. se pegó una ruta de archivo). Reiniciada.",
    errTunnelNotFound:
      "No se encontró tunnel-api-base.txt ; pega la URL del tunnel de la API o recarga.",
    errTunnelBaseNotFound:
      "No se pudo cargar tunnel-api-base.txt. Pega la URL del tunnel de la API o recarga.",
    errUseFullUrl:
      "Usa una URL completa (https://….trycloudflare.com), no una ruta de log.",
    errSetApiFirst: "Primero establece la URL base de la API.",
    nothingToExport: "Aún no hay nada que exportar.",
    preparingCsv: "Preparando CSV…",
    savedConversationCsv: "conversation.csv guardado",
    fetchingLogs: "Descargando registros…",
    savedLogsCsv: "chatbot_logs.csv guardado",
    checkingHealth: "Comprobando…",
    sending: "Enviando…",
    chatCleared: "Chat borrado.",
    okMs: "OK — {{ms}} ms en total",
    ok: "OK",
    labelHealth: "Estado",
    labelReady: "Listo",
    langName_en: "Inglés",
    langName_fr: "Francés",
    langName_es: "Español",
    langName_pt: "Portugués",
    langName_hi: "Hindi",
    helpBtnTitle: "Ayuda",
    helpModalTitle: "Cómo usar este chatbot",
    helpCloseLabel: "Cerrar ayuda",
    helpLoadError: "No se pudo cargar el contenido de ayuda. Inténtelo más tarde.",
  },

  pt: {
    docTitle: "Climate Academy — chat",
    appTitle: "Chat Climate Academy",
    appSubtitle: "Respostas baseadas no livro através do URL da API abaixo.",
    labelChatLang: "Idioma do chat",
    hintChatLang:
      "As respostas usam só este idioma ; faça perguntas nesse idioma. O manual Climate Academy continua em inglês.",
    labelApiUrl: "URL base da API",
    placeholderApiUrl: "https://your-api.trycloudflare.com",
    btnHealth: "Verificar estado",
    btnClear: "Limpar chat",
    exportCsvSummary: "Exportar CSV…",
    btnExportChat: "Descarregar conversa",
    btnExportLogs: "Registos do servidor",
    ariaConversation: "Conversa",
    srQuestionLabel: "A sua pergunta",
    placeholderQuestion: "Pergunte sobre o livro…",
    btnSend: "Enviar",
    ariaSampleMount: "Perguntas de exemplo",
    sourcesHeading: "Fontes",
    settingsHeading: "Configurações",
    queryHeading: "Consulta",
    sourcesHint: "Clique num número de cita numa resposta.",
    ariaSources: "Fontes",
    bookHeading: "Manual do aluno",
    btnResetBook: "Repor destaque",
    ariaStudentBook: "Manual do aluno",
    bookIframeTitle: "Manual Climate Academy",
    encyclopediaHeading: "Enciclopédia",
    encyclopediaIframeTitle: "Entrada da enciclopédia Climate Academy",
    sampleQuestionsSummary: "Perguntas de exemplo",
    sampleQuestionsIntro:
      "As linhas seguem o idioma acima ; o texto do livro continua em inglês.",
    sourcesEmpty: "Nenhuma fonte selecionada.",
    labelSourceId: "ID da fonte",
    labelSection: "Secção",
    labelChunk: "Fragmento",
    labelAnchor: "Âncora",
    labelPassage: "Trecho",
    threadEmptyWelcome:
      "Escolha o idioma acima e pergunte nesse idioma. As citações abrem o livro em inglês.",
    chipShowSource: "Mostrar fonte",
    operatorDetails: "Detalhes (operador)",
    errApiBaseInvalidSaved:
      "O URL da API guardado não é um http(s) válido (p. ex. colou-se um caminho de ficheiro). Reposto.",
    errTunnelNotFound:
      "tunnel-api-base.txt não encontrado — cole o URL do tunnel da API ou recarregue.",
    errTunnelBaseNotFound:
      "Não foi possível carregar tunnel-api-base.txt. Cole o URL do tunnel da API ou recarregue.",
    errUseFullUrl:
      "Use um URL completo (https://….trycloudflare.com), não um caminho de log.",
    errSetApiFirst: "Defina primeiro o URL base da API.",
    nothingToExport: "Ainda não há nada para exportar.",
    preparingCsv: "A preparar CSV…",
    savedConversationCsv: "conversation.csv guardado",
    fetchingLogs: "A obter registos…",
    savedLogsCsv: "chatbot_logs.csv guardado",
    checkingHealth: "A verificar…",
    sending: "A enviar…",
    chatCleared: "Chat limpo.",
    okMs: "OK — {{ms}} ms no total",
    ok: "OK",
    labelHealth: "Estado",
    labelReady: "Pronto",
    langName_en: "Inglês",
    langName_fr: "Francês",
    langName_es: "Espanhol",
    langName_pt: "Português",
    langName_hi: "Hindi",
    helpBtnTitle: "Ajuda",
    helpModalTitle: "Como usar este chatbot",
    helpCloseLabel: "Fechar ajuda",
    helpLoadError: "Não foi possível carregar o conteúdo de ajuda. Tente mais tarde.",
  },

  hi: {
    docTitle: "Climate Academy — चैट",
    appTitle: "Climate Academy चैट",
    appSubtitle: "आपके API के माध्यम से पुस्तक-आधारित उत्तर।",
    labelChatLang: "चैट की भाषा",
    hintChatLang:
      "उत्तर केवल इसी भाषा में होंगे; प्रश्न भी इसी भाषा में लिखें। Climate Academy पुस्तक अंग्रेज़ी में ही रहती है।",
    labelApiUrl: "API आधार URL",
    placeholderApiUrl: "https://your-api.trycloudflare.com",
    btnHealth: "स्वास्थ्य जाँचें",
    btnClear: "चैट साफ़ करें",
    exportCsvSummary: "CSV निर्यात…",
    btnExportChat: "चैट डाउनलोड",
    btnExportLogs: "सर्वर लॉग",
    ariaConversation: "बातचीत",
    srQuestionLabel: "आपका प्रश्न",
    placeholderQuestion: "पुस्तक के बारे में पूछें…",
    btnSend: "भेजें",
    ariaSampleMount: "नमूना प्रश्न",
    sourcesHeading: "स्रोत",
    settingsHeading: "सेटिंग्स",
    queryHeading: "चैट",
    sourcesHint: "उत्तर में उद्धरण संख्या पर क्लिक करें।",
    ariaSources: "स्रोत",
    bookHeading: "छात्र पुस्तक",
    btnResetBook: "हाइलाइट रीसेट",
    ariaStudentBook: "छात्र पुस्तक",
    bookIframeTitle: "Climate Academy छात्र पुस्तक",
    encyclopediaHeading: "विश्वकोश",
    encyclopediaIframeTitle: "Climate Academy विश्वकोश प्रविष्टि",
    sampleQuestionsSummary: "नमूना प्रश्न",
    sampleQuestionsIntro:
      "पंक्तियाँ ऊपर की भाषा से मेल खाती हैं; पुस्तक अंग्रेज़ी में रहती है।",
    sourcesEmpty: "कोई स्रोत चुना नहीं।",
    labelSourceId: "स्रोत ID",
    labelSection: "खंड",
    labelChunk: "खंड टुकड़ा",
    labelAnchor: "एंकर",
    labelPassage: "अनुच्छेद",
    threadEmptyWelcome:
      "ऊपर भाषा चुनें, फिर उसी भाषा में पूछें। उद्धरण अंग्रेज़ी पुस्तक खोलते हैं।",
    chipShowSource: "स्रोत दिखाएँ",
    operatorDetails: "ऑपरेटर विवरण",
    errApiBaseInvalidSaved:
      "सहेजा गया API आधार मान्य http(s) URL नहीं था (उदा. फाइल पथ चिपकाया गया)। रीसेट किया गया।",
    errTunnelNotFound:
      "tunnel-api-base.txt नहीं मिला — API टनल URL पेस्ट करें या पृष्ठ रीलोड करें।",
    errTunnelBaseNotFound:
      "इस पृष्ठ से tunnel-api-base.txt लोड नहीं हो सका। API टनल URL पेस्ट करें या रीलोड करें।",
    errUseFullUrl:
      "पूरा URL लिखें (जैसे https://….trycloudflare.com), लॉग फाइल पथ नहीं।",
    errSetApiFirst: "पहले API आधार URL सेट करें।",
    nothingToExport: "अभी निर्यात के लिए कुछ नहीं।",
    preparingCsv: "CSV तैयार हो रहा है…",
    fetchingLogs: "लॉग लाए जा रहे हैं…",
    savedConversationCsv: "conversation.csv सहेजा गया",
    savedLogsCsv: "chatbot_logs.csv सहेजा गया",
    checkingHealth: "जाँच हो रही है…",
    sending: "भेजा जा रहा है…",
    chatCleared: "चैट साफ़ हो गई।",
    okMs: "ठीक — कुल {{ms}} ms",
    ok: "ठीक",
    labelHealth: "स्वास्थ्य",
    labelReady: "तैयार",
    langName_en: "अंग्रेज़ी",
    langName_fr: "फ़्रांसिसी",
    langName_es: "स्पैनिश",
    langName_pt: "पुर्तगाली",
    langName_hi: "हिन्दी",
    helpBtnTitle: "सहायता",
    helpModalTitle: "इस चैटबॉट का उपयोग कैसे करें",
    helpCloseLabel: "सहायता बंद करें",
    helpLoadError: "सहायता सामग्री लोड नहीं हो सकी। कृपया बाद में पुनः प्रयास करें।",
  },
};