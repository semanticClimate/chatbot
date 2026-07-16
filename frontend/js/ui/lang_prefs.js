/**
 * Chat / response language: fixed set, persisted for sample chips and POST /ask.
 */

export const STORAGE_KEY_CHAT_LANG = "climate_chat_language";
/** Migrates selections saved by older Sample-questions-only UI. */
export const STORAGE_KEY_LEGACY_EXAMPLE_LANG = "climate_web_client_example_lang";

export const CHAT_LANGUAGES = [
  { id: "en", label: "English" },
  { id: "fr", label: "Français" },
  { id: "es", label: "Español" },
  { id: "pt", label: "Português" },
  { id: "hi", label: "हिन्दी" },
];

/** @returns {typeof CHAT_LANGUAGES[number]["id"]} */
export function defaultChatLang() {
  return "en";
}

/** @returns {typeof CHAT_LANGUAGES[number]["id"]} */
export function normalizeChatLangId(raw) {
  const s = String(raw || "").toLowerCase().trim();
  if (CHAT_LANGUAGES.some((x) => x.id === s)) return /** @type {any} */ (s);
  return defaultChatLang();
}

/** @returns {typeof CHAT_LANGUAGES[number]["id"]} */
export function loadChatLanguage() {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY_CHAT_LANG);
    if (v) return normalizeChatLangId(v);
    const legacy = window.localStorage.getItem(STORAGE_KEY_LEGACY_EXAMPLE_LANG);
    if (legacy) return normalizeChatLangId(legacy);
  } catch {
    /* ignore */
  }
  return defaultChatLang();
}

/** @param {string} id */
export function saveChatLanguage(id) {
  const norm = normalizeChatLangId(id);
  try {
    window.localStorage.setItem(STORAGE_KEY_CHAT_LANG, norm);
  } catch {
    /* ignore */
  }
  return norm;
}
